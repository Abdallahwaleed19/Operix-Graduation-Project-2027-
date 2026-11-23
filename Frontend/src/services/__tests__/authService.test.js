/**
 * Automated Test Suite for Operix authService
 * Tests all requirements:
 * 1. Registration & email unverified flag
 * 2. Unverified login rejection
 * 3. Verification code rejection & validation
 * 4. Successful login after verification
 * 5. Forgot password token generation
 * 6. Invalid token rejection
 * 7. Password reset & login with new password
 * 8. All 4 pre-seeded role accounts
 */

// Simulated browser localStorage for Node environment
const store = new Map();
global.localStorage = {
  getItem: (key) => store.get(key) || null,
  setItem: (key, val) => store.set(key, String(val)),
  removeItem: (key) => store.delete(key),
  clear: () => store.clear()
};

global.sessionStorage = { ...global.localStorage };

// Mock import.meta.env
global.import_meta = {
  env: {
    VITE_USE_MOCK_DATA: 'true',
    VITE_API_BASE_URL: 'http://localhost:8000/api/v1'
  }
};

async function runTestSuite() {
  console.log('--- STARTING OPERIX AUTH SERVICE TEST SUITE ---');
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

  // Import authService dynamically
  const { authService } = await import('../authService.js');

  // Test 1: Pre-seeded accounts exist and can authenticate
  console.log('\n[Suite 1: Pre-seeded Role Accounts]');
  try {
    const adminSession = await authService.login({ email: 'mona@plant1.example', password: 'admin123' });
    assert(adminSession.user.role === 'Administrator', 'Admin logs in with role Administrator');
    assert(adminSession.user.isEmailVerified === true, 'Admin account has isEmailVerified = true');

    const managerSession = await authService.login({ email: 'omar@plant1.example', password: 'manager123' });
    assert(managerSession.user.role === 'Factory Manager', 'Manager logs in with role Factory Manager');

    const supervisorSession = await authService.login({ email: 'karim.adel@operix.io', password: 'password123' });
    assert(supervisorSession.user.role === 'Safety Supervisor', 'Supervisor logs in with role Safety Supervisor');

    const viewerSession = await authService.login({ email: 'sara@plant1.example', password: 'viewer123' });
    assert(viewerSession.user.role === 'Viewer', 'Viewer logs in with role Viewer');
  } catch (err) {
    assert(false, `Pre-seeded role login threw error: ${err.message}`);
  }

  // Test 2: Invalid credentials rejection
  console.log('\n[Suite 2: Credential Rejection]');
  try {
    await authService.login({ email: 'karim.adel@operix.io', password: 'WRONG_PASSWORD' });
    assert(false, 'Should have rejected incorrect password');
  } catch (err) {
    assert(err.message === 'Invalid email or password.', 'Rejects incorrect password with clean message');
  }

  try {
    await authService.login({ email: 'unknown.user@operix.io', password: 'password123' });
    assert(false, 'Should have rejected unknown user');
  } catch (err) {
    assert(err.message === 'Invalid email or password.', 'Rejects unknown user with clean message');
  }

  // Test 3: Unverified account login prevention
  console.log('\n[Suite 3: Unverified Account Login Prevention]');
  try {
    await authService.login({ email: 'youssef@plant1.example', password: 'password123' });
    assert(false, 'Should have rejected unverified account');
  } catch (err) {
    assert(err.code === 'EMAIL_NOT_VERIFIED', 'Rejects unverified account with code EMAIL_NOT_VERIFIED');
  }

  // Test 4: Registration Flow
  console.log('\n[Suite 4: User Registration Flow]');
  let regResult;
  try {
    regResult = await authService.register({
      fullName: 'Hassan Zaki',
      email: 'hassan.zaki@operix.io',
      password: 'password123',
      role: 'Safety Supervisor',
      factory: 'Plant 1'
    });
    assert(regResult.success === true, 'Registration succeeded');
    assert(regResult.email === 'hassan.zaki@operix.io', 'Returns registered email');
    assert(regResult.testVerificationCode === '123456', 'Returns test verification code');
  } catch (err) {
    assert(false, `Registration failed: ${err.message}`);
  }

  // Duplicate registration rejection
  try {
    await authService.register({
      fullName: 'Hassan Zaki',
      email: 'hassan.zaki@operix.io',
      password: 'password123'
    });
    assert(false, 'Should have prevented duplicate registration');
  } catch (err) {
    assert(err.message.includes('already exists'), 'Rejects duplicate email registration');
  }

  // Try to log in as newly registered user before verifying
  try {
    await authService.login({ email: 'hassan.zaki@operix.io', password: 'password123' });
    assert(false, 'Should have rejected unverified new user');
  } catch (err) {
    assert(err.code === 'EMAIL_NOT_VERIFIED', 'Newly registered user cannot log in before verification');
  }

  // Test 5: Email Verification Validation
  console.log('\n[Suite 5: Email Verification Validation]');
  // Try incorrect code
  try {
    await authService.verifyEmail({ email: 'hassan.zaki@operix.io', code: '999999' });
    assert(false, 'Should have rejected incorrect code 999999');
  } catch (err) {
    assert(err.message.includes('Invalid verification code'), 'Rejects incorrect code');
  }

  // Try correct code
  try {
    const verifyRes = await authService.verifyEmail({ email: 'hassan.zaki@operix.io', code: '123456' });
    assert(verifyRes.success === true, 'Verification succeeds with code 123456');
    assert(verifyRes.status === 'Active', 'User status becomes Active');
  } catch (err) {
    assert(false, `Valid verification failed: ${err.message}`);
  }

  // Now login as newly verified user
  try {
    const session = await authService.login({ email: 'hassan.zaki@operix.io', password: 'password123' });
    assert(session.user.name === 'Hassan Zaki', 'Login succeeds for newly verified user');
    assert(session.user.isEmailVerified === true, 'Session reflects isEmailVerified = true');
  } catch (err) {
    assert(false, `Login after verification failed: ${err.message}`);
  }

  // Session check & logout
  const current = authService.getCurrentSession();
  assert(current !== null && current.user.email === 'hassan.zaki@operix.io', 'getCurrentSession retrieves active session');
  authService.logout();
  const afterLogout = authService.getCurrentSession();
  assert(afterLogout === null, 'Session is cleared after logout');

  // Test 6: Password Reset Flow
  console.log('\n[Suite 6: Password Reset Flow]');
  let resetReq;
  try {
    resetReq = await authService.requestPasswordReset('sara@plant1.example');
    assert(resetReq.success === true, 'Password reset request succeeds');
    assert(typeof resetReq.testResetToken === 'string' && resetReq.testResetToken.startsWith('rst-'), 'Generates rst-... token');
  } catch (err) {
    assert(false, `Password reset request failed: ${err.message}`);
  }

  // Test invalid token
  const invalidVal = await authService.validateResetToken('rst-fake-token-999');
  assert(invalidVal.valid === false, 'Rejects invalid reset token');

  // Test valid token
  const validVal = await authService.validateResetToken(resetReq.testResetToken);
  assert(validVal.valid === true, 'Validates genuine reset token');
  assert(validVal.email === 'sara@plant1.example', 'Token matches target email');

  // Reset password
  try {
    const resetRes = await authService.resetPassword({
      token: resetReq.testResetToken,
      newPassword: 'newviewerpass123'
    });
    assert(resetRes.success === true, 'Password reset succeeds');
  } catch (err) {
    assert(false, `resetPassword failed: ${err.message}`);
  }

  // Re-using token must fail
  const reusedVal = await authService.validateResetToken(resetReq.testResetToken);
  assert(reusedVal.valid === false, 'Cannot re-use already-used reset token');

  // Login with old password must fail
  try {
    await authService.login({ email: 'sara@plant1.example', password: 'viewer123' });
    assert(false, 'Old password should no longer work');
  } catch (err) {
    assert(err.message === 'Invalid email or password.', 'Old password rejected');
  }

  // Login with new password must succeed
  try {
    const newViewerSession = await authService.login({ email: 'sara@plant1.example', password: 'newviewerpass123' });
    assert(newViewerSession.user.email === 'sara@plant1.example', 'Login succeeds with new password');
    assert(newViewerSession.user.role === 'Viewer', 'Viewer role preserved');
  } catch (err) {
    assert(false, `Login with new password failed: ${err.message}`);
  }

  console.log(`\n========================================`);
  console.log(`TOTAL TESTS: ${passed + failed} | PASSED: ${passed} | FAILED: ${failed}`);
  console.log(`========================================\n`);

  if (failed > 0) process.exit(1);
}

runTestSuite().catch(err => {
  console.error('Test runner fatal error:', err);
  process.exit(1);
});
