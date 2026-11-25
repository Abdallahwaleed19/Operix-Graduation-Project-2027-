import React, { useState } from 'react';
import AuthLayout from '../../components/layout/AuthLayout';
import { Link, useSearchParams } from 'react-router-dom';
import { Lock, Eye, EyeOff, CheckCircle, AlertCircle, KeyRound } from 'lucide-react';
import { authService } from '../../services/authService';
import Logo from '../../components/common/Logo';

export default function AcceptInvitePage() {
  const [searchParams] = useSearchParams();
  const [token, setToken] = useState(searchParams.get('token') || '');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [successData, setSuccessData] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg('');

    if (!token.trim()) {
      setErrorMsg('Invitation token is missing. Please open the link from your email.');
      return;
    }
    if (password.length < 6) {
      setErrorMsg('Password must be at least 6 characters.');
      return;
    }
    if (password !== confirmPassword) {
      setErrorMsg('Passwords do not match.');
      return;
    }

    setIsLoading(true);
    try {
      const res = await authService.acceptInvite({ token: token.trim(), password });
      setSuccessData(res);
    } catch (err) {
      setErrorMsg(err.message || 'Invalid or expired invitation link.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthLayout
      badge="TEAM INVITATION"
      title="Activate your Operix account."
      subtitle="Set your personal password to complete your factory invitation and start monitoring."
      type="forgot"
    >
      <div className="auth-card" style={{ maxWidth: '420px', width: '100%' }}>
        <div style={{ marginBottom: '1.5rem', textAlign: 'center' }}>
          <Logo />
          <h2 style={{ marginTop: '1rem', fontSize: '1.35rem', fontWeight: 700, color: 'var(--text-primary)' }}>
            Accept Invitation
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
            Choose a password for your account
          </p>
        </div>

        {successData ? (
          <div style={{ textAlign: 'center', padding: '1rem 0' }}>
            <CheckCircle size={44} color="#16a34a" style={{ margin: '0 auto 0.75rem' }} />
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              Account Activated
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: '0.5rem 0 1.25rem' }}>
              {successData.message || 'Your account is now active.'}
            </p>
            <Link to="/login" className="btn btn-primary" style={{ width: '100%', display: 'inline-block', textAlign: 'center' }}>
              Sign in to Operix
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
            {errorMsg && (
              <div style={{
                display: 'flex', alignItems: 'center', gap: '8px',
                padding: '10px 12px', marginBottom: '1rem', borderRadius: '8px',
                backgroundColor: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)',
                color: '#EF4444', fontSize: '13px'
              }}>
                <AlertCircle size={16} />
                <span>{errorMsg}</span>
              </div>
            )}

            {!searchParams.get('token') && (
              <div className="form-group">
                <label className="form-label">Invitation Token</label>
                <div style={{ position: 'relative' }}>
                  <KeyRound size={15} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                  <input
                    type="text"
                    className="form-control"
                    style={{ paddingLeft: '36px' }}
                    placeholder="Paste token from email"
                    value={token}
                    onChange={(e) => setToken(e.target.value)}
                    required
                  />
                </div>
              </div>
            )}

            <div className="form-group">
              <label className="form-label">New Password</label>
              <div style={{ position: 'relative' }}>
                <Lock size={15} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                <input
                  type={showPassword ? 'text' : 'password'}
                  className="form-control"
                  style={{ paddingLeft: '36px', paddingRight: '38px' }}
                  placeholder="At least 6 characters"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  style={{ position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Confirm Password</label>
              <div style={{ position: 'relative' }}>
                <Lock size={15} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                <input
                  type={showPassword ? 'text' : 'password'}
                  className="form-control"
                  style={{ paddingLeft: '36px' }}
                  placeholder="Repeat your password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                />
              </div>
            </div>

            <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '0.5rem' }} disabled={isLoading}>
              {isLoading ? 'Activating...' : 'Activate Account'}
            </button>

            <div style={{ textAlign: 'center', marginTop: '1rem', fontSize: '13px' }}>
              <Link to="/login" style={{ color: 'var(--accent-primary)' }}>
                Back to Sign in
              </Link>
            </div>
          </form>
        )}
      </div>
    </AuthLayout>
  );
}
