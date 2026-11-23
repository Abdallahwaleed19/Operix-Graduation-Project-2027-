import React from 'react';
import Navbar from '../../components/common/Navbar';
import MetricCard from '../../components/common/MetricCard';
import IncidentsShiftChart from '../../components/charts/IncidentsShiftChart';
import CameraFeedCard from '../../components/common/CameraFeedCard';
import { useData } from '../../context/DataContext';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, Download } from 'lucide-react';

export default function FactoryOverviewPage() {
  const { factory, metrics } = useData();
  const navigate = useNavigate();

  const handleExport = () => {
    navigate('/reports');
  };

  return (
    <>
      <Navbar
        title="Factory Overview"
        subtitle={`${factory.name} · ${factory.shift}`}
        rightActions={
          <>
            <span className="header-pill-info">
              <span className="badge-dot" />
              All 24 sources online
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

            <IncidentsShiftChart />
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
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                  <span className="badge-dot" style={{ backgroundColor: '#EF4444', marginTop: '6px' }} />
                  <div>
                    <div style={{ fontWeight: 700, fontSize: '13.5px' }}>Missing helmet</div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Zone B · Press Line · 09:42</div>
                  </div>
                </div>
                <span className="badge-dot" style={{ backgroundColor: '#EF4444' }} />
              </div>

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                  <span className="badge-dot" style={{ backgroundColor: '#EF4444', marginTop: '6px' }} />
                  <div>
                    <div style={{ fontWeight: 700, fontSize: '13.5px' }}>Restricted-zone entry</div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Zone D · Furnace · 09:18</div>
                  </div>
                </div>
                <span className="badge-dot" style={{ backgroundColor: '#EF4444' }} />
              </div>

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                  <span className="badge-dot" style={{ backgroundColor: '#F59E0B', marginTop: '6px' }} />
                  <div>
                    <div style={{ fontWeight: 700, fontSize: '13.5px' }}>Fatigue signs</div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Zone A · Assembly · 08:55</div>
                  </div>
                </div>
                <span className="badge-dot" style={{ backgroundColor: '#F59E0B' }} />
              </div>

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                  <span className="badge-dot" style={{ backgroundColor: '#EF4444', marginTop: '6px' }} />
                  <div>
                    <div style={{ fontWeight: 700, fontSize: '13.5px' }}>Abnormal temperature</div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Zone F · Boiler · 08:31</div>
                  </div>
                </div>
                <span className="badge-dot" style={{ backgroundColor: '#EF4444' }} />
              </div>
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
              3 featured sources · AI detection enabled
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1.25rem' }}>
            {/* Feed 1: CAM-04 */}
            <CameraFeedCard
              camId="CAM-04"
              title="Press Line"
              isLive={true}
              timestamp="09:42:03 / PLANT 1"
              detections={[
                { label: 'Worker #14 · No helmet', type: 'danger', left: '16%', top: '24%', width: '90px', height: '110px' },
                { label: 'Worker #22 · PPE OK', type: 'success', left: '60%', top: '28%', width: '85px', height: '105px' }
              ]}
            />

            {/* Feed 2: CAM-02 */}
            <CameraFeedCard
              camId="CAM-02"
              title="Assembly"
              isLive={true}
              timestamp="09:42:03 / PLANT 1"
              detections={[
                { label: 'Worker #07 · Fatigue', type: 'warning', left: '35%', top: '26%', width: '100px', height: '115px' }
              ]}
            />

            {/* Feed 3: THM-01 */}
            <CameraFeedCard
              camId="THM-01"
              title="Boiler"
              isLive={true}
              isThermal={true}
              temperature="92°C"
              minTemp="24°C"
              maxTemp="92°C"
            />
          </div>
        </div>
      </div>
    </>
  );
}
