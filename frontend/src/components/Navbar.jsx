import React from 'react';

export default function Navbar({ activeTab, setActiveTab, healthData, sessionId }) {
  const isConnected = healthData?.database?.connected;
  const isAtlas = healthData?.database?.storage_type === 'MongoDB Atlas';
  const hasGemini = healthData?.llm?.api_key_configured;

  return (
    <nav className="navbar">
      <div className="nav-brand">
        <div className="brand-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
          </svg>
        </div>
        <div>
          <div className="brand-title">Prompt Injection Forensics</div>
          <div className="brand-subtitle">Observable RAG Foundation</div>
        </div>
      </div>

      <div className="nav-tabs">
        <button
          className={`nav-tab ${activeTab === 'chat' ? 'active' : ''}`}
          onClick={() => setActiveTab('chat')}
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
          </svg>
          Chat & Citations
        </button>

        <button
          className={`nav-tab ${activeTab === 'documents' ? 'active' : ''}`}
          onClick={() => setActiveTab('documents')}
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
            <polyline points="10 9 9 9 8 9"/>
          </svg>
          Documents
        </button>

        <button
          className={`nav-tab ${activeTab === 'debug' ? 'active' : ''}`}
          onClick={() => setActiveTab('debug')}
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
          </svg>
          Activity & Timeline
        </button>
      </div>

      <div className="nav-status">
        <span className="status-pill" title={`Session ID: ${sessionId || 'Initializing'}`}>
          <span className="status-dot blue"></span>
          {sessionId ? sessionId.slice(0, 10) : 'INIT'}
        </span>

        <span className="status-pill" title={isAtlas ? 'Connected to MongoDB Atlas' : 'In-Memory DB Active'}>
          <span className={`status-dot ${isConnected ? 'green' : 'yellow'}`}></span>
          {isAtlas ? 'Atlas' : 'DB: Mock'}
        </span>

        <span className="status-pill" title={hasGemini ? 'Gemini API Key Configured' : 'Simulated LLM (No API Key)'}>
          <span className={`status-dot ${hasGemini ? 'green' : 'yellow'}`}></span>
          {hasGemini ? 'Gemini Live' : 'Simulated'}
        </span>
      </div>
    </nav>
  );
}
