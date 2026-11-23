import React from 'react';
import Navbar from '../../components/common/Navbar';
import { useNavigate } from 'react-router-dom';
import { Users, Camera, Shield, Sliders, Plus, ExternalLink, Activity } from 'lucide-react';

export default function SettingsHubPage() {
  const navigate = useNavigate();

  return (
    <>
      <Navbar
        title="Settings"
        subtitle="Users, devices and alert preferences"
      />

      <div className="page-container">
        {/* Quick Settings Subnav Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '0.5rem' }}>
          <div
            className="operix-card"
            style={{ padding: '1rem 1.25rem', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '12px' }}
            onClick={() => navigate('/settings/cameras')}
          >
            <Camera size={18} color="var(--primary)" />
            <div>
              <div style={{ fontWeight: 700, fontSize: '13px' }}>Cameras</div>
              <div style={{ fontSize: '11.5px', color: 'var(--text-muted)' }}>22 registered</div>
            </div>
          </div>

          <div
            className="operix-card"
            style={{ padding: '1rem 1.25rem', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '12px' }}
            onClick={() => navigate('/settings/sensors')}
          >
            <Activity size={18} color="var(--primary)" />
            <div>
              <div style={{ fontWeight: 700, fontSize: '13px' }}>Sensors</div>
              <div style={{ fontSize: '11.5px', color: 'var(--text-muted)' }}>13 registered</div>
            </div>
          </div>

          <div
            className="operix-card"
            style={{ padding: '1rem 1.25rem', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '12px' }}
            onClick={() => navigate('/settings/users')}
          >
            <Users size={18} color="var(--primary)" />
            <div>
              <div style={{ fontWeight: 700, fontSize: '13px' }}>Users & Roles</div>
              <div style={{ fontSize: '11.5px', color: 'var(--text-muted)' }}>4 team members</div>
            </div>
          </div>

          <div
            className="operix-card"
            style={{ padding: '1rem 1.25rem', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '12px' }}
            onClick={() => navigate('/settings/matrix')}
          >
            <Shield size={18} color="var(--primary)" />
            <div>
              <div style={{ fontWeight: 700, fontSize: '13px' }}>Role Matrix</div>
              <div style={{ fontSize: '11.5px', color: 'var(--text-muted)' }}>Permissions & RBAC</div>
            </div>
          </div>
        </div>

        {/* 2 Primary Figma Panels */}
        <div className="grid-2col-equal">
          {/* Left: Users & permissions */}
          <div className="operix-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <div>
              <div className="card-header-flex">
                <div>
                  <h3 className="card-title">Users & permissions</h3>
                  <p className="card-subtitle">Manage access to your plant workspace</p>
                </div>
                <button
                  className="btn btn-outline btn-sm"
                  onClick={() => navigate('/settings/users')}
                >
                  Manage <ExternalLink size={12} />
                </button>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', marginTop: '1.25rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: '0.85rem', borderBottom: '1px solid var(--border-subtle)' }}>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: '13.5px' }}>Mona Hassan</div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Administrator</div>
                  </div>
                  <span className="status-pill online">
                    <span className="badge-dot" /> Active
                  </span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: '0.85rem', borderBottom: '1px solid var(--border-subtle)' }}>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: '13.5px' }}>Omar Khaled</div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Safety Supervisor</div>
                  </div>
                  <span className="status-pill online">
                    <span className="badge-dot" /> Active
                  </span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: '13.5px' }}>Sara Nabil</div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Factory Manager</div>
                  </div>
                  <span className="status-pill online">
                    <span className="badge-dot" /> Active
                  </span>
                </div>
              </div>
            </div>

            <div style={{ marginTop: '2rem', paddingTop: '1rem', borderTop: '1px solid var(--border-subtle)', fontSize: '12px', color: 'var(--text-muted)' }}>
              3 members · Role-based access control
            </div>
          </div>

          {/* Right: Cameras & sensors */}
          <div className="operix-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <div>
              <div className="card-header-flex">
                <div>
                  <h3 className="card-title">Cameras & sensors</h3>
                  <p className="card-subtitle">Connected hardware and registration</p>
                </div>
                <button
                  className="btn btn-outline btn-sm"
                  onClick={() => navigate('/settings/factory')}
                >
                  Factory Settings
                </button>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', marginTop: '1.25rem' }}>
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontWeight: 700, fontSize: '13.5px' }}>CCTV cameras</span>
                    <span style={{ fontSize: '12.5px', color: '#10B981', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span className="badge-dot" style={{ backgroundColor: '#10B981' }} /> 18 online
                    </span>
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>18 registered</div>
                </div>

                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontWeight: 700, fontSize: '13.5px' }}>Thermal cameras</span>
                    <span style={{ fontSize: '12.5px', color: '#10B981', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span className="badge-dot" style={{ backgroundColor: '#10B981' }} /> 4 online
                    </span>
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>4 registered</div>
                </div>

                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontWeight: 700, fontSize: '13.5px' }}>Temperature sensors</span>
                    <span style={{ fontSize: '12.5px', color: '#F59E0B', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span className="badge-dot" style={{ backgroundColor: '#10B981' }} /> 12 online · 1 offline
                    </span>
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>13 registered</div>
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '2rem', paddingTop: '1rem', borderTop: '1px solid var(--border-subtle)' }}>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => navigate('/settings/cameras')}
              >
                <Plus size={13} />
                Register device
              </button>
              <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Plant 1</span>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
