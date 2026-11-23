import React, { useState, useEffect } from 'react';
import Navbar from '../../components/common/Navbar';
import { ArrowUpRight } from 'lucide-react';
import { analyticsService } from '../../services';

export default function HeatmapsTrackingPage() {
  const [timeRange, setTimeRange] = useState('Last 4 hours');
  const [trackedWorkers, setTrackedWorkers] = useState([]);

  useEffect(() => {
    let isMounted = true;
    analyticsService.getTrackedWorkers(timeRange).then(data => {
      if (isMounted) setTrackedWorkers(data || []);
    });
    return () => { isMounted = false; };
  }, [timeRange]);

  return (
    <>
      <Navbar
        title="Heatmaps & Tracking"
        subtitle="Movement density across cameras"
        rightActions={
          <select
            className="form-control form-select"
            style={{ width: '150px', padding: '0.45rem 0.8rem', fontSize: '13px' }}
            value={timeRange}
            onChange={e => setTimeRange(e.target.value)}
          >
            <option value="Last 1 hour">Last 1 hour</option>
            <option value="Last 4 hours">Last 4 hours</option>
            <option value="Current shift">Current shift</option>
            <option value="Full day">Full day</option>
          </select>
        }
      />

      <div className="page-container">
        <div className="grid-2col-settings">
          {/* Factory Floor Heatmap */}
          <div className="operix-card">
            <div className="card-header-flex">
              <div>
                <h3 className="card-title">Factory floor · last 4 hours</h3>
                <span className="card-subtitle">Plant 1 · Movement density</span>
              </div>
              <span className="camera-live-badge">
                <span className="badge-dot pulse" />
                Live
              </span>
            </div>

            {/* Floor Map Graphic with Heat Density */}
            <div className="floor-heatmap-container">
              {/* Heat Blurs */}
              <div className="heat-blob blue" />
              <div className="heat-blob yellow" />
              <div className="heat-blob red" />
              <div className="heat-blob green" />

              {/* Zone A */}
              <div className="floor-zone-box">
                <span className="zone-badge-label">Zone A</span>
                <div style={{ display: 'flex', gap: '8px', marginTop: 'auto', opacity: 0.3 }}>
                  <div style={{ width: '32px', height: '28px', background: '#64748B', borderRadius: '4px' }} />
                  <div style={{ width: '32px', height: '28px', background: '#64748B', borderRadius: '4px' }} />
                </div>
              </div>

              {/* Zone B */}
              <div className="floor-zone-box">
                <span className="zone-badge-label">Zone B</span>
                <div style={{ display: 'flex', gap: '8px', marginTop: 'auto', opacity: 0.3 }}>
                  <div style={{ width: '32px', height: '28px', background: '#64748B', borderRadius: '4px' }} />
                  <div style={{ width: '32px', height: '28px', background: '#64748B', borderRadius: '4px' }} />
                </div>
              </div>

              {/* Zone C */}
              <div className="floor-zone-box">
                <span className="zone-badge-label">Zone C</span>
                <div style={{ display: 'flex', gap: '8px', marginTop: 'auto', opacity: 0.3 }}>
                  <div style={{ width: '32px', height: '28px', background: '#64748B', borderRadius: '4px' }} />
                  <div style={{ width: '32px', height: '28px', background: '#64748B', borderRadius: '4px' }} />
                </div>
              </div>

              {/* Zone D - Restricted */}
              <div className="floor-zone-box restricted">
                <span className="zone-badge-label restricted">Zone D · Restricted</span>
                <div style={{ display: 'flex', gap: '8px', marginTop: 'auto', opacity: 0.3 }}>
                  <div style={{ width: '48px', height: '28px', background: '#EF4444', borderRadius: '4px' }} />
                  <div style={{ width: '48px', height: '28px', background: '#EF4444', borderRadius: '4px' }} />
                </div>
              </div>
            </div>

            {/* Heat Gradient Legend */}
            <div style={{ marginTop: '1.25rem' }}>
              <span style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
                Movement density
              </span>
              <div style={{ display: 'flex', gap: '4px', width: '180px', height: '6px' }}>
                <div style={{ flex: 1, backgroundColor: '#94A3B8', borderRadius: '2px' }} />
                <div style={{ flex: 1, backgroundColor: '#648BA8', borderRadius: '2px' }} />
                <div style={{ flex: 1, backgroundColor: '#3B6280', borderRadius: '2px' }} />
                <div style={{ flex: 1, backgroundColor: '#D97706', borderRadius: '2px' }} />
                <div style={{ flex: 1, backgroundColor: '#DC2626', borderRadius: '2px' }} />
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', width: '180px', fontSize: '11px', color: 'var(--text-light)', marginTop: '4px' }}>
                <span>Low</span>
                <span>High</span>
              </div>
            </div>

            <div style={{ marginTop: '1.5rem', color: '#DC2626', fontSize: '12.5px', fontWeight: 600 }}>
              Zone D is restricted to authorized personnel.
            </div>
          </div>

          {/* Right Tracked Workers */}
          <div className="operix-card">
            <h3 className="card-title">Tracked workers</h3>
            <p className="card-subtitle" style={{ marginBottom: '1.25rem' }}>
              Cross-camera identity continuity
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {trackedWorkers.map((w, idx) => (
                <div
                  key={idx}
                  style={{
                    backgroundColor: 'var(--bg-card-subtle)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '10px',
                    padding: '1rem 1.25rem',
                    position: 'relative'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '11px', fontWeight: 800, color: 'var(--primary)', letterSpacing: '0.04em' }}>
                      {w.id}
                    </span>
                    <ArrowUpRight size={16} color="var(--text-light)" />
                  </div>

                  <div style={{ fontSize: '15px', fontWeight: 800, color: 'var(--text-primary)', margin: '4px 0 8px' }}>
                    {w.route}
                  </div>

                  <div style={{
                    fontSize: '12px',
                    fontWeight: 600,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    color: w.statusType === 'danger' ? '#EF4444' : w.statusType === 'success' ? '#10B981' : '#F59E0B'
                  }}>
                    <span
                      className="badge-dot"
                      style={{
                        backgroundColor: w.statusType === 'danger' ? '#EF4444' : w.statusType === 'success' ? '#10B981' : '#F59E0B'
                      }}
                    />
                    {w.status}
                  </div>
                </div>
              ))}
            </div>

            <div style={{ marginTop: '2.5rem', fontSize: '12px', color: 'var(--text-muted)' }}>
              Tracking confidence ≥ 95%
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
