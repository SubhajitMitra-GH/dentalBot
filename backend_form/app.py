from flask import Flask, request, jsonify
import requests, json
import google.generativeai as genai
import os

app = Flask(__name__)

# Configure Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
gemini_model = genai.GenerativeModel("gemini-1.5-flash")

# 🔗 Audio backend endpoint
AUDIO_BACKEND_URL = "https://scribeAI-audio.onrender.com/transcribe"

@app.route("/fill_form", methods=["POST"])
def fill_form():
    data = request.get_json()
    text = data.get("text", "")
    if not text:
        return jsonify({"error": "Missing text"}), 400

    schema = {
        "Patient Name": "",
        "Age": "",
        "Symptoms": "",
        "Diagnosis": "",
        "Prescription": ""
    }

    schema_prompt = "\n".join([f'- "{k}": "{v}"' for k, v in schema.items()])
    prompt = f"""You are an expert medical scribe. Fill this JSON schema from the given text.

    Schema:
    {schema_prompt}

    Text:
    ---
    {text}
    ---
    """

    try:
        res = gemini_model.generate_content(prompt)
        response_text = res.text.strip().replace("```json", "").replace("```", "")
        return jsonify(json.loads(response_text))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/process_audio", methods=["POST"])
def process_audio():
    if "audio_data" not in request.files:
        return jsonify({"error": "No audio file"}), 400

    files = {"audio_data": request.files["audio_data"]}
    try:
        audio_res = requests.post(AUDIO_BACKEND_URL, files=files, timeout=300)
        audio_res.raise_for_status()
        text = audio_res.json().get("text", "")
    except Exception as e:
        return jsonify({"error": f"Transcription failed: {e}"}), 500

    # Now send to Gemini
    fill_res = fill_form_from_text(text)
    return jsonify({
        "transcribed_text": text,
        "extracted_data": fill_res
    })

def fill_form_from_text(text):
    schema = {
        "Patient Name": "",
        "Age": "",
        "Symptoms": "",
        "Diagnosis": "",
        "Prescription": ""
    }
    schema_prompt = "\n".join([f'- "{k}": "{v}"' for k, v in schema.items()])
    prompt = f"""You are an expert medical scribe. Fill this JSON schema from the given text.

    Schema:
    {schema_prompt}

    Text:
    ---
    {text}
    ---
    """

    try:
        res = gemini_model.generate_content(prompt)
        response_text = res.text.strip().replace("```json", "").replace("```", "")
        return json.loads(response_text)
    except:
        return {"error": "Gemini failed"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10001)
