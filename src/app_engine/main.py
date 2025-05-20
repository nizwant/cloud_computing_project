from flask import Flask, render_template
import logging

from utils_misc import format_duration_ms, get_release_year
from utils_db import list_tracks_helper

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
app.logger.setLevel(logging.INFO)

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


# --- Helper for Jinja2 template to access utility functions ---
@app.context_processor
def utility_processor():
    return dict(
        format_duration_ms=format_duration_ms, get_release_year=get_release_year
    )
