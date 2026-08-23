"""The password policy, and the only supported way to turn a password into a hash.

The rules themselves are two lines long. What earns this module a file of its
own is that the rules are enforced in *three* places that must agree:

* ``app.schemas.auth._validate_password`` runs at the request boundary, so a
  short password comes back as a 422 field error the registration form can
  render next to the input;
* ``validate_password_strength`` below runs in the flow layer, so a password
  that reached the service by some other route (a future admin endpoint, a
  seed script, a test) is refused with the ``auth.weak_password`` code the
  frontend translates rather than a bare 500; and
* ``app.core.security.hash_password`` raises ``ValueError`` on anything over
  bcrypt's 72-byte ceiling, which is the backstop none of the above may reach.

Three checks of the same rule look redundant until one of them is missing: the
schema cannot cover a non-HTTP caller, the flow layer cannot produce a nice
per-field error, and the primitive can only raise. ``hash_new_password`` exists
so no caller has to remember which of the three it is standing in front of —
every password this application ever stores goes through it.
"""

from __future__ import annotations

from app.core.config import settings
from app.core.errors import raise_problem

# Imported rather than restated: 72 is a property of bcrypt, and a fourth copy
# of the number in this codebase is a fourth place to forget to change. The
# *lower* bound is the opposite — it is policy, so it lives in settings where a
# deployment can raise it.
from app.core.security import MAX_PASSWORD_BYTES, hash_password


def password_policy_violation(password: str) -> str | None:
    """Return why this password is unacceptable, or ``None`` if it is fine.

    Both bounds are real. The lower one is policy. The upper one is bcrypt's,
    and it counts **bytes**: this project ships a German locale, every umlaut
    costs two of them, and "Sträußchen-Passphrase…" runs out of room a dozen
    characters earlier than its English equivalent. Measuring characters here
    would let a password through that ``hash_password`` then refuses.

    Note what is deliberately *not* checked: no character-class requirement, no
    dictionary lookup, no maximum age. Those rules push people towards
    "Passw0rd!" and a sticky note; length is the one input that reliably buys
    entropy.
    """
    if len(password) < settings.PASSWORD_MIN_LENGTH:
        return (
            f"Your password must be at least {settings.PASSWORD_MIN_LENGTH} "
            "characters long."
        )
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        return (
            f"Your password may be at most {MAX_PASSWORD_BYTES} bytes long. "
            "Accented and non-Latin characters count as more than one."
        )
    return None


def validate_password_strength(password: str) -> None:
    """Raise ``auth.weak_password`` unless the password satisfies the policy.

    422 rather than 400: this is a field-level complaint about the body that
    was sent, which is exactly what the surrounding validation errors are, and
    the frontend already renders a 422 next to the offending input.
    """
    violation = password_policy_violation(password)
    if violation is not None:
        raise_problem(422, code="auth.weak_password", detail=violation)


def hash_new_password(password: str) -> str:
    """Validate a password against the policy and return its bcrypt hash.

    The single entry point for *setting* a password — registration, reset and
    change all go through here. Calling ``core.security.hash_password``
    directly skips the policy and, worse, turns an over-long password into an
    unhandled ``ValueError`` (a 500) instead of a field error, so don't.

    Callers should invoke this **before** any irreversible step in the flow: a
    weak password must not consume the one-time reset token that the user would
    then have to request all over again.
    """
    validate_password_strength(password)
    return hash_password(password)
