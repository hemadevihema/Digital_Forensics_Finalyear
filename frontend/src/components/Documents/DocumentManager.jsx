import React, { useState, useRef } from 'react';
import DocumentList from './DocumentList';
import ChunkViewerModal from './ChunkViewerModal';
import { uploadDocument, deleteDocument } from '../../services/api';

const PROCESSING_STEPS = [
  'Uploading...',
  'Parsing...',
  'Chunking...',
  'Generating embeddings...',
  'Indexing...',
  'Completed ✓',
];

export default function DocumentManager({ documents, refreshDocuments, sessionId }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [uploadError, setUploadError] = useState(null);
  const [inspectDoc, setInspectDoc] = useState(null);
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setUploadError(null);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setSelectedFile(e.dataTransfer.files[0]);
      setUploadError(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile || uploading) return;

    setUploading(true);
    setUploadError(null);
    setCurrentStep(0);

    // Simulate stepping through visual processing stages while request executes
    const stepInterval = setInterval(() => {
      setCurrentStep((prev) => (prev < 4 ? prev + 1 : prev));
    }, 450);

    try {
      await uploadDocument(selectedFile, sessionId);
      clearInterval(stepInterval);
      setCurrentStep(5); // Completed ✓
      setTimeout(() => {
        setSelectedFile(null);
        setUploading(false);
        setCurrentStep(0);
        refreshDocuments();
      }, 1000);
    } catch (err) {
      clearInterval(stepInterval);
      setUploading(false);
      setUploadError(err.message || 'Upload failed');
    }
  };

  const handleDelete = async (docId) => {
    if (!window.confirm('Remove this document from FAISS and MongoDB Atlas?')) return;
    try {
      await deleteDocument(docId);
      refreshDocuments();
    } catch (err) {
      alert(`Delete error: ${err.message}`);
    }
  };

  return (
    <div className="docs-view">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#fff' }}>Knowledge Documents</h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            Upload corporate policy and handbook files to extract, chunk, and index into FAISS.
          </p>
        </div>
        <button className="btn-subtle" onClick={refreshDocuments}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="23 4 23 10 17 10"/>
            <polyline points="1 20 1 14 7 14"/>
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
          </svg>
          Refresh Index
        </button>
      </div>

      {/* Upload Dropzone */}
      <div
        className="upload-dropzone"
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
        onClick={() => !uploading && fileInputRef.current?.click()}
      >
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          accept=".pdf,.txt,.md,.markdown,.docx"
          style={{ display: 'none' }}
        />
        <svg className="upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
          <polyline points="17 8 12 3 7 8"/>
          <line x1="12" y1="3" x2="12" y2="15"/>
        </svg>

        {selectedFile ? (
          <div>
            <div style={{ fontWeight: 600, color: '#fff' }}>Selected: {selectedFile.name}</div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
              {(selectedFile.size / 1024).toFixed(1)} KB — Click "Start Indexing" below
            </div>
          </div>
        ) : (
          <div>
            <div style={{ fontWeight: 600, color: '#fff' }}>
              Drop documents here or click to browse
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.3rem' }}>
              Supports PDF, TXT, Markdown, and DOCX (up to 25MB)
            </div>
          </div>
        )}
      </div>

      {/* Upload Actions & Stepper */}
      {selectedFile && !uploading && (
        <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center' }}>
          <button className="btn-send" onClick={handleUpload}>
            <span>Start Processing & Indexing</span>
          </button>
          <button className="btn-subtle" onClick={() => setSelectedFile(null)}>
            Cancel
          </button>
        </div>
      )}

      {uploading && (
        <div className="glass-card" style={{ padding: '1rem 1.5rem' }}>
          <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#fff', marginBottom: '0.75rem' }}>
            Processing Pipeline: {selectedFile?.name}
          </div>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            {PROCESSING_STEPS.map((step, idx) => {
              const isPassed = idx < currentStep;
              const isCurrent = idx === currentStep;
              return (
                <span
                  key={idx}
                  className="status-pill"
                  style={{
                    background: isPassed
                      ? 'rgba(16, 185, 129, 0.15)'
                      : isCurrent
                      ? 'rgba(99, 102, 241, 0.25)'
                      : 'rgba(255,255,255,0.03)',
                    borderColor: isCurrent ? 'var(--accent-indigo)' : 'var(--border-subtle)',
                    color: isPassed ? 'var(--accent-emerald)' : isCurrent ? '#fff' : 'var(--text-subtle)',
                  }}
                >
                  <span
                    className={`status-dot ${isPassed ? 'green' : isCurrent ? 'blue' : 'yellow'}`}
                  ></span>
                  {step}
                </span>
              );
            })}
          </div>
        </div>
      )}

      {uploadError && (
        <div className="glass-card" style={{ borderColor: 'var(--accent-rose)', color: '#fda4af', fontSize: '0.85rem' }}>
          ⚠️ Upload Error: {uploadError}
        </div>
      )}

      {/* Document Listing */}
      <DocumentList
        documents={documents}
        onViewChunks={(doc) => setInspectDoc(doc)}
        onDeleteDocument={handleDelete}
      />

      {/* Chunk Viewer Modal */}
      {inspectDoc && (
        <ChunkViewerModal
          documentId={inspectDoc.document_id}
          filename={inspectDoc.filename}
          onClose={() => setInspectDoc(null)}
        />
      )}
    </div>
  );
}
