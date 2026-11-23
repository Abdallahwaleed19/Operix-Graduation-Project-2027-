import React, { useState } from 'react';
import Navbar from '../../components/common/Navbar';
import { useAuth } from '../../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Check, Shield, Building, Edit2 } from 'lucide-react';

export default function ProfilePage() {
  const { currentUser, logout, isSupervisor, updateUserProfile } = useAuth();
  const navigate = useNavigate();

  // Safe fallback user model to guarantee zero render crashes
  const user = currentUser || {
    name: 'Karim Adel',
    email: 'karim.adel@operix.io',
    initials: 'KA',
    role: 'Safety Supervisor',
    factory: 'Plant 1',
    timezone: 'Africa/Cairo',
    status: 'Active',
    platformAdmin: false,
    memberships: [
      { factory: 'Plant 1', role: 'Safety Supervisor', status: 'Active' },
      { factory: 'Plant 3', role: 'Safety Supervisor', status: 'Pending' }
    ],
    notifications: {
      dashboardAlerts: true,
      emailAlerts: true,
      minSeverity: 'Medium'
    }
  };

  const memberships = (user.memberships && Array.isArray(user.memberships) && user.memberships.length > 0)
    ? user.memberships
    : [
        { factory: user.factory || 'Plant 1', role: user.role || 'Safety Supervisor', status: 'Active' },
        { factory: 'Plant 3', role: user.role || 'Safety Supervisor', status: 'Pending' }
      ];

  const [dashboardAlerts, setDashboardAlerts] = useState(user.notifications?.dashboardAlerts ?? true);
  const [emailAlerts, setEmailAlerts] = useState(user.notifications?.emailAlerts ?? true);
  const [isEditing, setIsEditing] = useState(false);
  const [fullName, setFullName] = useState(user.name || '');

  const handleSignOut = () => {
    logout();
    navigate('/login');
  };

  const handleSaveProfile = () => {
    updateUserProfile({ name: fullName });
    setIsEditing(false);
  };

  return (
    <>
      <Navbar
        title="Profile"
        subtitle="Account, factory membership and notifications"
        rightActions={
          <button className="btn btn-secondary" onClick={() => navigate('/')}>
            <ArrowLeft size={14} />
            Back to dashboard
          </button>
        }
      />

      <div className="page-container">
        <div className="grid-2col-settings">
          {/* Left Column: User Summary & Factory Memberships */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            {/* Identity Card */}
            <div className="operix-card" style={{ textAlign: 'center', padding: '2rem 1.5rem' }}>
              <div style={{
                width: '74px',
                height: '74px',
                borderRadius: '50%',
                backgroundColor: 'var(--primary)',
                color: '#FFFFFF',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '24px',
                fontWeight: 800,
                margin: '0 auto 1rem',
                border: '3px solid var(--border-color)'
              }}>
                {user.initials || 'OP'}
              </div>

              <h2 style={{ fontSize: '20px', fontWeight: 800, color: 'var(--text-primary)', marginBottom: '4px' }}>
                {user.name}
              </h2>
              <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '1rem' }}>
                {user.email}
              </div>

              <div style={{ display: 'flex', justifyContent: 'center', gap: '8px', marginBottom: '1.5rem' }}>
                <span className="status-pill neutral" style={{ fontSize: '12px' }}>
                  <Shield size={12} color="var(--primary)" />
                  {user.role}
                </span>
                <span className="status-pill online" style={{ fontSize: '12px' }}>
                  <span className="badge-dot" />
                  {user.status}
                </span>
              </div>

              <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '1.25rem', textAlign: 'left', display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '13px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Factory</span>
                  <span style={{ fontWeight: 600 }}>{user.factory}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Timezone</span>
                  <span style={{ fontWeight: 600 }}>{user.timezone}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Membership</span>
                  <span style={{ fontWeight: 600, color: '#10B981' }}>Active</span>
                </div>
              </div>

              <div style={{ marginTop: '1.5rem', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <button
                  className="btn btn-primary"
                  style={{ width: '100%' }}
                  onClick={() => setIsEditing(!isEditing)}
                >
                  {isEditing ? 'Cancel edit' : 'Edit profile'}
                </button>
                <button
                  className="btn btn-secondary"
                  style={{ width: '100%' }}
                  onClick={handleSignOut}
                >
                  Sign out
                </button>
              </div>
            </div>

            {/* Factory memberships */}
            <div className="operix-card">
              <h4 style={{ fontSize: '14px', fontWeight: 700, marginBottom: '1rem' }}>
                Factory memberships
              </h4>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {memberships.map((m, idx) => (
                  <div key={idx} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <div className="btn-icon" style={{ backgroundColor: 'var(--bg-active-nav)', border: 'none' }}>
                        <Building size={16} color="var(--primary)" />
                      </div>
                      <div>
                        <div style={{ fontWeight: 700, fontSize: '13.5px' }}>{m.factory}</div>
                        <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{m.role}</div>
                      </div>
                    </div>

                    <span className={`status-pill ${m.status === 'Active' ? 'online' : 'warning'}`}>
                      <span className="badge-dot" />
                      {m.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Right Column: Profile Details, Permissions & Notifications */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            {/* Personal Information */}
            <div className="operix-card">
              <div className="card-header-flex">
                <h3 className="card-title">Personal information</h3>
                <button
                  className="btn btn-outline btn-sm"
                  onClick={() => setIsEditing(!isEditing)}
                >
                  {isEditing ? 'Cancel' : 'Edit'}
                </button>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div className="form-group" style={{ margin: 0 }}>
                  <label className="form-label">Full name</label>
                  <input
                    type="text"
                    className="form-control"
                    value={fullName}
                    disabled={!isEditing}
                    onChange={e => setFullName(e.target.value)}
                  />
                </div>

                <div className="form-group" style={{ margin: 0 }}>
                  <label className="form-label">Work email</label>
                  <input
                    type="email"
                    className="form-control"
                    value={user.email}
                    disabled
                  />
                </div>

                <div className="form-group" style={{ margin: 0 }}>
                  <label className="form-label">Account status</label>
                  <div className="form-control" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span className="badge-dot" style={{ backgroundColor: '#10B981' }} />
                    <span>Active</span>
                  </div>
                </div>

                <div className="form-group" style={{ margin: 0 }}>
                  <label className="form-label">Platform admin</label>
                  <input
                    type="text"
                    className="form-control"
                    value={user.platformAdmin ? 'Yes' : 'No'}
                    disabled
                  />
                </div>
              </div>

              {isEditing && (
                <div style={{ marginTop: '1.25rem', display: 'flex', justifyContent: 'flex-end' }}>
                  <button className="btn btn-primary btn-sm" onClick={handleSaveProfile}>
                    Save changes
                  </button>
                </div>
              )}
            </div>

            {/* Role & Permissions */}
            <div className="operix-card">
              <div className="card-header-flex">
                <div>
                  <h3 className="card-title">Role & permissions</h3>
                  <p className="card-subtitle">Your role in Plant 1 decides which Operix areas and actions you can open.</p>
                </div>
                <span className="status-pill neutral">
                  <Shield size={13} color="var(--primary)" />
                  {user.role}
                </span>
              </div>

              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '1.25rem' }}>
                {[
                  'Monitor Worker Safety',
                  'Detect Worker Fatigue',
                  'Monitor Fire and Smoke',
                  'View Real-Time Alerts',
                  'Review Incident Evidence'
                ].map((perm, idx) => (
                  <span
                    key={idx}
                    className="status-pill neutral"
                    style={{ padding: '6px 14px', fontSize: '12.5px', gap: '8px' }}
                  >
                    <Check size={14} color="#10B981" />
                    {perm}
                  </span>
                ))}
              </div>
            </div>

            {/* Notifications & Security */}
            <div className="operix-card">
              <h3 className="card-title" style={{ marginBottom: '1.25rem' }}>
                Notifications & security
              </h3>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '13.5px' }}>Dashboard alerts</div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Real-time banners on high severity events</div>
                  </div>
                  <label className="switch-wrapper">
                    <input
                      type="checkbox"
                      className="switch-input"
                      checked={dashboardAlerts}
                      onChange={e => setDashboardAlerts(e.target.checked)}
                    />
                    <span className="switch-slider" />
                  </label>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '13.5px' }}>Email alerts</div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Immediate dispatch to registered work email</div>
                  </div>
                  <label className="switch-wrapper">
                    <input
                      type="checkbox"
                      className="switch-input"
                      checked={emailAlerts}
                      onChange={e => setEmailAlerts(e.target.checked)}
                    />
                    <span className="switch-slider" />
                  </label>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '13.5px' }}>Minimum alert severity</div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Filter thresholds for automated notification dispatch</div>
                  </div>
                  <span className="status-pill neutral font-mono">Medium</span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '0.75rem', borderTop: '1px solid var(--border-subtle)' }}>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '13.5px' }}>Password</div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Last changed 4 weeks ago</div>
                  </div>
                  <button
                    className="btn btn-outline btn-sm"
                    onClick={() => alert('Password reset verification link sent to your email.')}
                  >
                    Change password
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
