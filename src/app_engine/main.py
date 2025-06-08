from flask import Flask, render_template, request, jsonify, redirect, url_for
import logging
import json
from google.cloud import pubsub_v1

import sys
import os

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src"))
)

from app_engine.utils_misc import format_duration_ms, get_release_year
from app_engine.utils_db import list_tracks_helper, check_if_song_exists

from io import BytesIO
from abracadabra.recognize import recognize_song

app = Flask(__name__)


@app.template_filter("from_json")
def from_json(value):
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        try:
            # Handle the case where the string uses single quotes
            return eval(value)
        except Exception as e:
            return {"error": str(e)}


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
app.logger.setLevel(logging.INFO)

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path("cloud-computing-project-458205", "songs-to-process")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/add_song")
def add_song():
    return render_template("add_song.html")


@app.route("/list_songs/")
def list_songs():
    return list_tracks_helper(app=app)


@app.route("/push_to_pub_sub", methods=["POST"])
def push_to_pub_sub():
    data = request.get_json()
    title = data.get("title")
    artist = data.get("artist")
    check = check_if_song_exists(app, title=title, artist=artist)

    if check["status"] == "success":
        message_json = json.dumps(data)
        publisher.publish(topic_path, message_json.encode("utf-8"))
    return jsonify(check), 200


# @app.route("/identify", methods=["POST"])
# def identify():
#     audio_file = request.files.get("audio_file")
#     if not audio_file:
#         return jsonify({"error": "No file uploaded"}), 400
#
#     # Extract original file extension for pydub
#     filename = audio_file.filename
#     ext = os.path.splitext(filename)[1].lower()  # e.g. '.mp3', '.wav'
#
#     # Create a temporary file with the original extension
#     with tempfile.NamedTemporaryFile(suffix=ext, delete=True) as temp_file:
#         audio_file.save(temp_file.name)
#
#         # Call your recognize_song function on this temp file
#         result = recognize_song(temp_file.name)
#
#     if result is None:
#         return redirect(url_for("result", match="No match found"))
#
#     # If result is a dict, convert to string or jsonify
#     match_str = str(result)  # or json.dumps(result) if needed
#
#     return redirect(url_for("result", match=match_str))


@app.route("/identify", methods=["POST"])
def identify():
    audio_file = request.files.get("audio_file")
    if not audio_file:
        return jsonify({"error": "No file uploaded"}), 400

    audio_buffer = BytesIO(audio_file.read())

    result = recognize_song(audio_buffer, db_type="gcp")

    if result is None:
        return redirect(url_for("result", match="No match found"))

    match_str = str(result)
    return redirect(url_for("result", match=match_str))


@app.route("/result")
def result():
    # Expecting match info passed as query parameters or via session/POST
    match = request.args.get("match")  # e.g. JSON string or simple text
    return render_template("result.html", match=match)


# --- Helper for Jinja2 template to access utility functions ---
@app.context_processor
def utility_processor():
    return dict(
        format_duration_ms=format_duration_ms, get_release_year=get_release_year
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)