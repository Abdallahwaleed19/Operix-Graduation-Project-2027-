import React from 'react';
import { Clock } from 'lucide-react';

/**
 * Displays a clear, honest indicator on modules awaiting Core Backend APIs (S-1 through S-4).
 */
export default function PendingBackendBadge({ dependency = 'Core API', moduleCode = '' }) {
  return (
    <span
      title={`Awaiting backend endpoint implementation (${dependency})`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        padding: '4px 10px',
        borderRadius: '999px',
        fontSize: '11.5px',
        fontWeight: 600,
        backgroundColor: 'rgba(245, 158, 11, 0.14)',
        color: '#f59e0b',
        border: '1px solid rgba(245, 158, 11, 0.35)',
        whiteSpace: 'nowrap'
      }}
    >
      <Clock size={12} />
      <span>{moduleCode ? `${moduleCode}: ` : ''}Pending Backend ({dependency})</span>
    </span>
  );
}
