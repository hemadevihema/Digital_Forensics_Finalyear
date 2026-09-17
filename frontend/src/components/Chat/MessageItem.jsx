import React, { useState } from 'react';
import CitationCard from './CitationCard';

export default function MessageItem({ message, onViewContext }) {
  const isUser = message.role === 'user';
  const [showForensics, setShowForensics] = useState(false);
  const forensics = message.forensics;

  const getAttributionBadge = () => {
    if (!forensics) return null;
    const attr = forensics.attribution;

    if (attr === 'USER') {
      return (
        <span className="forensic-badge badge-red" title={forensics.summary}>
          <span className="status-dot red"></span>
          Direct Injection Detected [USER]
        </span>
      );
    } else if (attr === 'DOCUMENT') {
      return (
        <span className="forensic-badge badge-yellow" title={forensics.summary}>
          <span className="status-dot yellow"></span>
          Indirect Injection Neutralized [DOCUMENT]
        </span>
      );
    } else if (attr === 'BOTH') {
      return (
        <span className="forensic-badge badge-red" title={forensics.summary}>
          <span className="status-dot red"></span>
          Multi-Vector Attack [USER & DOCUMENT]
        </span>
      );
    } else {
      return (
        <span className="forensic-badge badge-green" title="Scanned by 4-layer forensic detector">
          <span className="status-dot green"></span>
          Forensic Scan: Benign
        </span>
      );
    }
  };

  return (
    <div className={`message-bubble ${isUser ? 'message-user' : 'message-ai'}`}>
      <div className="message-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span>{isUser ? 'You' : 'AI Knowledge Assistant'}</span>
          {!isUser && getAttributionBadge()}
        </div>
        {message.timestamp && (
          <span style={{ fontSize: '0.72rem', opacity: 0.7 }}>
            {new Date(message.timestamp).toLocaleTimeString()}
          </span>
        )}
      </div>

      <div style={{ whiteSpace: 'pre-wrap', marginTop: '0.35rem' }}>{message.text}</div>

      {!isUser && forensics && (
        <div style={{ marginTop: '0.6rem' }}>
          <button
            type="button"
            className="btn-forensics-toggle"
            onClick={() => setShowForensics(!showForensics)}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
            </svg>
            {showForensics ? 'Hide Forensic Evidence' : 'Inspect Forensic Evidence & Layer Scores'}
          </button>

          {showForensics && (
            <div className="forensic-evidence-card">
              <div style={{ fontSize: '0.78rem', fontWeight: 600, marginBottom: '0.4rem', color: '#e0e7ff' }}>
                Multi-Layer Detection Breakdown ({forensics.scan_latency_ms}ms)
              </div>

              <div className="detector-scores-grid">
                <div className="score-pill">
                  <span className="score-label">1. Rule/Regex</span>
                  <span className={`score-value ${forensics.user_scan?.detector_results?.rule_regex_detector?.score > 0.5 ? 'text-red' : 'text-green'}`}>
                    {(forensics.user_scan?.detector_results?.rule_regex_detector?.score || 0).toFixed(2)}
                  </span>
                </div>

                <div className="score-pill">
                  <span className="score-label">2. TF-IDF Cosine</span>
                  <span className={`score-value ${forensics.user_scan?.detector_results?.tfidf_similarity_detector?.score > 0.4 ? 'text-red' : 'text-green'}`}>
                    {(forensics.user_scan?.detector_results?.tfidf_similarity_detector?.score || 0).toFixed(2)}
                  </span>
                </div>

                <div className="score-pill">
                  <span className="score-label">3. Semantic Vector</span>
                  <span className={`score-value ${forensics.user_scan?.detector_results?.semantic_embedding_detector?.score > 0.4 ? 'text-red' : 'text-green'}`}>
                    {(forensics.user_scan?.detector_results?.semantic_embedding_detector?.score || 0).toFixed(2)}
                  </span>
                </div>

                <div className="score-pill">
                  <span className="score-label">4. Contextual LLM</span>
                  <span className={`score-value ${forensics.user_scan?.detector_results?.gemini_contextual_classifier?.score > 0.5 ? 'text-red' : 'text-green'}`}>
                    {(forensics.user_scan?.detector_results?.gemini_contextual_classifier?.score || 0).toFixed(2)}
                  </span>
                </div>
              </div>

              <div style={{ marginTop: '0.4rem', fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                <strong>Attribution Analysis:</strong> {forensics.summary}
              </div>

              {forensics.culprit_chunk_ids && forensics.culprit_chunk_ids.length > 0 && (
                <div style={{ marginTop: '0.3rem', fontSize: '0.74rem', color: '#f87171' }}>
                  <strong>Culprit Chunks:</strong> {forensics.culprit_chunk_ids.join(', ')} (Document: {forensics.culprit_document_ids.join(', ')})
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {!isUser && message.citations && message.citations.length > 0 && (
        <div className="citations-box">
          <div className="citations-title">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="16" x2="12" y2="12"/>
              <line x1="12" y1="8" x2="12.01" y2="8"/>
            </svg>
            Sources Used
          </div>
          <div className="citation-chips">
            {message.citations.map((c, idx) => (
              <CitationCard
                key={idx}
                citation={c}
                onInspect={() => onViewContext && onViewContext(message)}
              />
            ))}
          </div>
        </div>
      )}

      {!isUser && message.retrieved_chunks && message.retrieved_chunks.length > 0 && (
        <button
          className="view-context-btn"
          onClick={() => onViewContext && onViewContext(message)}
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
            <circle cx="12" cy="12" r="3"/>
          </svg>
          View Retrieved Context ({message.retrieved_chunks.length} chunks)
        </button>
      )}
    </div>
  );
}
