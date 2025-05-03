from flask import Flask, request
import base64
import json
from video_handler import handle_youtube_url

app = Flask(__name__)


@app.route("/", methods=["POST"])
def pubsub_handler():
    envelope = request.get_json()

    if not envelope or "message" not in envelope:
        return "Bad Request: no Pub/Sub message received", 400

    pubsub_message = envelope["message"]
    data = base64.b64decode(pubsub_message.get("data", "")).decode("utf-8")

    try:
        message = json.loads(data)
        youtube_url = message.get("url")
        if not youtube_url:
            return "Missing YouTube URL", 400

        handle_youtube_url(youtube_url)
        return "OK", 200

    except Exception as e:
        print(f"Error: {e}")
        return "Internal Server Error", 500
