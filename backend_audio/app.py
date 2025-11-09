# backend_audio/app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import whisper, os, tempfile

app = Flask(__name__)
CORS(app, origins=["https://dentalbot-3lei.onrender.com"], supports_credentials=True)


model = whisper.load_model("tiny")

@app.route("/transcribe", methods=["POST"])
def transcribe():
    if "audio_data" not in request.files:
        return jsonify({"error": "No audio file received"}), 400

    audio = request.files["audio_data"]

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
            audio.save(tmp.name)
            print(f"Saved temp file at {tmp.name}")

            result = model.transcribe(tmp.name, fp16=False)
            os.remove(tmp.name)

        text = result.get("text", "").strip()
        return jsonify({"text": text})

    except Exception as e:
        print("❌ Transcription failed:", e)
        return jsonify({"error": str(e)}), 500



