import React from 'react';

export default function CitationCard({ citation, onInspect }) {
  return (
    <span
      className="citation-chip"
      onClick={onInspect}
      style={{ cursor: onInspect ? 'pointer' : 'default' }}
      title={`Chunk: ${citation.chunk_id} | Similarity: ${citation.score}`}
    >
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <polyline points="14 2 14 8 20 8"/>
      </svg>
      {citation.source} — Page {citation.page}
    </span>
  );
}
