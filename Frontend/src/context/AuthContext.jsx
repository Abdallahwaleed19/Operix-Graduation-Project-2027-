import React, { createContext, useContext, useState, useEffect } from 'react';
import { roleMatrixData } from '../data/mockData';
import { authService } from '../services/authService';

const AuthContext = createContext();

export const ROLES = {
  ADMIN: 'Administrator',
  MANAGER: 'Factory Manager',
  SUPERVISOR: 'Safety Supervisor',
  VIEWER: 'Viewer'
};

export function AuthProvider({ children }) {
  // Initialize from persistent session if one exists
  const initialSession = authService.getCurrentSession();

  const [currentUser, setCurrentUser] = useState(initialSession ? initialSession.user : null);
  const [isAuthenticated, setIsAuthenticated] = useState(!!initialSession);
  const [authLoading, setAuthLoading] = useState(false);

  // Restore or validate session on mount
  useEffect(() => {
    const session = authService.getCurrentSession();
    if (session && session.user) {
      setCurrentUser(session.user);
      setIsAuthenticated(true);
    } else {
      setCurrentUser(null);
      setIsAuthenticated(false);
    }
  }, []);

  const switchRole = (newRole) => {
    if (!currentUser) return;
    const updated = {
      ...currentUser,
      role: newRole
    };
    setCurrentUser(updated);

    // Update stored session with switched role
    const session = authService.getCurrentSession();
    if (session) {
      session.user.role = newRole;
      const key = 'operix_auth_session';
      if (localStorage.getItem(key)) {
        localStorage.setItem(key, JSON.stringify(session));
      } else if (sessionStorage.getItem(key)) {
        sessionStorage.setItem(key, JSON.stringify(session));
      }
    }
  };

  const hasPermission = (permissionCode) => {
    if (!currentUser) return false;
    const perm = roleMatrixData.find(p => p.code === permissionCode);
    if (!perm) return false;

    switch (currentUser.role) {
      case ROLES.ADMIN:
        return !!perm.admin;
      case ROLES.MANAGER:
        return !!perm.manager;
      case ROLES.SUPERVISOR:
        return !!perm.supervisor;
      case ROLES.VIEWER:
        return !!perm.viewer;
      default:
        return false;
    }
  };

  const login = async (email, password, keepSignedIn = true) => {
    setAuthLoading(true);
    try {
      const session = await authService.login({ email, password, keepSignedIn });
      setCurrentUser(session.user);
      setIsAuthenticated(true);
      return session;
    } finally {
      setAuthLoading(false);
    }
  };

  const logout = () => {
    authService.logout();
    setCurrentUser(null);
    setIsAuthenticated(false);
  };

  const updateUserProfile = (updatedFields) => {
    if (!currentUser) return;
    const updated = {
      ...currentUser,
      ...updatedFields
    };
    setCurrentUser(updated);

    const session = authService.getCurrentSession();
    if (session) {
      session.user = { ...session.user, ...updatedFields };
      const key = 'operix_auth_session';
      if (localStorage.getItem(key)) {
        localStorage.setItem(key, JSON.stringify(session));
      } else if (sessionStorage.getItem(key)) {
        sessionStorage.setItem(key, JSON.stringify(session));
      }
    }
  };

  return (
    <AuthContext.Provider
      value={{
        currentUser,
        role: currentUser?.role || 'Guest',
        switchRole,
        hasPermission,
        isAuthenticated,
        authLoading,
        login,
        logout,
        updateUserProfile,
        isViewer: currentUser?.role === ROLES.VIEWER,
        isSupervisor: currentUser?.role === ROLES.SUPERVISOR,
        isAdmin: currentUser?.role === ROLES.ADMIN,
        isManager: currentUser?.role === ROLES.MANAGER
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
