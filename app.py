import os
import glob
import tempfile
import subprocess
import yt_dlp
import imageio_ffmpeg

from flask import Flask, request, send_file, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route("/")
def home():
    return jsonify({
        "app": "ZORTAX Creator",
        "status": "online"
    })

@app.route("/health")
def health():
    return jsonify({"status": "online"})

@app.route("/process", methods=["POST"])
def process():
    url = request.form.get("url") or (
        request.json.get("url") if request.is_json else None
    )

    if not url or not (
        "youtube.com/" in url or "youtu.be/" in url
    ):
        return jsonify({"error": "Geçerli YouTube bağlantısı gir"}), 400

    with tempfile.TemporaryDirectory() as folder:
        kaynak = os.path.join(folder, "video.%(ext)s")

        try:
            options = {
                "format": "best[height<=720]/best",
                "outtmpl": kaynak,
                "noplaylist": True,
                "quiet": True,
            }

            with yt_dlp.YoutubeDL(options) as ydl:
                ydl.download([url])

            videolar = glob.glob(os.path.join(folder, "video.*"))
            if not videolar:
                return jsonify({"error": "Video indirilemedi"}), 500

            giris = videolar[0]
            cikis = os.path.join(folder, "ZORTAX_FINAL.mp4")
            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

            filtre = (
                "[0:v]split=2[bg][fg];"
                "[bg]scale=1080:1920:force_original_aspect_ratio=increase,"
                "crop=1080:1920,boxblur=25:10[blur];"
                "[fg]scale=1080:1920:force_original_aspect_ratio=decrease[front];"
                "[blur][front]overlay=(W-w)/2:(H-h)/2,setsar=1[v]"
            )

            subprocess.run([
                ffmpeg, "-y", "-i", giris,
                "-filter_complex", filtre,
                "-map", "[v]", "-map", "0:a?",
                "-c:v", "libx264", "-preset", "ultrafast",
                "-crf", "23", "-c:a", "aac",
                "-movflags", "+faststart", cikis
            ], check=True)

            return send_file(
                cikis,
                as_attachment=True,
                download_name="ZORTAX_FINAL.mp4"
            )

        except Exception as e:
            return jsonify({"error": str(e)}), 500
