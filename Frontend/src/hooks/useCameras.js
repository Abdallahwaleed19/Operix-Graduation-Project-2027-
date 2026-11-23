import { useData } from '../context/DataContext';

export function useCameras(filters = {}) {
  const { cameras, toggleCamera, updateCamera, addCamera, isLoading } = useData();

  let filtered = cameras || [];
  if (filters.zone && filters.zone !== 'All') {
    filtered = filtered.filter(c => c.zone === filters.zone);
  }
  if (filters.status && filters.status !== 'All') {
    filtered = filtered.filter(c => c.status.toLowerCase() === filters.status.toLowerCase());
  }

  return {
    cameras: filtered,
    totalCount: cameras ? cameras.length : 0,
    onlineCount: cameras ? cameras.filter(c => c.status === 'Online').length : 0,
    toggleCamera,
    updateCamera,
    addCamera,
    isLoading
  };
}

export default useCameras;
