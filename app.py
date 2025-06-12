@app.route("/slack/events", methods=["POST"])
def slack_events():
    data = request.get_json()

    # 💡 Handle Slack's URL verification challenge
    if data.get("type") == "url_verification":
        challenge = data.get("challenge")
        return challenge, 200, {'Content-Type': 'text/plain'}

    # 💬 Handle regular Slack message events
    event = data.get("event", {})
    if event.get("type") == "message" and not event.get("bot_id"):
        message = event.get("text", "")
        print(f"Nachricht empfangen: {message}")

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
            print(f"Fehler beim Senden an Vestaboard: {e}")

    return jsonify({"status": "ok"}), 200
