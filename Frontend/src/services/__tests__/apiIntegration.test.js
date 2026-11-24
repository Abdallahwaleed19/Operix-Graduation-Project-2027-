/**
 * Verification Test Suite for FastAPI Backend Integration
 * Validates:
 * 1. buildUrl handles base URLs and /api/v1 endpoints cleanly
 * 2. Envelope unwrapping { status: "success", data, meta }
 * 3. Error envelope handling { status: "error", error_code, message }
 * 4. analyticsService endpoints (/overview, /summary, /attendance, /incidents, /productivity, /camera-coverage)
 * 5. assistantService endpoints (/ask, /sources, /conversations/{id}, /health, /actions/execute)
 * 6. incidentService endpoints (/upload, /evidence, /evidence/{id}/download, /verify-integrity)
 * 7. reportService endpoints (/generate, /reports, /reports/{id}/download)
 * 8. authService ws-ticket endpoint (/auth/ws-ticket)
 */

import { buildUrl } from '../apiClient.js';
import { analyticsService } from '../analyticsService.js';
import { assistantService } from '../assistantService.js';
import { incidentService } from '../incidentService.js';
import { reportService } from '../reportService.js';
import { authService } from '../authService.js';

// Setup mock browser environment
const store = new Map();
global.localStorage = {
  getItem: (key) => store.get(key) || null,
  setItem: (key, val) => store.set(key, String(val)),
  removeItem: (key) => store.delete(key),
  clear: () => store.clear()
};
global.sessionStorage = { ...global.localStorage };

async function runTests() {
  console.log('--- STARTING FASTAPI BACKEND INTEGRATION TEST SUITE ---');
  let passed = 0;
  let failed = 0;

  function assert(condition, testName) {
    if (condition) {
      console.log(`[PASS] ${testName}`);
      passed++;
    } else {
      console.error(`[FAIL] ${testName}`);
      failed++;
    }
  }

  // Suite 1: URL Normalization
  console.log('\n[Suite 1: URL Normalization]');
  assert(buildUrl('/api/v1/analytics/summary').includes('/api/v1/analytics/summary'), 'Resolves /api/v1 prefix correctly');
  assert(!buildUrl('/api/v1/analytics/summary').includes('/api/v1/api/v1'), 'Prevents duplicated /api/v1/api/v1 prefix');
  assert(buildUrl('https://custom.operix.io/api/v1/test') === 'https://custom.operix.io/api/v1/test', 'Preserves absolute URLs');

  // Suite 2: Workforce Analytics Endpoints
  console.log('\n[Suite 2: Workforce Analytics Service]');
  const overview = await analyticsService.getOverview();
  assert(overview && overview.total_workers > 0, 'getOverview returns total_workers');
  assert(overview.role_breakdown && typeof overview.role_breakdown === 'object', 'getOverview returns role_breakdown');

  const summary = await analyticsService.getSummary({ periodHours: 720 });
  assert(summary && summary.period_hours === 720, 'getSummary respects period_hours');
  assert(summary.camera_coverage_pct > 0, 'getSummary returns camera_coverage_pct');

  const coverage = await analyticsService.getCameraCoverage(720);
  assert(coverage && coverage.uptime_percentage > 90, 'getCameraCoverage returns uptime_percentage');

  // Suite 3: RAG Assistant & Remediation Actions
  console.log('\n[Suite 3: RAG Assistant & Actions Service]');
  const askRes = await assistantService.ask({ question: 'What are the PPE helmet rules in Zone B?' });
  assert(askRes && askRes.answer && askRes.answer.length > 10, 'ask returns detailed safety answer');
  assert(askRes.has_sufficient_evidence === true, 'ask returns has_sufficient_evidence flag');
  assert(Array.isArray(askRes.citations) && askRes.citations.length > 0, 'ask returns verified source citations');

  const actionRes = await assistantService.executeAction({
    actionId: 'ACT-001',
    actionType: 'acknowledge_incident',
    parameters: { incident_id: '22222222-2222-2222-2222-222222222222' }
  });
  assert(actionRes && actionRes.status === 'executed', 'executeAction executes remediation action');
  assert(actionRes.audit_reference && actionRes.audit_reference.startsWith('AUDIT-'), 'executeAction produces audit reference');

  const clearRes = await assistantService.clearConversation('conv-123');
  assert(clearRes && clearRes.success, 'clearConversation succeeds');

  const healthRes = await assistantService.checkHealth();
  assert(healthRes && healthRes.status === 'healthy', 'assistant checkHealth returns healthy');

  // Suite 4: Incident Evidence Service
  console.log('\n[Suite 4: Incident Evidence Service]');
  const uploadRes = await incidentService.uploadEvidence({
    eventId: 'INC-2041',
    kind: 'snapshot',
    fileBase64: 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=',
    contentType: 'image/png'
  });
  assert(uploadRes && uploadRes.evidence_id, 'uploadEvidence generates evidence record');
  assert(uploadRes.sha256 && uploadRes.sha256.length === 64, 'uploadEvidence includes SHA-256 hash');

  const integrityRes = await incidentService.verifyEvidenceIntegrity('INC-2041');
  assert(integrityRes && integrityRes.integrity_status === 'valid', 'verifyEvidenceIntegrity verifies cryptographic checksum');

  const evidenceList = await incidentService.listEvidence();
  assert(Array.isArray(evidenceList) && evidenceList.length > 0, 'listEvidence returns evidence records');

  // Suite 5: Reports Generation Service
  console.log('\n[Suite 5: Reports Generation Service]');
  const reportRes = await reportService.generateReport({
    reportType: 'workforce',
    format: 'pdf',
    dateFrom: '2026-11-01',
    dateTo: '2026-11-24'
  });
  assert(reportRes && reportRes.format === 'PDF', 'generateReport creates PDF report metadata');
  assert(reportRes.status === 'Generated', 'generateReport marks status as Generated');

  const reportsList = await reportService.getReports();
  assert(Array.isArray(reportsList) && reportsList.length > 0, 'getReports retrieves reports list');

  // Suite 6: Auth WebSocket Ticket Endpoint
  console.log('\n[Suite 6: Auth WebSocket Ticket Service]');
  const wsTicketRes = await authService.getWsTicket('aaaaaaaa-0001-0001-0001-000000000001');
  assert(wsTicketRes && wsTicketRes.ticket, 'getWsTicket returns signed ticket');
  assert(wsTicketRes.expires_in_seconds === 30, 'getWsTicket expires in 30 seconds');

  console.log(`\n========================================`);
  console.log(`TOTAL TESTS: ${passed + failed} | PASSED: ${passed} | FAILED: ${failed}`);
  console.log(`========================================\n`);

  if (failed > 0) process.exit(1);
}

runTests();
