import React from 'react';

export default function IncidentsShiftChart() {
  // Points along shift: 06:00 (4), 07:00 (6), 08:00 (5), 09:00 (8), 10:00 (12), 11:00 (6), 12:00 (6), 13:00 (10), 14:00 (7)
  return (
    <div style={{ width: '100%', height: '220px', position: 'relative', marginTop: '0.5rem' }}>
      <svg
        viewBox="0 0 540 180"
        style={{ width: '100%', height: '150px', overflow: 'visible' }}
        preserveAspectRatio="none"
      >
        <defs>
          <linearGradient id="incidentGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#3B6280" stopOpacity="0.35" />
            <stop offset="100%" stopColor="#3B6280" stopOpacity="0.0" />
          </linearGradient>
        </defs>

        {/* Horizontal grid lines */}
        <line x1="30" y1="20" x2="530" y2="20" stroke="var(--border-subtle)" strokeWidth="1" />
        <line x1="30" y1="60" x2="530" y2="60" stroke="var(--border-subtle)" strokeWidth="1" />
        <line x1="30" y1="100" x2="530" y2="100" stroke="var(--border-subtle)" strokeWidth="1" />
        <line x1="30" y1="140" x2="530" y2="140" stroke="var(--border-subtle)" strokeWidth="1" />

        {/* Y Axis Labels */}
        <text x="12" y="24" fontSize="11" fill="var(--text-light)" textAnchor="end">12</text>
        <text x="12" y="64" fontSize="11" fill="var(--text-light)" textAnchor="end">8</text>
        <text x="12" y="104" fontSize="11" fill="var(--text-light)" textAnchor="end">4</text>
        <text x="12" y="144" fontSize="11" fill="var(--text-light)" textAnchor="end">0</text>

        {/* Area fill */}
        <path
          d="M 35 100 
             C 70 80, 100 95, 135 80 
             C 160 70, 180 85, 210 65 
             C 230 45, 250 20, 275 20 
             C 300 20, 320 75, 355 75 
             C 380 75, 410 40, 445 40 
             C 475 40, 500 70, 530 65 
             L 530 140 L 35 140 Z"
          fill="url(#incidentGradient)"
        />

        {/* Stroke Line */}
        <path
          d="M 35 100 
             C 70 80, 100 95, 135 80 
             C 160 70, 180 85, 210 65 
             C 230 45, 250 20, 275 20 
             C 300 20, 320 75, 355 75 
             C 380 75, 410 40, 445 40 
             C 475 40, 500 70, 530 65"
          fill="none"
          stroke="#3B6280"
          strokeWidth="2.5"
          strokeLinecap="round"
        />
      </svg>

      {/* X Axis Time Labels */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        paddingLeft: '35px',
        paddingRight: '10px',
        marginTop: '10px',
        fontSize: '11px',
        color: 'var(--text-light)'
      }}>
        <span>06:00</span>
        <span>08:00</span>
        <span>10:00</span>
        <span>12:00</span>
        <span>14:00</span>
      </div>
    </div>
  );
}
