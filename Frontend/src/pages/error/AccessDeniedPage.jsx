import React, { useState } from 'react';
import Navbar from '../../components/common/Navbar';
import { useNavigate } from 'react-router-dom';
import { ShieldAlert, Check } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export default function AccessDeniedPage() {
  const navigate = useNavigate();
  const { role } = useAuth();
  const [requested, setRequested] = useState(false);

  const handleRequestAccess = () => {
    setRequested(true);
    setTimeout(() => setRequested(false), 4000);
  };

  return (
    <>
      <Navbar
        title="Settings"
        subtitle="Restricted area"
      />

      <div className="page-container">
        <div className="access-denied-container">
          <div className="access-denied-box">
            <div className="access-denied-code">
              403
            </div>

            <h2 style={{ fontSize: '20px', fontWeight: 800, color: 'var(--text-primary)', letterSpacing: '-0.02em' }}>
              You don't have access to Settings
            </h2>

            <p style={{ fontSize: '13.5px', color: 'var(--text-muted)', lineHeight: 1.5, maxWidth: '360px' }}>
              Your role ({role || 'Viewer'}) doesn't include the <code>device.manage</code> permission.<br />
              Ask your factory admin to change your role.
            </p>

            {requested && (
              <div style={{
                fontSize: '12.5px',
                color: 'var(--success-text)',
                backgroundColor: 'var(--success-bg)',
                padding: '8px 14px',
                borderRadius: '6px',
                border: '1px solid var(--success-border)',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}>
                <Check size={14} /> Access request submitted to factory admin.
              </div>
            )}

            <div style={{ display: 'flex', gap: '12px', marginTop: '1rem', width: '100%', justifyContent: 'center' }}>
              <button
                className="btn btn-primary"
                onClick={() => navigate('/')}
              >
                Back to Dashboard
              </button>

              <button
                className="btn btn-secondary"
                disabled={requested}
                onClick={handleRequestAccess}
              >
                {requested ? 'Requested' : 'Request access'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
