const BASE_URL = ''; // Proxied via Vite

export async function fetchHealth() {
  const res = await fetch(`${BASE_URL}/health`);
  if (!res.ok) throw new Error('Health check failed');
  return res.json();
}

export async function fetchDocuments() {
  const res = await fetch(`${BASE_URL}/documents`);
  if (!res.ok) throw new Error('Failed to fetch documents');
  return res.json();
}

export async function uploadDocument(file, sessionId = 'DEFAULT-SESSION') {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('session_id', sessionId);

  const res = await fetch(`${BASE_URL}/documents/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || 'Upload failed');
  }
  return res.json();
}

export async function deleteDocument(documentId) {
  const res = await fetch(`${BASE_URL}/documents/${documentId}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to delete document');
  return res.json();
}

export async function fetchDocumentChunks(documentId) {
  const res = await fetch(`${BASE_URL}/documents/${documentId}/chunks`);
  if (!res.ok) throw new Error('Failed to fetch chunks');
  return res.json();
}

export async function sendChatMessage(userQuestion, sessionId = null, topK = 5) {
  const res = await fetch(`${BASE_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_question: userQuestion,
      session_id: sessionId,
      top_k: topK,
    }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || 'Chat query failed');
  }
  return res.json();
}

export async function fetchRequestEvents(requestId) {
  const res = await fetch(`${BASE_URL}/events/request/${requestId}`);
  if (!res.ok) throw new Error('Failed to fetch request events');
  return res.json();
}

export async function fetchRequestRetrievals(requestId) {
  const res = await fetch(`${BASE_URL}/requests/${requestId}/retrievals`);
  if (!res.ok) throw new Error('Failed to fetch retrieval details');
  return res.json();
}

export async function fetchRecentRequests() {
  const res = await fetch(`${BASE_URL}/events/requests`);
  if (!res.ok) throw new Error('Failed to fetch recent requests');
  return res.json();
}

export async function fetchForensicsEvaluation(includeLlm = false) {
  const res = await fetch(`${BASE_URL}/forensics/evaluate?include_llm=${includeLlm}`);
  if (!res.ok) throw new Error('Failed to run benchmark evaluation');
  return res.json();
}

export async function scanTextForensics(text, includeLlm = true) {
  const res = await fetch(`${BASE_URL}/forensics/scan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, include_llm: includeLlm }),
  });
  if (!res.ok) throw new Error('Forensic text scan failed');
  return res.json();
}

export async function fetchForensicsConfig() {
  const res = await fetch(`${BASE_URL}/forensics/config`);
  if (!res.ok) throw new Error('Failed to fetch forensics config');
  return res.json();
}

export async function fetchAttackGraph(requestId) {
  const res = await fetch(`${BASE_URL}/forensics/graph/${encodeURIComponent(requestId)}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Failed to fetch attack graph');
  }
  return res.json();
}

export async function fetchForensicReport(requestId, format = 'json') {
  const res = await fetch(`${BASE_URL}/forensics/report/${encodeURIComponent(requestId)}?format=${format}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Failed to fetch forensic report');
  }
  if (format === 'json') {
    return res.json();
  }
  return res.blob();
}

export function getForensicReportPdfUrl(requestId) {
  return `${BASE_URL}/forensics/report/${encodeURIComponent(requestId)}?format=pdf`;
}
