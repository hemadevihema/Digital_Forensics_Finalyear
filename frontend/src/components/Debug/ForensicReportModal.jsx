import React, { useState, useEffect } from 'react';
import { fetchForensicReport, getForensicReportPdfUrl } from '../../services/api';

export default function ForensicReportModal({ requestId, onClose }) {
  const [reportData, setReportData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!requestId) return;
    setLoading(true);
    setError(null);

    fetchForensicReport(requestId, 'json')
      .then((data) => {
        setReportData(data);
      })
      .catch((err) => {
        setError(err.message);
      })
      .finally(() => {
        setLoading(false);
      });
  }, [requestId]);

  const handleExportJson = () => {
    if (!reportData) return;
    const blob = new Blob([JSON.stringify(reportData, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Forensic_Audit_Report_${requestId}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleExportPdf = () => {
    const pdfUrl = getForensicReportPdfUrl(requestId);
    window.open(pdfUrl, '_blank');
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        background: 'rgba(0, 0, 0, 0.82)',
        backdropFilter: 'blur(8px)',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '2rem',
      }}
    >
      <div
        className="glass-card"
        style={{
          width: '100%',
          maxWidth: '960px',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          background: 'rgba(15, 23, 42, 0.98)',
          border: '1px solid rgba(255, 255, 255, 0.15)',
          borderRadius: '14px',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.6)',
          overflow: 'hidden',
        }}
      >
        {/* Header Bar */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '1.2rem 1.5rem',
            borderBottom: '1px solid var(--border-subtle)',
            background: 'rgba(30, 41, 59, 0.5)',
          }}
        >
          <div>
            <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700, color: '#f8fafc' }}>
              PROMPT INJECTION FORENSIC AUDIT REPORT
            </h3>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              Request: <code style={{ color: '#38bdf8' }}>{requestId}</code>
            </span>
          </div>

          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
            <button
              onClick={handleExportJson}
              disabled={loading || !reportData}
              className="secondary-btn"
              style={{ fontSize: '0.8rem', padding: '0.4rem 0.8rem' }}
            >
              💾 Export JSON
            </button>
            <button
              onClick={handleExportPdf}
              disabled={loading || !reportData}
              className="primary-btn"
              style={{ fontSize: '0.8rem', padding: '0.4rem 0.8rem' }}
            >
              📥 Export PDF
            </button>
            <button
              onClick={onClose}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#94a3b8',
                fontSize: '1.4rem',
                cursor: 'pointer',
                padding: '0 0.5rem',
                lineHeight: 1,
              }}
            >
              &times;
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '1.5rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '1.5rem',
            fontSize: '0.85rem',
            color: '#cbd5e1',
          }}
        >
          {loading && (
            <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
              Compiling observable audit trail and forensic incident metrics...
            </div>
          )}

          {error && (
            <div style={{ padding: '1rem', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '8px', color: '#fca5a5' }}>
              Error loading forensic report: {error}
            </div>
          )}

          {!loading && reportData && (
            <>
              {/* 1. Incident Summary */}
              <div style={{ background: 'rgba(0,0,0,0.3)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                <h4 style={{ margin: '0 0 0.75rem 0', color: '#93c5fd', fontSize: '0.92rem' }}>
                  1. Incident Summary
                </h4>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.75rem' }}>
                  <div>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Report Reference: </span>
                    <div style={{ fontWeight: 600, color: '#fff' }}>{reportData.report_id}</div>
                  </div>
                  <div>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Classification: </span>
                    <div>
                      <span className={`forensic-badge ${reportData.incident.classification === 'MALICIOUS_INJECTION' ? 'badge-red' : reportData.incident.classification === 'SUSPICIOUS' ? 'badge-yellow' : 'badge-green'}`}>
                        {reportData.incident.classification}
                      </span>
                    </div>
                  </div>
                  <div>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Vector Provenance: </span>
                    <div>
                      <span className={`forensic-badge ${reportData.incident.source in { USER: 1, BOTH: 1 } ? 'badge-red' : reportData.incident.source === 'DOCUMENT' ? 'badge-yellow' : 'badge-green'}`}>
                        {reportData.incident.source}
                      </span>
                    </div>
                  </div>
                  <div>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Outcome Status: </span>
                    <div style={{ fontWeight: 600, color: '#38bdf8' }}>{reportData.outcome.status}</div>
                  </div>
                </div>
              </div>

              {/* 4. User Prompt */}
              <div>
                <h4 style={{ margin: '0 0 0.5rem 0', color: '#93c5fd', fontSize: '0.92rem' }}>
                  4. User Prompt Input
                </h4>
                <div style={{ padding: '0.75rem', background: 'rgba(0,0,0,0.4)', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.08)', fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: '#f1f5f9' }}>
                  {reportData.prompt.text}
                </div>
              </div>

              {/* 5 & 6. Detection Signals */}
              <div>
                <h4 style={{ margin: '0 0 0.5rem 0', color: '#93c5fd', fontSize: '0.92rem' }}>
                  5 & 6. Detection Results & Multi-Layer Signals
                </h4>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '0.75rem', marginTop: '0.5rem' }}>
                  <div style={{ padding: '0.6rem', background: 'rgba(0,0,0,0.3)', borderRadius: '6px' }}>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Layer 1 (Rule/Regex)</span>
                    <div style={{ fontSize: '1rem', fontWeight: 700, color: '#fff' }}>{reportData.detection.rule_score}</div>
                  </div>
                  <div style={{ padding: '0.6rem', background: 'rgba(0,0,0,0.3)', borderRadius: '6px' }}>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Layer 2 (TF-IDF)</span>
                    <div style={{ fontSize: '1rem', fontWeight: 700, color: '#fff' }}>{reportData.detection.tfidf_score}</div>
                  </div>
                  <div style={{ padding: '0.6rem', background: 'rgba(0,0,0,0.3)', borderRadius: '6px' }}>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Layer 3 (Semantic)</span>
                    <div style={{ fontSize: '1rem', fontWeight: 700, color: '#fff' }}>{reportData.detection.semantic_score}</div>
                  </div>
                  <div style={{ padding: '0.6rem', background: 'rgba(0,0,0,0.3)', borderRadius: '6px' }}>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Layer 4 (Gemini LLM)</span>
                    <div style={{ fontSize: '1rem', fontWeight: 700, color: '#fff' }}>{reportData.detection.llm_score}</div>
                  </div>
                  <div style={{ padding: '0.6rem', background: 'rgba(99, 102, 241, 0.15)', borderRadius: '6px', border: '1px solid rgba(99, 102, 241, 0.4)' }}>
                    <span style={{ fontSize: '0.7rem', color: '#c7d2fe' }}>Ensemble Risk Total</span>
                    <div style={{ fontSize: '1.1rem', fontWeight: 800, color: '#a5b4fc' }}>{reportData.detection.risk_score}</div>
                  </div>
                </div>
              </div>

              {/* 7. Source Attribution */}
              <div>
                <h4 style={{ margin: '0 0 0.5rem 0', color: '#93c5fd', fontSize: '0.92rem' }}>
                  7. Source Attribution
                </h4>
                <div style={{ padding: '0.75rem', background: 'rgba(0,0,0,0.3)', borderRadius: '6px' }}>
                  <p style={{ margin: '0 0 0.4rem 0' }}><strong>Attribution Verdict:</strong> {reportData.attribution.source}</p>
                  <p style={{ margin: '0 0 0.4rem 0' }}><strong>Forensic Reasoning:</strong> {reportData.detection.reasoning}</p>
                  {reportData.attribution.chunk_ids && reportData.attribution.chunk_ids.length > 0 && (
                    <p style={{ margin: 0, color: '#f87171' }}>
                      <strong>Compromised Document Chunks:</strong> {reportData.attribution.chunk_ids.join(', ')}
                    </p>
                  )}
                </div>
              </div>

              {/* 8. Retrieved Chunks Preview */}
              <div>
                <h4 style={{ margin: '0 0 0.5rem 0', color: '#93c5fd', fontSize: '0.92rem' }}>
                  8. Retrieved Documents & Chunks ({reportData.retrieval.length})
                </h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {reportData.retrieval.map((item) => (
                    <div
                      key={item.chunk_id}
                      style={{
                        padding: '0.6rem 0.8rem',
                        background: 'rgba(0,0,0,0.25)',
                        borderRadius: '6px',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        fontSize: '0.78rem',
                      }}
                    >
                      <div>
                        <span style={{ color: '#38bdf8', fontWeight: 600 }}>Rank #{item.rank}: </span>
                        <span>{item.source} (p.{item.page}) — </span>
                        <code style={{ color: '#cbd5e1' }}>{item.chunk_id}</code>
                      </div>
                      <span style={{ color: '#94a3b8', fontFamily: 'var(--font-mono)' }}>
                        Score: {item.score.toFixed(3)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* 11. Performance Metrics */}
              <div>
                <h4 style={{ margin: '0 0 0.5rem 0', color: '#93c5fd', fontSize: '0.92rem' }}>
                  11. Latency & Performance Breakdown
                </h4>
                <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', fontSize: '0.8rem' }}>
                  <div style={{ padding: '0.5rem 0.8rem', background: 'rgba(0,0,0,0.3)', borderRadius: '6px' }}>
                    Embedding: <strong>{reportData.performance.embedding_time_ms} ms</strong>
                  </div>
                  <div style={{ padding: '0.5rem 0.8rem', background: 'rgba(0,0,0,0.3)', borderRadius: '6px' }}>
                    Retrieval: <strong>{reportData.performance.retrieval_time_ms} ms</strong>
                  </div>
                  <div style={{ padding: '0.5rem 0.8rem', background: 'rgba(0,0,0,0.3)', borderRadius: '6px' }}>
                    LLM Latency: <strong>{reportData.performance.llm_latency_ms} ms</strong>
                  </div>
                  <div style={{ padding: '0.5rem 0.8rem', background: 'rgba(16, 185, 129, 0.15)', borderRadius: '6px', border: '1px solid rgba(16, 185, 129, 0.3)' }}>
                    Total Request: <strong style={{ color: '#34d399' }}>{reportData.performance.total_latency_ms} ms</strong>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
