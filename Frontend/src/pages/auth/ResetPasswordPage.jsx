import React, { useState, useEffect } from 'react';
import AuthLayout from '../../components/layout/AuthLayout';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { Lock, Eye, EyeOff, CheckCircle, ArrowLeft, KeyRound, AlertCircle } from 'lucide-react';
import { authService } from '../../services/authService';
import Logo from '../../components/common/Logo';

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const urlToken = searchParams.get('token') || '';
  const [token, setToken] = useState(urlToken);
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const [isLoading, setIsLoading] = useState(false);
  const [tokenStatus, setTokenStatus] = useState(null); // { valid: boolean, email?: string, message?: string }
  const [errorMsg, setErrorMsg] = useState('');
  const [isSuccess, setIsSuccess] = useState(false);

  // Validate token whenever token changes
  useEffect(() => {
    if (!token.trim()) {
      setTokenStatus(null);
      return;
    }

    let isMounted = true;
    authService.validateResetToken(token.trim()).then(res => {
      if (isMounted) {
        setTokenStatus(res);
        if (!res.valid) {
          setErrorMsg(res.message || 'Invalid or expired reset token.');
        } else {
          setErrorMsg('');
        }
      }
    });

    return () => { isMounted = false; };
  }, [token]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg('');

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
      await authService.resetPassword({
        token: token.trim(),
        newPassword
      });
      setIsSuccess(true);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to reset password. Token may be invalid or expired.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthLayout
      badge="PASSWORD RESET"
      title="Create your new password."
      subtitle="Ensure your account is secure by setting a strong password for your Operix workspace."
      type="forgot"
    >
      <div style={{ width: '100%', maxWidth: '440px' }}>
        <div className="auth-card">
          <div style={{ marginBottom: '1.75rem' }}>
            <div className="auth-mobile-logo" style={{ marginBottom: '1.25rem' }}>
              <Logo size={46} showText={true} />
            </div>
            <h2 style={{ fontSize: '24px', fontWeight: 800, color: 'var(--text-primary)', letterSpacing: '-0.02em', marginBottom: '6px' }}>
              Set new password
            </h2>
            <p style={{ fontSize: '13.5px', color: 'var(--text-muted)' }}>
              {tokenStatus?.valid
                ? `Resetting password for ${tokenStatus.email}`
                : 'Enter your reset token and new password'}
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
              <AlertCircle size={16} style={{ flexShrink: 0 }} />
              <span>{errorMsg}</span>
            </div>
          )}

          {isSuccess ? (
            <div style={{ textAlign: 'center', padding: '1rem 0' }}>
              <div style={{
                width: '52px',
                height: '52px',
                borderRadius: '50%',
                backgroundColor: 'rgba(16, 185, 129, 0.12)',
                color: '#10B981',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 1rem'
              }}>
                <CheckCircle size={28} />
              </div>
              <h3 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '8px' }}>
                Password reset complete!
              </h3>
              <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '1.5rem', lineHeight: 1.5 }}>
                Your password has been securely updated. You can now sign in with your new credentials.
              </p>
              <Link
                to="/login"
                className="btn btn-primary"
                style={{ width: '100%', padding: '0.75rem', fontSize: '14px', borderRadius: '8px' }}
              >
                Sign in with new password
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit}>
              {/* Token field (pre-filled from URL or editable) */}
              <div className="form-group">
                <label className="form-label">Reset token</label>
                <div className="input-with-icon">
                  <KeyRound size={16} />
                  <input
                    type="text"
                    className="form-control"
                    placeholder="e.g. rst-xxx..."
                    value={token}
                    onChange={e => setToken(e.target.value)}
                    required
                  />
                </div>
                {tokenStatus?.valid && (
                  <span style={{ fontSize: '11.5px', color: '#10B981', fontWeight: 600, display: 'inline-block', marginTop: '4px' }}>
                    ✓ Valid reset token for {tokenStatus.email}
                  </span>
                )}
              </div>

              {/* New Password */}
              <div className="form-group">
                <label className="form-label">New password</label>
                <div className="input-with-icon">
                  <Lock size={16} />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    className="form-control has-toggle"
                    placeholder="At least 6 characters"
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

              {/* Confirm Password */}
              <div className="form-group" style={{ marginBottom: '1.5rem' }}>
                <label className="form-label">Confirm new password</label>
                <div className="input-with-icon">
                  <Lock size={16} />
                  <input
                    type={showConfirmPassword ? 'text' : 'password'}
                    className="form-control has-toggle"
                    placeholder="Repeat new password"
                    value={confirmPassword}
                    onChange={e => setConfirmPassword(e.target.value)}
                    required
                  />
                  <button
                    type="button"
                    className="password-toggle-btn"
                    onClick={() => setShowConfirmPassword(p => !p)}
                    title={showConfirmPassword ? 'Hide password' : 'Show password'}
                    aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
                  >
                    {showConfirmPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                className="btn btn-primary"
                disabled={isLoading || (tokenStatus && !tokenStatus.valid)}
                style={{ width: '100%', padding: '0.75rem', fontSize: '14px', borderRadius: '8px' }}
              >
                {isLoading ? 'Updating password...' : 'Update password'}
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
