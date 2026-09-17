import React from 'react';

export default function TimelineView({ events }) {
  if (!events || events.length === 0) {
    return (
      <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', padding: '1.5rem 0' }}>
        No correlated events recorded for this request yet.
      </div>
    );
  }

  return (
    <div className="timeline-container">
      {events.map((evt, idx) => {
        const timeStr = new Date(evt.timestamp).toLocaleTimeString();
        return (
          <div key={evt.event_id || idx} className="timeline-item">
            <span className="timeline-time">{timeStr}</span>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span className="timeline-type">{evt.event_type}</span>
                <span className="timeline-component">{evt.component}</span>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-subtle)', fontFamily: 'var(--font-mono)' }}>
                  {evt.event_id}
                </span>
              </div>
              {evt.data && Object.keys(evt.data).length > 0 && (
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                  {Object.entries(evt.data).map(([k, v]) => (
                    <span key={k} style={{ marginRight: '0.75rem' }}>
                      <span style={{ color: 'var(--text-subtle)' }}>{k}:</span> {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {evt.duration_ms !== null && evt.duration_ms !== undefined && (
              <span className="timeline-duration">
                {evt.duration_ms} ms
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}
