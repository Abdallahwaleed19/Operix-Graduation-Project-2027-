import React, { useState } from 'react';
import Navbar from '../../components/common/Navbar';
import CameraFeedCard from '../../components/common/CameraFeedCard';
import { useAuth } from '../../context/AuthContext';

export default function LiveMonitoringPage() {
  const [activeZone, setActiveZone] = useState('All zones');
  const { isViewer } = useAuth();

  return (
    <>
      <Navbar
        title="Live Monitoring"
        subtitle="Real-time detections from CCTV and thermal sources"
        rightActions={
          <div className="tab-pills">
            {['All zones', 'Production', 'Storage'].map((zone) => (
              <button
                key={zone}
                className={`tab-pill-btn ${activeZone === zone ? 'active' : ''}`}
                onClick={() => setActiveZone(zone)}
              >
                {zone}
              </button>
            ))}
          </div>
        }
      />

      <div className="page-container">
        {/* 6 Camera Live Stream Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1.25rem' }}>
          {/* CAM-01 */}
          <CameraFeedCard
            camId="CAM-01"
            title="Gate"
            isLive={true}
            timestamp="09:42:03 / PLANT 1"
            detections={[
              { label: '#16 · PPE OK', type: 'success', left: '18%', top: '25%', width: '80px', height: '100px' },
              { label: '#32 · PPE OK', type: 'success', left: '55%', top: '25%', width: '80px', height: '100px' }
            ]}
          />

          {/* CAM-04 */}
          <CameraFeedCard
            camId="CAM-04"
            title="Press Line"
            isLive={true}
            timestamp="09:42:03 / PLANT 1"
            detections={[
              { label: 'Worker #14 · No helmet', type: 'danger', left: '16%', top: '25%', width: '90px', height: '105px' },
              { label: 'Worker #22 · PPE OK', type: 'success', left: '60%', top: '28%', width: '85px', height: '100px' }
            ]}
          />

          {/* CAM-07 */}
          <CameraFeedCard
            camId="CAM-07"
            title="Furnace"
            isLive={true}
            timestamp="09:42:03 / PLANT 1"
            detections={[
              { label: '#09 · Restricted zone', type: 'danger', left: '42%', top: '24%', width: '90px', height: '115px' }
            ]}
          />

          {/* CAM-02 */}
          <CameraFeedCard
            camId="CAM-02"
            title="Assembly"
            isLive={true}
            timestamp="09:42:03 / PLANT 1"
            detections={[
              { label: 'Worker #07 · Fatigue', type: 'warning', left: '34%', top: '26%', width: '95px', height: '110px' }
            ]}
          />

          {/* CAM-09 */}
          <CameraFeedCard
            camId="CAM-09"
            title="Loading"
            isLive={true}
            timestamp="09:42:03 / PLANT 1"
            detections={[
              { label: '#44 · No vest', type: 'warning', left: '20%', top: '26%', width: '85px', height: '105px' },
              { label: '#52 · PPE OK', type: 'success', left: '58%', top: '27%', width: '85px', height: '105px' }
            ]}
          />

          {/* THM-01 */}
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

        {/* Source Health Summary Card */}
        <div className="operix-card">
          <div className="card-header-flex" style={{ marginBottom: '1rem' }}>
            <h3 className="card-title">Source health</h3>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Last checked 2 seconds ago
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1.5rem' }}>
            <div>
              <div style={{ fontSize: '12.5px', color: 'var(--text-muted)', marginBottom: '4px' }}>CCTV cameras</div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
                <span style={{ fontSize: '24px', fontWeight: 800, color: 'var(--text-primary)' }}>18 / 18</span>
                <span className="status-pill online" style={{ padding: '2px 8px', fontSize: '11px' }}>
                  <span className="badge-dot" /> All systems online
                </span>
              </div>
            </div>

            <div>
              <div style={{ fontSize: '12.5px', color: 'var(--text-muted)', marginBottom: '4px' }}>Thermal cameras</div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
                <span style={{ fontSize: '24px', fontWeight: 800, color: 'var(--text-primary)' }}>4 / 4</span>
                <span className="status-pill online" style={{ padding: '2px 8px', fontSize: '11px' }}>
                  <span className="badge-dot" /> All systems online
                </span>
              </div>
            </div>

            <div>
              <div style={{ fontSize: '12.5px', color: 'var(--text-muted)', marginBottom: '4px' }}>Temp. sensors</div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
                <span style={{ fontSize: '24px', fontWeight: 800, color: 'var(--text-primary)' }}>12 / 13</span>
                <span className="status-pill warning" style={{ padding: '2px 8px', fontSize: '11px' }}>
                  <span className="badge-dot" /> 1 sensor offline
                </span>
              </div>
            </div>

            <div>
              <div style={{ fontSize: '12.5px', color: 'var(--text-muted)', marginBottom: '4px' }}>Data gaps today</div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
                <span style={{ fontSize: '24px', fontWeight: 800, color: 'var(--text-primary)' }}>1</span>
                <span className="status-pill warning" style={{ padding: '2px 8px', fontSize: '11px' }}>
                  <span className="badge-dot" /> Review required
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Live Feeds Footer Note */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: 'var(--text-muted)' }}>
          <span className="badge-dot" style={{ backgroundColor: '#10B981' }} />
          <strong style={{ color: 'var(--text-primary)' }}>LIVE FEEDS</strong>
          <span>AI detection is active across all connected sources</span>
        </div>
      </div>
    </>
  );
}
