import apiClient, { isMockEnabled } from './apiClient';
import { initialFactory, initialNotificationTargets } from '../data/mockData';

/**
 * Factory Plant Configuration & Notification Targets Service
 * Connects to FastAPI endpoint `/api/v1/factories/current`
 */
export const factoryService = {
  async getFactorySettings() {
    if (isMockEnabled('factory')) {
      return { ...initialFactory };
    }
    // Real backend endpoint: GET /api/v1/factories/current
    const res = await apiClient.get('/api/v1/factories/current');
    // Normalize to shape DataContext expects: { name, shift, timezone, ... }
    if (res && res.name) {
      return {
        name: res.name,
        shift: res.shift || 'Day Shift',
        timezone: res.timezone || 'Africa/Cairo',
        id: res.id,
        status: res.status,
      };
    }
    return res;
  },

  async updateFactorySettings(settings) {
    if (isMockEnabled('factory')) {
      Object.assign(initialFactory, settings);
      return { success: true, ...initialFactory };
    }
    // No PATCH endpoint exists yet — silently skip to avoid errors
    return { success: false, message: 'Factory update endpoint not yet available.' };
  },

  async getNotificationTargets() {
    if (isMockEnabled('factory')) {
      return [...initialNotificationTargets];
    }
    // No notification target endpoint exists yet — return empty array
    return [];
  },

  async toggleNotificationTarget(id) {
    if (isMockEnabled('factory')) {
      const target = initialNotificationTargets.find(t => t.id === id);
      if (target) {
        target.enabled = !target.enabled;
      }
      return { success: true, id };
    }
    return { success: false };
  },

  async addNotificationTarget(targetPayload) {
    if (isMockEnabled('factory')) {
      const newTarget = {
        id: `notif-${Date.now()}`,
        ...targetPayload
      };
      initialNotificationTargets.push(newTarget);
      return { success: true, ...newTarget };
    }
    return { success: false };
  },

  async removeNotificationTarget(id) {
    if (isMockEnabled('factory')) {
      const idx = initialNotificationTargets.findIndex(t => t.id === id);
      if (idx !== -1) initialNotificationTargets.splice(idx, 1);
      return { success: true, id };
    }
    return { success: false };
  }
};

export default factoryService;
