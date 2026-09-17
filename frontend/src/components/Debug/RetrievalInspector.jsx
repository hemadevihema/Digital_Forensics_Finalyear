import React from 'react';

export default function RetrievalInspector({ retrievalData }) {
  const chunks = retrievalData?.retrieved_chunks || [];

  if (chunks.length === 0) {
    return (
      <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', padding: '1.5rem 0' }}>
        No chunks were retrieved for this request.
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <div style={{ fontSize: '0.85rem', color: 'var(--accent-cyan)', fontWeight: 600 }}>
        Retrieved Chunks & Similarity Scores ({chunks.length} total)
      </div>

      {chunks.map((item, idx) => (
        <div key={idx} className="glass-card" style={{ background: 'rgba(255, 255, 255, 0.02)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <span style={{ fontWeight: 600, color: '#fff', fontSize: '0.85rem' }}>
              Rank #{item.rank} — {item.source} (Page {item.page})
            </span>
            <span className="status-pill" style={{ color: 'var(--accent-emerald)', borderColor: 'rgba(16, 185, 129, 0.3)' }}>
              Similarity Score: {item.score}
            </span>
          </div>

          <div style={{ display: 'flex', gap: '1rem', fontSize: '0.72rem', color: 'var(--text-subtle)', fontFamily: 'var(--font-mono)', marginBottom: '0.5rem' }}>
            <span>Document ID: {item.document_id}</span>
            <span>•</span>
            <span>Chunk ID: {item.chunk_id}</span>
          </div>

          <div className="code-block" style={{ fontSize: '0.78rem' }}>
            {item.text}
          </div>
        </div>
      ))}
    </div>
  );
}
