import React from 'react';
import Navbar from '../../components/common/Navbar';
import MetricCard from '../../components/common/MetricCard';
import IncidentsShiftChart from '../../components/charts/IncidentsShiftChart';
import CameraFeedCard from '../../components/common/CameraFeedCard';
import { useData } from '../../context/DataContext';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, Download } from 'lucide-react';

export default function FactoryOverviewPage() {
  const { factory, metrics, incidents, cameras, sensors } = useData();
  const navigate = useNavigate();

  const totalSources = (cameras?.length || 0) + (sensors?.length || 0);
  const onlineSources =
    (cameras?.filter(c => c.status === 'Online' || c.status === 'available')?.length || 0) +
    (sensors?.filter(s => s.status === 'Online' || s.status === 'available')?.length || 0);

  const recentIncidents = (incidents || []).slice(0, 4);
  const featuredCameras = (cameras || []).slice(0, 3);

  const handleExport = () => {
    navigate('/reports');
  };

  return (
    <>
      <Navbar
        title="Factory Overview"
        subtitle={`${factory.name || 'Plant 1 · Menoufia'} · ${factory.shift || 'Day Shift'}`}
        rightActions={
          <>
            <span className="header-pill-info">
              <span className="badge-dot" />
              {totalSources > 0 ? `${onlineSources} of ${totalSources} sources online` : '0 sources configured'}
            </span>
            <button className="btn btn-primary" onClick={handleExport}>
              <Download size={15} />
              Export report
            </button>
          </>
        }
      />

      <div className="page-container">
        {/* Top 4 KPI Metrics */}
        <div className="metrics-grid">
          <MetricCard
            label="Active incidents"
            value={metrics.activeIncidents}
            delta={metrics.activeIncidentsDelta}
            deltaType="danger"
          />
          <MetricCard
            label="PPE compliance"
            value={metrics.ppeCompliance}
            delta={metrics.ppeComplianceDelta}
            deltaType="up"
          />
          <MetricCard
            label="Workers on floor"
            value={metrics.workersOnFloor}
            subValue={`of ${metrics.workersScheduled} scheduled`}
            delta=""
          />
          <MetricCard
            label="Average response"
            value={metrics.avgResponse}
            delta={metrics.avgResponseDelta}
            deltaType="down"
          />
        </div>

        {/* Shift Trends & Latest Alerts */}
        <div className="grid-2col-dashboard">
          {/* Incidents over the shift chart */}
          <div className="operix-card">
            <div className="card-header-flex">
              <div>
                <h3 className="card-title">Incidents over the shift</h3>
                <span className="card-subtitle">06:00 – 14:00</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: 'var(--text-muted)' }}>
                <span className="badge-dot" style={{ backgroundColor: '#3B6280' }} />
                <span>Incidents</span>
              </div>
            </div>

            <IncidentsShiftChart incidents={incidents} />
          </div>

          {/* Latest Alerts */}
          <div className="operix-card">
            <div className="card-header-flex">
              <h3 className="card-title">Latest alerts</h3>
              <Link
                to="/incidents"
                style={{
                  fontSize: '12px',
                  fontWeight: 600,
                  color: 'var(--primary)',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px'
                }}
              >
                View all <ArrowRight size={13} />
              </Link>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '0.5rem' }}>
              {recentIncidents.length === 0 ? (
                <div style={{ padding: '1.5rem 0', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
                  No incidents recorded in database yet.
                </div>
              ) : (
                recentIncidents.map((inc) => {
                  const color = inc.severity === 'High' || inc.severity === 'critical' ? '#EF4444' : '#F59E0B';
                  return (
                    <div key={inc.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                        <span className="badge-dot" style={{ backgroundColor: color, marginTop: '6px' }} />
                        <div>
                          <div style={{ fontWeight: 700, fontSize: '13.5px' }}>{inc.title || inc.event_type}</div>
                          <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                            {inc.zone || 'Factory Floor'} · {inc.timestamp || inc.created_at || ''}
                          </div>
                        </div>
                      </div>
                      <span className="badge-dot" style={{ backgroundColor: color }} />
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>

        {/* Live Operations Section */}
        <div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
            <span style={{ fontSize: '11px', fontWeight: 800, letterSpacing: '0.08em', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
              Live Operations
            </span>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              {featuredCameras.length} featured sources
            </span>
          </div>

          {featuredCameras.length === 0 ? (
            <div className="operix-card" style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
              No cameras configured in database yet. Add cameras from Settings &rarr; Cameras.
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1.25rem' }}>
              {featuredCameras.map((cam) => (
                <CameraFeedCard
                  key={cam.id}
                  camId={cam.code || cam.id}
                  title={cam.name || cam.zone || 'Camera'}
                  isLive={cam.status === 'Online' || cam.status === 'available'}
                  timestamp={`${cam.zone || 'Plant 1 · Menoufia'}`}
                  detections={[]}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
