import React, { useState } from 'react';
import AuthLayout from '../../components/layout/AuthLayout';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Mail, Lock, Eye, EyeOff, Shield, AlertCircle, ArrowRight, CheckCircle2 } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import Logo from '../../components/common/Logo';
import { API_CONFIG } from '../../services/apiClient';

export default function LoginPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { login } = useAuth();

  const passedEmail = location.state?.email || '';
  const [email, setEmail] = useState(passedEmail);
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [keepSignedIn, setKeepSignedIn] = useState(true);

  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [unverifiedEmail, setUnverifiedEmail] = useState('');

  const redirectPath = location.state?.from?.pathname || '/';

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg('');
    setUnverifiedEmail('');
    setIsLoading(true);

    try {
      await login(email.trim(), password, keepSignedIn);
      navigate(redirectPath, { replace: true });
    } catch (err) {
      if (err.code === 'EMAIL_NOT_VERIFIED' || err.message.toLowerCase().includes('not verified')) {
        setUnverifiedEmail(err.email || email.trim());
        setErrorMsg('Your email address has not been verified yet.');
      } else {
        setErrorMsg(err.message || 'Invalid email or password.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectDemoAccount = (demoEmail, demoPass) => {
    setEmail(demoEmail);
    setPassword(demoPass);
    setErrorMsg('');
    setUnverifiedEmail('');
  };

  return (
    <AuthLayout
      badge="AI-POWERED INDUSTRIAL VISION"
      title="Safer factory floors, detected in real time."
      subtitle="Operix watches every camera feed, flags PPE and restricted-zone violations, keeps the evidence and alerts the right people."
      type="login"
    >
      <div style={{ width: '100%', maxWidth: '440px' }}>
        <div className="auth-card">
          <div style={{ marginBottom: '1.75rem' }}>
            <div className="auth-mobile-logo" style={{ marginBottom: '1.25rem' }}>
              <Logo size={46} showText={true} />
            </div>
            <h2 style={{ fontSize: '24px', fontWeight: 800, color: 'var(--text-primary)', letterSpacing: '-0.02em', marginBottom: '6px' }}>
              Welcome back
            </h2>
            <p style={{ fontSize: '13.5px', color: 'var(--text-muted)' }}>
              Sign in to your Operix workspace
            </p>
          </div>

          {/* Error Banner */}
          {errorMsg && (
            <div style={{
              backgroundColor: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              borderRadius: '8px',
              padding: '12px 14px',
              fontSize: '13px',
              color: '#EF4444',
              marginBottom: '1.25rem'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600 }}>
                <AlertCircle size={16} style={{ flexShrink: 0 }} />
                <span>{errorMsg}</span>
              </div>
              {unverifiedEmail && (
                <div style={{ marginTop: '8px', paddingLeft: '24px' }}>
                  <button
                    type="button"
                    onClick={() => navigate('/verify-email', { state: { email: unverifiedEmail } })}
                    className="btn btn-secondary btn-sm"
                    style={{ fontSize: '12px', padding: '4px 10px', color: '#EF4444', borderColor: 'rgba(239, 68, 68, 0.4)' }}
                  >
                    Verify Email Now &rarr;
                  </button>
                </div>
              )}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="form-label">Work email</label>
              <div className="input-with-icon">
                <Mail size={16} />
                <input
                  type="email"
                  className="form-control"
                  placeholder="name@company.com"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  required
                />
              </div>
            </div>

            <div className="form-group">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.45rem' }}>
                <label className="form-label" style={{ margin: 0 }}>Password</label>
                <Link to="/forgot-password" style={{ fontSize: '12px', color: 'var(--primary)', fontWeight: 600 }}>
                  Forgot password?
                </Link>
              </div>

              <div className="input-with-icon">
                <Lock size={16} />
                <input
                  type={showPassword ? 'text' : 'password'}
                  className="form-control has-toggle"
                  placeholder="Enter your password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  required
                />
                <button
                  type="button"
                  className="password-toggle-btn"
                  onClick={() => setShowPassword(p => !p)}
                  title={showPassword ? 'Hide password' : 'Show password'}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', margin: '1.25rem 0 1.5rem' }}>
              <label className="switch-wrapper">
                <input
                  type="checkbox"
                  className="switch-input"
                  checked={keepSignedIn}
                  onChange={e => setKeepSignedIn(e.target.checked)}
                />
                <span className="switch-slider" />
              </label>
              <span style={{ fontSize: '13px', color: 'var(--text-secondary)', fontWeight: 500 }}>
                Keep me signed in
              </span>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="btn btn-primary"
              style={{ width: '100%', padding: '0.75rem', fontSize: '14px', borderRadius: '8px' }}
            >
              {isLoading ? 'Signing in...' : 'Sign in'}
            </button>

            <div style={{ textAlign: 'center', marginTop: '1.5rem', fontSize: '13px', color: 'var(--text-muted)' }}>
              New to Operix?{' '}
              <Link to="/register" style={{ color: 'var(--primary)', fontWeight: 700 }}>
                Create an account
              </Link>
            </div>
          </form>

          {/* Quick Mock Role Accounts Helper (Visible only in Mock Mode) */}
          {API_CONFIG.useMock && (
            <div style={{
              marginTop: '1.5rem',
              paddingTop: '1.25rem',
              borderTop: '1px solid var(--border-color)',
              fontSize: '11.5px',
              color: 'var(--text-muted)'
            }}>
              <div style={{ fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px', color: 'var(--text-secondary)' }}>
                Quick Test Accounts (Mock Mode)
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                <button
                  type="button"
                  onClick={() => handleSelectDemoAccount('mona@plant1.example', 'admin123')}
                  className="btn btn-secondary btn-sm"
                  style={{ fontSize: '11px', padding: '3px 8px' }}
                  title="Administrator account"
                >
                  Admin
                </button>
                <button
                  type="button"
                  onClick={() => handleSelectDemoAccount('omar@plant1.example', 'manager123')}
                  className="btn btn-secondary btn-sm"
                  style={{ fontSize: '11px', padding: '3px 8px' }}
                  title="Factory Manager account"
                >
                  Manager
                </button>
                <button
                  type="button"
                  onClick={() => handleSelectDemoAccount('karim.adel@operix.io', 'password123')}
                  className="btn btn-secondary btn-sm"
                  style={{ fontSize: '11px', padding: '3px 8px' }}
                  title="Safety Supervisor account"
                >
                  Supervisor
                </button>
                <button
                  type="button"
                  onClick={() => handleSelectDemoAccount('sara@plant1.example', 'viewer123')}
                  className="btn btn-secondary btn-sm"
                  style={{ fontSize: '11px', padding: '3px 8px' }}
                  title="Viewer account"
                >
                  Viewer
                </button>
                <button
                  type="button"
                  onClick={() => handleSelectDemoAccount('youssef@plant1.example', 'password123')}
                  className="btn btn-secondary btn-sm"
                  style={{ fontSize: '11px', padding: '3px 8px', color: '#D97706', borderColor: 'rgba(217, 119, 6, 0.3)' }}
                  title="Unverified account (test rejection)"
                >
                  Unverified
                </button>
              </div>
            </div>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px', fontSize: '11.5px', color: 'var(--text-light)', marginTop: '1.25rem' }}>
          <Shield size={13} />
          <span>Access is role-based and verified by the Operix backend</span>
        </div>
      </div>
    </AuthLayout>
  );
}
