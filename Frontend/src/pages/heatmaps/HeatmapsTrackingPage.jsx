import React from 'react';
import { Navigate } from 'react-router-dom';

/**
 * HeatmapsTrackingPage (DEPRECATED)
 * Per project specification rule 3.A: Heatmap feature has been permanently
 * removed from Operix. Navigations are redirected to Workforce Analytics.
 */
export default function HeatmapsTrackingPage() {
  return <Navigate to="/analytics" replace />;
}
