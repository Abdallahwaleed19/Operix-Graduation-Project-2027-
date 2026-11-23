import React from 'react';
import { useAuth, ROLES } from '../../context/AuthContext';
import { Shield, Check, X } from 'lucide-react';

export default function RoleSwitcherModal({ isOpen, onClose }) {
  const { role, switchRole } = useAuth();

  if (!isOpen) return null;

  const roleOptions = [
    {
      id: ROLES.ADMIN,
      name: 'Administrator',
      desc: 'Full access to all systems, settings, users, and configuration.',
      badge: 'All Permissions'
    },
    {
      id: ROLES.MANAGER,
      name: 'Factory Manager',
      desc: 'Access to dashboards, analytics, rules, and cameras. No user management.',
      badge: 'Manager Access'
    },
    {
      id: ROLES.SUPERVISOR,
      name: 'Safety Supervisor',
      desc: 'Live monitoring, alerts, incident resolution, and evidence review.',
      badge: 'Floor Safety'
    },
    {
      id: ROLES.VIEWER,
      name: 'Viewer',
      desc: 'Read-only access to dashboard, live feeds, incidents and reports.',
      badge: 'Read-Only'
    }
  ];

  const handleSelectRole = (selectedRole) => {
    switchRole(selectedRole);
    onClose();
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-dialog" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Shield size={20} color="var(--primary)" />
            <h3 className="modal-title">Switch Active Role</h3>
          </div>
          <button className="btn-icon" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '4px' }}>
            Choose a role to test role-based access control, UI variations, and permissions according to the Figma specs.
          </p>

          {roleOptions.map(opt => {
            const isSelected = role === opt.id;
            return (
              <div
                key={opt.id}
                onClick={() => handleSelectRole(opt.id)}
                style={{
                  border: isSelected ? '2px solid var(--primary)' : '1px solid var(--border-color)',
                  backgroundColor: isSelected ? 'var(--bg-active-nav)' : 'var(--bg-card)',
                  borderRadius: '10px',
                  padding: '12px 16px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  transition: 'all 0.15s ease'
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontWeight: 700, fontSize: '14px', color: 'var(--text-primary)' }}>
                      {opt.name}
                    </span>
                    <span className="status-pill neutral" style={{ fontSize: '11px', padding: '2px 8px' }}>
                      {opt.badge}
                    </span>
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
                    {opt.desc}
                  </div>
                </div>
                {isSelected && (
                  <div style={{
                    width: '24px',
                    height: '24px',
                    borderRadius: '50%',
                    backgroundColor: 'var(--primary)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#fff'
                  }}>
                    <Check size={14} />
                  </div>
                )}
              </div>
            );
          })}
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
