import React, { useState, ChangeEvent } from 'react';
import axios from 'axios';
import './FileUpload.css';

interface Metadata {
  filename: string;
  size: number;
  content_type: string;
  [key: string]: any; // For additional metadata fields
}

const FileUpload: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [metadata, setMetadata] = useState<Metadata | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
      setMetadata(null);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    setLoading(true);
    try {
      const response = await axios.post<Metadata>('http://localhost:8000/api/upload/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      setMetadata(response.data);
    } catch (error) {
      console.error('Error uploading file:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="upload-container">
      <h2>📁 Upload a File</h2>
      <input type="file" onChange={handleFileChange} className="file-input" />
      <button onClick={handleUpload} className="upload-button" disabled={!file || loading}>
        {loading ? 'Uploading...' : 'Upload & Fetch Metadata'}
      </button>

      {metadata && (
        <div className="metadata-display">
          <h3>🧾 Extracted Metadata</h3>
          <pre>{JSON.stringify(metadata, null, 2)}</pre>
        </div>
      )}
    </div>
  );
};

export default FileUpload;