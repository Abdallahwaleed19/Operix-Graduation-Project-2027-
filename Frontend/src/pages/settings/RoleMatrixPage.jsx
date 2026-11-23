import React from 'react';
import Navbar from '../../components/common/Navbar';
import { roleMatrixData } from '../../data/mockData';
import { Check, Minus, Star, Shield } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function RoleMatrixPage() {
  const navigate = useNavigate();

  return (
    <>
      <Navbar
        title="Role Access Matrix"
        subtitle="Which role can see and do what in the plant workspace"
        backTo="/settings"
        backLabel="Back to Settings"
      />

      <div className="page-container">
        <div className="grid-2col-settings">
          {/* Left Table Panel */}
          <div className="operix-table-card">
            <div style={{ padding: '1.25rem 1.5rem', borderBottom: '1px solid var(--border-color)' }}>
              <h3 className="card-title">Role ⇄ Permission</h3>
              <p className="card-subtitle">roles ⇄ permissions through role_permissions · sample seed data</p>
            </div>

            <div className="table-responsive">
              <table className="operix-table">
                <thead>
                  <tr>
                    <th style={{ minWidth: '150px' }}>code</th>
                    <th style={{ minWidth: '180px' }}>description</th>
                    <th style={{ textAlign: 'center', minWidth: '70px' }}>Admin</th>
                    <th style={{ textAlign: 'center', minWidth: '70px' }}>Manager</th>
                    <th style={{ textAlign: 'center', minWidth: '70px' }}>Supervisor</th>
                    <th style={{ textAlign: 'center', minWidth: '70px' }}>Viewer</th>
                  </tr>
                </thead>
                <tbody>
                  {roleMatrixData.map((perm) => (
                    <tr key={perm.code}>
                      <td style={{ fontFamily: 'JetBrains Mono', fontSize: '12px', color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
                        {perm.code}
                      </td>
                      <td style={{ fontWeight: 600, whiteSpace: 'nowrap' }}>
                        {perm.description}
                      </td>
                      <td style={{ textAlign: 'center' }}>
                        {perm.admin ? <Check size={16} color="#10B981" /> : <Minus size={14} color="var(--text-light)" />}
                      </td>
                      <td style={{ textAlign: 'center' }}>
                        {perm.manager ? <Check size={16} color="#10B981" /> : <Minus size={14} color="var(--text-light)" />}
                      </td>
                      <td style={{ textAlign: 'center' }}>
                        {perm.supervisor ? <Check size={16} color="#10B981" /> : <Minus size={14} color="var(--text-light)" />}
                      </td>
                      <td style={{ textAlign: 'center' }}>
                        {perm.viewer ? <Check size={16} color="#10B981" /> : <Minus size={14} color="var(--text-light)" />}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Right Card: How access is resolved */}
          <div className="operix-card">
            <h3 className="card-title">How access is resolved</h3>
            <p className="card-subtitle" style={{ marginBottom: '1.5rem' }}>
              From login to what the UI shows
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              <div style={{ display: 'flex', gap: '12px' }}>
                <div style={{
                  width: '26px',
                  height: '26px',
                  borderRadius: '50%',
                  backgroundColor: 'var(--bg-active-nav)',
                  color: 'var(--primary)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontWeight: 800,
                  fontSize: '12px',
                  flexShrink: 0
                }}>
                  1
                </div>
                <div style={{ fontSize: '13px', color: 'var(--text-primary)', lineHeight: 1.5 }}>
                  A user joins a factory through <strong>factory_memberships</strong> (is_active)
                </div>
              </div>

              <div style={{ display: 'flex', gap: '12px' }}>
                <div style={{
                  width: '26px',
                  height: '26px',
                  borderRadius: '50%',
                  backgroundColor: 'var(--bg-active-nav)',
                  color: 'var(--primary)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontWeight: 800,
                  fontSize: '12px',
                  flexShrink: 0
                }}>
                  2
                </div>
                <div style={{ fontSize: '13px', color: 'var(--text-primary)', lineHeight: 1.5 }}>
                  The membership holds one <strong>role_id</strong>
                </div>
              </div>

              <div style={{ display: 'flex', gap: '12px' }}>
                <div style={{
                  width: '26px',
                  height: '26px',
                  borderRadius: '50%',
                  backgroundColor: 'var(--bg-active-nav)',
                  color: 'var(--primary)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontWeight: 800,
                  fontSize: '12px',
                  flexShrink: 0
                }}>
                  3
                </div>
                <div style={{ fontSize: '13px', color: 'var(--text-primary)', lineHeight: 1.5 }}>
                  <strong>role_permissions</strong> lists what the role allows; the UI shows only that
                </div>
              </div>

              <div style={{ display: 'flex', gap: '12px', marginTop: '0.5rem', paddingTop: '1.25rem', borderTop: '1px solid var(--border-subtle)' }}>
                <div style={{
                  width: '26px',
                  height: '26px',
                  borderRadius: '50%',
                  backgroundColor: 'var(--bg-card-subtle)',
                  color: 'var(--text-muted)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0
                }}>
                  <Star size={13} />
                </div>
                <div style={{ fontSize: '12.5px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                  <strong>users.is_platform_admin</strong> sees every factory
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
