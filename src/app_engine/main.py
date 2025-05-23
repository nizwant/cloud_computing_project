from flask import Flask, render_template, request, jsonify
import logging
import json
from google.cloud import pubsub_v1

from utils_misc import format_duration_ms, get_release_year
from utils_db import list_tracks_helper, check_if_song_exists

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
app.logger.setLevel(logging.INFO)

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path("cloud-computing-project-458205", "songs-to-process")
# --- Parameters ---
ITEMS_PER_PAGE = 10  # Number of tracks to display per page


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
    return list_tracks_helper(app=app, items_per_page=ITEMS_PER_PAGE)


@app.route("/push_to_pub_sub", methods=["POST"])
def push_to_pub_sub():
    data = request.get_json()

    title = data.get("title")
    artist = data.get("artist")

    check = check_if_song_exists(app, title=title, artist=artist)

    if check["status"] == "success":
        message_json = json.dumps(data)
        future = publisher.publish(topic_path, message_json.encode("utf-8"))
    return jsonify(check), 200


# --- Helper for Jinja2 template to access utility functions ---
@app.context_processor
def utility_processor():
    return dict(
        format_duration_ms=format_duration_ms, get_release_year=get_release_year
    )
