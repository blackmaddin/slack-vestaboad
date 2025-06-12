import os
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

VB_API_KEY = os.environ.get("VESTABOARD_API_KEY")
VB_SUB_ID = os.environ.get("VESTABOARD_SUBSCRIBER_ID")

def format_to_vestaboard(text):
    padded = text.ljust(132)[:132]
    ascii_codes = [ord(c) for c in padded]
    return [ascii_codes[i:i+22] for i in range(0, 132, 22)]

@app.route("/slack/events", methods=["POST"])
def slack_events():
    data = request.json
    event = data.get("event", {})
    if event.get("type") == "message" and not event.get("bot_id"):
        message = event.get("text", "")
        vb_url = f"https://rw.vestaboard.com/subscriptions/{VB_SUB_ID}/message"
        headers = {
            "X-Vestaboard-Api-Key": VB_API_KEY,
            "Content-Type": "application/json"
        }
        requests.post(vb_url, json=format_to_vestaboard(message), headers=headers)
    return jsonify({"ok": True})

@app.route("/")
def hello():
    return "Vestaboard-Bot läuft!", 200
