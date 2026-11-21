
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

app.config["MAX_CONTENT_LENGTH"] = 300 * 1024 * 1024

@app.route("/")
def home():
    return jsonify({
        "app": "ZORTAX Creator",
        "status": "online"
    })

@app.route("/health")
def health():
    return jsonify({"status": "online"})

@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "Video 300 MB sınırını aşıyor."}), 413

@app.route("/process", methods=["POST"])
def process():
    try:
        with tempfile.TemporaryDirectory() as folder:

            video_path = None

            # TELEFONDAN VIDEO YÜKLEME
            uploaded = request.files.get("video")

            if uploaded and uploaded.filename:
                ext = os.path.splitext(uploaded.filename)[1].lower()

                if ext not in [".mp4", ".mov", ".webm", ".mkv"]:
                    return jsonify({
                        "error": "MP4, MOV, WEBM veya MKV video yükle."
                    }), 400

                video_path = os.path.join(folder, "input" + ext)
                uploaded.save(video_path)

                if os.path.getsize(video_path) == 0:
                    return jsonify({"error": "Video dosyası boş."}), 400

            else:
                # YOUTUBE LINKI
                data = request.get_json(silent=True) or {}
                url = request.form.get("url") or data.get("url")

                if not url or not (
                    "youtube.com/" in url or "youtu.be/" in url
                ):
                    return jsonify({
                        "error": "Video yükle veya YouTube bağlantısı gir."
                    }), 400

                options = {
                    "format": "best[height<=720]/best",
                    "outtmpl": os.path.join(folder, "video.%(ext)s"),
                    "noplaylist": True,
                    "quiet": True
                }

                with yt_dlp.YoutubeDL(options) as ydl:
                    ydl.download([url])

                videos = glob.glob(os.path.join(folder, "video.*"))

                if not videos:
                    return jsonify({
                        "error": "YouTube videosu indirilemedi."
                    }), 500

                video_path = videos[0]

            # DIKEY VIDEO MOTORU
            output_path = os.path.join(folder, "ZORTAX_FINAL.mp4")

            filter_complex = (
                "[0:v]split=2[bg][fg];"
                "[bg]scale=720:1280:force_original_aspect_ratio=increase,"
                "crop=720:1280,boxblur=25:10[blur];"
                "[fg]scale=720:1280:force_original_aspect_ratio=decrease[front];"
                "[blur][front]overlay=(W-w)/2:(H-h)/2,setsar=1[v]"
            )

            subprocess.run([
                imageio_ffmpeg.get_ffmpeg_exe(),
                "-y",
                "-i", video_path,
                "-filter_complex", filter_complex,
                "-map", "[v]",
                "-map", "0:a?",
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-crf", "25",
                "-c:a", "aac",
                "-movflags", "+faststart",
                output_path
            ], check=True)

            with open(output_path, "rb") as f:
                result = f.read()

            return send_file(
                BytesIO(result),
                mimetype="video/mp4",
                as_attachment=True,
                download_name="ZORTAX_FINAL.mp4"
            )

    except subprocess.CalledProcessError:
        return jsonify({
            "error": "Video dönüştürülemedi. Daha küçük bir video dene."
        }), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500
                    
