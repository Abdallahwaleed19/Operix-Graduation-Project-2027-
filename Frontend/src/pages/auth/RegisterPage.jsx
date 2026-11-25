import React, { useState } from 'react';
import AuthLayout from '../../components/layout/AuthLayout';
import { Link, useNavigate } from 'react-router-dom';
import { User, Mail, Lock, Building, LayoutGrid, Shield, Sliders, CheckCircle2, Lock as LockIcon, AlertCircle } from 'lucide-react';
import Logo from '../../components/common/Logo';
import { authService } from '../../services/authService';

export default function RegisterPage() {
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [factory, setFactory] = useState('Plant 1');
  const [selectedRole, setSelectedRole] = useState('Safety Supervisor');
  const [agreed, setAgreed] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const handleRegister = async (e) => {
    e.preventDefault();
    setErrorMsg('');
    setSuccessMsg('');

    if (password.length < 6) {
      setErrorMsg('Password must be at least 6 characters.');
      return;
    }

    if (password !== confirmPassword) {
      setErrorMsg('Passwords do not match.');
      return;
    }

    if (!agreed) {
      setErrorMsg('You must agree to the Terms of use and Privacy policy.');
      return;
    }

    setIsLoading(true);
    try {
      const res = await authService.register({
        fullName,
        email,
        password,
        role: selectedRole,
        factory
      });

      if (res.testVerificationCode) {
        navigate('/verify-email', {
          state: {
            email,
            testVerificationCode: res.testVerificationCode,
            role: selectedRole,
            factory
          }
        });
      } else {
        setSuccessMsg(
          res.message ||
            'Account request submitted. An administrator has been notified and must approve your account before you can sign in.'
        );
      }
    } catch (err) {
      setErrorMsg(err.message || 'Registration failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthLayout
      badge="GET STARTED"
      title="Get the right access from day one."
      subtitle="Create your account, pick your role and your factory admin activates your membership."
      type="register"
    >
      <div style={{ width: '100%', maxWidth: '520px' }}>
        <div className="auth-card" style={{ padding: '2rem 2.25rem' }}>
          <div style={{ marginBottom: '1.5rem' }}>
            <div className="auth-mobile-logo" style={{ marginBottom: '1.25rem' }}>
              <Logo size={46} showText={true} />
            </div>
            <h2 style={{ fontSize: '24px', fontWeight: 800, color: 'var(--text-primary)', letterSpacing: '-0.02em', marginBottom: '4px' }}>
              Create your account
            </h2>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
              Choose your role so Operix can set the right permissions
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

          {successMsg && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              backgroundColor: 'rgba(16, 185, 129, 0.12)',
              border: '1px solid rgba(16, 185, 129, 0.35)',
              borderRadius: '8px',
              padding: '12px 14px',
              fontSize: '13px',
              color: '#10B981',
              marginBottom: '1.25rem'
            }}>
              <CheckCircle2 size={16} style={{ flexShrink: 0 }} />
              <span>{successMsg}</span>
            </div>
          )}

          <form onSubmit={handleRegister}>
            {/* Name & Email Row */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <div className="form-group">
                <label className="form-label">Full name</label>
                <div className="input-with-icon">
                  <User size={15} />
                  <input
                    type="text"
                    className="form-control"
                    placeholder="Your full name"
                    value={fullName}
                    onChange={e => setFullName(e.target.value)}
                    required
                  />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Work email</label>
                <div className="input-with-icon">
                  <Mail size={15} />
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
            </div>

            {/* Password Row */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <div className="form-group">
                <label className="form-label">Password</label>
                <div className="input-with-icon">
                  <Lock size={15} />
                  <input
                    type="password"
                    className="form-control"
                    placeholder="Create a password"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    required
                  />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Confirm password</label>
                <div className="input-with-icon">
                  <Lock size={15} />
                  <input
                    type="password"
                    className="form-control"
                    placeholder="Repeat your password"
                    value={confirmPassword}
                    onChange={e => setConfirmPassword(e.target.value)}
                    required
                  />
                </div>
              </div>
            </div>

            {/* Factory Selector */}
            <div className="form-group">
              <label className="form-label">Factory</label>
              <div className="input-with-icon">
                <Building size={15} />
                <select
                  className="form-control form-select"
                  value={factory}
                  onChange={e => setFactory(e.target.value)}
                >
                  <option value="Plant 1">Plant 1 · Menoufia</option>
                  <option value="Plant 2">Plant 2 · 10th of Ramadan</option>
                  <option value="Plant 3">Plant 3 · Helwan Logistics</option>
                </select>
              </div>
            </div>

            {/* Role Selection Cards */}
            <div style={{ marginBottom: '1.25rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <label className="form-label" style={{ margin: 0 }}>Select your role</label>
                <span style={{ fontSize: '11px', color: 'var(--text-light)', fontWeight: 600 }}>Required</span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px' }}>
                {/* Role 1: Factory Manager */}
                <div
                  onClick={() => setSelectedRole('Factory Manager')}
                  style={{
                    border: selectedRole === 'Factory Manager' ? '2px solid var(--primary)' : '1px solid var(--border-color)',
                    backgroundColor: selectedRole === 'Factory Manager' ? 'var(--bg-active-nav)' : 'var(--bg-card)',
                    borderRadius: '8px',
                    padding: '12px 10px',
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    minHeight: '110px'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <LayoutGrid size={16} color="var(--primary)" />
                    <div style={{
                      width: '16px',
                      height: '16px',
                      borderRadius: '50%',
                      border: '1.5px solid var(--border-color)',
                      backgroundColor: selectedRole === 'Factory Manager' ? 'var(--primary)' : 'transparent'
                    }} />
                  </div>
                  <div>
                    <div style={{ fontSize: '12.5px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '2px' }}>
                      Factory Manager
                    </div>
                    <div style={{ fontSize: '10.5px', color: 'var(--text-muted)', lineHeight: 1.3 }}>
                      Dashboard, workforce analytics and reports
                    </div>
                  </div>
                </div>

                {/* Role 2: Safety Supervisor */}
                <div
                  onClick={() => setSelectedRole('Safety Supervisor')}
                  style={{
                    border: selectedRole === 'Safety Supervisor' ? '2px solid var(--primary)' : '1px solid var(--border-color)',
                    backgroundColor: selectedRole === 'Safety Supervisor' ? 'var(--bg-active-nav)' : 'var(--bg-card)',
                    borderRadius: '8px',
                    padding: '12px 10px',
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    minHeight: '110px'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Shield size={16} color="var(--primary)" />
                    <CheckCircle2 size={16} color="var(--primary)" />
                  </div>
                  <div>
                    <div style={{ fontSize: '12.5px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '2px' }}>
                      Safety Supervisor
                    </div>
                    <div style={{ fontSize: '10.5px', color: 'var(--text-muted)', lineHeight: 1.3 }}>
                      Live alerts, incidents and evidence review
                    </div>
                  </div>
                </div>

                {/* Role 3: System Administrator */}
                <div
                  style={{
                    border: '1px dashed var(--border-color)',
                    borderRadius: '8px',
                    padding: '12px 10px',
                    opacity: 0.65,
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    minHeight: '110px',
                    backgroundColor: 'var(--bg-card-subtle)'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Sliders size={16} color="var(--text-muted)" />
                    <LockIcon size={14} color="var(--text-muted)" />
                  </div>
                  <div>
                    <div style={{ fontSize: '12.5px', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '2px' }}>
                      System Administrator
                    </div>
                    <div style={{ fontSize: '10.5px', color: 'var(--text-muted)' }}>
                      By invitation only
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Admin approval info banner */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              padding: '10px 14px',
              borderRadius: '8px',
              backgroundColor: 'var(--bg-card-subtle)',
              border: '1px solid var(--border-color)',
              fontSize: '12px',
              color: 'var(--text-secondary)',
              marginBottom: '1.25rem'
            }}>
              <Shield size={15} color="var(--primary)" style={{ flexShrink: 0 }} />
              <span>After you verify your email, your factory admin activates your membership.</span>
            </div>

            {/* Terms checkbox */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '1.5rem' }}>
              <input
                type="checkbox"
                id="terms"
                checked={agreed}
                onChange={e => setAgreed(e.target.checked)}
                style={{ width: '16px', height: '16px', accentColor: 'var(--primary)' }}
                required
              />
              <label htmlFor="terms" style={{ fontSize: '12.5px', color: 'var(--text-secondary)' }}>
                I agree to the <span style={{ color: 'var(--primary)', fontWeight: 600 }}>Terms of use</span> and <span style={{ color: 'var(--primary)', fontWeight: 600 }}>Privacy policy</span>
              </label>
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              style={{ width: '100%', padding: '0.75rem', fontSize: '14px', borderRadius: '8px' }}
            >
              Create account
            </button>

            <div style={{ textAlign: 'center', marginTop: '1.25rem', fontSize: '13px', color: 'var(--text-muted)' }}>
              Already have an account?{' '}
              <Link to="/login" style={{ color: 'var(--primary)', fontWeight: 700 }}>
                Sign in
              </Link>
            </div>
          </form>
        </div>
      </div>
    </AuthLayout>
  );
}
