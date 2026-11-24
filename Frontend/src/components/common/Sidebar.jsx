import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { useAuth, ROLES } from '../../context/AuthContext';
import Logo from './Logo';
import {
  LayoutGrid,
  Monitor,
  AlertTriangle,
  BarChart2,
  Thermometer,
  Sliders,
  MessageSquare,
  FileText,
  Settings
} from 'lucide-react';

export default function Sidebar() {
  const { role, isViewer, isSupervisor } = useAuth();
  const location = useLocation();

  // Navigation items available to all or role-dependent
  const mainNavItems = [
    { name: 'Dashboard', path: '/', icon: LayoutGrid },
    { name: 'Live Monitoring', path: '/monitoring', icon: Monitor },
    { name: 'Incidents', path: '/incidents', icon: AlertTriangle },
    // Only non-viewers see workforce, thermal by default in sidebar
    ...(!isViewer ? [
      { name: 'Workforce Analytics', path: '/analytics', icon: BarChart2 },
      { name: 'Thermal Monitoring', path: '/thermal', icon: Thermometer },
    ] : [])
  ];

  // Configure section
  const configureNavItems = [
    { name: 'No-Code Rule Builder', path: '/rules', icon: Sliders },
    { name: 'AI Assistant', path: '/assistant', icon: MessageSquare },
    { name: 'Reports', path: '/reports', icon: FileText },
    { name: 'Settings', path: '/settings', icon: Settings },
  ];

  // For Viewer: Reports is placed in main list or allowed, but Configure section is restricted
  const viewerNavItems = [
    { name: 'Dashboard', path: '/', icon: LayoutGrid },
    { name: 'Live Monitoring', path: '/monitoring', icon: Monitor },
    { name: 'Incidents', path: '/incidents', icon: AlertTriangle },
    { name: 'Reports', path: '/reports', icon: FileText },
  ];

  const currentNav = isViewer ? viewerNavItems : mainNavItems;

  return (
    <aside className="app-sidebar">
      {/* Top Industrial Diagonal Caution Stripes */}
      <div className="sidebar-stripe-ribbon" />

      {/* Brand Logo Header */}
      <div className="sidebar-brand">
        <Logo size={40} showText={true} />
      </div>

      {/* Navigation List */}
      <nav className="sidebar-nav">
        {currentNav.map((item) => {
          const Icon = item.icon;
          const isActive = location.pathname === item.path || (item.path !== '/' && location.pathname.startsWith(item.path));
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={`sidebar-nav-item ${isActive ? 'active' : ''}`}
            >
              <Icon size={18} />
              <span>{item.name}</span>
            </NavLink>
          );
        })}

        {/* Configure Section (Hidden for Viewer) */}
        {!isViewer && (
          <>
            <div className="sidebar-nav-section-title">Configure</div>
            {configureNavItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname.startsWith(item.path);
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  className={`sidebar-nav-item ${isActive ? 'active' : ''}`}
                >
                  <Icon size={18} />
                  <span>{item.name}</span>
                </NavLink>
              );
            })}
          </>
        )}
      </nav>

      {/* Sidebar Footer */}
      <div className="sidebar-footer">
        {/* Role indicator pill if in Viewer or Supervisor role mode (from screens 23 & 24) */}
        {isViewer && (
          <div className="sidebar-role-badge" style={{ color: '#D97706', borderColor: '#FDE68A' }}>
            <span className="badge-dot" style={{ backgroundColor: '#F59E0B' }}></span>
            <span>Viewer · Read-only</span>
          </div>
        )}

        {isSupervisor && (
          <div className="sidebar-role-badge" style={{ color: '#059669', borderColor: '#A7F3D0' }}>
            <span className="badge-dot" style={{ backgroundColor: '#10B981' }}></span>
            <span>Safety Supervisor</span>
          </div>
        )}

        {/* Live sync heartbeat status */}
        <div className="sidebar-status-box">
          <div className="status-active-row">
            <span className="badge-dot pulse" />
            <span>Monitoring active</span>
          </div>
          <div className="status-sync-time">Last sync 2 sec ago</div>
        </div>
      </div>
    </aside>
  );
}
