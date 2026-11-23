import React, { useState } from 'react';
import AuthLayout from '../../components/layout/AuthLayout';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Mail, Check, AlertCircle, Shield, ArrowRight, CheckCircle2 } from 'lucide-react';
import { authService } from '../../services/authService';
import Logo from '../../components/common/Logo';

export default function VerifyEmailPage() {
  const location = useLocation();
  const navigate = useNavigate();

  // Read email from navigation state or fallback
  const passedEmail = location.state?.email || '';
  const initialTestCode = location.state?.testVerificationCode || '123456';

  const [email, setEmail] = useState(passedEmail || 'karim.adel@operix.io');
  const [code, setCode] = useState('');
  const [testCode, setTestCode] = useState(initialTestCode);
  const [isVerified, setIsVerified] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [resendStatus, setResendStatus] = useState(false);

  const handleVerify = async (e) => {
    e.preventDefault();
    if (!code.trim()) {
      setErrorMsg('Please enter the 6-digit verification code.');
      return;
    }

    setIsSubmitting(true);
    setErrorMsg('');
    try {
      const res = await authService.verifyEmail({
        email: email.trim(),
        code: code.trim()
      });
      setIsVerified(true);
      setSuccessMsg(res.message || 'Email verified successfully!');
    } catch (err) {
      setErrorMsg(err.message || 'Verification failed. Please check the code.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleResend = async () => {
    setErrorMsg('');
    setResendStatus(false);
    try {
      const res = await authService.resendVerificationCode(email.trim());
      setResendStatus(true);
      if (res.testVerificationCode) {
        setTestCode(res.testVerificationCode);
      }
      setTimeout(() => setResendStatus(false), 4000);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to resend verification code.');
    }
  };

  const fillTestCode = () => {
    if (testCode) {
      setCode(testCode);
      setErrorMsg('');
    }
  };

  return (
    <AuthLayout
      badge="ACCOUNT VERIFICATION"
      title={isVerified ? "Verification complete." : "Almost there."}
      subtitle={isVerified
        ? "Your email is verified. Your factory administrator activates full access according to your role."
        : "Verify your email to activate your account and access the Operix platform."}
      type="verify"
    >
      <div style={{ width: '100%', maxWidth: '440px' }}>
        <div className="auth-card" style={{ padding: '2.25rem' }}>
          <div className="auth-mobile-logo" style={{ marginBottom: '1.25rem', textAlign: 'center' }}>
            <Logo size={46} showText={true} />
          </div>

          {/* Header Icon */}
          <div style={{
            width: '60px',
            height: '60px',
            borderRadius: '50%',
            backgroundColor: isVerified ? 'rgba(16, 185, 129, 0.15)' : 'var(--primary)',
            color: isVerified ? '#10B981' : '#FFFFFF',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 1.25rem'
          }}>
            {isVerified ? <CheckCircle2 size={32} /> : <Mail size={26} />}
          </div>

          <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
            <h2 style={{ fontSize: '22px', fontWeight: 800, color: 'var(--text-primary)', marginBottom: '6px', letterSpacing: '-0.02em' }}>
              {isVerified ? 'Email verified!' : 'Check your inbox'}
            </h2>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
              {isVerified ? (
                <>Your email address <strong>{email}</strong> has been successfully confirmed.</>
              ) : (
                <>We sent a verification code to <strong>{email}</strong>.<br />Enter the 6-digit code below to confirm your account.</>
              )}
            </p>
          </div>

          {/* Error Banner */}
          {errorMsg && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              backgroundColor: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              borderRadius: '8px',
              padding: '10px 14px',
              fontSize: '12.5px',
              color: '#EF4444',
              marginBottom: '1.25rem'
            }}>
              <AlertCircle size={16} style={{ flexShrink: 0 }} />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Success Banner */}
          {successMsg && isVerified && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              backgroundColor: 'rgba(16, 185, 129, 0.1)',
              border: '1px solid rgba(16, 185, 129, 0.3)',
              borderRadius: '8px',
              padding: '10px 14px',
              fontSize: '12.5px',
              color: '#10B981',
              marginBottom: '1.25rem'
            }}>
              <Check size={16} style={{ flexShrink: 0 }} />
              <span>{successMsg}</span>
            </div>
          )}

          {/* Pending / Verified Status Box */}
          <div style={{
            backgroundColor: 'var(--bg-card-subtle)',
            border: '1px solid var(--border-color)',
            borderRadius: '10px',
            padding: '1rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '10px',
            marginBottom: '1.5rem'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '12.5px' }}>
              <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>Email verification</span>
              {isVerified ? (
                <span style={{ color: '#10B981', display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 700 }}>
                  <Check size={14} /> Verified
                </span>
              ) : (
                <span style={{ color: '#D97706', display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600 }}>
                  <span className="badge-dot" style={{ backgroundColor: '#F59E0B' }} />
                  Pending code
                </span>
              )}
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '12.5px' }}>
              <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>Factory membership · Plant 1</span>
              <span style={{ color: '#3B6280', display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600 }}>
                <Shield size={13} color="var(--primary)" />
                {isVerified ? 'Active & Assigned' : 'Awaiting activation'}
              </span>
            </div>
          </div>

          {!isVerified ? (
            <form onSubmit={handleVerify}>
              {/* Verification Code Form Field */}
              <div className="form-group" style={{ marginBottom: '1.25rem' }}>
                <label className="form-label" style={{ textAlign: 'left', display: 'block' }}>
                  6-digit verification code
                </label>
                <input
                  type="text"
                  maxLength={6}
                  className="form-control"
                  placeholder="123456"
                  value={code}
                  onChange={e => setCode(e.target.value.replace(/[^0-9]/g, ''))}
                  style={{
                    letterSpacing: '0.35em',
                    fontSize: '20px',
                    fontWeight: 700,
                    textAlign: 'center',
                    padding: '0.65rem'
                  }}
                  required
                />
              </div>

              {/* Dev Helper Pill (Mock Mode) */}
              {testCode && (
                <div style={{
                  backgroundColor: 'var(--bg-app)',
                  border: '1px dashed var(--primary)',
                  borderRadius: '6px',
                  padding: '8px 12px',
                  fontSize: '11.5px',
                  color: 'var(--text-secondary)',
                  marginBottom: '1.25rem',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between'
                }}>
                  <span>
                    Mock Mode Code: <strong style={{ color: 'var(--primary)', letterSpacing: '0.1em' }}>{testCode}</strong>
                  </span>
                  <button
                    type="button"
                    onClick={fillTestCode}
                    className="btn btn-secondary btn-sm"
                    style={{ padding: '3px 8px', fontSize: '11px' }}
                  >
                    Auto-Fill
                  </button>
                </div>
              )}

              <button
                type="submit"
                disabled={isSubmitting}
                className="btn btn-primary"
                style={{ width: '100%', padding: '0.75rem', fontSize: '14px', borderRadius: '8px', marginBottom: '10px' }}
              >
                {isSubmitting ? 'Verifying...' : 'Verify code'}
              </button>

              <button
                type="button"
                className="btn btn-secondary"
                onClick={handleResend}
                style={{ width: '100%', padding: '0.65rem', fontSize: '12.5px', borderRadius: '8px' }}
              >
                Resend verification email
              </button>
            </form>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => navigate('/login', { state: { email } })}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  fontSize: '14px',
                  borderRadius: '8px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px'
                }}
              >
                <span>Proceed to Sign In</span>
                <ArrowRight size={15} />
              </button>
            </div>
          )}

          {resendStatus && (
            <div style={{ fontSize: '12px', color: '#10B981', marginTop: '1rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px' }}>
              <Check size={14} /> A new verification code has been generated!
            </div>
          )}

          <div style={{ textAlign: 'center', marginTop: '1.5rem', fontSize: '13px' }}>
            <Link to="/login" style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>
              Back to sign in
            </Link>
          </div>
        </div>
      </div>
    </AuthLayout>
  );
}
