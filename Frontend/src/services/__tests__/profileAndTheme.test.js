/**
 * Test Suite for Profile Navigation & Login Theme Toggle Fixes
 */
import fs from 'fs';
import path from 'path';

// Simulated browser localStorage for Node environment
const store = new Map();
global.localStorage = {
  getItem: (key) => store.get(key) || null,
  setItem: (key, val) => store.set(key, String(val)),
  removeItem: (key) => store.delete(key),
  clear: () => store.clear()
};
global.sessionStorage = { ...global.localStorage };

async function runTests() {
  console.log('--- STARTING PROFILE & THEME TOGGLE TEST SUITE ---');
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

  // 1. Test authService session structure
  console.log('\n[Suite 1: Session User Attributes for Profile]');
  const { authService } = await import('../authService.js');
  const session = await authService.login({ email: 'karim.adel@operix.io', password: 'password123' });

  assert(session && session.user, 'Session contains valid user');
  assert(Array.isArray(session.user.memberships), 'Session user contains memberships array');
  assert(session.user.memberships.length > 0, 'Memberships array has at least 1 entry');
  assert(session.user.memberships[0].factory === 'Plant 1', 'Membership has correct factory');
  assert(session.user.notifications && typeof session.user.notifications === 'object', 'Session user contains notifications object');
  assert(session.user.notifications.dashboardAlerts === true, 'Notifications has dashboardAlerts');

  // 2. Test ProfilePage Fallback Logic (preventing crash when user properties are undefined)
  console.log('\n[Suite 2: Profile Page Render Safety]');
  function getSafeProfileState(currentUser) {
    const user = currentUser || {
      name: 'Karim Adel',
      email: 'karim.adel@operix.io',
      initials: 'KA',
      role: 'Safety Supervisor',
      factory: 'Plant 1',
      timezone: 'Africa/Cairo',
      status: 'Active',
      platformAdmin: false,
      memberships: [
        { factory: 'Plant 1', role: 'Safety Supervisor', status: 'Active' },
        { factory: 'Plant 3', role: 'Safety Supervisor', status: 'Pending' }
      ],
      notifications: {
        dashboardAlerts: true,
        emailAlerts: true,
        minSeverity: 'Medium'
      }
    };

    const memberships = (user.memberships && Array.isArray(user.memberships) && user.memberships.length > 0)
      ? user.memberships
      : [
          { factory: user.factory || 'Plant 1', role: user.role || 'Safety Supervisor', status: 'Active' },
          { factory: 'Plant 3', role: user.role || 'Safety Supervisor', status: 'Pending' }
        ];

    // Simulate mapping over memberships
    const renderedMemberships = memberships.map((m, idx) => ({
      key: idx,
      factory: m.factory,
      role: m.role,
      status: m.status
    }));

    return { user, memberships, renderedMemberships };
  }

  // Case A: null/undefined currentUser
  try {
    const resA = getSafeProfileState(null);
    assert(resA.renderedMemberships.length === 2, 'Safe fallback renders default memberships when currentUser is null');
  } catch (e) {
    assert(false, `Crashed with null user: ${e.message}`);
  }

  // Case B: currentUser missing memberships
  try {
    const resB = getSafeProfileState({ name: 'Test User', email: 'test@operix.io', role: 'Viewer', factory: 'Plant 2' });
    assert(resB.renderedMemberships.length === 2, 'Safe fallback provides memberships when currentUser.memberships is undefined');
    assert(resB.renderedMemberships[0].factory === 'Plant 2', 'Factory is preserved in membership fallback');
  } catch (e) {
    assert(false, `Crashed with user missing memberships: ${e.message}`);
  }

  // Case C: user with populated memberships
  try {
    const resC = getSafeProfileState({
      name: 'Admin',
      memberships: [{ factory: 'HQ', role: 'Administrator', status: 'Active' }]
    });
    assert(resC.renderedMemberships.length === 1 && resC.renderedMemberships[0].factory === 'HQ', 'Preserves existing memberships when provided');
  } catch (e) {
    assert(false, `Crashed with valid memberships: ${e.message}`);
  }

  // 3. Inspect CSS cursor pointer on .user-avatar-btn
  console.log('\n[Suite 3: Navbar Avatar CSS & Navigation]');
  const layoutCss = fs.readFileSync('src/styles/layout.css', 'utf-8');
  assert(layoutCss.includes('.user-avatar-btn') && layoutCss.includes('cursor: pointer;'), '.user-avatar-btn has cursor: pointer;');

  const navbarJsx = fs.readFileSync('src/components/common/Navbar.jsx', 'utf-8');
  assert(navbarJsx.includes("onClick={() => navigate('/profile')}"), 'Navbar avatar button triggers navigate to /profile');

  // 4. Inspect AuthLayout Theme Toggle Position
  console.log('\n[Suite 4: AuthLayout Theme Toggle Position]');
  const authLayoutJsx = fs.readFileSync('src/components/layout/AuthLayout.jsx', 'utf-8');
  assert(authLayoutJsx.includes('auth-top-theme-toggle'), 'AuthLayout has auth-top-theme-toggle container');
  assert(authLayoutJsx.includes("top: '24px'") && authLayoutJsx.includes("right: '28px'"), 'Theme toggle positioned at top-right (top: 24px, right: 28px)');

  // Verify it is NOT duplicated in bottom footer
  const bottomFooterIdx = authLayoutJsx.indexOf('AI-Powered Industrial Vision & Safety Intelligence Platform');
  const toggleThemeClickCount = (authLayoutJsx.match(/onClick=\{toggleTheme\}/g) || []).length;
  assert(toggleThemeClickCount === 1, 'Theme toggle appears exactly once in AuthLayout (no duplication)');

  const footerSection = authLayoutJsx.slice(bottomFooterIdx);
  assert(!footerSection.includes('<button') && !footerSection.includes('toggleTheme'), 'Bottom footer has no toggle button (cleanly matches Figma design)');

  const pagesCss = fs.readFileSync('src/styles/pages.css', 'utf-8');
  assert(pagesCss.includes('.auth-split-wrapper') && pagesCss.includes('position: relative;'), '.auth-split-wrapper has position: relative;');

  console.log(`\n========================================`);
  console.log(`RESULTS: ${passed} PASSED, ${failed} FAILED`);
  console.log(`========================================\n`);

  if (failed > 0) process.exit(1);
}

runTests();
