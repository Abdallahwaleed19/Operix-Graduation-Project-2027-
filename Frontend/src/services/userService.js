import apiClient, { isMockEnabled } from './apiClient';
import { initialUsers, roleMatrixData } from '../data/mockData';

const ROLE_CODE_TO_LABEL = {
  factory_admin: 'Administrator',
  platform_admin: 'Administrator',
  factory_manager: 'Factory Manager',
  safety_supervisor: 'Safety Supervisor',
  viewer: 'Viewer',
  operator: 'Operator',
};

const ROLE_LABEL_TO_CODE = {
  Administrator: 'factory_admin',
  'System Administrator': 'factory_admin',
  'Factory Manager': 'factory_manager',
  'Safety Supervisor': 'safety_supervisor',
  Viewer: 'viewer',
  Operator: 'operator',
};

const STATUS_TO_LABEL = {
  active: 'Active',
  invited: 'Invited',
  disabled: 'Disabled',
};

function mapBackendUser(u) {
  if (!u) return u;
  const rawStatus = String(u.status || '').toLowerCase();
  const roleCode = u.role_code || 'safety_supervisor';
  return {
    id: u.user_id || u.id,
    name: u.full_name || u.name || u.email,
    email: u.email,
    roleCode,
    role: ROLE_CODE_TO_LABEL[roleCode] || u.role_name || roleCode,
    status: STATUS_TO_LABEL[rawStatus] || u.status || 'Invited',
    access: u.membership_active ? 'Active' : 'Inactive',
    rawStatus,
    membershipActive: Boolean(u.membership_active),
  };
}

/**
 * User Accounts & Role Permissions Service
 * Connects to FastAPI endpoint `/api/v1/users` and `/api/v1/roles`
 */
export const userService = {
  async getUsers(filters = {}) {
    if (isMockEnabled('users')) {
      let result = [...initialUsers];
      if (filters.role && filters.role !== 'All') {
        result = result.filter(u => u.role.toLowerCase() === filters.role.toLowerCase());
      }
      return result;
    }
    const params = new URLSearchParams(filters).toString();
    const res = await apiClient.get(`/api/v1/users${params ? `?${params}` : ''}`);
    const items = Array.isArray(res) ? res : (res?.items || []);
    return items.map(mapBackendUser);
  },

  async getUserById(id) {
    if (isMockEnabled('users')) {
      return initialUsers.find(u => u.id === id) || null;
    }
    const res = await apiClient.get(`/api/v1/users/${id}`);
    return mapBackendUser(res);
  },

  async toggleUserAccess(id, currentUser = null) {
    if (isMockEnabled('users')) {
      const user = initialUsers.find(u => u.id === id);
      if (user) {
        const isActive = user.access === 'Active';
        user.access = isActive ? 'Inactive' : 'Active';
        user.status = isActive ? 'Inactive' : 'Active';
      }
      return { success: true, id };
    }
    const currentlyActive = currentUser
      ? (currentUser.access === 'Active' && currentUser.status === 'Active')
      : false;
    const nextActive = !currentlyActive;
    const res = await apiClient.patch(`/api/v1/users/${id}`, {
      membership_active: nextActive,
      status: nextActive ? 'active' : 'disabled',
    });
    return mapBackendUser(res);
  },

  async inviteUser(userPayload) {
    if (isMockEnabled('users')) {
      const newUser = {
        id: `usr-${Date.now()}`,
        status: 'Invited',
        access: 'Inactive',
        ...userPayload
      };
      initialUsers.push(newUser);
      return { success: true, ...newUser };
    }
    const roleCode = ROLE_LABEL_TO_CODE[userPayload.role] || userPayload.role_code || 'safety_supervisor';
    const res = await apiClient.post('/api/v1/users/invite', {
      email: userPayload.email,
      full_name: userPayload.name || userPayload.full_name || userPayload.email.split('@')[0],
      role_code: roleCode,
    });
    return mapBackendUser(res);
  },

  async updateUserRole(id, newRole) {
    if (isMockEnabled('users')) {
      const user = initialUsers.find(u => u.id === id);
      if (user) {
        user.role = newRole;
      }
      return { success: true, id, role: newRole };
    }
    const roleCode = ROLE_LABEL_TO_CODE[newRole] || newRole;
    const res = await apiClient.patch(`/api/v1/users/${id}`, { role_code: roleCode });
    return mapBackendUser(res);
  },

  async deleteUser(id) {
    if (isMockEnabled('users')) {
      const idx = initialUsers.findIndex(u => u.id === id);
      if (idx !== -1) initialUsers.splice(idx, 1);
      return { deleted: true, user_id: id };
    }
    return apiClient.delete(`/api/v1/users/${id}`);
  },

  async getRoleMatrix() {
    if (isMockEnabled('users')) {
      return roleMatrixData;
    }
    return apiClient.get('/api/v1/roles/matrix');
  }
};

export default userService;
