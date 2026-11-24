import apiClient, { isMockEnabled } from './apiClient.js';
import { initialIncidents, initialShiftIncidents } from '../data/mockData.js';

/**
 * Incidents & Vision Evidence Service
 * Connects to FastAPI `/api/v1/incidents` and `/api/v1/evidence`
 */
export const incidentService = {
  /**
   * Fetch incidents list with optional status/severity filters
   */
  async getIncidents(filters = {}) {
    if (isMockEnabled('incidents')) {
      let result = [...initialIncidents];
      if (filters.status && filters.status !== 'All') {
        result = result.filter(i => i.status.toLowerCase() === filters.status.toLowerCase());
      }
      if (filters.severity && filters.severity !== 'All') {
        result = result.filter(i => i.severity.toLowerCase() === filters.severity.toLowerCase());
      }
      return result;
    }

    const params = new URLSearchParams();
    if (filters.status && filters.status !== 'All') params.set('status', filters.status);
    if (filters.severity && filters.severity !== 'All') params.set('severity', filters.severity);
    return apiClient.get(`/api/v1/incidents${params.toString() ? `?${params}` : ''}`);
  },

  /**
   * Fetch single incident details
   */
  async getIncidentById(id) {
    if (isMockEnabled('incidents')) {
      return initialIncidents.find(i => i.id === id) || null;
    }
    return apiClient.get(`/api/v1/incidents/${id}`);
  },

  /**
   * Mark incident as resolved
   */
  async resolveIncident(id) {
    if (isMockEnabled('incidents')) {
      const inc = initialIncidents.find(i => i.id === id);
      if (inc) {
        inc.status = 'Resolved';
        inc.auditTrail.push({
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          text: 'Resolved by user',
          detail: 'Marked as resolved in dashboard'
        });
      }
      return { success: true, id };
    }
    return apiClient.post(`/api/v1/incidents/${id}/resolve`);
  },

  /**
   * Fetch shift incident distribution
   */
  async getShiftIncidents() {
    if (isMockEnabled('incidents')) {
      return initialShiftIncidents;
    }
    return apiClient.get('/api/v1/analytics/shift-incidents');
  },

  // -------------------------------------------------------------
  // Evidence API Endpoints (/api/v1/evidence)
  // -------------------------------------------------------------

  /**
   * POST /api/v1/evidence/upload
   * Upload incident snapshot image or video clip
   */
  async uploadEvidence({ eventId, kind = 'snapshot', fileBase64, contentType = 'image/jpeg', durationS = null }) {
    if (isMockEnabled('evidence')) {
      const evidenceRecord = {
        evidence_id: `ev-${Date.now()}`,
        event_id: eventId || '11111111-1111-1111-1111-111111111111',
        kind,
        content_type: contentType,
        sha256: 'a1b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890',
        size_bytes: fileBase64 ? Math.round(fileBase64.length * 0.75) : 102400,
        uploaded_at: new Date().toISOString()
      };
      return evidenceRecord;
    }

    return apiClient.post('/api/v1/evidence/upload', {
      event_id: eventId,
      kind,
      file_base64: fileBase64,
      content_type: contentType,
      duration_s: durationS
    });
  },

  /**
   * GET /api/v1/evidence
   * List evidence records for an event or factory
   */
  async listEvidence(params = {}) {
    if (isMockEnabled('evidence')) {
      return [
        {
          evidence_id: 'ev-001',
          event_id: 'INC-2041',
          kind: 'snapshot',
          content_type: 'image/jpeg',
          filename: 'press_line_helmet_violation.jpg',
          sha256: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
          size_bytes: 245120,
          captured_at: new Date().toISOString()
        }
      ];
    }

    const q = new URLSearchParams();
    if (params.eventId) q.set('event_id', params.eventId);
    if (params.incidentId) q.set('incident_id', params.incidentId);
    if (params.kind) q.set('kind', params.kind);
    if (params.page) q.set('page', String(params.page));
    if (params.pageSize) q.set('page_size', String(params.pageSize));

    return apiClient.get(`/api/v1/evidence${q.toString() ? `?${q}` : ''}`);
  },

  /**
   * GET /api/v1/evidence/{evidence_id}
   */
  async getEvidenceMetadata(evidenceId) {
    if (isMockEnabled('evidence')) {
      return {
        evidence_id: evidenceId,
        sha256: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        status: 'verified'
      };
    }
    return apiClient.get(`/api/v1/evidence/${evidenceId}`);
  },

  /**
   * GET /api/v1/evidence/{evidence_id}/download
   * Downloads evidence snapshot or video clip with Bearer token
   */
  async downloadEvidence(evidenceId, filename = 'evidence_file.jpg') {
    if (isMockEnabled('evidence')) {
      alert(`[Mock Mode] Evidence file "${filename}" downloaded.`);
      return true;
    }
    return apiClient.downloadBlob(`/api/v1/evidence/${evidenceId}/download`, filename);
  },

  /**
   * POST /api/v1/evidence/{evidence_id}/verify-integrity
   * Recomputes SHA-256 on disk and compares with database checksum
   */
  async verifyEvidenceIntegrity(evidenceId) {
    if (isMockEnabled('evidence')) {
      return {
        evidence_id: evidenceId,
        integrity_status: 'valid',
        sha256: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        verified_at: new Date().toISOString(),
        message: 'SHA-256 checksum matches stored evidence record exactly.'
      };
    }
    return apiClient.post(`/api/v1/evidence/${evidenceId}/verify-integrity`);
  }
};

export default incidentService;
