import { useState, useEffect } from 'react';
import { analyticsService } from '../services';

export function useAnalytics(range = 'This week') {
  const [metrics, setMetrics] = useState(null);
  const [departments, setDepartments] = useState([]);
  const [idleZones, setIdleZones] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    async function loadData() {
      try {
        const [met, dept, idle] = await Promise.all([
          analyticsService.getWorkforceMetrics(range),
          analyticsService.getWorkforceDepartments(),
          analyticsService.getIdleTimeZones()
        ]);
        if (isMounted) {
          setMetrics(met);
          setDepartments(dept);
          setIdleZones(idle);
          setLoading(false);
        }
      } catch (err) {
        console.error('Failed to load analytics:', err);
        if (isMounted) setLoading(false);
      }
    }
    loadData();
    return () => { isMounted = false; };
  }, [range]);

  return { metrics, departments, idleZones, loading };
}

export default useAnalytics;
