import React from 'react';

export default function CameraFeedCard({
  camId = 'CAM-04',
  title = 'Press Line',
  isLive = true,
  timestamp = '09:42:03 / PLANT 1',
  isThermal = false,
  temperature = '92°C',
  minTemp = '24°C',
  maxTemp = '92°C',
  detections = [],
  height = 180
}) {
  return (
    <div className="camera-feed-card">
      <div className="camera-feed-header">
        <span>{camId} · {title}</span>
        {isLive && (
          <span className="camera-live-badge">
            <span className="badge-dot pulse" />
            LIVE
          </span>
        )}
      </div>

      <div
        className={`camera-feed-viewport ${isThermal ? 'thermal-viewport' : ''}`}
        style={{ height: `${height}px` }}
      >
        {!isThermal ? (
          <>
            {/* Background Floor Grid */}
            <div className="camera-floor-grid" />

            {/* Industrial Machinery Silhouettes */}
            <div className="camera-silhouettes">
              <div className="machine-block" />
              <div className="machine-block" />
              <div className="machine-block" />
            </div>

            {/* Overhead Industrial Truss Graphic */}
            <svg className="camera-truss" viewBox="0 0 400 200" preserveAspectRatio="none">
              <line x1="0" y1="180" x2="200" y2="40" />
              <line x1="400" y1="180" x2="200" y2="40" />
              <line x1="0" y1="40" x2="400" y2="40" />
            </svg>

            {/* Simulated Live AI Bounding Boxes */}
            {detections.map((d, i) => (
              <div
                key={i}
                className={`detection-box ${d.type || 'danger'}`}
                style={{
                  left: d.left || '20%',
                  top: d.top || '30%',
                  width: d.width || '100px',
                  height: d.height || '110px'
                }}
              >
                <span className={`detection-tag ${d.type || 'danger'}`}>
                  {d.label}
                </span>
              </div>
            ))}
          </>
        ) : (
          <>
            {/* Thermal boiler visualization with hot-spot columns */}
            <div style={{
              display: 'flex',
              width: '100%',
              height: '100%',
              justifyContent: 'space-around',
              alignItems: 'center',
              padding: '0 20px',
              opacity: 0.45
            }}>
              <div style={{ width: '40px', height: '80%', background: '#4A1224', borderRadius: '4px' }} />
              <div style={{ width: '40px', height: '80%', background: '#66162B', borderRadius: '4px' }} />
              <div style={{ width: '40px', height: '80%', background: '#A11D25', borderRadius: '4px' }} />
              <div style={{ width: '40px', height: '80%', background: '#66162B', borderRadius: '4px' }} />
            </div>

            {/* Center hot core glow */}
            <div style={{
              position: 'absolute',
              width: '120px',
              height: '120px',
              borderRadius: '50%',
              background: 'radial-gradient(circle, rgba(254, 240, 138, 0.95) 0%, rgba(245, 158, 11, 0.7) 40%, transparent 80%)',
              filter: 'blur(10px)',
              pointerEvents: 'none'
            }} />

            <div className="thermal-temp-display">
              {temperature}
            </div>
          </>
        )}
      </div>

      <div className="camera-feed-footer">
        {isThermal ? (
          <>
            <span>MAX {maxTemp}</span>
            <span>MIN {minTemp}</span>
          </>
        ) : (
          <span>{timestamp}</span>
        )}
      </div>
    </div>
  );
}
