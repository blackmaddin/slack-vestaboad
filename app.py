from flask import Flask, request, jsonify, render_template, redirect, abort, session, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import os
import requests
import logging
import hashlib
import hmac
import secrets
import time

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True  # damit Templates automatisch neu geladen werden
load_dotenv()
RATE_LIMIT_STORAGE_URI = os.environ.get("RATE_LIMIT_STORAGE_URI", "memory://")

# 🔐 Rate Limiter initialisieren
limiter = Limiter(key_func=get_remote_address, storage_uri=RATE_LIMIT_STORAGE_URI)
limiter.init_app(app)

# 🔑 API Keys aus Umgebungsvariablen
VB_API_KEY = os.environ.get("VESTABOARD_API_KEY")
VB_API_SECRET = os.environ.get("VESTABOARD_API_SECRET")
VB_SUBSCRIPTION_ID = os.environ.get("VESTABOARD_SUBSCRIPTION_ID")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")
SLACK_VERIFICATION_TOKEN = os.environ.get("SLACK_VERIFICATION_TOKEN")
WEB_SECRET_PATH = os.environ.get("WEB_SECRET_PATH")
WEB_FORM_TOKEN = os.environ.get("WEB_FORM_TOKEN")
FLASK_SECRET_KEY = os.environ.get("FLASK_SECRET_KEY")
MAX_MESSAGE_LENGTH = int(os.environ.get("MAX_MESSAGE_LENGTH", "200"))
WEB_FORM_TOKEN_REQUIRED = os.environ.get("WEB_FORM_TOKEN_REQUIRED", "false").lower() in ("1", "true", "yes", "on")

if not (VB_API_KEY and VB_API_SECRET and VB_SUBSCRIPTION_ID):
    raise RuntimeError("Missing Vestaboard credentials in environment.")
if not WEB_SECRET_PATH:
    raise RuntimeError("Missing WEB_SECRET_PATH in environment.")
if WEB_FORM_TOKEN_REQUIRED and not WEB_FORM_TOKEN:
    raise RuntimeError("Missing WEB_FORM_TOKEN in environment.")
if not FLASK_SECRET_KEY:
    raise RuntimeError("Missing FLASK_SECRET_KEY in environment.")

app.secret_key = FLASK_SECRET_KEY

# 📦 Logging
logging.basicConfig(level=logging.INFO)
app.logger.setLevel(logging.INFO)

vesta_session = requests.Session()
retry_strategy = Retry(
    total=3,
    connect=3,
    read=3,
    backoff_factor=0.5,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=frozenset(["POST"]),
)
adapter = HTTPAdapter(max_retries=retry_strategy)
vesta_session.mount("https://", adapter)


def has_valid_slack_auth(raw_body, parsed_json):
    ts = request.headers.get("X-Slack-Request-Timestamp", "")
    sig = request.headers.get("X-Slack-Signature", "")

    if SLACK_SIGNING_SECRET:
        try:
            ts_int = int(ts)
        except ValueError:
            return False

        # Protect against replay attacks.
        if abs(int(time.time()) - ts_int) > 300:
            return False

        base = f"v0:{ts}:{raw_body.decode('utf-8')}".encode("utf-8")
        expected = "v0=" + hmac.new(
            SLACK_SIGNING_SECRET.encode("utf-8"),
            base,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, sig)

    if SLACK_VERIFICATION_TOKEN:
        return hmac.compare_digest(
            str(parsed_json.get("token", "")),
            SLACK_VERIFICATION_TOKEN,
        )

    app.logger.error("Slack auth misconfigured: no signing secret or verification token set.")
    return False


def normalize_message(value):
    message = (value or "").strip()
    if not message:
        return None
    if len(message) > MAX_MESSAGE_LENGTH:
        return None
    return message


def post_to_vestaboard(message):
    url = f"https://subscriptions.vestaboard.com/subscriptions/{VB_SUBSCRIPTION_ID}/message"
    headers = {
        "x-vestaboard-api-key": VB_API_KEY,
        "x-vestaboard-api-secret": VB_API_SECRET,
        "Content-Type": "application/json",
    }
    payload = {"text": message}
    response = vesta_session.post(url, json=payload, headers=headers, timeout=(3.05, 10))
    response.raise_for_status()
    return response


