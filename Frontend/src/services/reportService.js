import apiClient, { isMockEnabled } from './apiClient.js';
import { initialReports } from '../data/mockData.js';

/**
 * Compliance & Safety Reports Service
 * Connects directly to FastAPI `/api/v1/reports`
 */
export const reportService = {
  /**
   * GET /api/v1/reports
   * List generated safety reports
   */
  async getReports() {
    if (isMockEnabled('reports')) {
      return [...initialReports];
    }
    return apiClient.get('/api/v1/reports');
  },

  /**
   * POST /api/v1/reports/generate
   * Trigger report generation (PDF or Excel)
   */
  async generateReport(reportPayload = {}) {
    const {
      reportType = 'workforce',
      format = 'pdf',
      dateFrom = null,
      dateTo = null,
      title = 'Workforce Safety Compliance Report'
    } = reportPayload;

    if (isMockEnabled('reports')) {
      const created = {
        id: `rep-${Date.now()}`,
        report_id: `rep-${Date.now()}`,
        title,
        type: reportType === 'workforce' ? 'Workforce Analytics' : reportType,
        report_type: reportType,
        date: new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }),
        format: format.toUpperCase(),
        size: format.toLowerCase() === 'pdf' ? '1.8 MB' : '450 KB',
        status: 'Generated',
        download_url: `/api/v1/reports/rep-${Date.now()}/download`
      };
      initialReports.unshift(created);
      return created;
    }

    return apiClient.post('/api/v1/reports/generate', {
      report_type: reportType,
      format: format.toLowerCase(),
      date_from: dateFrom,
      date_to: dateTo
    });
  },

  /**
   * GET /api/v1/reports/{report_id}
   */
  async getReportMetadata(reportId) {
    if (isMockEnabled('reports')) {
      return initialReports.find(r => r.id === reportId || r.report_id === reportId) || null;
    }
    return apiClient.get(`/api/v1/reports/${reportId}`);
  },

  /**
   * GET /api/v1/reports/{report_id}/download
   * Downloads protected PDF or Excel report artifact with Bearer token
   */
  async downloadReport(reportId, filename = null) {
    const ext = filename?.endsWith('.xlsx') ? 'xlsx' : 'pdf';
    const targetFilename = filename || `Operix_Safety_Report_${reportId}.${ext}`;

    if (isMockEnabled('reports')) {
      alert(`[Mock Mode] Report "${targetFilename}" downloaded successfully.`);
      return true;
    }

    return apiClient.downloadBlob(`/api/v1/reports/${reportId}/download`, targetFilename);
  }
};

export default reportService;
