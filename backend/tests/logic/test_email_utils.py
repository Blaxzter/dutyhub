"""Unit tests for the email utility helpers.

Nothing here touches the network: ``fm.send_message`` is always patched with an
``AsyncMock`` so no SMTP connection is ever opened.
"""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, PropertyMock, patch

import pytest
from fastapi_mail import MessageSchema, MessageType

from app.core.config import Settings, settings
from app.logic.utils import email_utils
from app.logic.utils.email_utils import (
    TEMPLATE_FOLDER,
    EmailData,
    generate_test_email,
    send_email,
    send_email_template,
)

TEST_EMAIL_TEMPLATE = TEMPLATE_FOLDER / "test_email.html"


def _sent_message(mock_send: AsyncMock) -> MessageSchema:
    """Return the MessageSchema handed to the patched ``fm.send_message``."""
    call = mock_send.await_args
    assert call is not None, "send_message was never awaited"
    message = call.args[0]
    assert isinstance(message, MessageSchema)
    return message


def _sole_recipient(message: MessageSchema) -> str:
    """Return the string form of the message's single recipient."""
    assert len(message.recipients) == 1
    return str(message.recipients[0])


def _payload(message: MessageSchema) -> dict[str, Any]:
    """Dump the message.

    ``MessageSchema.body`` and ``.template_body`` are declared as loose unions,
    so the dumped payload keeps the assertions readable and type-clean.
    """
    return message.model_dump()


