import React, { useEffect, useState } from 'react';
import { fetchDocumentChunks } from '../../services/api';

export default function ChunkViewerModal({ documentId, filename, onClose }) {
  const [chunks, setChunks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function loadChunks() {
      try {
        setLoading(true);
        const data = await fetchDocumentChunks(documentId);
        setChunks(data.chunks || []);
      } catch (err) {
        setError(err.message || 'Failed to load chunks');
      } finally {
        setLoading(false);
      }
    }
    loadChunks();
  }, [documentId]);

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '850px' }}>
        <div className="modal-header">
          <div>
            <h3 style={{ fontSize: '1.05rem', color: '#fff' }}>Document Chunks Inspection</h3>
            <span style={{ fontSize: '0.78rem', color: 'var(--accent-cyan)', fontFamily: 'var(--font-mono)' }}>
              {filename} ({chunks.length} chunks)
            </span>
          </div>
          <button className="btn-subtle" onClick={onClose}>✕</button>
        </div>

        <div className="modal-body">
          {loading && <div style={{ color: 'var(--text-muted)' }}>Loading chunks from MongoDB Atlas...</div>}
          {error && <div style={{ color: 'var(--accent-rose)' }}>{error}</div>}

          {!loading && !error && chunks.length === 0 && (
            <div style={{ color: 'var(--text-muted)' }}>No chunks found for this document.</div>
          )}

          {!loading && chunks.map((c, i) => (
            <div key={i} className="glass-card" style={{ marginBottom: '1rem', background: 'rgba(255,255,255,0.02)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem', fontSize: '0.78rem' }}>
                <span style={{ color: 'var(--accent-indigo)', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>
                  {c.chunk_id}
                </span>
                <span style={{ color: 'var(--text-subtle)' }}>
                  Page {c.page} | Index: {c.chunk_index}
                </span>
              </div>
              <div className="code-block" style={{ fontSize: '0.8rem', background: 'rgba(0,0,0,0.35)' }}>
                {c.text}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
