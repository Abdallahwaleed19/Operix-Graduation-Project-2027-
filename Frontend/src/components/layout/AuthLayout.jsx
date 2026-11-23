import React from 'react';
import { Eye, ShieldCheck, BellRing, UserCheck, Sliders, PlayCircle, KeyRound, Mail } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { Sun, Moon } from 'lucide-react';
import Logo from '../common/Logo';

export default function AuthLayout({
  badge = 'AI-POWERED INDUSTRIAL VISION',
  title = 'Safer factory floors, detected in real time.',
  subtitle = 'Operix watches every camera feed, flags PPE and restricted-zone violations, keeps the evidence and alerts the right people.',
  type = 'login', // 'login' | 'register' | 'forgot' | 'verify'
  children
}) {
  const { isDark, toggleTheme } = useTheme();

  // Choose feature cards based on the screen type
  const renderFeatures = () => {
    if (type === 'register') {
      return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div className="operix-card" style={{ padding: '14px 18px', display: 'flex', gap: '14px', alignItems: 'center' }}>
            <div className="btn-icon" style={{ backgroundColor: 'var(--bg-active-nav)', border: 'none' }}>
              <UserCheck size={18} color="var(--primary)" />
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: '13.5px' }}>Create your account</div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Use your work email and a strong password</div>
            </div>
          </div>

          <div className="operix-card" style={{ padding: '14px 18px', display: 'flex', gap: '14px', alignItems: 'center' }}>
            <div className="btn-icon" style={{ backgroundColor: 'var(--bg-active-nav)', border: 'none' }}>
              <ShieldCheck size={18} color="var(--primary)" />
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: '13.5px' }}>Choose your role</div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Permissions follow your role inside the factory</div>
            </div>
          </div>

          <div className="operix-card" style={{ padding: '14px 18px', display: 'flex', gap: '14px', alignItems: 'center' }}>
            <div className="btn-icon" style={{ backgroundColor: 'var(--bg-active-nav)', border: 'none' }}>
              <PlayCircle size={18} color="var(--primary)" />
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: '13.5px' }}>Start monitoring</div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Once your factory admin activates your membership</div>
            </div>
          </div>
        </div>
      );
    }

    if (type === 'forgot') {
      return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div className="operix-card" style={{ padding: '14px 18px', display: 'flex', gap: '14px', alignItems: 'center' }}>
            <div className="btn-icon" style={{ backgroundColor: 'var(--bg-active-nav)', border: 'none' }}>
              <Mail size={18} color="var(--primary)" />
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: '13.5px' }}>Enter your work email</div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>We send a one-time reset link</div>
            </div>
          </div>

          <div className="operix-card" style={{ padding: '14px 18px', display: 'flex', gap: '14px', alignItems: 'center' }}>
            <div className="btn-icon" style={{ backgroundColor: 'var(--bg-active-nav)', border: 'none' }}>
              <KeyRound size={18} color="var(--primary)" />
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: '13.5px' }}>Open the link</div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>It works once and expires shortly</div>
            </div>
          </div>

          <div className="operix-card" style={{ padding: '14px 18px', display: 'flex', gap: '14px', alignItems: 'center' }}>
            <div className="btn-icon" style={{ backgroundColor: 'var(--bg-active-nav)', border: 'none' }}>
              <ShieldCheck size={18} color="var(--primary)" />
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: '13.5px' }}>Choose a new password</div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Then sign in as usual</div>
            </div>
          </div>
        </div>
      );
    }

    if (type === 'verify') {
      return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div className="operix-card" style={{ padding: '14px 18px', display: 'flex', gap: '14px', alignItems: 'center' }}>
            <div className="btn-icon" style={{ backgroundColor: 'var(--bg-active-nav)', border: 'none' }}>
              <Mail size={18} color="var(--primary)" />
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: '13.5px' }}>Verify your email</div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Open the link we sent to your inbox</div>
            </div>
          </div>

          <div className="operix-card" style={{ padding: '14px 18px', display: 'flex', gap: '14px', alignItems: 'center' }}>
            <div className="btn-icon" style={{ backgroundColor: 'var(--bg-active-nav)', border: 'none' }}>
              <ShieldCheck size={18} color="var(--primary)" />
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: '13.5px' }}>Wait for approval</div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Your factory admin activates your membership</div>
            </div>
          </div>

          <div className="operix-card" style={{ padding: '14px 18px', display: 'flex', gap: '14px', alignItems: 'center' }}>
            <div className="btn-icon" style={{ backgroundColor: 'var(--bg-active-nav)', border: 'none' }}>
              <PlayCircle size={18} color="var(--primary)" />
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: '13.5px' }}>Start monitoring</div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Dashboards unlock once you are active</div>
            </div>
          </div>
        </div>
      );
    }

    // Default Login Features
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <div className="operix-card" style={{ padding: '14px 18px', display: 'flex', gap: '14px', alignItems: 'center' }}>
          <div className="btn-icon" style={{ backgroundColor: 'var(--bg-active-nav)', border: 'none' }}>
            <Eye size={18} color="var(--primary)" />
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: '13.5px' }}>Continuous detection</div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>RTSP streams analysed for people, PPE and tracking</div>
          </div>
        </div>

        <div className="operix-card" style={{ padding: '14px 18px', display: 'flex', gap: '14px', alignItems: 'center' }}>
          <div className="btn-icon" style={{ backgroundColor: 'var(--bg-active-nav)', border: 'none' }}>
            <ShieldCheck size={18} color="var(--primary)" />
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: '13.5px' }}>Incident & evidence</div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Every violation stored with image or clip evidence</div>
          </div>
        </div>

        <div className="operix-card" style={{ padding: '14px 18px', display: 'flex', gap: '14px', alignItems: 'center' }}>
          <div className="btn-icon" style={{ backgroundColor: 'var(--bg-active-nav)', border: 'none' }}>
            <BellRing size={18} color="var(--primary)" />
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: '13.5px' }}>Instant alerts</div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Dashboard and configured channels, with no delay</div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="auth-split-wrapper">
      {/* Top Header Theme Toggle */}
      <div
        className="auth-top-theme-toggle"
        style={{
          position: 'absolute',
          top: '24px',
          right: '28px',
          zIndex: 50
        }}
      >
        <button
          className="btn-icon"
          onClick={toggleTheme}
          title={isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
          aria-label={isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
          style={{
            backgroundColor: 'var(--bg-card)',
            border: '1px solid var(--border-color)',
            boxShadow: 'var(--shadow-sm)'
          }}
        >
          {isDark ? <Sun size={18} /> : <Moon size={18} />}
        </button>
      </div>

      {/* Brand Side (Left) */}
      <div className="auth-brand-side">
        <div>
          {/* Top Industrial Diagonal Caution Stripes */}
          <div
            className="sidebar-stripe-ribbon"
            style={{ borderRadius: '4px', marginBottom: '2rem' }}
          />

          <div style={{ marginBottom: '3rem' }}>
            <Logo size={52} showText={true} />
          </div>

          <div style={{ maxWidth: '480px' }}>
            <div style={{
              fontSize: '11px',
              fontWeight: 800,
              letterSpacing: '0.08em',
              color: 'var(--primary)',
              textTransform: 'uppercase',
              marginBottom: '10px'
            }}>
              {badge}
            </div>
            <h1 style={{
              fontSize: '36px',
              fontWeight: 800,
              lineHeight: 1.15,
              letterSpacing: '-0.03em',
              color: 'var(--text-primary)',
              marginBottom: '1rem'
            }}>
              {title}
            </h1>
            <p style={{
              fontSize: '14px',
              lineHeight: 1.6,
              color: 'var(--text-muted)',
              marginBottom: '2.5rem'
            }}>
              {subtitle}
            </p>

            {renderFeatures()}
          </div>
        </div>

        <div style={{
          marginTop: '3rem',
          fontSize: '12px',
          color: 'var(--text-light)'
        }}>
          AI-Powered Industrial Vision & Safety Intelligence Platform · Graduation Project
        </div>
      </div>

      {/* Form Side (Right) */}
      <div className="auth-form-side">
        {children}
      </div>
    </div>
  );
}
