import React, { useState, useEffect } from "react";
import DropZone from "./components/DropZone";
import HistorySidebar from "./components/HistorySidebar";
import TextAreaSection from "./components/TextAreaSection";
import "./styles/style.css";

const API_BASE = import.meta.env.VITE_BACKEND_URL;

export default function App() {
  const [droppedFiles, setDroppedFiles] = useState([]);
  const [extractedText, setExtractedText] = useState("");
  const [summaryText, setSummaryText] = useState("");
  const [history, setHistory] = useState([]);
  const [readOnlyExtracted, setReadOnlyExtracted] = useState(true);
  const [readOnlySummary, setReadOnlySummary] = useState(true);
  const [user, setUser] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE}/me`, { credentials: "include" })
      .then((res) => res.json())
      .then((data) => {
        if (data.email) {
          setUser(data.email);
          fetch(`${API_BASE}/history`, { credentials: "include" })
            .then((res) => res.json())
            .then((backendHistory) => {
              setHistory(
                backendHistory.map((item, index) => ({
                  id: item.session_id || index,
                  title: item.title || `Session ${index + 1}`,
                  extracted: item.extracted || "",
                  summary: item.summary || "",
                }))
              );
            });
        }
      })
      .catch(() => setUser(null));
  }, []);

  const saveSession = async (title, summaryOverride = null) => {
    const newEntry = {
      title,
      extracted: extractedText,
      summary: summaryOverride ?? summaryText,
    };
    const updatedHistory = [{ id: Date.now(), ...newEntry }, ...history];
    setHistory(updatedHistory);

    if (user) {
      await fetch(`${API_BASE}/history/save`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(newEntry),
      });
    }
  };

  const handleExtract = async () => {
    if (!droppedFiles.length) return alert("Please upload image(s)/PDF(s).");

    const formData = new FormData();
    droppedFiles.forEach((f) => formData.append("files", f));

    const res = await fetch(`${API_BASE}/extract`, {
      method: "POST",
      body: formData,
      credentials: "include",
    });
    const data = await res.json();
    setExtractedText(data.text || "No text found.");
    setDroppedFiles([]);
  };

  const handleSummarize = async () => {
    if (!extractedText.trim()) return alert("Please extract text first.");

    const res = await fetch(`${API_BASE}/summarize`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: extractedText }),
    });

    const data = await res.json();
    const summary = data.summary || "❌ No summary returned";
    setSummaryText(summary);

    const title = prompt("💾 Save this session with a title:", "Untitled Notes");
    if (title) saveSession(title, summary);
  };

  const handleDownload = async (format, filename) => {
    if (!extractedText && !summaryText) return alert("Nothing to download.");

    const res = await fetch(`${API_BASE}/download`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ extracted: extractedText, summary: summaryText, format }),
      credentials: "include",
    });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${filename}.${format}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const exportToGoogleDocs = async () => {
    const title = prompt("📄 Enter Google Doc title:", "StudyBuddy Notes");
    if (!title) return;

    const res = await fetch(`${API_BASE}/export/docs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ extracted: extractedText, summary: summaryText, title }),
      credentials: "include",
    });
    const data = await res.json();
    if (data.doc_url) window.open(data.doc_url, "_blank");
    else {
      alert("❌ Failed to export. Try logging in.");
      window.location.href = `${API_BASE}/authorize`;
    }
  };

  return (
    <div className="app-wrapper">
      <div className="topbar">
        <h1>📚 StudyBuddy</h1>
        {user ? (
          <div className="auth-info">
            👤 {user}
            <button
              onClick={async () => {
                await fetch(`${API_BASE}/logout`, {
                  method: "POST",
                  credentials: "include",
                });
                setUser(null);
                setHistory([]);
              }}
            >
              🚪 Logout
            </button>
          </div>
        ) : (
          <button onClick={() => (window.location.href = `${API_BASE}/authorize`)}>
            🔐 Login with Google
          </button>
        )}
      </div>

      <div className="main-layout">
        <HistorySidebar
          history={history}
          setExtractedText={setExtractedText}
          setSummaryText={setSummaryText}
          setHistory={setHistory}
        />

        <div className="main-content">
          <p>Upload handwritten/digital notes to extract and organize text.</p>
          <DropZone setDroppedFiles={setDroppedFiles} droppedFiles={droppedFiles} />
          <button onClick={handleExtract}>Extract Text</button>

          <TextAreaSection
            title="📝 Extracted Text"
            text={extractedText}
            setText={setExtractedText}
            readOnly={readOnlyExtracted}
            toggleReadOnly={() => setReadOnlyExtracted(!readOnlyExtracted)}
            editLabel="✏️ Edit Extracted Text"
            doneLabel="✅ Done Editing"
          />

          <button onClick={handleSummarize}>Summarize Notes</button>

          <TextAreaSection
            title="📌 Summary"
            text={summaryText}
            setText={setSummaryText}
            readOnly={readOnlySummary}
            toggleReadOnly={() => setReadOnlySummary(!readOnlySummary)}
            editLabel="✏️ Edit Summary"
            doneLabel="✅ Done Editing"
          />

          <div className="download-section">
            <label>Download as:</label>
            <select id="formatSelect">
              <option value="txt">.txt</option>
              <option value="md">.md</option>
            </select>
            <label>📄 File Name:</label>
            <input id="filenameInput" type="text" placeholder="e.g. MyClassNotes" />
            <button
              onClick={() => {
                const format = document.getElementById("formatSelect").value;
                const filename = document.getElementById("filenameInput").value || "StudyNotes";
                handleDownload(format, filename);
              }}
            >
              Download
            </button>
          </div>

          <button onClick={exportToGoogleDocs}>📝 Export to Google Docs</button>
        </div>
      </div>
    </div>
  );
}
