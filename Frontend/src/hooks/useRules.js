import { useData } from '../context/DataContext';

export function useRules(filters = {}) {
  const { rules, toggleRule, updateRule, deleteRule, isLoading } = useData();

  let filtered = rules || [];
  if (filters.type && filters.type !== 'All') {
    filtered = filtered.filter(r => r.type.toLowerCase() === filters.type.toLowerCase());
  }

  return {
    rules: filtered,
    totalCount: rules ? rules.length : 0,
    activeCount: rules ? rules.filter(r => r.enabled).length : 0,
    toggleRule,
    updateRule,
    deleteRule,
    isLoading
  };
}

export default useRules;
