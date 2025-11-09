from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
import re
import os
import google.generativeai as genai

app = Flask(__name__)

CORS(app, origins=["https://dentalbot-3lei.onrender.com"], supports_credentials=True)


# Configure Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
gemini_model = genai.GenerativeModel("gemini-2.5-flash")

# Audio backend endpoint (set to your deployed audio service)
AUDIO_BACKEND_URL = "https://dentalaudio.onrender.com/transcribe"
# Increase if needed, but keep reasonable for serverless timeouts
AUDIO_REQUEST_TIMEOUT = 300

# --- Full voice-fillable schema with descriptions (from your original file) ---
VOICE_FILLABLE_SCHEMA = {
    'organised_by': "The name of the organization conducting the event.",
    'department': "The specific department involved.",
    'event_date': "The date of the event.",
    'event_place': "The city or location of the event.",
    'event_district': "The district where the event is taking place.",
    'patient_name': "The patient's full name.",
    'patient_age': "The patient's age in years.",
    'patient_contact': "The patient's contact phone number.",
    'patient_education': "The patient's educational qualifications.",
    'family_monthly_income': "The monthly income of the patient's family.",
    'chief_complaint': "The primary medical or dental complaint from the patient, in their own words.",
    'past_medical_history_others': "Any other past medical conditions mentioned that are not in the Yes/No list.",
    'past_dental_visit_details': "Details about the last dental visit if mentioned (e.g., 'about a year ago for a cleaning').",
    'personal_habits_others': "Any other personal habits mentioned besides smoking or alcohol.",
    'clinical_decayed': "Description or count of decayed teeth.",
    'clinical_missing': "Description or count of missing teeth.",
    'clinical_filled': "Description or count of filled teeth.",
    'clinical_pain': "Details about any dental pain the patient is experiencing.",
    'clinical_fractured_teeth': "Details about any fractured teeth.",
    'clinical_mobility': "Details about any mobile or loose teeth.",
    'clinical_examination_others': "Any other clinical findings mentioned.",
    'oral_mucosal_lesion': "Description of any oral mucosal lesions observed.",
    'teeth_cleaning_method': "The method the patient uses for cleaning their teeth (e.g., 'brush and paste twice a day').",
    'doctors_name': "The name of the examining doctor.",
    'treatment_plan': "The proposed treatment plan based on the examination."
}

# --- Prompt builder ---
def build_schema_prompt(schema: dict) -> str:
    """
    Returns a human-friendly schema description for the model prompt.
    Each line contains the field key and its description.
    """
    lines = []
    for k, desc in schema.items():
        lines.append(f'- "{k}": "{desc}"')
    return "\n".join(lines)

def build_prompt(schema: dict, transcript: str) -> str:
    schema_desc = build_schema_prompt(schema)
    prompt = f"""
You are an expert medical scribe specializing in dental forms. Your job is to read the transcript and extract values for the exact JSON schema listed below.

JSON Schema to fill:
{schema_desc}

Extraction rules (MUST obey):
- Output a single, valid JSON object and nothing else.
- The JSON object MUST contain exactly the keys listed above, no additional keys.
- If a key's information is not present in the transcript, set its value to the empty string "".
- Translate any non-English text into English.
- Normalize numeric values: ages and counts should be digits (e.g., "42", not "forty-two").
- Format dates as YYYY-MM-DD if possible; otherwise use a clear unambiguous format (e.g., "January 2, 2024").
- Normalize phone numbers to digits only where possible (e.g., "9876543210").
- For free-text fields keep short, factual answers (no commentary).
- Do NOT answer yes/no questions — leave the field empty ("") if not explicitly stated.
- The output must be plain JSON only (no surrounding markdown/fences, no explanation).

Transcript:
---
{transcript}
---

Now produce the JSON object only.
"""
    return prompt

# --- Robust JSON extraction from model response ---
def extract_json_from_text(text: str) -> dict:
    """
    Try to find the first {...} JSON object in text and parse it.
    If direct json.loads(text) fails, use regex to extract a JSON block.
    """
    # Try direct parse first
    try:
        return json.loads(text)
    except Exception:
        pass

    # Remove common code fences
    cleaned = text.replace("```json", "").replace("```", "").strip()

    # Regex to extract the first {...} block
    match = re.search(r"(\{(?:[^{}]|(?R))*\})", cleaned, flags=re.DOTALL)
    if match:
        candidate = match.group(1)
        try:
            return json.loads(candidate)
        except Exception:
            # Last resort: try to "fix" trailing commas and simple issues
            candidate_fixed = re.sub(r",\s*}", "}", candidate)
            candidate_fixed = re.sub(r",\s*]", "]", candidate_fixed)
            try:
                return json.loads(candidate_fixed)
            except Exception:
                pass

    raise ValueError("Failed to extract valid JSON from model response.")

# --- Validate and ensure all keys exist (fill missing with empty string) ---
def normalize_extracted(extracted: dict, schema_keys) -> dict:
    result = {}
    for key in schema_keys:
        v = extracted.get(key, "")
        if v is None:
            v = ""
        # Convert numbers to strings (keep consistent)
        if isinstance(v, (int, float)):
            v = str(v)
        # Final safety: ensure string
        if not isinstance(v, str):
            try:
                v = json.dumps(v, ensure_ascii=False)
            except:
                v = str(v)
        result[key] = v.strip()
    return result

# --- Core function to call Gemini and parse result ---
def fill_form_from_text(text: str) -> dict:
    prompt = build_prompt(VOICE_FILLABLE_SCHEMA, text)
    try:
        res = gemini_model.generate_content(prompt)
        response_text = res.text.strip()
        # try to extract JSON
        extracted = extract_json_from_text(response_text)
        normalized = normalize_extracted(extracted, VOICE_FILLABLE_SCHEMA.keys())
        return normalized
    except Exception as e:
        # Return error dictionary so caller can decide how to respond
        return {"error": f"Gemini failed: {str(e)}"}

# --- Endpoints ---

@app.route("/fill_form", methods=["POST"])
def fill_form():
    # Accept either JSON body { "text": "..." } or form-encoded
    data = request.get_json(silent=True) or request.form
    text = data.get("text", "") if isinstance(data, dict) else ""
    if not text:
        return jsonify({"error": "Missing 'text' in request body"}), 400

    result = fill_form_from_text(text)
    if "error" in result:
        return jsonify(result), 500
    return jsonify(result), 200

@app.route("/process_audio", methods=["POST", "OPTIONS"])
def process_audio():
    if request.method == "OPTIONS":
        return '', 204
    if "audio_data" not in request.files:
        return jsonify({"error": "No audio file"}), 400

    files = {"audio_data": request.files["audio_data"]}
    try:
        # Forward audio to audio backend
        audio_res = requests.post(AUDIO_BACKEND_URL, files=files, timeout=AUDIO_REQUEST_TIMEOUT)
        audio_res.raise_for_status()
        text = audio_res.json().get("text", "")
    except Exception as e:
        return jsonify({"error": f"Transcription failed: {e}"}), 500

    if not text:
        return jsonify({"error": "Transcription returned empty text"}), 500

    fill_res = fill_form_from_text(text)
    if "error" in fill_res:
        return jsonify({"error": fill_res["error"]}), 500

    return jsonify({
        "transcribed_text": text,
        "extracted_data": fill_res
    }), 200

