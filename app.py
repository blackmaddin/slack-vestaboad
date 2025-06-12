from flask import Flask, request, jsonify
import os
import requests

app = Flask(__name__)

VB_API_KEY = os.environ.get("VESTABOARD_API_KEY")
VB_API_SECRET = os.environ.get("VESTABOARD_API_SECRET")
VB_SUBSCRIPTION_ID = os.environ.get("VESTABOARD_SUBSCRIPTION_ID")

@app.route("/slack/events", methods=["POST"])
def slack_events():
    data = request.get_json()

    # 👇 Slack-Challenge beantworten (für URL-Verifizierung)
    if data.get("type") == "url_verification":
        return data["challenge"], 200, {'Content-Type': 'text/plain'}

    # 👇 Slack Message Event verarbeiten
    event = data.get("event", {})
    if event.get("type") == "message" and not event.get("bot_id"):
        message = event.get("text", "")
        headers = {
            "x-vestaboard-api-key": VB_API_KEY,
            "x-vestaboard-api-secret": VB_API_SECRET,
            "Content-Type": "application/json"
        }
        payload = {"text": message}
        url = f"https://subscriptions.vestaboard.com/subscriptions/{VB_SUBSCRIPTION_ID}/message"
        requests.post(url, json=payload, headers=headers)

    return jsonify({"ok": True}), 200
