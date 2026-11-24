# Frontend Testing & Verification Guide

---

## 1. Automated Unit & Integration Test Suites

Run tests directly via Node.js ESM:

```powershell
node src/services/__tests__/apiIntegration.test.js
node src/services/__tests__/authService.test.js
node src/services/__tests__/profileAndTheme.test.js
node src/services/__tests__/loginMockModeVisibility.test.js
```

### Coverage Summary
- `apiIntegration.test.js`: Validates `buildUrl`, envelope unwrapping, error handling, and all connected endpoint paths (`analytics`, `assistant`, `reports`, `evidence`, `ws-ticket`).
- `authService.test.js`: Validates session storage, expiration, RBAC permissions, and auth state transitions.
- `profileAndTheme.test.js`: Validates profile updates and dark/light theme persistence.
- `loginMockModeVisibility.test.js`: Ensures demo credentials are hidden in production/live mode (`API_CONFIG.useMock = false`).

---

## 2. Production Build Verification

```powershell
npm run build
```

Expected outcome: Vite production bundle compiles cleanly with 0 errors.
