import React, { useState } from 'react';
import Navbar from '../../components/common/Navbar';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Save, Trash2, Edit3, MousePointer, Move, XCircle } from 'lucide-react';

export default function ZoneEditorPage() {
  const navigate = useNavigate();

  const [activeTool, setActiveTool] = useState('Draw polygon');
  const [selectedCamera, setSelectedCamera] = useState('CAM-04 · Press Line');
  const [zoneName, setZoneName] = useState('Zone D · Restricted');
  const [zoneType, setZoneType] = useState('Restricted');
  const [department, setDepartment] = useState('Production');
  const [isActive, setIsActive] = useState(true);

  // 5 Points for polygon matching Figma Screen 20
  const [points, setPoints] = useState([
    { x: 120, y: 140 },
    { x: 270, y: 110 },
    { x: 380, y: 180 },
    { x: 345, y: 320 },
    { x: 140, y: 310 }
  ]);

  const [draggingPointIndex, setDraggingPointIndex] = useState(null);

  const handleMouseDown = (index, e) => {
    e.stopPropagation();
    if (activeTool === 'Delete point') {
      if (points.length > 3) {
        setPoints(points.filter((_, i) => i !== index));
      } else {
        alert('A zone polygon must have at least 3 points.');
      }
      return;
    }
    setDraggingPointIndex(index);
  };

  const handleMouseMove = (e) => {
    if (draggingPointIndex === null) return;
    const svgRect = e.currentTarget.getBoundingClientRect();
    const x = Math.max(10, Math.min(590, e.clientX - svgRect.left));
    const y = Math.max(10, Math.min(390, e.clientY - svgRect.top));

    setPoints(prev =>
      prev.map((pt, i) => (i === draggingPointIndex ? { x, y } : pt))
    );
  };

  const handleMouseUp = () => {
    setDraggingPointIndex(null);
  };

  const handleSvgClick = (e) => {
    if (activeTool === 'Draw polygon') {
      const svgRect = e.currentTarget.getBoundingClientRect();
      const x = e.clientX - svgRect.left;
      const y = e.clientY - svgRect.top;
      if (points.length < 8) {
        setPoints([...points, { x, y }]);
      }
    }
  };

  const polygonSvgPoints = points.map(p => `${p.x},${p.y}`).join(' ');

  const handleSaveZone = () => {
    alert(`Zone "${zoneName}" calibrated and saved with ${points.length} boundary vertices!`);
    navigate('/rules');
  };

  return (
    <>
      <Navbar
        title="Zone Editor"
        subtitle="Draw and edit monitoring zones on a camera view"
        rightActions={
          <button className="btn btn-secondary btn-sm" onClick={() => navigate('/rules')}>
            <ArrowLeft size={14} />
            Back to rules
          </button>
        }
      />

      <div className="page-container">
        <div className="grid-2col-settings">
          {/* Left Canvas Panel */}
          <div className="operix-card">
            <h3 className="card-title">Camera view</h3>
            <p className="card-subtitle" style={{ marginBottom: '1.25rem' }}>
              Every zone belongs to one camera; draw its polygon on the frame
            </p>

            {/* Toolbar */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '8px' }}>
              <div className="tab-pills">
                {['Select', 'Draw polygon', 'Move point', 'Delete point'].map(tool => (
                  <button
                    key={tool}
                    className={`tab-pill-btn ${activeTool === tool ? 'active' : ''}`}
                    onClick={() => setActiveTool(tool)}
                  >
                    {tool}
                  </button>
                ))}
              </div>

              <select
                className="form-control form-select"
                style={{ width: '220px', padding: '0.45rem 0.8rem', fontSize: '12.5px' }}
                value={selectedCamera}
                onChange={e => setSelectedCamera(e.target.value)}
              >
                <option value="CAM-04 · Press Line">CAM-04 · Press Line</option>
                <option value="CAM-01 · Gate">CAM-01 · Gate</option>
                <option value="CAM-07 · Furnace">CAM-07 · Furnace</option>
                <option value="CAM-02 · Assembly">CAM-02 · Assembly</option>
              </select>
            </div>

            {/* Interactive SVG Drawing Canvas */}
            <div
              style={{
                width: '100%',
                height: '400px',
                backgroundColor: 'var(--bg-card-subtle)',
                borderRadius: '8px',
                border: '1px solid var(--border-color)',
                position: 'relative',
                overflow: 'hidden',
                userSelect: 'none'
              }}
            >
              {/* Camera Feed Watermark */}
              <div style={{ position: 'absolute', left: '16px', top: '14px', fontSize: '11px', color: 'var(--text-light)', fontFamily: 'JetBrains Mono', zIndex: 5 }}>
                {selectedCamera} · Live
              </div>

              <svg
                width="100%"
                height="100%"
                viewBox="0 0 600 400"
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                onClick={handleSvgClick}
                style={{ cursor: activeTool === 'Draw polygon' ? 'crosshair' : activeTool === 'Move point' ? 'move' : 'default' }}
              >
                {/* Background Calibration Grid */}
                <defs>
                  <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                    <path d="M 40 0 L 0 0 0 40" fill="none" stroke="var(--border-subtle)" strokeWidth="1" />
                  </pattern>
                </defs>
                <rect width="100%" height="100%" fill="url(#grid)" />

                {/* Zone B Reference Outline */}
                <rect
                  x="420"
                  y="80"
                  width="130"
                  height="120"
                  rx="6"
                  fill="rgba(59, 130, 246, 0.08)"
                  stroke="#3B82F6"
                  strokeWidth="2"
                />
                <text x="430" y="105" fontSize="12" fontWeight="700" fill="#3B82F6">
                  Zone B
                </text>

                {/* Machinery Silhouettes */}
                <rect x="150" y="220" width="60" height="45" rx="4" fill="rgba(100, 116, 139, 0.25)" />
                <rect x="230" y="220" width="60" height="45" rx="4" fill="rgba(100, 116, 139, 0.25)" />
                <rect x="310" y="220" width="60" height="45" rx="4" fill="rgba(100, 116, 139, 0.25)" />

                {/* User Drawn Polygon */}
                <polygon
                  points={polygonSvgPoints}
                  fill="rgba(220, 38, 38, 0.65)"
                  stroke="#DC2626"
                  strokeWidth="2"
                />

                {/* Polygon Label */}
                <text
                  x="200"
                  y="200"
                  fontSize="12"
                  fontWeight="700"
                  fill="#FFFFFF"
                  style={{ pointerEvents: 'none', textShadow: '0 1px 3px rgba(0,0,0,0.6)' }}
                >
                  Zone D · Restricted
                </text>

                {/* Vertex Handle Nodes */}
                {points.map((pt, i) => (
                  <circle
                    key={i}
                    cx={pt.x}
                    cy={pt.y}
                    r={6}
                    fill="#FFFFFF"
                    stroke="#DC2626"
                    strokeWidth="2.5"
                    style={{ cursor: 'pointer' }}
                    onMouseDown={(e) => handleMouseDown(i, e)}
                  />
                ))}
              </svg>
            </div>

            <div style={{ marginTop: '1rem', fontSize: '11.5px', color: 'var(--text-light)' }}>
              Zone boundaries are camera-calibrated.
            </div>
          </div>

          {/* Right Properties Panel */}
          <div className="operix-card">
            <h3 className="card-title">Zone properties</h3>
            <p className="card-subtitle" style={{ marginBottom: '1.5rem' }}>
              Edit the selected zone
            </p>

            <div className="form-group">
              <label className="form-label">Zone name</label>
              <input
                type="text"
                className="form-control"
                value={zoneName}
                onChange={e => setZoneName(e.target.value)}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Zone type</label>
              <select
                className="form-control form-select"
                value={zoneType}
                onChange={e => setZoneType(e.target.value)}
              >
                <option value="Restricted">Restricted</option>
                <option value="Machine area">Machine area</option>
                <option value="Walkway">Walkway</option>
                <option value="Assembly line">Assembly line</option>
              </select>
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

            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', margin: '1.25rem 0' }}>
              <label className="switch-wrapper">
                <input
                  type="checkbox"
                  className="switch-input"
                  checked={isActive}
                  onChange={e => setIsActive(e.target.checked)}
                />
                <span className="switch-slider" />
              </label>
              <span style={{ fontSize: '13px', fontWeight: 600 }}>Active</span>
            </div>

            <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '1rem', display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '13px', marginBottom: '1.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Polygon</span>
                <span style={{ fontWeight: 700 }}>{points.length} points</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Version</span>
                <span style={{ fontWeight: 700 }}>2</span>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>Rules using this zone</span>
                <span className="status-pill neutral font-mono">Restricted access</span>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '10px' }}>
              <button
                type="button"
                className="btn btn-primary"
                style={{ flex: 1 }}
                onClick={handleSaveZone}
              >
                Save zone
              </button>
              <button
                type="button"
                className="btn btn-danger-outline"
                onClick={() => {
                  if (confirm('Delete this zone?')) {
                    navigate('/rules');
                  }
                }}
              >
                Delete zone
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
