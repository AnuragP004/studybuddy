import os
import json
import base64
import requests
from datetime import datetime
from io import BytesIO
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_session import Session
from pdf2image import convert_from_bytes
from dotenv import load_dotenv

# ------------------- Setup -------------------

load_dotenv()

app = Flask(__name__, static_folder="static")
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev")

app.config.update(
    SESSION_TYPE="filesystem",
    SESSION_FILE_DIR="./flask_session",
    SESSION_PERMANENT=False,
    SESSION_COOKIE_SAMESITE="None",
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_DOMAIN=".onrender.com"
)
Session(app)

CORS(
    app,
    supports_credentials=True,
    origins=["https://studybuddy-frontend-lwwq.onrender.com"]
)

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# ------------------- Routes -------------------

@app.route('/')
def index():
    return "StudyBuddy Backend is running 🚀"

# ----------------- OCR -------------------

def extract_text_from_base64(base64_img):
    payload = {
        "requests": [{
            "image": {"content": base64_img},
            "features": [{"type": "DOCUMENT_TEXT_DETECTION"}]
        }]
    }
    response = requests.post(
        f"https://vision.googleapis.com/v1/images:annotate?key={GOOGLE_API_KEY}",
        headers={"Content-Type": "application/json"},
        json=payload
    )
    result = response.json()
    return result["responses"][0].get("fullTextAnnotation", {}).get("text", "")

@app.route("/extract", methods=["POST"])
def extract_text():
    extracted_texts = []
    for file_data in request.files.getlist("files"):
        filename = file_data.filename.lower()
        if filename.endswith(".pdf"):
            pdf_images = convert_from_bytes(file_data.read())
            for img in pdf_images:
                buffered = BytesIO()
                img.save(buffered, format="JPEG")
                base64_img = base64.b64encode(buffered.getvalue()).decode()
                text = extract_text_from_base64(base64_img)
                extracted_texts.append(text)
        else:
            image_bytes = file_data.read()
            base64_img = base64.b64encode(image_bytes).decode()
            text = extract_text_from_base64(base64_img)
            extracted_texts.append(text)

    return jsonify({"text": "\n\n---\n\n".join(extracted_texts)})

# ------------------- Summarize -------------------

@app.route("/summarize", methods=["POST"])
def summarize():
    try:
        data = request.get_json()
        input_text = data.get("text", "").strip()
        if not input_text:
            return jsonify({"summary": "❌ No input text to summarize"}), 400

        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{
                "parts": [{"text": f"Summarize the following study notes into bullet points:\n\n{input_text}"}]
            }]
        }
        response = requests.post(endpoint, headers={"Content-Type": "application/json"}, json=payload)
        result = response.json()
        summary = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "⚠️ No summary returned.")
        return jsonify({"summary": summary})

    except Exception as e:
        return jsonify({"summary": f"❌ Summarization failed: {str(e)}"}), 500

# ------------------- File Download -------------------

@app.route("/download", methods=["POST"])
def download():
    data = request.get_json()
    extracted = data.get("extracted", "")
    summary = data.get("summary", "")
    format = data.get("format", "txt")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    user_dir = os.path.join("sessions", "anonymous")
    folder_path = os.path.join(user_dir, f"session_{timestamp}")
    os.makedirs(folder_path, exist_ok=True)

    with open(os.path.join(folder_path, "extracted.txt"), "w", encoding="utf-8") as f:
        f.write(extracted)
    with open(os.path.join(folder_path, "summary.txt"), "w", encoding="utf-8") as f:
        f.write(summary)
    with open(os.path.join(folder_path, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump({"timestamp": timestamp, "format": format}, f)

    content = f"📚 Extracted Notes\n\n{extracted}\n\n---\n\n📌 Summary\n\n{summary}"
    ext = "md" if format == "md" else "txt"
    final_path = os.path.join(folder_path, f"StudyNotes.{ext}")
    with open(final_path, "w", encoding="utf-8") as f:
        f.write(content)

    return send_file(final_path, as_attachment=True, download_name=f"StudyNotes.{ext}", mimetype="text/plain")

# ------------------- History -------------------

@app.route("/history", methods=["GET"])
def list_history():
    user_dir = os.path.join("sessions", "anonymous")
    history = []
    if os.path.exists(user_dir):
        for session_folder in sorted(os.listdir(user_dir), reverse=True):
            folder_path = os.path.join(user_dir, session_folder)
            meta_file = os.path.join(folder_path, "metadata.json")
            if os.path.exists(meta_file):
                with open(meta_file, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                extracted = summary = ""
                try:
                    with open(os.path.join(folder_path, "extracted.txt"), "r", encoding="utf-8") as f1:
                        extracted = f1.read()
                    with open(os.path.join(folder_path, "summary.txt"), "r", encoding="utf-8") as f2:
                        summary = f2.read()
                except Exception:
                    pass
                history.append({
                    "session_id": session_folder,
                    "title": meta.get("title", session_folder),
                    "timestamp": meta.get("timestamp"),
                    "extracted": extracted,
                    "summary": summary
                })
    return jsonify(history)

@app.route("/history/<session_id>", methods=["GET"])
def get_session_by_id(session_id):
    user_dir = os.path.join("sessions", "anonymous")
    folder = os.path.join(user_dir, session_id)
    with open(os.path.join(folder, "extracted.txt"), "r", encoding="utf-8") as f1, \
         open(os.path.join(folder, "summary.txt"), "r", encoding="utf-8") as f2:
        return jsonify({"extracted": f1.read(), "summary": f2.read()})

@app.route("/history/save", methods=["POST"])
def save_session():
    data = request.get_json()
    title = data.get("title", "Untitled Session")
    extracted = data.get("extracted", "")
    summary = data.get("summary", "")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    user_dir = os.path.join("sessions", "anonymous")
    folder_path = os.path.join(user_dir, f"session_{timestamp}")
    os.makedirs(folder_path, exist_ok=True)

    with open(os.path.join(folder_path, "extracted.txt"), "w", encoding="utf-8") as f:
        f.write(extracted)
    with open(os.path.join(folder_path, "summary.txt"), "w", encoding="utf-8") as f:
        f.write(summary)
    with open(os.path.join(folder_path, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump({"title": title, "timestamp": timestamp}, f)

    return jsonify({"message": "Session saved."})

@app.route("/history/delete/<session_id>", methods=["DELETE"])
def delete_session(session_id):
    user_dir = os.path.join("sessions", "anonymous")
    folder_path = os.path.join(user_dir, session_id)

    if os.path.exists(folder_path):
        import shutil
        shutil.rmtree(folder_path)
        return jsonify({"message": "Deleted successfully."})
    return jsonify({"error": "Session not found."}), 404

# ------------------- Start Server -------------------

if __name__ == "__main__":
    os.makedirs("sessions", exist_ok=True)
    os.makedirs("flask_session", exist_ok=True)
    app.run(debug=True)