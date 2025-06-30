# StudyBuddy

**StudyBuddy** is a smart note-organizing tool that helps you extract, summarize, and manage notes from images or PDFs using OCR and generative AI. It supports Google login, exports to Google Docs, and maintains a history of your sessions.

---

## Features

* Upload handwritten/digital notes (images or PDFs)
* Extract text using Google Vision OCR
* Summarize notes using Gemini Pro (Google Generative Language API)
* Save sessions with extracted text and summary
* Export notes as `.txt`, `.md`, or directly to Google Docs
* User authentication via Google OAuth2
* Session history with ability to save, retrieve, and delete
* Cyberpunk-inspired responsive UI with dark-glass styling

---

## Tech Stack

* **Frontend**: React + Vite + Tailwind CSS
* **Backend**: Python (Flask)
* **OCR**: Google Cloud Vision API
* **Summarization**: Gemini API (`generativelanguage.googleapis.com`)
* **Authentication**: Google OAuth2 (via `google-auth-oauthlib`)
* **PDF/Image Support**: `pdf2image`, `Pillow`

---

## Requirements

Make sure the following are installed:

* Python 3.9+
* Node.js (for frontend)
* Google Cloud project with:

  * Vision API enabled
  * Gemini API key (Generative Language API)
  * OAuth 2.0 Client credentials for web

---

## Python Dependencies

Create a virtual environment and install dependencies:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**requirements.txt** includes:

```
Flask
flask-cors
google-auth
google-auth-oauthlib
google-api-python-client
pdf2image
Pillow
python-dotenv
requests
```

---

## Project Structure

```
StudyBuddy/
├── backend/
│   ├── server.py
│   ├── credentials.json         # [DO NOT COMMIT]
│   ├── .env                     # [DO NOT COMMIT]
│   ├── requirements.txt
│   └── sessions/                # Saved session data
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   ├── styles/
│   │   │   └── style.css
│   │   └── main.jsx
│   ├── index.html
│   └── vite.config.js
└── README.md
```

---

## Environment Variables

Create a `.env` file in the `backend/` folder with the following:

```
FLASK_SECRET_KEY=your_flask_secret
GOOGLE_API_KEY=your_google_vision_api_key
GEMINI_API_KEY=your_gemini_api_key
GOOGLE_CLIENT_SECRET_FILE=credentials.json
GOOGLE_REDIRECT_URI=http://localhost:5000/callback
```

> Note: Never commit `.env` or `credentials.json` to version control. Add them to your `.gitignore`.

---

## Run Instructions

### Backend (Flask)

```bash
cd backend
python server.py
```

### Frontend (Vite + React)

```bash
cd frontend
npm install
npm run dev
```

---

## Deployment Notes

* For production, use HTTPS for both backend and frontend.
* Use environment variables securely in cloud deployment platforms.
* Store session data securely and consider database integration for scalability.
