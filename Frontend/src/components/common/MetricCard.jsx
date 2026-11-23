import React from 'react';

export default function MetricCard({ label, value, subValue, delta, deltaType = 'up' }) {
  return (
    <div className="metric-card">
      <span className="metric-label">{label}</span>
      <div className="metric-value-row">
        <span className="metric-value">{value}</span>
        {subValue && <span className="metric-value-sub">{subValue}</span>}
      </div>
      {delta && (
        <span className={`metric-delta ${deltaType}`}>
          {delta}
        </span>
      )}
    </div>
  );
}
