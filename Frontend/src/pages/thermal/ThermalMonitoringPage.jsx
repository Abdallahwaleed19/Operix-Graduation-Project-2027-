import React, { useState, useEffect } from 'react';
import Navbar from '../../components/common/Navbar';
import CameraFeedCard from '../../components/common/CameraFeedCard';
import { AlertCircle } from 'lucide-react';
import { sensorService } from '../../services';

export default function ThermalMonitoringPage() {
  const [sensorReadings, setSensorReadings] = useState([]);

  useEffect(() => {
    let isMounted = true;
    sensorService.getThermalReadings().then(readings => {
      if (isMounted) setSensorReadings(readings || []);
    });
    return () => { isMounted = false; };
  }, []);

  return (
    <>
      <Navbar
        title="Thermal Monitoring"
        subtitle="Temperature, fire and smoke detection"
      />

      <div className="page-container">
        <div className="grid-2col-settings">
          {/* Left Large Radiometric Stream Card */}
          <div className="operix-card">
            <div style={{ marginBottom: '1rem' }}>
              <h3 className="card-title">THM-01 · Boiler room</h3>
              <p className="card-subtitle">Radiometric stream · Updated 2 sec ago</p>
            </div>

            <CameraFeedCard
              camId="THM-01"
              title="Boiler"
              isLive={true}
              isThermal={true}
              temperature="92°C"
              minTemp="24°C"
              maxTemp="92°C"
              height={260}
            />

            {/* Thermal Range Bar */}
            <div style={{ marginTop: '1.5rem' }}>
              <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)' }}>
                Thermal range
              </span>
              <div className="thermal-gradient-bar" />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: 'var(--text-muted)' }}>
                <span>24°C</span>
                <span style={{ fontWeight: 700, color: '#EF4444' }}>92°C</span>
              </div>
            </div>
          </div>

          {/* Right Monitored Assets & Alarm Box */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            {/* Sensor readings list */}
            <div className="operix-card">
              <h3 className="card-title">Sensor readings</h3>
              <p className="card-subtitle" style={{ marginBottom: '1.5rem' }}>
                Plant 1 · All monitored assets
              </p>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                {sensorReadings.map((sr, idx) => (
                  <div key={idx}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', fontWeight: 600, marginBottom: '6px' }}>
                      <span style={{ color: 'var(--text-primary)' }}>{sr.label}</span>
                      <span style={{ color: sr.color, fontWeight: 700 }}>{sr.temp}</span>
                    </div>
                    <div style={{ height: '7px', backgroundColor: 'var(--border-subtle)', borderRadius: '9999px', overflow: 'hidden' }}>
                      <div
                        style={{
                          width: `${sr.percent}%`,
                          height: '100%',
                          backgroundColor: sr.color,
                          borderRadius: '9999px'
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Abnormal Temperature Callout Banner */}
            <div
              style={{
                backgroundColor: 'var(--bg-card-subtle)',
                border: '1px solid var(--border-color)',
                borderRadius: 'var(--radius-lg)',
                padding: '1.5rem'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#EF4444', fontWeight: 700, fontSize: '14px', marginBottom: '8px' }}>
                <AlertCircle size={18} />
                <span>Abnormal temperature</span>
              </div>
              <p style={{ fontSize: '13px', color: 'var(--text-primary)', marginBottom: '1.25rem' }}>
                Boiler core is 18°C above the rule limit.
              </p>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                Rule threshold: 74°C · Escalation active
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