def ensure_csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


@app.after_request
def add_security_headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    return resp

@app.route("/slack/events", methods=["POST"])
@limiter.limit("30 per minute")
def slack_events():
    raw_body = request.get_data(cache=True)
    data = request.get_json(silent=True) or {}

    if not has_valid_slack_auth(raw_body, data):
        app.logger.warning("Rejected unauthenticated Slack request from %s", request.remote_addr)
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    if data.get("type") == "url_verification":
        return data["challenge"], 200, {'Content-Type': 'text/plain'}

    event = data.get("event", {})
    if (
        event.get("type") == "message"
        and not event.get("bot_id")
        and not event.get("subtype")
    ):
        message = normalize_message(event.get("text", ""))
        if not message:
            app.logger.info(
                "Slack message ignored (invalid length/content) event_id=%s channel=%s",
                data.get("event_id"),
                event.get("channel"),
            )
            return jsonify({"ok": True}), 200

        # Nachricht an Vestaboard
        try:
            post_to_vestaboard(message)
            app.logger.info(
                "Slack message forwarded event_id=%s channel=%s len=%d",
                data.get("event_id"),
                event.get("channel"),
                len(message),
            )
        except Exception as e:
            app.logger.error("Vestaboard send failed for Slack event_id=%s: %s", data.get("event_id"), e)

    return jsonify({"ok": True}), 200

@app.route("/")
def index():
    return "Bot running", 200


@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"}), 200

# 📄 Formular anzeigen
@app.route(f"/p/{WEB_SECRET_PATH}", methods=["GET"])
def post_form():
    csrf_token = ensure_csrf_token()
    return render_template(
        "post.html",
        csrf_token=csrf_token,
        action_url=url_for("post_submit"),
        require_access_token=WEB_FORM_TOKEN_REQUIRED,
        error=None,
    )

# 📤 Formular absenden
@app.route(f"/p/{WEB_SECRET_PATH}/submit", methods=["POST"])
@limiter.limit("5 per minute")
def post_submit():
    csrf_in = request.form.get("csrf_token", "")
    csrf_expected = session.get("csrf_token", "")
    if not csrf_expected or not hmac.compare_digest(csrf_in, csrf_expected):
        abort(403)

    if WEB_FORM_TOKEN_REQUIRED:
        form_token = request.form.get("access_token", "")
        if not hmac.compare_digest(form_token, WEB_FORM_TOKEN):
            csrf_token = ensure_csrf_token()
            return (
                render_template(
                    "post.html",
                    csrf_token=csrf_token,
                    action_url=url_for("post_submit"),
                    require_access_token=WEB_FORM_TOKEN_REQUIRED,
                    error="Access code invalid.",
                ),
                403,
            )

    message = normalize_message(request.form.get("message", ""))
    if not message:
        csrf_token = ensure_csrf_token()
        return (
            render_template(
                "post.html",
                csrf_token=csrf_token,
                action_url=url_for("post_submit"),
                require_access_token=WEB_FORM_TOKEN_REQUIRED,
                error=f"Message required and must be <= {MAX_MESSAGE_LENGTH} characters.",
            ),
            400,
        )

    try:
        post_to_vestaboard(message)
        app.logger.info("Web message forwarded ip=%s len=%d", request.remote_addr, len(message))
    except Exception as e:
        app.logger.error("Vestaboard send failed for web request ip=%s: %s", request.remote_addr, e)
        csrf_token = ensure_csrf_token()
        return (
            render_template(
                "post.html",
                csrf_token=csrf_token,
                action_url=url_for("post_submit"),
                require_access_token=WEB_FORM_TOKEN_REQUIRED,
                error="Send failed. Please try again.",
            ),
            502,
        )

    return redirect(f"/p/{WEB_SECRET_PATH}")

# 🧪 Nur lokal starten – bei Deployment über Gunicorn NICHT nötig
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
