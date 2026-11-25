import React, { useState } from 'react';
import Navbar from '../../components/common/Navbar';
import PendingBackendBadge from '../../components/common/PendingBackendBadge';
import { useData } from '../../context/DataContext';
import { isMockEnabled } from '../../services/apiClient';
import { Plus, UserPlus, Trash2, Check } from 'lucide-react';

export default function UsersRolesPage() {
  const { users, toggleUserAccess, inviteUser, updateUserRole, deleteUser } = useData();

  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('Safety Supervisor');
  const [inviteFactory, setInviteFactory] = useState('Plant 1');
  const [selectedRolePreview, setSelectedRolePreview] = useState('Safety Supervisor');
  const [actionError, setActionError] = useState('');

  // Role permissions template for display
  const permissionsMap = {
    'Safety Supervisor': {
      'incident.view': true,
      'incident.resolve': true,
      'rule.manage': false,
      'device.manage': false,
      'user.manage': false
    },
    'Administrator': {
      'incident.view': true,
      'incident.resolve': true,
      'rule.manage': true,
      'device.manage': true,
      'user.manage': true
    },
    'Factory Manager': {
      'incident.view': true,
      'incident.resolve': true,
      'rule.manage': true,
      'device.manage': true,
      'user.manage': false
    },
    'Viewer': {
      'incident.view': true,
      'incident.resolve': false,
      'rule.manage': false,
      'device.manage': false,
      'user.manage': false
    }
  };

  const handleSendInvite = async (e) => {
    e.preventDefault();
    if (!inviteEmail) return;
    setActionError('');
    try {
      await inviteUser({
        name: inviteEmail.split('@')[0],
        email: inviteEmail,
        role: inviteRole
      });
      setInviteEmail('');
      alert(`Invitation created & email dispatched to ${inviteEmail} for role ${inviteRole}`);
    } catch (err) {
      setActionError(err.message || 'Failed to invite user.');
    }
  };

  const handleDeleteUser = async (u) => {
    if (!window.confirm(`Delete ${u.name} (${u.email}) permanently from operix_db?`)) return;
    setActionError('');
    try {
      await deleteUser(u.id);
    } catch (err) {
      setActionError(err.message || 'Failed to delete user.');
    }
  };

  return (
    <>
      <Navbar
        title="Users & Roles"
        subtitle="Invite members and manage role-based access"
        backTo="/settings"
        backLabel="Back to Settings"
        rightActions={
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            {isMockEnabled('users') && (
              <PendingBackendBadge moduleCode="S-4" dependency="Users & Roles API" />
            )}
            <button
              className="btn btn-primary"
              onClick={() => document.getElementById('invite-email-input')?.focus()}
            >
              <Plus size={15} />
              Invite user
            </button>
          </div>
        }
      />

      <div className="page-container">
        {actionError && (
          <div style={{
            marginBottom: '1rem',
            padding: '10px 14px',
            borderRadius: '8px',
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            color: '#EF4444',
            fontSize: '13px',
            fontWeight: 600
          }}>
            {actionError}
          </div>
        )}
        <div className="grid-2col-settings">
          {/* Members Table */}
          <div className="operix-table-card">
            <div style={{ padding: '1.25rem 1.5rem', borderBottom: '1px solid var(--border-color)' }}>
              <h3 className="card-title">Members</h3>
              <p className="card-subtitle">{users.length} members · Role-based access control</p>
            </div>

            <div className="table-responsive">
              <table className="operix-table">
                <thead>
                  <tr>
                    <th style={{ minWidth: '160px' }}>Member</th>
                    <th style={{ minWidth: '160px' }}>Role</th>
                    <th style={{ minWidth: '100px' }}>Status</th>
                    <th style={{ minWidth: '100px' }}>Access</th>
                    <th style={{ minWidth: '110px', textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => {
                    const isActive = u.access === 'Active';
                    return (
                      <tr key={u.id}>
                        <td>
                          <div style={{ fontWeight: 700, fontSize: '13.5px', color: 'var(--text-primary)', whiteSpace: 'nowrap' }}>
                            {u.name}
                          </div>
                          <div style={{ fontSize: '12px', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                            {u.email}
                          </div>
                        </td>
                        <td>
                          <select
                            className="form-control form-select"
                            style={{ width: '155px', padding: '0.4rem 0.75rem', fontSize: '12.5px' }}
                            value={u.role}
                            onChange={(e) => {
                              updateUserRole(u.id, e.target.value);
                              setSelectedRolePreview(e.target.value);
                            }}
                          >
                            <option value="Administrator">Administrator</option>
                            <option value="Factory Manager">Factory Manager</option>
                            <option value="Safety Supervisor">Safety Supervisor</option>
                            <option value="Viewer">Viewer</option>
                          </select>
                        </td>
                        <td>
                          <span className={`status-pill ${u.status === 'Active' ? 'online' : 'warning'}`} style={{ whiteSpace: 'nowrap' }}>
                            <span className="badge-dot" />
                            {u.status}
                          </span>
                        </td>
                        <td>
                          <span className={`status-pill ${isActive ? 'online' : 'disabled'}`} style={{ whiteSpace: 'nowrap' }}>
                            <span className="badge-dot" />
                            {u.access}
                          </span>
                        </td>
                        <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
                          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                            <button
                              className={isActive ? 'btn btn-danger-outline btn-sm' : 'btn btn-secondary btn-sm'}
                              onClick={() => toggleUserAccess(u.id).catch(err => setActionError(err.message || 'Action failed'))}
                            >
                              {u.status === 'Invited' && !isActive ? (
                                <>
                                  <Check size={13} />
                                  Approve
                                </>
                              ) : isActive ? 'Deactivate' : 'Activate'}
                            </button>
                            <button
                              type="button"
                              className="btn btn-danger-outline btn-sm"
                              title="Delete user"
                              onClick={() => handleDeleteUser(u)}
                              style={{ padding: '0.35rem 0.55rem' }}
                            >
                              <Trash2 size={14} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Right Column: Invite & Permissions preview */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            {/* Invite User Card */}
            <div className="operix-card">
              <h3 className="card-title">Invite user</h3>
              <p className="card-subtitle" style={{ marginBottom: '1.25rem' }}>
                Creates the user and an invite link
              </p>

              <form onSubmit={handleSendInvite}>
                <div className="form-group">
                  <label className="form-label">Work email</label>
                  <input
                    id="invite-email-input"
                    type="email"
                    className="form-control"
                    placeholder="name@company.com"
                    value={inviteEmail}
                    onChange={e => setInviteEmail(e.target.value)}
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Role</label>
                  <select
                    className="form-control form-select"
                    value={inviteRole}
                    onChange={e => {
                      setInviteRole(e.target.value);
                      setSelectedRolePreview(e.target.value);
                    }}
                  >
                    <option value="Safety Supervisor">Safety Supervisor</option>
                    <option value="Factory Manager">Factory Manager</option>
                    <option value="Administrator">Administrator</option>
                    <option value="Viewer">Viewer</option>
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Factory</label>
                  <select
                    className="form-control form-select"
                    value={inviteFactory}
                    onChange={e => setInviteFactory(e.target.value)}
                  >
                    <option value="Plant 1">Plant 1 · Menoufia</option>
                    <option value="Plant 2">Plant 2</option>
                    <option value="Plant 3">Plant 3</option>
                  </select>
                </div>

                <button type="submit" className="btn btn-primary" style={{ width: '100%' }}>
                  <UserPlus size={15} />
                  Send invite
                </button>
              </form>
            </div>

            {/* Role Permissions Card */}
            <div className="operix-card">
              <h3 className="card-title">Role permissions</h3>
              <p className="card-subtitle" style={{ marginBottom: '1.25rem' }}>
                {selectedRolePreview}
              </p>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', fontSize: '13px' }}>
                {Object.entries(permissionsMap[selectedRolePreview] || permissionsMap['Safety Supervisor']).map(([permCode, isAllowed]) => (
                  <div key={permCode} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontFamily: 'JetBrains Mono', color: 'var(--text-secondary)' }}>
                      {permCode}
                    </span>
                    <label className="switch-wrapper">
                      <input
                        type="checkbox"
                        className="switch-input"
                        checked={isAllowed}
                        disabled
                      />
                      <span className="switch-slider" />
                    </label>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
