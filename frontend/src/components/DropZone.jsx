// src/components/DropZone.jsx
import React, { useCallback } from "react";
import { useDropzone } from "react-dropzone";
import "../styles/style.css";

export default function DropZone({ setDroppedFiles, droppedFiles }) {
  const onDrop = useCallback(
    (acceptedFiles) => {
      setDroppedFiles([...droppedFiles, ...acceptedFiles]);
    },
    [droppedFiles, setDroppedFiles]
  );

  const handleRemove = (indexToRemove) => {
    const newFiles = droppedFiles.filter((_, idx) => idx !== indexToRemove);
    setDroppedFiles(newFiles);
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "image/*": [],
      "application/pdf": [],
    },
  });

  return (
    <div className="dropzone-wrapper">
      <div {...getRootProps()} className={`dropzone-box ${isDragActive ? "active" : ""}`}>
        <input {...getInputProps()} />
        <p>📥 <strong>Drag & drop</strong> notes here or <u>click to upload</u>.</p>
      </div>

      {droppedFiles && droppedFiles.length > 0 && (
        <div className="uploaded-files-box">
          <p>📎 <strong>Files uploaded:</strong></p>
          <ul>
            {droppedFiles.map((file, idx) => (
              <li key={idx} className="file-item">
                {file.name}
                <button className="remove-btn" onClick={() => handleRemove(idx)}>❌</button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