class TestGenerateTestEmail:
    """Test suite for generate_test_email (pure Jinja2 template rendering)."""

    def test_template_folder_contains_test_email_template(self) -> None:
        """The shipped build folder must contain the rendered test template."""
        assert TEMPLATE_FOLDER.is_dir(), f"missing template folder {TEMPLATE_FOLDER}"
        assert TEST_EMAIL_TEMPLATE.is_file(), f"missing {TEST_EMAIL_TEMPLATE}"

    def test_returns_email_data_with_expected_subject(self) -> None:
        """The returned EmailData carries the project-scoped test subject."""
        email_data = generate_test_email("recipient@example.com")

        assert isinstance(email_data, EmailData)
        assert email_data.subject == f"{settings.PROJECT_NAME} - Test email"

    def test_html_content_is_non_empty(self) -> None:
        """Rendering the shipped template produces actual HTML."""
        email_data = generate_test_email("recipient@example.com")

        assert email_data.html_content != ""
        assert "<html" in email_data.html_content.lower()

    def test_html_content_contains_email_and_project_name(self) -> None:
        """Both Jinja2 variables are substituted into the rendered output."""
        email_data = generate_test_email("recipient@example.com")

        assert "recipient@example.com" in email_data.html_content
        assert settings.PROJECT_NAME in email_data.html_content

    def test_html_content_has_no_unrendered_placeholders(self) -> None:
        """No ``{{ ... }}`` placeholder survives rendering."""
        email_data = generate_test_email("recipient@example.com")

        assert "{{" not in email_data.html_content
        assert "}}" not in email_data.html_content

    def test_reads_template_from_template_folder(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The template is read from TEMPLATE_FOLDER at call time."""
        (tmp_path / "test_email.html").write_text(
            "<p>{{ project_name }} greets {{ email }}</p>", encoding="ascii"
        )
        monkeypatch.setattr(email_utils, "TEMPLATE_FOLDER", tmp_path)

        email_data = generate_test_email("someone@example.com")

        assert email_data.html_content == (
            f"<p>{settings.PROJECT_NAME} greets someone@example.com</p>"
        )
        assert email_data.subject == f"{settings.PROJECT_NAME} - Test email"

    def test_raises_when_template_is_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A missing template surfaces as a FileNotFoundError, not a silent pass."""
        monkeypatch.setattr(email_utils, "TEMPLATE_FOLDER", tmp_path)

        with pytest.raises(FileNotFoundError):
            generate_test_email("someone@example.com")


@pytest.mark.asyncio
class TestSendEmail:
    """Test suite for send_email."""

    @patch("app.logic.utils.email_utils.fm.send_message", new_callable=AsyncMock)
    @patch.object(Settings, "emails_configured", new_callable=PropertyMock)
    async def test_sends_message_with_expected_fields(
        self, mock_configured: PropertyMock, mock_send: AsyncMock
    ) -> None:
        """The message is built from the arguments and sent exactly once."""
        mock_configured.return_value = True

        await send_email(
            email_to="recipient@example.com",
            subject="Hello there",
            html_content="<p>Body</p>",
        )

        mock_send.assert_awaited_once()
        message = _sent_message(mock_send)
        assert message.subject == "Hello there"
        assert "recipient@example.com" in _sole_recipient(message)
        assert _payload(message)["body"] == "<p>Body</p>"
        assert message.subtype == MessageType.html

    @patch("app.logic.utils.email_utils.fm.send_message", new_callable=AsyncMock)
    @patch.object(Settings, "emails_configured", new_callable=PropertyMock)
    async def test_sends_message_without_template_name(
        self, mock_configured: PropertyMock, mock_send: AsyncMock
    ) -> None:
        """send_email sends a plain message, not a templated one."""
        mock_configured.return_value = True

        await send_email(email_to="recipient@example.com", subject="Subject")

        call = mock_send.await_args
        assert call is not None
        assert "template_name" not in call.kwargs
        assert len(call.args) == 1

    @patch("app.logic.utils.email_utils.fm.send_message", new_callable=AsyncMock)
    @patch.object(Settings, "emails_configured", new_callable=PropertyMock)
    async def test_defaults_to_empty_subject_and_body(
        self, mock_configured: PropertyMock, mock_send: AsyncMock
    ) -> None:
        """subject and html_content default to empty strings."""
        mock_configured.return_value = True

        await send_email(email_to="recipient@example.com")

        message = _sent_message(mock_send)
        assert message.subject == ""
        assert _payload(message)["body"] == ""

    @patch("app.logic.utils.email_utils.fm.send_message", new_callable=AsyncMock)
    @patch.object(Settings, "emails_configured", new_callable=PropertyMock)
    async def test_raises_when_emails_not_configured(
        self, mock_configured: PropertyMock, mock_send: AsyncMock
    ) -> None:
        """Without email settings the bare assert trips before anything is sent."""
        mock_configured.return_value = False

        with pytest.raises(AssertionError, match="no provided configuration"):
            await send_email(email_to="recipient@example.com", subject="Subject")

        mock_send.assert_not_awaited()


@pytest.mark.asyncio
class TestSendEmailTemplate:
    """Test suite for send_email_template."""

    @patch("app.logic.utils.email_utils.fm.send_message", new_callable=AsyncMock)
    @patch.object(Settings, "emails_configured", new_callable=PropertyMock)
    async def test_sends_message_with_template_name(
        self, mock_configured: PropertyMock, mock_send: AsyncMock
    ) -> None:
        """The template name is forwarded as a keyword argument."""
        mock_configured.return_value = True

        await send_email_template(
            email_to="recipient@example.com",
            subject="Welcome",
            template_name="welcome.html",
            template_body={"name": "Ada"},
        )

        mock_send.assert_awaited_once()
        call = mock_send.await_args
        assert call is not None
        assert call.kwargs["template_name"] == "welcome.html"

    @patch("app.logic.utils.email_utils.fm.send_message", new_callable=AsyncMock)
    @patch.object(Settings, "emails_configured", new_callable=PropertyMock)
    async def test_passes_template_body_through(
        self, mock_configured: PropertyMock, mock_send: AsyncMock
    ) -> None:
        """template_body reaches the MessageSchema untouched."""
        mock_configured.return_value = True
        template_body = {"name": "Ada", "link": "https://example.com"}

        await send_email_template(
            email_to="recipient@example.com",
            subject="Welcome",
            template_name="welcome.html",
            template_body=template_body,
        )

        message = _sent_message(mock_send)
        assert _payload(message)["template_body"] == template_body
        assert message.subject == "Welcome"
        assert "recipient@example.com" in _sole_recipient(message)
        assert message.subtype == MessageType.html

    @patch("app.logic.utils.email_utils.fm.send_message", new_callable=AsyncMock)
    @patch.object(Settings, "emails_configured", new_callable=PropertyMock)
    async def test_raises_when_emails_not_configured(
        self, mock_configured: PropertyMock, mock_send: AsyncMock
    ) -> None:
        """Without email settings the bare assert trips before anything is sent."""
        mock_configured.return_value = False

        with pytest.raises(AssertionError, match="no provided configuration"):
            await send_email_template(
                email_to="recipient@example.com",
                subject="Welcome",
                template_name="welcome.html",
                template_body={"name": "Ada"},
            )

        mock_send.assert_not_awaited()
