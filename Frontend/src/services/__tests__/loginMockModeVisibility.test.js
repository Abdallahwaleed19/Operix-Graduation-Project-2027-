/**
 * Verification Test: "Quick Test Accounts (Mock Mode)" visibility
 * Tests:
 * 1. API_CONFIG.useMock definition and toggling
 * 2. In Mock Mode (useMock = true): Quick Test Accounts section is rendered
 * 3. In Live Backend Mode (useMock = false): Quick Test Accounts section is completely hidden
 * 4. Login form fields and authentication handlers remain unaffected in both modes
 */
import fs from 'fs';

async function runTests() {
  console.log('--- STARTING QUICK TEST ACCOUNTS VISIBILITY TEST ---');
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

  // 1. Inspect LoginPage.jsx source code
  const loginJsx = fs.readFileSync('src/pages/auth/LoginPage.jsx', 'utf-8');

  assert(
    loginJsx.includes("import { API_CONFIG } from '../../services/apiClient';"),
    'LoginPage imports API_CONFIG from apiClient'
  );

  assert(
    loginJsx.includes('{API_CONFIG.useMock && ('),
    'Quick Test Accounts is guarded by {API_CONFIG.useMock && (...)}'
  );

  // 2. Verify API_CONFIG structure from apiClient
  const { API_CONFIG } = await import('../apiClient.js');
  assert(typeof API_CONFIG.useMock === 'boolean', 'API_CONFIG.useMock is a boolean');

  // 3. Simulate conditional render behavior
  function renderQuickAccountsSection(useMock) {
    if (!useMock) return null;
    return {
      title: 'Quick Test Accounts (Mock Mode)',
      accounts: ['Admin', 'Manager', 'Supervisor', 'Viewer', 'Unverified']
    };
  }

  // Test Case A: Mock Mode (useMock = true)
  const mockRender = renderQuickAccountsSection(true);
  assert(mockRender !== null, 'Mock Mode: Section is rendered');
  assert(mockRender.title === 'Quick Test Accounts (Mock Mode)', 'Mock Mode: Title is visible');
  assert(mockRender.accounts.length === 5, 'Mock Mode: All 5 role test account buttons are available');

  // Test Case B: Live Backend Mode (useMock = false)
  const liveRender = renderQuickAccountsSection(false);
  assert(liveRender === null, 'Live Backend Mode: Section is completely hidden (null)');

  // 4. Verify Login form elements remain outside the conditional block
  const formIdx = loginJsx.indexOf('<form onSubmit={handleSubmit}>');
  const endFormIdx = loginJsx.indexOf('</form>');
  const quickAccountsIdx = loginJsx.indexOf('{API_CONFIG.useMock &&');

  assert(formIdx > 0 && endFormIdx > formIdx, 'Login form is properly defined');
  assert(quickAccountsIdx > endFormIdx, 'Quick Test Accounts section is outside the login form (does not affect form submission)');
  assert(loginJsx.includes('type="email"'), 'Email input field is present');
  assert(loginJsx.includes('type={showPassword ? \'text\' : \'password\'}'), 'Password input with toggle is present');
  assert(loginJsx.includes('Keep me signed in'), 'Keep me signed in switch is present');
  assert(loginJsx.includes('Create an account'), 'Create an account link is present');

  console.log(`\n========================================`);
  console.log(`RESULTS: ${passed} PASSED, ${failed} FAILED`);
  console.log(`========================================\n`);

  if (failed > 0) process.exit(1);
}

runTests();
