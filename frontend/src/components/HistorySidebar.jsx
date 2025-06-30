// src/components/HistorySidebar.jsx
import React from "react";

export default function HistorySidebar({ history, setExtractedText, setSummaryText, setHistory }) {
  const loadSession = (entry) => {
    setExtractedText(entry.extracted);
    setSummaryText(entry.summary);
  };

  const renameSession = (id, newTitle) => {
    const updated = history.map((h) => (h.id === id ? { ...h, title: newTitle } : h));
    setHistory(updated);
  };

  const deleteSession = async (id) => {
  // Remove from frontend
  const updated = history.filter((h) => h.id !== id);
  setHistory(updated);

  // Also remove from backend
  try {
    await fetch(`${import.meta.env.VITE_BACKEND_URL}/history/delete/${id}`, {
      method: "DELETE",
      credentials: "include",
    });
  } catch (err) {
    console.error("❌ Failed to delete from backend", err);
  }
};


  return (
    <div id="historySidebar">
      <h2>📜 History</h2>
      <div id="historyList">
        {history.map((entry) => (
          <div className="history-entry" key={entry.id}>
            <div className="bubble" onClick={() => loadSession(entry)}>
              <span
                contentEditable
                suppressContentEditableWarning
                onBlur={(e) => renameSession(entry.id, e.target.innerText)}
              >
                {entry.title}
              </span>
              <button onClick={(e) => { e.stopPropagation(); deleteSession(entry.id); }}>🗑️</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
