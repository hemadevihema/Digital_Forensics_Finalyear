import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import ChatInterface from './components/Chat/ChatInterface';
import DocumentManager from './components/Documents/DocumentManager';
import DebugPanel from './components/Debug/DebugPanel';
import { fetchHealth, fetchDocuments } from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('chat'); // 'chat' | 'documents' | 'debug'
  const [healthData, setHealthData] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [sessionId, setSessionId] = useState('');
  const [selectedRequestId, setSelectedRequestId] = useState('');

  const refreshHealth = async () => {
    try {
      const data = await fetchHealth();
      setHealthData(data);
    } catch (err) {
      console.error('Health check error:', err);
    }
  };

  const refreshDocs = async () => {
    try {
      const docs = await fetchDocuments();
      setDocuments(docs || []);
    } catch (err) {
      console.error('Fetch docs error:', err);
    }
  };

  useEffect(() => {
    // Generate initial session ID
    const sid = 'SES-' + Math.random().toString(36).substring(2, 8).toUpperCase();
    setSessionId(sid);

    refreshHealth();
    refreshDocs();

    const interval = setInterval(() => {
      refreshHealth();
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="app-container">
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        healthData={healthData}
        sessionId={sessionId}
      />

      <main className="main-content">
        {activeTab === 'chat' && (
          <ChatInterface
            sessionId={sessionId}
            setSessionId={setSessionId}
            onSelectRequest={(reqId) => setSelectedRequestId(reqId)}
          />
        )}

        {activeTab === 'documents' && (
          <DocumentManager
            documents={documents}
            refreshDocuments={refreshDocs}
            sessionId={sessionId}
          />
        )}

        {activeTab === 'debug' && (
          <DebugPanel
            selectedRequestId={selectedRequestId}
            onSelectRequest={(reqId) => setSelectedRequestId(reqId)}
          />
        )}
      </main>
    </div>
  );
}
