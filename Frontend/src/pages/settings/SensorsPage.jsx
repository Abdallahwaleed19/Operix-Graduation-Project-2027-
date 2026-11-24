import React, { useState } from 'react';
import Navbar from '../../components/common/Navbar';
import PendingBackendBadge from '../../components/common/PendingBackendBadge';
import { useData } from '../../context/DataContext';
import { useNavigate } from 'react-router-dom';
import { Plus, Search } from 'lucide-react';

export default function SensorsPage() {
  const { sensors, toggleSensor } = useData();
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');

  const filteredSensors = sensors.filter(s =>
    s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    s.location.toLowerCase().includes(searchQuery.toLowerCase()) ||
    s.department.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <>
      <Navbar
        title="Sensors"
        subtitle="Register, edit and disable sensors"
        backTo="/settings"
        backLabel="Back to Settings"
        rightActions={
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <PendingBackendBadge moduleCode="S-3" dependency="Sensors API" />
            <button
              className="btn btn-primary"
              onClick={() => navigate('/settings/sensors/edit/new')}
            >
              <Plus size={15} />
              Add sensor
            </button>
          </div>
        }
      />

      <div className="page-container">
        {/* Sub-tabs & Search */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}>
          <div className="tab-pills">
            <button
              className="tab-pill-btn"
              onClick={() => navigate('/settings/cameras')}
            >
              Cameras · 22
            </button>
            <button className="tab-pill-btn active">
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

        {/* Sensors Table Card */}
        <div className="operix-table-card">
          <div className="table-responsive">
            <table className="operix-table">
              <thead>
                <tr>
                  <th style={{ minWidth: '150px' }}>Sensor</th>
                  <th style={{ minWidth: '110px' }}>Department</th>
                  <th style={{ minWidth: '110px' }}>Type</th>
                  <th style={{ minWidth: '70px' }}>Unit</th>
                  <th style={{ minWidth: '110px' }}>Sampling</th>
                  <th style={{ minWidth: '100px' }}>Status</th>
                  <th style={{ minWidth: '140px', textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredSensors.map((s) => {
                  const statusClass = s.status.toLowerCase();
                  const isDisabled = s.status === 'Disabled';

                  return (
                    <tr key={s.id}>
                      <td style={{ fontWeight: 700, color: 'var(--text-primary)', whiteSpace: 'nowrap' }}>
                        {s.name}
                      </td>
                      <td style={{ color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
                        {s.department}
                      </td>
                      <td style={{ color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
                        {s.type}
                      </td>
                      <td style={{ fontFamily: 'JetBrains Mono', color: 'var(--text-secondary)' }}>
                        {s.unit}
                      </td>
                      <td style={{ color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                        {s.sampling}
                      </td>
                      <td>
                        <span className={`status-pill ${statusClass}`} style={{ whiteSpace: 'nowrap' }}>
                          <span className="badge-dot" />
                          {s.status}
                        </span>
                      </td>
                      <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
                        <div style={{ display: 'inline-flex', gap: '8px' }}>
                          <button
                            className="btn btn-secondary btn-sm"
                            onClick={() => navigate(`/settings/sensors/edit/${s.id}`)}
                          >
                            Edit
                          </button>
                          <button
                            className={isDisabled ? 'btn btn-secondary btn-sm' : 'btn btn-danger-outline btn-sm'}
                            onClick={() => toggleSensor(s.id)}
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
            <span>Showing 5 of 13 sensors · One reading is stored per sampling interval</span>
          </div>
        </div>
      </div>
    </>
  );
}
