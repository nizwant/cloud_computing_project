from flask import Flask, render_template, redirect, url_for

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html", title="Home", count=5)


@app.route("/about")
def about():
    return render_template("about.html", title="About")


@app.route("/add_song")
def add_song():
    return render_template("add_song.html")


@app.route("/list_songs")
def list_songs():
    return render_template("list_songs.html")


# @app.route("/increment", methods=["POST"])
# def increment():
#     return redirect(url_for("index"))
