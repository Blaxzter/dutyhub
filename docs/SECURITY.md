# Security Policy

Security is very important for this project. 🔒

Learn more about it below. 👇

## Authentication & Security Architecture

This project authenticates people itself, against its own database. There is no
third-party identity provider. `docs/AUTH.md` is the full description; the
security-relevant properties are:

-   **Split credentials** — a stateless HS256 access token that lives 15 minutes
    and is held in memory by the browser, plus an opaque refresh token that lives
    in an `httpOnly`, host-only, path-scoped cookie. JavaScript can never read
    the long-lived half.
-   **Passwords** — bcrypt with a per-hash salt, verified in constant time.
    Plaintext is never stored or logged.
-   **Tokens at rest are hashed** — refresh tokens and the email-borne
    verification and reset links are stored only as SHA-256 digests, so a leaked
    database dump hands out no live sessions and no live links.
-   **Rotation with reuse detection** — every refresh replaces the token.
    Presenting one that has already been spent is treated as theft and revokes
    every session that account owns.
-   **Revocation** — sessions are rows. Signing a device out, changing a
    password or resetting one takes effect immediately, not when a JWT lapses.
-   **Rate limiting** on login, registration, password reset and verification
    resends, keyed so that no caller can lock another account out.

### How Security Works

1. **Sign-in**: the Vue frontend posts credentials to `POST /api/v1/auth/login`;
   the backend verifies the bcrypt hash and issues the token pair.
2. **API protection**: every protected endpoint resolves the caller through the
   dependency aliases in `backend/app/api/deps.py`, which verify the access
   token's HS256 signature and expiry locally and load the user row by primary
   key.
3. **Session renewal**: `POST /api/v1/auth/refresh` exchanges the cookie for a
   fresh access token and a rotated cookie. Nothing else on the API is sent the
   cookie.
4. **Authorisation**: permissions are **per event**, decided against
   `EventMembership` rows by `backend/app/logic/permissions.py`. The one global
   role is `admin`, the platform superadmin. No permission is carried in a token,
   so a revoked role takes effect on the next request.
5. **Secure communication**: all traffic uses HTTPS in deployed environments, and
   the refresh cookie is marked `Secure` everywhere except local development.

### Operational notes

-   `SECRET_KEY` signs the access tokens. Every environment other than local
    refuses to start while it still reads `changethis`. Rotating it invalidates
    outstanding access tokens (at most 15 minutes of disruption) and leaves
    refresh cookies working.
-   The `X-Test-User-Email` impersonation header used by the E2E suite is
    reachable only while `TESTING` is true, and the configuration layer refuses
    to construct settings with `TESTING` on in production.

## Versions

The latest version or release is supported.

You are encouraged to write tests for your application and update your versions frequently after ensuring that your tests are passing. This way you will benefit from the latest features, bug fixes, and **security fixes**.

## Reporting a Vulnerability

If you think you found a vulnerability, and even if you are not sure about it, please report it right away by creating a security issue at: https://github.com/Blaxzter/fastapi-vue-fullstack-template/issues

Please try to be as explicit as possible, describing all the steps and example code to reproduce the security issue. When creating the issue, please label it with "security" and mark it as confidential if the platform supports it.

I ([@Blaxzter](https://github.com/Blaxzter)) will review it thoroughly and get back to you.

## Public Discussions

Please restrain from publicly discussing a potential security vulnerability. 🙊

It's better to discuss privately and try to find a solution first, to limit the potential impact as much as possible.

---

Thanks for your help!

The community and I thank you for that. 🙇
