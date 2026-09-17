import React, { useState, useRef, useEffect } from 'react';
import MessageItem from './MessageItem';
import { sendChatMessage } from '../../services/api';

export default function ChatInterface({ sessionId, setSessionId, onSelectRequest }) {
  const [messages, setMessages] = useState([
    {
      role: 'ai',
      text: 'Hello! I am your observable AI Knowledge Assistant. Upload knowledge documents or ask questions about existing corporate policies.',
      timestamp: new Date().toISOString(),
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeModalMessage, setActiveModalMessage] = useState(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const query = input.trim();
    if (!query || loading) return;

    setInput('');
    const userMsg = {
      role: 'user',
      text: query,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const response = await sendChatMessage(query, sessionId);
      if (response.session_id && response.session_id !== sessionId) {
        setSessionId(response.session_id);
      }

      const aiMsg = {
        role: 'ai',
        text: response.answer,
        citations: response.citations,
        retrieved_chunks: response.retrieved_chunks,
        metrics: response.metrics,
        forensics: response.forensics,
        request_id: response.request_id,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, aiMsg]);

      // Inform parent about latest request for the forensic timeline
      if (onSelectRequest && response.request_id) {
        onSelectRequest(response.request_id);
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'ai',
          text: `Error: ${err.message || 'Failed to generate response.'}`,
          timestamp: new Date().toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const sampleQuestions = [
    "What is the annual leave allowance?",
    "Tell me about the 401(k) matching benefits.",
    "What are the corporate password requirements?",
    "What is the capital of France?"
  ];

  return (
    <div className="chat-container">
      <div className="messages-area">
        {messages.map((msg, index) => (
          <MessageItem
            key={index}
            message={msg}
            onViewContext={(m) => setActiveModalMessage(m)}
          />
        ))}

        {loading && (
          <div className="message-bubble message-ai" style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <span className="status-dot green" style={{ animation: 'pulse 1s infinite' }}></span>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              Retrieving relevant context from FAISS & generating response...
            </span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {messages.length === 1 && (
        <div style={{ marginBottom: '1rem' }}>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-subtle)', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Quick Prompts:
          </div>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            {sampleQuestions.map((q, idx) => (
              <button
                key={idx}
                className="btn-subtle"
                onClick={() => setInput(q)}
                style={{ fontSize: '0.8rem', padding: '0.4rem 0.8rem' }}
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      <form className="chat-input-bar" onSubmit={handleSubmit}>
        <input
          type="text"
          className="chat-input-field"
          placeholder="Ask a question about your uploaded documents..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
        />
        <button type="submit" className="btn-send" disabled={loading || !input.trim()}>
          <span>Send</span>
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <line x1="22" y1="2" x2="11" y2="13"/>
            <polygon points="22 2 15 22 11 13 2 9 22 2"/>
          </svg>
        </button>
      </form>

      {/* Retrieved Context Modal */}
      {activeModalMessage && (
        <div className="modal-backdrop" onClick={() => setActiveModalMessage(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div>
                <h3 style={{ fontSize: '1rem', color: '#fff' }}>Retrieved Chunks & Vector Scores</h3>
                <span style={{ fontSize: '0.75rem', color: 'var(--accent-cyan)', fontFamily: 'var(--font-mono)' }}>
                  Request ID: {activeModalMessage.request_id || 'N/A'}
                </span>
              </div>
              <button className="btn-subtle" onClick={() => setActiveModalMessage(null)}>✕</button>
            </div>
            <div className="modal-body">
              {activeModalMessage.retrieved_chunks?.map((chunk, i) => (
                <div key={i} className="glass-card" style={{ marginBottom: '1rem', background: 'rgba(255,255,255,0.03)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', fontSize: '0.8rem' }}>
                    <span style={{ color: 'var(--accent-cyan)', fontWeight: 600 }}>
                      Rank #{chunk.rank} — {chunk.source} (Page {chunk.page})
                    </span>
                    <span className="status-pill" style={{ fontSize: '0.7rem' }}>
                      Similarity Score: {chunk.score}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-subtle)', fontFamily: 'var(--font-mono)', marginBottom: '0.5rem' }}>
                    Chunk ID: {chunk.chunk_id} | Document ID: {chunk.document_id}
                  </div>
                  <div className="code-block" style={{ fontSize: '0.8rem', background: 'rgba(0,0,0,0.4)' }}>
                    {chunk.text}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
