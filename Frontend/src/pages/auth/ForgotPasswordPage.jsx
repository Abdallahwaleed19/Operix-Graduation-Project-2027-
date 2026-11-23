import React, { useState } from 'react';
import AuthLayout from '../../components/layout/AuthLayout';
import { Link, useNavigate } from 'react-router-dom';
import { Mail, ArrowLeft, CheckCircle, ArrowRight, AlertCircle } from 'lucide-react';
import { authService } from '../../services/authService';
import Logo from '../../components/common/Logo';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [testToken, setTestToken] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email.trim()) return;

    setIsLoading(true);
    setErrorMsg('');
    try {
      const res = await authService.requestPasswordReset(email.trim());
      setSubmitted(true);
      if (res.testResetToken) {
        setTestToken(res.testResetToken);
      }
    } catch (err) {
      setErrorMsg(err.message || 'Failed to request reset link.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthLayout
      badge="ACCOUNT RECOVERY"
      title="Reset your password in a minute."
      subtitle="We send a one-time link to your work email so you can choose a new password and get back to monitoring."
      type="forgot"
    >
      <div style={{ width: '100%', maxWidth: '440px' }}>
        <div className="auth-card">
          <div style={{ marginBottom: '1.75rem' }}>
            <div className="auth-mobile-logo" style={{ marginBottom: '1.25rem' }}>
              <Logo size={46} showText={true} />
            </div>
            <h2 style={{ fontSize: '24px', fontWeight: 800, color: 'var(--text-primary)', letterSpacing: '-0.02em', marginBottom: '6px' }}>
              Forgot your password?
            </h2>
            <p style={{ fontSize: '13.5px', color: 'var(--text-muted)' }}>
              Enter your work email and we'll send you a reset link.
            </p>
          </div>

          {errorMsg && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              backgroundColor: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              borderRadius: '8px',
              padding: '10px 14px',
              fontSize: '13px',
              color: '#EF4444',
              marginBottom: '1.25rem'
            }}>
              <AlertCircle size={16} />
              <span>{errorMsg}</span>
            </div>
          )}

          {submitted ? (
            <div style={{ textAlign: 'center', padding: '0.5rem 0' }}>
              <div style={{
                width: '48px',
                height: '48px',
                borderRadius: '50%',
                backgroundColor: 'rgba(16, 185, 129, 0.12)',
                color: '#10B981',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 1rem'
              }}>
                <CheckCircle size={26} />
              </div>
              <h3 style={{ fontSize: '17px', fontWeight: 700, marginBottom: '6px', color: 'var(--text-primary)' }}>
                Reset instructions generated
              </h3>
              <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '1.25rem', lineHeight: 1.5 }}>
                If an account exists for <strong>{email}</strong>, a password reset token has been created.
              </p>

              {/* Dev Token Simulation Helper */}
              {testToken && (
                <div style={{
                  backgroundColor: 'var(--bg-card-subtle)',
                  border: '1px dashed var(--primary)',
                  borderRadius: '8px',
                  padding: '12px',
                  textAlign: 'left',
                  marginBottom: '1.25rem',
                  fontSize: '12px'
                }}>
                  <div style={{ fontWeight: 700, color: 'var(--primary)', marginBottom: '4px' }}>
                    Mock Mode · Simulated Reset Token:
                  </div>
                  <div style={{ fontFamily: 'monospace', backgroundColor: 'var(--bg-card)', padding: '6px 8px', borderRadius: '4px', wordBreak: 'break-all' }}>
                    {testToken}
                  </div>
                  <button
                    type="button"
                    className="btn btn-primary btn-sm"
                    onClick={() => navigate(`/reset-password?token=${testToken}`)}
                    style={{ marginTop: '8px', width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}
                  >
                    <span>Proceed to Reset Password</span>
                    <ArrowRight size={14} />
                  </button>
                </div>
              )}

              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <Link to="/reset-password" className="btn btn-secondary" style={{ width: '100%', fontSize: '13px' }}>
                  Enter token manually
                </Link>
                <Link to="/login" style={{ fontSize: '12.5px', color: 'var(--text-muted)', marginTop: '6px' }}>
                  Back to sign in
                </Link>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit}>
              <div className="form-group" style={{ marginBottom: '1.5rem' }}>
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

              <button
                type="submit"
                disabled={isLoading}
                className="btn btn-primary"
                style={{ width: '100%', padding: '0.75rem', fontSize: '14px', borderRadius: '8px' }}
              >
                {isLoading ? 'Processing...' : 'Send reset link'}
              </button>

              <div style={{ textAlign: 'center', marginTop: '1.5rem' }}>
                <Link
                  to="/login"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px',
                    fontSize: '13px',
                    color: 'var(--text-secondary)',
                    fontWeight: 600
                  }}
                >
                  <ArrowLeft size={14} />
                  Back to sign in
                </Link>
              </div>
            </form>
          )}
        </div>
      </div>
    </AuthLayout>
  );
}
