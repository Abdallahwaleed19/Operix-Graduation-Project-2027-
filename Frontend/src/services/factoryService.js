import apiClient, { isMockEnabled } from './apiClient';
import { initialFactory, initialNotificationTargets } from '../data/mockData';

/**
 * Factory Plant Configuration & Notification Targets Service
 * Connects to FastAPI endpoint `/factory`
 */
export const factoryService = {
  async getFactorySettings() {
    if (isMockEnabled('factory')) {
      return { ...initialFactory };
    }
    return apiClient.get('/factory/settings');
  },

  async updateFactorySettings(settings) {
    if (isMockEnabled('factory')) {
      Object.assign(initialFactory, settings);
      return { success: true, ...initialFactory };
    }
    return apiClient.patch('/factory/settings', settings);
  },

  async getNotificationTargets() {
    if (isMockEnabled('factory')) {
      return [...initialNotificationTargets];
    }
    return apiClient.get('/factory/notifications');
  },

  async toggleNotificationTarget(id) {
    if (isMockEnabled('factory')) {
      const target = initialNotificationTargets.find(t => t.id === id);
      if (target) {
        target.enabled = !target.enabled;
      }
      return { success: true, id };
    }
    return apiClient.post(`/factory/notifications/${id}/toggle`);
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
    return apiClient.post('/factory/notifications', targetPayload);
  },

  async removeNotificationTarget(id) {
    if (isMockEnabled('factory')) {
      const idx = initialNotificationTargets.findIndex(t => t.id === id);
      if (idx !== -1) initialNotificationTargets.splice(idx, 1);
      return { success: true, id };
    }
    return apiClient.delete(`/factory/notifications/${id}`);
  }
};

export default factoryService;
