import tempfile
import os
from flask import jsonify

from abracadabra.recognize import recognize_song


# The most important function in this project!!!
def add(a, b):
    return a + b


def recognize_http(request):
    if request.method != "POST":
        return jsonify({"error": "Method not allowed. Use POST."}), 405

    audio_file = request.files.get("audio_file")
    if not audio_file:
        return jsonify({"error": "No file uploaded"}), 400

    filename = audio_file.filename
    ext = os.path.splitext(filename)[1].lower()

    with tempfile.NamedTemporaryFile(suffix=ext, delete=True) as temp_file:
        audio_file.save(temp_file.name)
        result = recognize_song(temp_file.name)

    if result is None:
        return jsonify({"match": None})

    return jsonify({"match": result})
