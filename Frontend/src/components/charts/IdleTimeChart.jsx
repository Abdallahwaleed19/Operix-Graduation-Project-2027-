import React from 'react';
import { initialIdleTimeZones } from '../../data/mockData';

export default function IdleTimeChart({ data }) {
  const zones = data && data.length > 0 ? data : initialIdleTimeZones;

  return (
    <div style={{ width: '100%', marginTop: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {zones.map((z, i) => (
        <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', fontWeight: 600 }}>
            <span style={{ color: 'var(--text-primary)' }}>{z.name}</span>
            <span style={{ color: z.isHigh ? '#D97706' : 'var(--text-muted)' }}>{z.percent}%</span>
          </div>

          <div style={{ width: '100%', height: '8px', backgroundColor: 'var(--border-subtle)', borderRadius: '9999px', overflow: 'hidden' }}>
            <div
              style={{
                width: `${(z.percent / 30) * 100}%`,
                height: '100%',
                backgroundColor: z.isHigh ? '#D97706' : '#3B6280',
                borderRadius: '9999px',
                transition: 'width 0.5s ease'
              }}
            />
          </div>
        </div>
      ))}

      <div style={{
        marginTop: '0.75rem',
        padding: '12px 16px',
        borderRadius: '8px',
        backgroundColor: 'var(--bg-card-subtle)',
        border: '1px solid var(--border-subtle)',
        fontSize: '12.5px',
        color: 'var(--text-secondary)'
      }}>
        Zone C has the highest idle time at 24%.
      </div>
    </div>
  );
}
