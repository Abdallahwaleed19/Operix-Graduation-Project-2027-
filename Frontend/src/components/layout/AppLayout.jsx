import React from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import Sidebar from '../common/Sidebar';
import { useAuth } from '../../context/AuthContext';
import AccessDeniedPage from '../../pages/error/AccessDeniedPage';

export default function AppLayout() {
  const { isViewer } = useAuth();
  const location = useLocation();

  // Screen 25: If a Viewer tries to navigate to Settings or Rule Builder, show Access Denied!
  const isRestrictedForViewer =
    isViewer &&
    (location.pathname.startsWith('/settings') ||
      location.pathname.startsWith('/rules') ||
      location.pathname.startsWith('/assistant'));

  return (
    <div className="app-shell">
      <Sidebar />
      <main className="app-main">
        {isRestrictedForViewer ? <AccessDeniedPage /> : <Outlet />}
      </main>
    </div>
  );
}
