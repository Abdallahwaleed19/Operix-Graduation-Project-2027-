import apiClient, { API_CONFIG } from './apiClient';
import { initialUsers, roleMatrixData } from '../data/mockData';

/**
 * User Accounts & Role Permissions Service
 * Connects to FastAPI endpoint `/users` and `/roles`
 */
export const userService = {
  async getUsers(filters = {}) {
    if (API_CONFIG.useMock) {
      let result = [...initialUsers];
      if (filters.role && filters.role !== 'All') {
        result = result.filter(u => u.role.toLowerCase() === filters.role.toLowerCase());
      }
      return result;
    }
    const params = new URLSearchParams(filters).toString();
    return apiClient.get(`/users${params ? `?${params}` : ''}`);
  },

  async getUserById(id) {
    if (API_CONFIG.useMock) {
      return initialUsers.find(u => u.id === id) || null;
    }
    return apiClient.get(`/users/${id}`);
  },

  async toggleUserAccess(id) {
    if (API_CONFIG.useMock) {
      const user = initialUsers.find(u => u.id === id);
      if (user) {
        const isActive = user.access === 'Active';
        user.access = isActive ? 'Inactive' : 'Active';
        user.status = isActive ? 'Inactive' : 'Active';
      }
      return { success: true, id };
    }
    return apiClient.post(`/users/${id}/toggle-access`);
  },

  async inviteUser(userPayload) {
    if (API_CONFIG.useMock) {
      const newUser = {
        id: `usr-${Date.now()}`,
        status: 'Invited',
        access: 'Inactive',
        ...userPayload
      };
      initialUsers.push(newUser);
      return { success: true, ...newUser };
    }
    return apiClient.post('/users/invite', userPayload);
  },

  async updateUserRole(id, newRole) {
    if (API_CONFIG.useMock) {
      const user = initialUsers.find(u => u.id === id);
      if (user) {
        user.role = newRole;
      }
      return { success: true, id, role: newRole };
    }
    return apiClient.patch(`/users/${id}/role`, { role: newRole });
  },

  async getRoleMatrix() {
    if (API_CONFIG.useMock) {
      return roleMatrixData;
    }
    return apiClient.get('/roles/matrix');
  }
};

export default userService;
