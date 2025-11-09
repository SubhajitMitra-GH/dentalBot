# backend_audio/app.py
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
model = whisper.load_model("tiny")

@app.route("/transcribe", methods=["POST"])
def transcribe():
    if "audio_data" not in request.files:
        return jsonify({"error": "No audio file"}), 400

    audio = request.files["audio_data"]
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
        audio.save(tmp.name)
        result = model.transcribe(tmp.name, fp16=False)
        os.remove(tmp.name)

    return jsonify({"text": result["text"].strip()})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
