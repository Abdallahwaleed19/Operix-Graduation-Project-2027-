import React, { useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import Sidebar from '../common/Sidebar';
import { useAuth } from '../../context/AuthContext';
import AccessDeniedPage from '../../pages/error/AccessDeniedPage';
import { websocketService } from '../../services/websocketService';

export default function AppLayout() {
  const { isViewer, isAuthenticated } = useAuth();
  const location = useLocation();

  useEffect(() => {
    if (isAuthenticated) {
      websocketService.connect();
    }
    return () => {
      websocketService.disconnect();
    };
  }, [isAuthenticated]);

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
