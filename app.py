import os
import glob
import tempfile
import subprocess
from io import BytesIO

import yt_dlp
import imageio_ffmpeg

from flask import Flask, request, send_file, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route("/")
def home():
    return jsonify({"app": "ZORTAX Creator", "status": "online"})

@app.route("/health")
def health():
    return jsonify({"status": "online"})

@app.route("/process", methods=["POST"])
def process():
    data = request.get_json(silent=True) or {}
    url = request.form.get("url") or data.get("url")

    if not url or not (
        "youtube.com/" in url or "youtu.be/" in url
    ):
        return jsonify({"error": "Geçerli YouTube bağlantısı gir"}), 400

    try:
        with tempfile.TemporaryDirectory() as folder:
            kaynak = os.path.join(folder, "video.%(ext)s")

            options = {
                "format": "best[height<=720]/best",
                "outtmpl": kaynak,
                "noplaylist": True,
                "quiet": True
            }

            with yt_dlp.YoutubeDL(options) as ydl:
                ydl.download([url])

            videolar = glob.glob(os.path.join(folder, "video.*"))
            if not videolar:
                return jsonify({"error": "Video indirilemedi"}), 500

            cikis = os.path.join(folder, "ZORTAX_FINAL.mp4")

            filtre = (
                "[0:v]split=2[bg][fg];"
                "[bg]scale=1080:1920:force_original_aspect_ratio=increase,"
                "crop=1080:1920,boxblur=25:10[blur];"
                "[fg]scale=1080:1920:force_original_aspect_ratio=decrease[front];"
                "[blur][front]overlay=(W-w)/2:(H-h)/2,setsar=1[v]"
            )

            subprocess.run([
                imageio_ffmpeg.get_ffmpeg_exe(),
                "-y", "-i", videolar[0],
                "-filter_complex", filtre,
                "-map", "[v]", "-map", "0:a?",
                "-c:v", "libx264", "-preset", "ultrafast",
                "-crf", "23", "-c:a", "aac",
                "-movflags", "+faststart", cikis
            ], check=True)

            with open(cikis, "rb") as f:
                video_data = f.read()

            return send_file(
                BytesIO(video_data),
                mimetype="video/mp4",
                as_attachment=True,
                download_name="ZORTAX_FINAL.mp4"
            )

    except Exception as e:
        return jsonify({"error": str(e)}), 500
