import apiClient, { API_CONFIG } from './apiClient';
import { initialReports } from '../data/mockData';

/**
 * Compliance & Safety Reports Service
 * Connects to FastAPI endpoint `/reports`
 */
export const reportService = {
  async getReports() {
    if (API_CONFIG.useMock) {
      return [...initialReports];
    }
    return apiClient.get('/reports');
  },

  async generateReport(reportPayload) {
    if (API_CONFIG.useMock) {
      const created = {
        id: `rep-${Date.now()}`,
        format: 'PDF',
        size: '1.8 MB',
        ...reportPayload
      };
      initialReports.unshift(created);
      return { success: true, ...created };
    }
    return apiClient.post('/reports/generate', reportPayload);
  }
};

export default reportService;
