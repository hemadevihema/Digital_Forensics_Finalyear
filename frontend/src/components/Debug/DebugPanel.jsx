import React, { useState, useEffect } from 'react';
import TimelineView from './TimelineView';
import RetrievalInspector from './RetrievalInspector';
import PromptInspector from './PromptInspector';
import ForensicInspector from './ForensicInspector';
import AttackGraphView from './AttackGraphView';
import { fetchRequestEvents, fetchRequestRetrievals, fetchRecentRequests } from '../../services/api';

export default function DebugPanel({ selectedRequestId, onSelectRequest }) {
  const [recentRequests, setRecentRequests] = useState([]);
  const [activeReqId, setActiveReqId] = useState(selectedRequestId || '');
  const [events, setEvents] = useState([]);
  const [retrievalData, setRetrievalData] = useState(null);
  const [subTab, setSubTab] = useState('forensics'); // 'forensics', 'timeline', 'retrievals', 'prompt'
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function loadRecent() {
      try {
        const reqs = await fetchRecentRequests();
        setRecentRequests(reqs || []);
        if (!activeReqId && reqs && reqs.length > 0) {
          setActiveReqId(reqs[0].request_id);
        }
      } catch (e) {
        // quiet fallback
      }
    }
    loadRecent();
  }, []);

  useEffect(() => {
    if (selectedRequestId && selectedRequestId !== activeReqId) {
      setActiveReqId(selectedRequestId);
    }
  }, [selectedRequestId]);

  useEffect(() => {
    if (!activeReqId) return;

    async function loadDetails() {
      setLoading(true);
      try {
        const [evData, retData] = await Promise.all([
          fetchRequestEvents(activeReqId).catch(() => ({ events: [] })),
          fetchRequestRetrievals(activeReqId).catch(() => null),
        ]);
        setEvents(evData.events || []);
        setRetrievalData(retData);
      } finally {
        setLoading(false);
      }
    }
    loadDetails();
  }, [activeReqId]);

  const metrics = retrievalData?.metrics || {};

  return (
    <div style={{ maxWidth: '1100px', margin: '0 auto', width: '100%', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#fff' }}>Forensic & Activity Inspector</h2>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
          Trace request lifecycle, inspect untrusted context boundaries, FAISS retrieval scores, and millisecond latencies.
        </p>
      </div>

      {/* Request Selector */}
      <div className="glass-card" style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '0.85rem 1.25rem' }}>
        <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontWeight: 500 }}>Select Request:</span>
        <select
          value={activeReqId}
          onChange={(e) => {
            setActiveReqId(e.target.value);
            if (onSelectRequest) onSelectRequest(e.target.value);
          }}
          style={{
            background: 'rgba(0,0,0,0.5)',
            border: '1px solid var(--border-subtle)',
            color: '#fff',
            padding: '0.45rem 0.85rem',
            borderRadius: '8px',
            fontFamily: 'var(--font-mono)',
            fontSize: '0.85rem',
            flex: 1,
            outline: 'none',
          }}
        >
          {recentRequests.length === 0 && <option value="">No requests recorded yet</option>}
          {recentRequests.map((r) => (
            <option key={r.request_id} value={r.request_id}>
              {r.request_id} — "{r.user_question?.slice(0, 45)}..." ({new Date(r.timestamp).toLocaleTimeString()})
            </option>
          ))}
        </select>
      </div>

      {activeReqId && (
        <>
          {/* Metrics Latency Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.75rem' }}>
            <div className="glass-card" style={{ padding: '0.85rem' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-subtle)', textTransform: 'uppercase' }}>Retrieval Time</div>
              <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--accent-cyan)', fontFamily: 'var(--font-mono)' }}>
                {metrics.retrieval_time_ms !== undefined ? `${metrics.retrieval_time_ms} ms` : 'N/A'}
              </div>
            </div>

            <div className="glass-card" style={{ padding: '0.85rem' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-subtle)', textTransform: 'uppercase' }}>Prompt Build Time</div>
              <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--accent-indigo)', fontFamily: 'var(--font-mono)' }}>
                {metrics.prompt_construction_time_ms !== undefined ? `${metrics.prompt_construction_time_ms} ms` : 'N/A'}
              </div>
            </div>

            <div className="glass-card" style={{ padding: '0.85rem' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-subtle)', textTransform: 'uppercase' }}>LLM Latency</div>
              <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--accent-amber)', fontFamily: 'var(--font-mono)' }}>
                {metrics.llm_latency_ms !== undefined ? `${metrics.llm_latency_ms} ms` : 'N/A'}
              </div>
            </div>

            <div className="glass-card" style={{ padding: '0.85rem' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-subtle)', textTransform: 'uppercase' }}>Injection Scan Time</div>
              <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#ec4899', fontFamily: 'var(--font-mono)' }}>
                {metrics.injection_scan_time_ms !== undefined ? `${metrics.injection_scan_time_ms} ms` : 'N/A'}
              </div>
            </div>

            <div className="glass-card" style={{ padding: '0.85rem' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-subtle)', textTransform: 'uppercase' }}>Total Request Latency</div>
              <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--accent-emerald)', fontFamily: 'var(--font-mono)' }}>
                {metrics.total_request_latency_ms !== undefined ? `${metrics.total_request_latency_ms} ms` : 'N/A'}
              </div>
            </div>
          </div>

          {/* Sub Navigation */}
          <div className="nav-tabs" style={{ alignSelf: 'flex-start' }}>
            <button
              className={`nav-tab ${subTab === 'forensics' ? 'active' : ''}`}
              onClick={() => setSubTab('forensics')}
            >
              🛡️ Injection Forensics & Attribution
            </button>
            <button
              className={`nav-tab ${subTab === 'attack-graph' ? 'active' : ''}`}
              onClick={() => setSubTab('attack-graph')}
            >
              🕸️ Causal Attack Graph
            </button>
            <button
              className={`nav-tab ${subTab === 'timeline' ? 'active' : ''}`}
              onClick={() => setSubTab('timeline')}
            >
              Event Timeline ({events.length})
            </button>
            <button
              className={`nav-tab ${subTab === 'retrievals' ? 'active' : ''}`}
              onClick={() => setSubTab('retrievals')}
            >
              Retrieval Scores ({retrievalData?.retrieved_chunks?.length || 0})
            </button>
            <button
              className={`nav-tab ${subTab === 'prompt' ? 'active' : ''}`}
              onClick={() => setSubTab('prompt')}
            >
              Prompt Boundaries & Context
            </button>
          </div>

          {/* Tab Content */}
          <div className="glass-card">
            {loading && <div style={{ color: 'var(--text-muted)' }}>Loading forensic data...</div>}
            {!loading && subTab === 'forensics' && <ForensicInspector retrievalData={retrievalData} />}
            {!loading && subTab === 'attack-graph' && <AttackGraphView requestId={activeReqId} />}
            {!loading && subTab === 'timeline' && <TimelineView events={events} />}
            {!loading && subTab === 'retrievals' && <RetrievalInspector retrievalData={retrievalData} />}
            {!loading && subTab === 'prompt' && <PromptInspector promptInspection={retrievalData?.prompt_inspection} />}
          </div>
        </>
      )}
    </div>
  );
}
