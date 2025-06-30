import os
import json
import base64
import requests
from datetime import datetime
from io import BytesIO
from flask import Flask, request, jsonify, session, redirect, send_file, render_template
from flask_cors import CORS
from pdf2image import convert_from_bytes
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from dotenv import load_dotenv
from flask_cors import CORS


if os.environ.get("FLASK_ENV") != "production":
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"



# Load .env vars
load_dotenv()

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev")
CORS(app, supports_credentials=True, origins=["https://studybuddy-frontend-lwwq.onrender.com"])  # then apply CORS

# Environment Config
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
CLIENT_SECRETS_FILE = os.environ.get("GOOGLE_CLIENT_SECRET_FILE", "credentials.json")
REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:5000/callback")
SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive.file",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email"
]

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/authorize")
def authorize():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    auth_url, state = flow.authorization_url(access_type="offline", include_granted_scopes="true")
    session["state"] = state
    return redirect(auth_url)

@app.route("/callback")
def oauth_callback():
    state = session["state"]
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        state=state,
        redirect_uri=REDIRECT_URI
    )
    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials

    print("REFRESH TOKEN:", credentials.refresh_token)


    userinfo = requests.get(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        headers={"Authorization": f"Bearer {credentials.token}"}
    ).json()

    session["user_email"] = userinfo.get("email")

    session["creds"] = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes
    }
    return redirect("http://localhost:5173")


@app.route("/me")
def get_user():
    if "user_email" in session:
        return jsonify({"email": session["user_email"]})
    return jsonify({"email": None}), 401

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully."})


# ----------------- OCR -------------------

def extract_text_from_base64(base64_img):
    payload = {
        "requests": [
            {
                "image": {"content": base64_img},
                "features": [{"type": "DOCUMENT_TEXT_DETECTION"}]
            }
        ]
    }
    response = requests.post(
        f"https://vision.googleapis.com/v1/images:annotate?key={GOOGLE_API_KEY}",
        headers={"Content-Type": "application/json"},
        json=payload
    )
    result = response.json()
    print("🔍 Google Vision API Result:", result)
    return result["responses"][0].get("fullTextAnnotation", {}).get("text", "")

@app.route("/extract", methods=["POST"])
def extract_text():
    try:
        if "user_email" not in session:
            return jsonify({"error": "Unauthorized"}), 401

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

        final_text = "\n\n---\n\n".join(extracted_texts)
        return jsonify({"text": final_text})

    except Exception as e:
        print("❌ OCR Error:", e)
        return jsonify({"error": str(e)}), 500

# ----------------- Summarization -------------------

@app.route("/summarize", methods=["POST"])
def summarize():
    try:
        data = request.get_json()
        input_text = data.get("text", "").strip()
        if not input_text:
            return jsonify({"summary": "❌ No input text to summarize"}), 400

        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [
                {"parts": [{"text": f"Summarize the following study notes into bullet points:\n\n{input_text}"}]}
            ]
        }
        response = requests.post(endpoint, headers={"Content-Type": "application/json"}, json=payload)
        result = response.json()
        summary = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "⚠️ No summary returned.")
        return jsonify({"summary": summary})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"summary": f"❌ Summarization failed: {str(e)}"}), 500

# ----------------- Download -------------------

@app.route("/download", methods=["POST"])
def download():
    try:
        if "user_email" not in session:
            return jsonify({"error": "Unauthorized"}), 401

        user_dir = os.path.join("sessions", session["user_email"].replace("@", "_"))
        os.makedirs(user_dir, exist_ok=True)

        data = request.get_json()
        extracted = data.get("extracted", "")
        summary = data.get("summary", "")
        format = data.get("format", "txt")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
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

    except Exception as e:
        print("❌ Download Error:", e)
        return jsonify({"error": str(e)}), 500

# ----------------- Export to Google Docs -------------------

from google.oauth2.credentials import Credentials

@app.route("/export/docs", methods=["POST"])
def export_to_google_docs():
    try:
        creds_data = session.get("creds")
        if not creds_data:
            return jsonify({"error": "User not authenticated with Google"}), 403

        # ✅ Rebuild credentials from session
        creds = Credentials(
            token=creds_data["token"],
            refresh_token=creds_data["refresh_token"],
            token_uri=creds_data["token_uri"],
            client_id=creds_data["client_id"],
            client_secret=creds_data["client_secret"],
            scopes=creds_data["scopes"]
        )

        service = build("docs", "v1", credentials=creds)

        data = request.get_json()
        title = data.get("title", "StudyBuddy Notes")
        content = f"📚 Extracted Notes\n\n{data.get('extracted', '')}\n\n---\n\n📌 Summary\n\n{data.get('summary', '')}"

        doc = service.documents().create(body={"title": title}).execute()
        doc_id = doc.get("documentId")

        service.documents().batchUpdate(
            documentId=doc_id,
            body={"requests": [{"insertText": {"location": {"index": 1}, "text": content}}]}
        ).execute()

        return jsonify({
            "message": "✅ Exported to Google Docs!",
            "doc_url": f"https://docs.google.com/document/d/{doc_id}"
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ----------------- Session History -------------------

@app.route("/history", methods=["GET"])
def list_history():
    if "user_email" not in session:
        return jsonify([])

    user_dir = os.path.join("sessions", session["user_email"].replace("@", "_"))
    history = []
    if os.path.exists(user_dir):
        for session_folder in sorted(os.listdir(user_dir), reverse=True):
            folder_path = os.path.join(user_dir, session_folder)
            meta_file = os.path.join(folder_path, "metadata.json")
            if os.path.exists(meta_file):
                with open(meta_file, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                # Read actual content for frontend
                extracted = ""
                summary = ""
                try:
                    with open(os.path.join(folder_path, "extracted.txt"), "r", encoding="utf-8") as f1:
                        extracted = f1.read()
                    with open(os.path.join(folder_path, "summary.txt"), "r", encoding="utf-8") as f2:
                        summary = f2.read()
                except Exception as e:
                    print(f"⚠️ Failed to read session files: {e}")

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
    try:
        if "user_email" not in session:
            return jsonify({"error": "Unauthorized"}), 401

        user_dir = os.path.join("sessions", session["user_email"].replace("@", "_"))
        folder = os.path.join(user_dir, session_id)
        with open(os.path.join(folder, "extracted.txt"), "r", encoding="utf-8") as f1, \
             open(os.path.join(folder, "summary.txt"), "r", encoding="utf-8") as f2:
            return jsonify({
                "extracted": f1.read(),
                "summary": f2.read()
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 404

@app.route("/history/save", methods=["POST"])
def save_session():
    if "user_email" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    title = data.get("title", "Untitled Session")
    extracted = data.get("extracted", "")
    summary = data.get("summary", "")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    user_dir = os.path.join("sessions", session["user_email"].replace("@", "_"))
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
    if "user_email" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_dir = os.path.join("sessions", session["user_email"].replace("@", "_"))
    folder_path = os.path.join(user_dir, session_id)

    try:
        if os.path.exists(folder_path):
            import shutil
            shutil.rmtree(folder_path)
            return jsonify({"message": "Deleted successfully."})
        else:
            return jsonify({"error": "Session not found."}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ----------------- Run App -------------------

if __name__ == "__main__":
    os.makedirs("sessions", exist_ok=True)
    app.run(debug=True)
