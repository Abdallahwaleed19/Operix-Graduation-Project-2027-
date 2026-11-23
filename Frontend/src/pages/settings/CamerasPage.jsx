import React, { useState } from 'react';
import Navbar from '../../components/common/Navbar';
import { useData } from '../../context/DataContext';
import { useNavigate } from 'react-router-dom';
import { Plus, Search, Edit2 } from 'lucide-react';

export default function CamerasPage() {
  const { cameras, toggleCamera } = useData();
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');

  const filteredCameras = cameras.filter(cam =>
    cam.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    cam.location.toLowerCase().includes(searchQuery.toLowerCase()) ||
    cam.department.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <>
      <Navbar
        title="Cameras"
        subtitle="Register, edit and disable cameras"
        backTo="/settings"
        backLabel="Back to Settings"
        rightActions={
          <button
            className="btn btn-primary"
            onClick={() => navigate('/settings/cameras/edit/new')}
          >
            <Plus size={15} />
            Add camera
          </button>
        }
      />

      <div className="page-container">
        {/* Sub-tabs & Search Bar */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}>
          <div className="tab-pills">
            <button className="tab-pill-btn active">
              Cameras · 22
            </button>
            <button
              className="tab-pill-btn"
              onClick={() => navigate('/settings/sensors')}
            >
              Sensors · 13
            </button>
          </div>

          <div className="input-with-icon" style={{ width: '280px' }}>
            <Search size={16} />
            <input
              type="text"
              className="form-control"
              placeholder="Search by name"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
            />
          </div>
        </div>

        {/* Cameras Table Card */}
        <div className="operix-table-card">
          <div className="table-responsive">
            <table className="operix-table">
              <thead>
                <tr>
                  <th style={{ minWidth: '150px' }}>Camera</th>
                  <th style={{ minWidth: '110px' }}>Department</th>
                  <th style={{ minWidth: '80px' }}>Type</th>
                  <th style={{ minWidth: '120px' }}>Location</th>
                  <th style={{ minWidth: '70px' }}>Zones</th>
                  <th style={{ minWidth: '100px' }}>Status</th>
                  <th style={{ minWidth: '140px', textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredCameras.map((cam) => {
                  const statusClass = cam.status.toLowerCase();
                  const isOnline = cam.status === 'Online';
                  const isDisabled = cam.status === 'Disabled';

                  return (
                    <tr key={cam.id}>
                      <td style={{ fontWeight: 700, color: 'var(--text-primary)', whiteSpace: 'nowrap' }}>
                        {cam.name}
                      </td>
                      <td style={{ color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
                        {cam.department}
                      </td>
                      <td style={{ color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
                        {cam.type}
                      </td>
                      <td style={{ color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                        {cam.location}
                      </td>
                      <td style={{ fontWeight: 600 }}>
                        {cam.zones}
                      </td>
                      <td>
                        <span className={`status-pill ${statusClass}`} style={{ whiteSpace: 'nowrap' }}>
                          <span className="badge-dot" />
                          {cam.status}
                        </span>
                      </td>
                      <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
                        <div style={{ display: 'inline-flex', gap: '8px' }}>
                          <button
                            className="btn btn-secondary btn-sm"
                            onClick={() => navigate(`/settings/cameras/edit/${cam.id}`)}
                          >
                            Edit
                          </button>
                          <button
                            className={isDisabled ? 'btn btn-secondary btn-sm' : 'btn btn-danger-outline btn-sm'}
                            onClick={() => toggleCamera(cam.id)}
                          >
                            {isDisabled ? 'Enable' : 'Disable'}
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="table-footer-meta">
            <span>Showing 6 of 22 cameras · Status comes from the stream health check · Disable stops detections</span>
          </div>
        </div>
      </div>
    </>
  );
}
