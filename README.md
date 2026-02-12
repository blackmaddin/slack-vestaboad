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

## Required Slack Setup
- Enable Event Subscriptions
- Request URL: `https://your-domain/slack/events`
- Subscribe to `message.channels` (or desired scopes/events)
- Install app to workspace

## License
MIT

Made with ❤️ in Neu-Ulm.
