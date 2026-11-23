import apiClient, { API_CONFIG } from './apiClient';
import { initialRules } from '../data/mockData';

/**
 * No-Code Safety Rules & Vision Geofences Service
 * Connects to FastAPI endpoint `/rules`
 */
export const ruleService = {
  async getRules(filters = {}) {
    if (API_CONFIG.useMock) {
      let result = [...initialRules];
      if (filters.type && filters.type !== 'All') {
        result = result.filter(r => r.type.toLowerCase() === filters.type.toLowerCase());
      }
      return result;
    }
    const params = new URLSearchParams(filters).toString();
    return apiClient.get(`/rules${params ? `?${params}` : ''}`);
  },

  async getRuleById(id) {
    if (API_CONFIG.useMock) {
      return initialRules.find(r => r.id === id) || null;
    }
    return apiClient.get(`/rules/${id}`);
  },

  async toggleRule(id) {
    if (API_CONFIG.useMock) {
      const rule = initialRules.find(r => r.id === id);
      if (rule) {
        rule.enabled = !rule.enabled;
      }
      return { success: true, id };
    }
    return apiClient.post(`/rules/${id}/toggle`);
  },

  async updateRule(id, updatedFields) {
    if (API_CONFIG.useMock) {
      const rule = initialRules.find(r => r.id === id);
      if (rule) {
        Object.assign(rule, updatedFields);
      }
      return { success: true, ...rule };
    }
    return apiClient.patch(`/rules/${id}`, updatedFields);
  },

  async createRule(newRule) {
    if (API_CONFIG.useMock) {
      const created = { id: `rule-${Date.now()}`, ...newRule };
      initialRules.push(created);
      return { success: true, ...created };
    }
    return apiClient.post('/rules', newRule);
  },

  async deleteRule(id) {
    if (API_CONFIG.useMock) {
      const index = initialRules.findIndex(r => r.id === id);
      if (index !== -1) initialRules.splice(index, 1);
      return { success: true, id };
    }
    return apiClient.delete(`/rules/${id}`);
  }
};

export default ruleService;
