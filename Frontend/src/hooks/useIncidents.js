import { useData } from '../context/DataContext';

export function useIncidents(filters = {}) {
  const { incidents, resolveIncident, isLoading } = useData();

  let filtered = incidents || [];
  if (filters.status && filters.status !== 'All') {
    filtered = filtered.filter(i => i.status.toLowerCase() === filters.status.toLowerCase());
  }
  if (filters.severity && filters.severity !== 'All') {
    filtered = filtered.filter(i => i.severity.toLowerCase() === filters.severity.toLowerCase());
  }

  return {
    incidents: filtered,
    totalCount: incidents ? incidents.length : 0,
    resolveIncident,
    isLoading
  };
}

export default useIncidents;
