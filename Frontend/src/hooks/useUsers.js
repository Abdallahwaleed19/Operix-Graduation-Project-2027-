import { useData } from '../context/DataContext';

export function useUsers(filters = {}) {
  const { users, toggleUserAccess, inviteUser, updateUserRole, isLoading } = useData();

  let filtered = users || [];
  if (filters.role && filters.role !== 'All') {
    filtered = filtered.filter(u => u.role.toLowerCase() === filters.role.toLowerCase());
  }

  return {
    users: filtered,
    totalCount: users ? users.length : 0,
    activeCount: users ? users.filter(u => u.access === 'Active').length : 0,
    toggleUserAccess,
    inviteUser,
    updateUserRole,
    isLoading
  };
}

export default useUsers;
