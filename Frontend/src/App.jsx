import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import AppLayout from './components/layout/AppLayout';
import ProtectedRoute from './components/common/ProtectedRoute';

// Page components
import FactoryOverviewPage from './pages/dashboard/FactoryOverviewPage';
import LiveMonitoringPage from './pages/monitoring/LiveMonitoringPage';
import IncidentsPage from './pages/incidents/IncidentsPage';
import WorkforceAnalyticsPage from './pages/analytics/WorkforceAnalyticsPage';
import ThermalMonitoringPage from './pages/thermal/ThermalMonitoringPage';
import RuleBuilderPage from './pages/rules/RuleBuilderPage';
import AIAssistantPage from './pages/assistant/AIAssistantPage';
import ReportsPage from './pages/reports/ReportsPage';
import SettingsHubPage from './pages/settings/SettingsHubPage';
import CamerasPage from './pages/settings/CamerasPage';
import EditCameraPage from './pages/settings/EditCameraPage';
import SensorsPage from './pages/settings/SensorsPage';
import EditSensorPage from './pages/settings/EditSensorPage';
import UsersRolesPage from './pages/settings/UsersRolesPage';
import FactorySettingsPage from './pages/settings/FactorySettingsPage';
import RoleMatrixPage from './pages/settings/RoleMatrixPage';
import EditRulePage from './pages/rules/EditRulePage';
import ZoneEditorPage from './pages/rules/ZoneEditorPage';
import ProfilePage from './pages/profile/ProfilePage';
import AccessDeniedPage from './pages/error/AccessDeniedPage';

// Auth pages
import LoginPage from './pages/auth/LoginPage';
import RegisterPage from './pages/auth/RegisterPage';
import ForgotPasswordPage from './pages/auth/ForgotPasswordPage';
import VerifyEmailPage from './pages/auth/VerifyEmailPage';
import ResetPasswordPage from './pages/auth/ResetPasswordPage';
import AcceptInvitePage from './pages/auth/AcceptInvitePage';

export default function App() {
  return (
    <Routes>
      {/* Auth Public Routes */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/verify-email" element={<VerifyEmailPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route path="/accept-invite" element={<AcceptInvitePage />} />

      {/* Main App Layout Routes (Protected) */}
      <Route element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
        {/* 01: Factory Overview */}
        <Route path="/" element={<FactoryOverviewPage />} />
        <Route path="/dashboard" element={<FactoryOverviewPage />} />

        {/* 02 & 23: Live Monitoring */}
        <Route path="/monitoring" element={<LiveMonitoringPage />} />
        <Route path="/viewer/monitoring" element={<LiveMonitoringPage />} />

        {/* 03 & 24: Incidents */}
        <Route path="/incidents" element={<IncidentsPage />} />
        <Route path="/supervisor/incidents" element={<IncidentsPage />} />

        {/* 04: Workforce Analytics */}
        <Route path="/analytics" element={<WorkforceAnalyticsPage />} />

        {/* 05: Heatmaps removed from project specification - redirect to analytics */}
        <Route path="/heatmaps" element={<Navigate to="/analytics" replace />} />

        {/* 06: Thermal Monitoring */}
        <Route path="/thermal" element={<ThermalMonitoringPage />} />

        {/* 07: No-Code Rule Builder */}
        <Route path="/rules" element={<RuleBuilderPage />} />

        {/* 19: Edit Rule */}
        <Route path="/rules/edit/:id" element={<EditRulePage />} />

        {/* 20: Zone Editor */}
        <Route path="/rules/zones" element={<ZoneEditorPage />} />

        {/* 08: AI Assistant */}
        <Route path="/assistant" element={<AIAssistantPage />} />

        {/* 09: Reports */}
        <Route path="/reports" element={<ReportsPage />} />

        {/* 10: Settings Hub */}
        <Route path="/settings" element={<SettingsHubPage />} />

        {/* 16: Cameras */}
        <Route path="/settings/cameras" element={<CamerasPage />} />

        {/* 17: Edit Camera */}
        <Route path="/settings/cameras/edit/:id" element={<EditCameraPage />} />

        {/* 26: Sensors */}
        <Route path="/settings/sensors" element={<SensorsPage />} />

        {/* 27: Edit Sensor */}
        <Route path="/settings/sensors/edit/:id" element={<EditSensorPage />} />

        {/* 18: Users & Roles */}
        <Route path="/settings/users" element={<UsersRolesPage />} />

        {/* 21: Factory Settings */}
        <Route path="/settings/factory" element={<FactorySettingsPage />} />

        {/* 22: Role Access Matrix */}
        <Route path="/settings/matrix" element={<RoleMatrixPage />} />

        {/* 13: Profile */}
        <Route path="/profile" element={<ProfilePage />} />

        {/* 25: 403 Access Denied */}
        <Route path="/access-denied" element={<AccessDeniedPage />} />
        <Route path="/403" element={<AccessDeniedPage />} />
      </Route>

      {/* Catch-all redirect */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
