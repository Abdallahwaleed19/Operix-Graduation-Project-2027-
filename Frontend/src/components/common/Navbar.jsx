import React, { useState } from 'react';
import { useTheme } from '../../context/ThemeContext';
import { useAuth } from '../../context/AuthContext';
import { Sun, Moon, Shield, ChevronDown, User, ArrowLeft, LogOut } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import RoleSwitcherModal from './RoleSwitcherModal';

export default function Navbar({ title, subtitle, rightActions, backTo, backLabel = 'Back to Settings' }) {
  const { isDark, toggleTheme } = useTheme();
  const { currentUser, role, logout } = useAuth();
  const navigate = useNavigate();
  const [isRoleModalOpen, setIsRoleModalOpen] = useState(false);

  return (
    <>
      <header className="app-header">
        <div className="header-left">
          <div className="header-title-row" style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
            {backTo && (
              <button
                className="btn btn-secondary btn-sm back-nav-btn"
                onClick={() => navigate(backTo)}
                title={backLabel}
                aria-label={backLabel}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '5px 12px',
                  fontSize: '12.5px',
                  fontWeight: 600,
                  borderRadius: 'var(--radius-md)',
                  cursor: 'pointer',
                  flexShrink: 0
                }}
              >
                <ArrowLeft size={14} />
                <span>{backLabel}</span>
              </button>
            )}
            <h1 className="header-page-title">{title}</h1>
          </div>
          {subtitle && <p className="header-page-subtitle">{subtitle}</p>}
        </div>

        <div className="header-right">
          {/* Dynamic actions passed from page (e.g. Export report, Add camera, etc.) */}
          {rightActions}

          {/* Theme switcher toggle button */}
          <button
            className="btn-icon"
            onClick={toggleTheme}
            title={isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
            aria-label="Toggle theme"
          >
            {isDark ? <Sun size={18} /> : <Moon size={18} />}
          </button>

          {/* Quick Role Switcher Pill */}
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => setIsRoleModalOpen(true)}
            title="Switch current simulated role"
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <Shield size={14} color="var(--primary)" />
            <span>{role}</span>
            <ChevronDown size={12} />
          </button>

          {/* User profile avatar */}
          <button
            className="user-avatar-btn"
            onClick={() => navigate('/profile')}
            title="User Profile & Settings"
            aria-label="User Profile"
          >
            {currentUser?.initials || <User size={16} />}
          </button>

          {/* Quick Sign Out button */}
          <button
            className="btn-icon"
            onClick={() => {
              logout();
              navigate('/login');
            }}
            title="Sign out of Operix"
            aria-label="Sign out"
          >
            <LogOut size={16} />
          </button>
        </div>
      </header>

      <RoleSwitcherModal
        isOpen={isRoleModalOpen}
        onClose={() => setIsRoleModalOpen(false)}
      />
    </>
  );
}
