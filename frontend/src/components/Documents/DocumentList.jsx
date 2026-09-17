import React from 'react';

export default function DocumentList({ documents, onViewChunks, onDeleteDocument }) {
  if (!documents || documents.length === 0) {
    return (
      <div className="glass-card" style={{ textAlign: 'center', padding: '3rem 1rem', color: 'var(--text-muted)' }}>
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ margin: '0 auto 0.75rem', opacity: 0.5 }}>
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
        </svg>
        <p style={{ fontSize: '0.95rem', fontWeight: 500 }}>No documents have been indexed yet.</p>
        <p style={{ fontSize: '0.8rem', color: 'var(--text-subtle)', marginTop: '0.25rem' }}>
          Upload PDF, TXT, Markdown, or DOCX files to populate your FAISS vector store.
        </p>
      </div>
    );
  }

  return (
    <div className="doc-grid">
      {documents.map((doc) => {
        const isIndexed = doc.status === 'indexed';
        const isFailed = doc.status === 'failed';

        return (
          <div key={doc.document_id} className="glass-card doc-card">
            <div>
              <div className="doc-card-header">
                <span className="doc-name">{doc.filename}</span>
                <span className="status-pill">
                  <span className={`status-dot ${isIndexed ? 'green' : isFailed ? 'yellow' : 'blue'}`}></span>
                  {isIndexed ? 'Indexed ✓' : doc.status}
                </span>
              </div>

              <div className="doc-meta">
                <span>Pages: {doc.page_count}</span>
                <span>•</span>
                <span>Chunks: {doc.chunk_count}</span>
                <span>•</span>
                <span>{(doc.file_size / 1024).toFixed(1)} KB</span>
              </div>

              <div style={{ fontSize: '0.72rem', color: 'var(--text-subtle)', fontFamily: 'var(--font-mono)', marginTop: '0.35rem' }}>
                ID: {doc.document_id}
              </div>
            </div>

            <div className="doc-actions">
              <button
                className="btn-subtle"
                onClick={() => onViewChunks(doc)}
                title="Inspect all text chunks and metadata"
              >
                View Chunks
              </button>
              <button
                className="btn-subtle btn-danger"
                onClick={() => onDeleteDocument(doc.document_id)}
                title="Remove from MongoDB Atlas and rebuild FAISS index"
              >
                Delete
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
