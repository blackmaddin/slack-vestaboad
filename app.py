import os
from flask import Flask, request, jsonify
import requests
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

VB_API_KEY = os.environ.get("VESTABOARD_API_KEY")
VB_API_SECRET = os.environ.get("VESTABOARD_API_SECRET")
VB_SUBSCRIPTION_ID = os.environ.get("VESTABOARD_SUBSCRIPTION_ID")

@app.route("/slack/events", methods=["POST"])
def slack_events():
    data = request.json
    event = data.get("event", {})

    if event.get("type") == "message" and not event.get("bot_id"):
        message = event.get("text", "")
        print(f"Empfangene Slack-Nachricht: {message}")

        headers = {
            "x-vestaboard-api-key": VB_API_KEY,
            "x-vestaboard-api-secret": VB_API_SECRET,
            "Content-Type": "application/json"
        }

        payload = {"text": message}
        url = f"https://subscriptions.vestaboard.com/subscriptions/{VB_SUBSCRIPTION_ID}/message"

        try:
            response = requests.post(url, json=payload, headers=headers)
            print(f"Vestaboard Antwort: {response.status_code}")
        except Exception as e:
            print(f"Fehler: {e}")

    return jsonify({"status": "ok"}), 200

@app.route("/")
def home():
    return "Slack → Vestaboard Forwarder läuft!", 200

