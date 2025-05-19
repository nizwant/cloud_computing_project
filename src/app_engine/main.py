from flask import Flask, render_template, redirect, url_for

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html", title="Home", count=5)


# @app.route("/about")
# def about():
#     return render_template("about.html", title="About")


@app.route("/add_song")
def about():
    return render_template("add-song.html")


@app.route("/increment", methods=["POST"])
def increment():
    return redirect(url_for("index"))
