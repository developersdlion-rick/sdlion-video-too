"""
Simple web app: dealer enters Name + Shop Name -> gets back a personalized
video.

Run:
    export ELEVENLABS_API_KEY=sk_xxx
    python app.py
Then open http://localhost:5000
"""
import os
import traceback

from flask import Flask, render_template, request, send_file, jsonify

import config
from video_pipeline import build_personalized_video
from tts import TTSError
from sarvam_tts import SarvamTTSError

TTS_ERRORS = (TTSError, SarvamTTSError)

app = Flask(__name__)

# Make sure these exist no matter how the app is started (python app.py
# locally, or gunicorn in production) -- gunicorn never runs the
# `if __name__ == "__main__":` block below.
os.makedirs(config.OUTPUT_DIR, exist_ok=True)
os.makedirs(config.TEMP_DIR, exist_ok=True)


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    name = request.form.get("name", "").strip()
    shop = request.form.get("shop", "").strip()

    if not name or not shop:
        return jsonify({"error": "Please enter both your name and shop name."}), 400

    try:
        output_path = build_personalized_video(name, shop)
    except TTS_ERRORS as e:
        return jsonify({"error": f"Voice generation failed: {e}"}), 502
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Something went wrong: {e}"}), 500

    filename = os.path.basename(output_path)
    return jsonify({
        "success": True,
        "download_url": f"/download/{filename}",
    })


@app.route("/download/<filename>", methods=["GET"])
def download(filename):
    path = os.path.join(config.OUTPUT_DIR, filename)
    if not os.path.exists(path):
        return "File not found", 404
    return send_file(path, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
