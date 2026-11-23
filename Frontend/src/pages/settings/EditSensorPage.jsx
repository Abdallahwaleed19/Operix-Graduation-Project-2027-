import React, { useState } from 'react';
import Navbar from '../../components/common/Navbar';
import { useParams, useNavigate } from 'react-router-dom';
import { useData } from '../../context/DataContext';
import { ArrowLeft, RefreshCw } from 'lucide-react';

export default function EditSensorPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { sensors, updateSensor } = useData();

  const sensor = sensors.find(s => s.id === id) || sensors[3] || {
    id: 'TMP-07',
    name: 'TMP-07 · Furnace',
    department: 'Production',
    type: 'Temperature',
    unit: '°C',
    location: 'Furnace bay',
    samplingSeconds: 10,
    deviceKey: '•••• •••• •••• (stored as a hash)',
    active: true,
    status: 'Offline',
    lastReading: '71.4 °C · 06:39'
  };

  const [name, setName] = useState(sensor.name);
  const [department, setDepartment] = useState(sensor.department);
  const [sensorType, setSensorType] = useState(sensor.type);
  const [unit, setUnit] = useState(sensor.unit);
  const [location, setLocation] = useState(sensor.location);
  const [samplingSeconds, setSamplingSeconds] = useState(sensor.samplingSeconds || 10);
  const [deviceKey, setDeviceKey] = useState(sensor.deviceKey);
  const [active, setActive] = useState(sensor.active);

  const handleSave = (e) => {
    e.preventDefault();
    updateSensor(sensor.id, {
      name,
      department,
      type: sensorType,
      unit,
      location,
      samplingSeconds: parseInt(samplingSeconds),
      sampling: `every ${samplingSeconds} s`,
      active
    });
    navigate('/settings/sensors');
  };

  const handleRegenerateKey = () => {
    setDeviceKey('opx_' + Math.random().toString(36).substring(2, 14) + ' (new hash)');
  };

  return (
    <>
      <Navbar
        title={`Edit sensor · ${sensor.id}`}
        subtitle="Update sensor details and sampling"
        backTo="/settings/sensors"
        backLabel="Back to Sensors"
      />

      <div className="page-container">
        <form onSubmit={handleSave} className="grid-2col-settings">
          {/* Left Form */}
          <div className="operix-card">
            <h3 className="card-title">Sensor details</h3>
            <p className="card-subtitle" style={{ marginBottom: '1.5rem' }}>
              How this sensor is identified and sampled
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem' }}>
              <div className="form-group">
                <label className="form-label">Name</label>
                <input
                  type="text"
                  className="form-control"
                  value={name}
                  onChange={e => setName(e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Department (optional)</label>
                <select
                  className="form-control form-select"
                  value={department}
                  onChange={e => setDepartment(e.target.value)}
                >
                  <option value="Production">Production</option>
                  <option value="Storage">Storage</option>
                  <option value="Security">Security</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Sensor type</label>
                <select
                  className="form-control form-select"
                  value={sensorType}
                  onChange={e => setSensorType(e.target.value)}
                >
                  <option value="Temperature">Temperature</option>
                  <option value="Pressure">Pressure</option>
                  <option value="Humidity">Humidity</option>
                  <option value="Vibration">Vibration</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Unit</label>
                <input
                  type="text"
                  className="form-control font-mono"
                  value={unit}
                  onChange={e => setUnit(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Location label (optional)</label>
                <input
                  type="text"
                  className="form-control"
                  value={location}
                  onChange={e => setLocation(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Sampling interval (seconds)</label>
                <input
                  type="number"
                  className="form-control font-mono"
                  value={samplingSeconds}
                  onChange={e => setSamplingSeconds(e.target.value)}
                />
              </div>
            </div>

            {/* Device Key */}
            <div className="form-group" style={{ marginTop: '0.5rem' }}>
              <label className="form-label">Device key</label>
              <div style={{ display: 'flex', gap: '10px' }}>
                <input
                  type="text"
                  className="form-control font-mono"
                  value={deviceKey}
                  readOnly
                />
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={handleRegenerateKey}
                >
                  Regenerate
                </button>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', margin: '1.75rem 0' }}>
              <label className="switch-wrapper">
                <input
                  type="checkbox"
                  className="switch-input"
                  checked={active}
                  onChange={e => setActive(e.target.checked)}
                />
                <span className="switch-slider" />
              </label>
              <span style={{ fontSize: '13px', fontWeight: 600 }}>
                Active · readings are accepted
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--border-color)', paddingTop: '1.5rem' }}>
              <button
                type="button"
                className="btn btn-danger-outline"
                onClick={() => {
                  if (confirm('Disable readings for this sensor?')) {
                    navigate('/settings/sensors');
                  }
                }}
              >
                Disable sensor
              </button>

              <div style={{ display: 'flex', gap: '10px' }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => navigate('/settings/sensors')}
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Save changes
                </button>
              </div>
            </div>
          </div>

          {/* Right Status Panel */}
          <div className="operix-card" style={{ height: 'fit-content' }}>
            <h3 className="card-title">Source status</h3>
            <p className="card-subtitle" style={{ marginBottom: '1.5rem' }}>
              Reported by the sensor
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', fontSize: '13px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: 'var(--text-muted)' }}>Status</span>
                <span className={`status-pill ${sensor.status === 'Online' ? 'online' : 'danger'}`}>
                  <span className="badge-dot" /> {sensor.status}
                </span>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: 'var(--text-muted)' }}>Status since</span>
                <span style={{ fontWeight: 600 }}>06:40 today</span>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: 'var(--text-muted)' }}>Last reading</span>
                <span style={{ fontWeight: 700, fontFamily: 'JetBrains Mono' }}>
                  {sensor.lastReading || '71.4 °C · 06:39'}
                </span>
              </div>
            </div>
          </div>
        </form>
      </div>
    </>
  );
}
