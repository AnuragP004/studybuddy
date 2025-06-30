// src/components/TextAreaSection.jsx
import React from "react";

export default function TextAreaSection({ title, text, setText, readOnly, toggleReadOnly, editLabel, doneLabel }) {
  return (
    <div className="output">
      <h2>{title}</h2>
      <textarea
        value={text}
        readOnly={readOnly}
        onChange={(e) => setText(e.target.value)}
        rows={title.includes("Summary") ? 10 : 15}
      />
      <button onClick={toggleReadOnly}>
        {readOnly ? editLabel : doneLabel}
      </button>
    </div>
  );
}
