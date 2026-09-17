import React from 'react';

export default function PromptInspector({ promptInspection }) {
  if (!promptInspection) {
    return (
      <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', padding: '1.5rem 0' }}>
        No prompt reconstruction data available for this request.
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div>
        <div style={{ fontSize: '0.8rem', color: 'var(--accent-indigo)', fontWeight: 600, marginBottom: '0.4rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          1. System Instructions (Trusted)
        </div>
        <div className="code-block" style={{ borderLeft: '3px solid var(--accent-indigo)' }}>
          {promptInspection.system_instructions}
        </div>
      </div>

      <div>
        <div style={{ fontSize: '0.8rem', color: 'var(--accent-amber)', fontWeight: 600, marginBottom: '0.4rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          2. Retrieved Untrusted Data Context (Quarantined)
        </div>
        <div className="code-block" style={{ borderLeft: '3px solid var(--accent-amber)' }}>
          {promptInspection.retrieved_untrusted_context}
        </div>
      </div>

      <div>
        <div style={{ fontSize: '0.8rem', color: 'var(--accent-cyan)', fontWeight: 600, marginBottom: '0.4rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          3. Full Constructed Prompt Dispatched to Gemini
        </div>
        <div className="code-block" style={{ borderLeft: '3px solid var(--accent-cyan)', maxHeight: '350px', overflowY: 'auto' }}>
          {promptInspection.full_constructed_prompt}
        </div>
      </div>
    </div>
  );
}
