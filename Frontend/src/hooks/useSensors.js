import { useData } from '../context/DataContext';

export function useSensors(filters = {}) {
  const { sensors, toggleSensor, updateSensor, isLoading } = useData();

  let filtered = sensors || [];
  if (filters.type && filters.type !== 'All') {
    filtered = filtered.filter(s => s.type.toLowerCase().includes(filters.type.toLowerCase()));
  }

  return {
    sensors: filtered,
    totalCount: sensors ? sensors.length : 0,
    onlineCount: sensors ? sensors.filter(s => s.status === 'Online').length : 0,
    toggleSensor,
    updateSensor,
    isLoading
  };
}

export default useSensors;
