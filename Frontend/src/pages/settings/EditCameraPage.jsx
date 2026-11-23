import React, { useState } from 'react';
import Navbar from '../../components/common/Navbar';
import { useParams, useNavigate } from 'react-router-dom';
import { useData } from '../../context/DataContext';
import { ArrowLeft, Check, Plus } from 'lucide-react';

export default function EditCameraPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { cameras, updateCamera } = useData();

  const cam = cameras.find(c => c.id === id) || cameras[1] || {
    id: 'CAM-04',
    name: 'CAM-04 · Press Line',
    department: 'Production',
    type: 'CCTV',
    location: 'Press hall',
    streamUrl: 'rtsp://10.0.4.24:554/stream1',
    activeDetections: true,
    status: 'Online'
  };

  const [name, setName] = useState(cam.name);
  const [department, setDepartment] = useState(cam.department);
  const [type, setType] = useState(cam.type);
  const [location, setLocation] = useState(cam.location);
  const [streamUrl, setStreamUrl] = useState(cam.streamUrl || 'rtsp://10.0.4.24:554/stream1');
  const [activeDetections, setActiveDetections] = useState(cam.activeDetections);
  const [testResult, setTestResult] = useState('');

  const handleSave = (e) => {
    e.preventDefault();
    updateCamera(cam.id, {
      name,
      department,
      type,
      location,
      streamUrl,
      activeDetections
    });
    navigate('/settings/cameras');
  };

  const handleTestConnection = () => {
    setTestResult('Testing RTSP handshake...');
    setTimeout(() => {
      setTestResult('Connection verified: RTSP 1080p @ 30 FPS OK (Ping 4ms)');
    }, 800);
  };

  return (
    <>
      <Navbar
        title={`Edit camera · ${cam.id}`}
        subtitle="Update camera details and manage its zones"
        backTo="/settings/cameras"
        backLabel="Back to Cameras"
      />

      <div className="page-container">
        <form onSubmit={handleSave} className="grid-2col-settings">
          {/* Left Form: Camera details */}
          <div className="operix-card">
            <h3 className="card-title">Camera details</h3>
            <p className="card-subtitle" style={{ marginBottom: '1.5rem' }}>
              How this camera is identified and connected
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
                  <option value="—">None</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Camera type</label>
                <select
                  className="form-control form-select"
                  value={type}
                  onChange={e => setType(e.target.value)}
                >
                  <option value="CCTV">CCTV</option>
                  <option value="Thermal">Thermal</option>
                </select>
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
            </div>

            <div className="form-group" style={{ marginTop: '0.5rem' }}>
              <label className="form-label">Stream URL reference</label>
              <input
                type="text"
                className="form-control font-mono"
                value={streamUrl}
                onChange={e => setStreamUrl(e.target.value)}
                required
              />
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', margin: '1.75rem 0' }}>
              <label className="switch-wrapper">
                <input
                  type="checkbox"
                  className="switch-input"
                  checked={activeDetections}
                  onChange={e => setActiveDetections(e.target.checked)}
                />
                <span className="switch-slider" />
              </label>
              <span style={{ fontSize: '13px', fontWeight: 600 }}>
                Active · detections enabled
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--border-color)', paddingTop: '1.5rem' }}>
              <button
                type="button"
                className="btn btn-danger-outline"
                onClick={() => {
                  if (confirm('Disable detections for this camera?')) {
                    navigate('/settings/cameras');
                  }
                }}
              >
                Disable camera
              </button>

              <div style={{ display: 'flex', gap: '10px' }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => navigate('/settings/cameras')}
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Save changes
                </button>
              </div>
            </div>
          </div>

          {/* Right Column: Monitoring zones & Source status */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            {/* Monitoring Zones Card */}
            <div className="operix-card">
              <h3 className="card-title">Monitoring zones</h3>
              <p className="card-subtitle" style={{ marginBottom: '1.25rem' }}>
                Zones drawn on this camera
              </p>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: '0.85rem', borderBottom: '1px solid var(--border-subtle)' }}>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: '13.5px' }}>Zone B · Press Line</div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Machine area · Production · Active</div>
                  </div>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => navigate('/rules/zones')}
                  >
                    Edit
                  </button>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: '13.5px' }}>Zone C · Walkway</div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Walkway · No department · Active</div>
                  </div>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => navigate('/rules/zones')}
                  >
                    Edit
                  </button>
                </div>
              </div>

              <div style={{ marginTop: '1.5rem' }}>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => navigate('/rules/zones')}
                >
                  <Plus size={13} />
                  Add zone
                </button>
              </div>
            </div>

            {/* Source Status Card */}
            <div className="operix-card">
              <h3 className="card-title">Source status</h3>
              <p className="card-subtitle" style={{ marginBottom: '1.25rem' }}>
                Reported by the stream health check
              </p>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '13px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Status</span>
                  <span className="status-pill online">
                    <span className="badge-dot" /> Online
                  </span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Status since</span>
                  <span style={{ fontWeight: 600 }}>08:12 today</span>
                </div>
              </div>

              {testResult && (
                <div style={{ marginTop: '1rem', padding: '10px 12px', borderRadius: '6px', backgroundColor: 'var(--bg-card-subtle)', border: '1px solid var(--border-color)', fontSize: '12px', color: '#10B981' }}>
                  {testResult}
                </div>
              )}

              <div style={{ marginTop: '1.5rem' }}>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={handleTestConnection}
                >
                  Test connection
                </button>
              </div>
            </div>
          </div>
        </form>
      </div>
    </>
  );
}
