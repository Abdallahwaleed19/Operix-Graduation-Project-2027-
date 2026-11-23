import React from 'react';
import { initialWorkforceDepartments } from '../../data/mockData';

export default function WorkforceDeptChart({ data }) {
  const departments = data && data.length > 0 ? data : initialWorkforceDepartments;

  return (
    <div style={{ width: '100%', marginTop: '1rem' }}>
      <div style={{ display: 'flex', height: '200px', alignItems: 'flex-end', gap: '24px', paddingLeft: '32px', position: 'relative' }}>
        {/* Y Axis Guide Lines */}
        <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, display: 'flex', flexDirection: 'column', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-light)', width: '28px' }}>
          <span>400</span>
          <span>300</span>
          <span>200</span>
          <span>100</span>
          <span>0</span>
        </div>

        <div style={{ position: 'absolute', left: '35px', right: 0, top: 0, borderTop: '1px solid var(--border-subtle)' }} />
        <div style={{ position: 'absolute', left: '35px', right: 0, top: '25%', borderTop: '1px solid var(--border-subtle)' }} />
        <div style={{ position: 'absolute', left: '35px', right: 0, top: '50%', borderTop: '1px solid var(--border-subtle)' }} />
        <div style={{ position: 'absolute', left: '35px', right: 0, top: '75%', borderTop: '1px solid var(--border-subtle)' }} />
        <div style={{ position: 'absolute', left: '35px', right: 0, bottom: 0, borderTop: '1px solid var(--border-subtle)' }} />

        {/* Bars */}
        <div style={{ display: 'flex', width: '100%', height: '100%', alignItems: 'flex-end', justifyContent: 'space-around', zIndex: 1 }}>
          {departments.map((d, i) => (
            <div key={i} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: '48px', height: '100%', justifyContent: 'flex-end' }}>
              <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px' }}>
                {d.hours}
              </span>
              <div
                style={{
                  width: '100%',
                  height: `${d.heightPercent}%`,
                  background: 'linear-gradient(180deg, #648BA8 0%, #3B6280 100%)',
                  borderRadius: '6px 6px 0 0',
                  transition: 'height 0.4s ease'
                }}
              />
            </div>
          ))}
        </div>
      </div>

      {/* X Axis Labels */}
      <div style={{ display: 'flex', justifyContent: 'space-around', paddingLeft: '32px', marginTop: '12px', fontSize: '12px', color: 'var(--text-secondary)', fontWeight: 500 }}>
        {departments.map((d, i) => (
          <span key={i} style={{ width: '48px', textAlign: 'center' }}>{d.name}</span>
        ))}
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '1.5rem', paddingTop: '1rem', borderTop: '1px solid var(--border-subtle)', fontSize: '12px' }}>
        <span style={{ color: 'var(--text-muted)' }}>Total net hours</span>
        <span style={{ fontWeight: 800, color: 'var(--text-primary)', fontSize: '14px' }}>1,284 h</span>
      </div>
    </div>
  );
}
