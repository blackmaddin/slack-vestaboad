# Slack -> Vestaboard Bridge

Small Flask service that forwards Slack messages or web form input to the Vestaboard Subscription API.

## Features
- Slack Events endpoint with request verification
- Private web form endpoint
- CSRF protection for form submits
- Rate limiting
- Retries/timeouts for Vestaboard API calls
- Dockerized deployment behind Nginx

## Quick Start
1. Clone repo:
   - `git clone https://github.com/blackmaddin/slack-vestaboad.git`
   - `cd slack-vestaboad`
2. Create env file:
   - `cp .env.example .env`
   - Fill all required values.
3. Run:
   - `docker compose up -d --build`
4. Test:
   - `curl -sS http://127.0.0.1:8000/healthz`

## Production Notes
- Keep app bound to localhost (`127.0.0.1:8000`) and proxy through HTTPS (Nginx/Caddy).
- Do not commit `.env`.
- Use Slack Signing Secret (recommended) over verification token fallback.
- Rotate credentials if exposed.

## Built-in Hardening Toggles
The code already includes security controls that can be enabled/configured via `.env`:

- `SLACK_SIGNING_SECRET`:
  Enables Slack signature verification (`X-Slack-Signature`) with replay protection.
- `WEB_FORM_TOKEN_REQUIRED=true`:
  Requires an additional access code for web form submissions.
- `WEB_FORM_TOKEN`:
  Access code used when `WEB_FORM_TOKEN_REQUIRED=true`.
- `RATE_LIMIT_STORAGE_URI`:
  Configure rate-limit backend (default `memory://`; use Redis in larger deployments).
- `MAX_MESSAGE_LENGTH`:
  Caps accepted message length.
- `FLASK_SECRET_KEY`:
  Required for secure session/CSRF handling.

Recommended stricter setup:
- Set `SLACK_SIGNING_SECRET` (and remove fallback token usage).
- Set `WEB_FORM_TOKEN_REQUIRED=true` for shared/public links.
- Use Redis-backed limiter storage instead of in-memory defaults.

## Required Slack Setup
- Enable Event Subscriptions
- Request URL: `https://your-domain/slack/events`
- Subscribe to `message.channels` (or desired scopes/events)
- Install app to workspace

## License
MIT

Made with ❤️ in Neu-Ulm.
