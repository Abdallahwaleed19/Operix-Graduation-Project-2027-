/**
 * Operix Authentication Service
 * 
 * Manages user registration, email verification, login/logout, session restoration,
 * and password reset flows.
 * Supports both Mock Mode (with simulated crypto hashing and local storage)
 * and FastAPI live backend endpoints.
 */

import apiClient, { API_CONFIG } from './apiClient.js';

const USERS_STORAGE_KEY = 'operix_users_db';
const SESSION_STORAGE_KEY = 'operix_auth_session';
const PENDING_VERIFICATIONS_KEY = 'operix_pending_verifications';
const RESET_TOKENS_KEY = 'operix_reset_tokens';

/**
 * SHA-256 password hashing helper (avoids storing plain-text passwords in localStorage)
 */
async function hashPassword(password) {
  try {
    if (typeof crypto !== 'undefined' && crypto.subtle) {
      const encoder = new TextEncoder();
      const data = encoder.encode(password + ':operix_salt_v1');
      const hashBuffer = await crypto.subtle.digest('SHA-256', data);
      return Array.from(new Uint8Array(hashBuffer))
        .map(b => b.toString(16).padStart(2, '0'))
        .join('');
    }
  } catch {
    // Fallback deterministic hash
  }
  let hash = 0;
  const str = password + ':operix_salt_v1';
  for (let i = 0; i < str.length; i++) {
    hash = (hash << 5) - hash + str.charCodeAt(i);
    hash |= 0;
  }
  return 'sh_' + Math.abs(hash).toString(16);
}

/**
 * Pre-seeded mock users for testing all roles
 */
async function getInitialUsers() {
  const hashDefault = await hashPassword('password123');
  const hashAdmin = await hashPassword('admin123');
  const hashManager = await hashPassword('manager123');
  const hashViewer = await hashPassword('viewer123');

  return [
    {
      id: 'usr-admin',
      name: 'Mona Hassan',
      email: 'mona@plant1.example',
      passwordHash: hashAdmin,
      role: 'Administrator',
      factory: 'Plant 1',
      timezone: 'Africa/Cairo',
      status: 'Active',
      isEmailVerified: true,
      initials: 'MH'
    },
    {
      id: 'usr-manager',
      name: 'Omar Khaled',
      email: 'omar@plant1.example',
      passwordHash: hashManager,
      role: 'Factory Manager',
      factory: 'Plant 1',
      timezone: 'Africa/Cairo',
      status: 'Active',
      isEmailVerified: true,
      initials: 'OK'
    },
    {
      id: 'usr-supervisor',
      name: 'Karim Adel',
      email: 'karim.adel@operix.io',
      passwordHash: hashDefault,
      role: 'Safety Supervisor',
      factory: 'Plant 1',
      timezone: 'Africa/Cairo',
      status: 'Active',
      isEmailVerified: true,
      initials: 'KA'
    },
    {
      id: 'usr-viewer',
      name: 'Sara Nabil',
      email: 'sara@plant1.example',
      passwordHash: hashViewer,
      role: 'Viewer',
      factory: 'Plant 1',
      timezone: 'Africa/Cairo',
      status: 'Active',
      isEmailVerified: true,
      initials: 'SN'
    },
    {
      id: 'usr-unverified',
      name: 'Youssef Adel',
      email: 'youssef@plant1.example',
      passwordHash: hashDefault,
      role: 'Viewer',
      factory: 'Plant 1',
      timezone: 'Africa/Cairo',
      status: 'Pending Verification',
      isEmailVerified: false,
      initials: 'YA'
    }
  ];
}

/**
 * Get or initialize mock user repository in localStorage
 */
async function getMockUsers() {
  const raw = localStorage.getItem(USERS_STORAGE_KEY);
  if (raw) {
    try {
      return JSON.parse(raw);
    } catch {
      // Reinitialize if corrupted
    }
  }
  const defaults = await getInitialUsers();
  localStorage.setItem(USERS_STORAGE_KEY, JSON.stringify(defaults));
  return defaults;
}

function saveMockUsers(users) {
  localStorage.setItem(USERS_STORAGE_KEY, JSON.stringify(users));
}

function getPendingVerifications() {
  const raw = localStorage.getItem(PENDING_VERIFICATIONS_KEY);
  return raw ? JSON.parse(raw) : {};
}

function savePendingVerifications(data) {
  localStorage.setItem(PENDING_VERIFICATIONS_KEY, JSON.stringify(data));
}

function getResetTokens() {
  const raw = localStorage.getItem(RESET_TOKENS_KEY);
  return raw ? JSON.parse(raw) : {};
}

function saveResetTokens(data) {
  localStorage.setItem(RESET_TOKENS_KEY, JSON.stringify(data));
}

export const authService = {
  /**
   * Register a new user
   */
  async register({ fullName, email, password, role = 'Safety Supervisor', factory = 'Plant 1' }) {
    const normalizedEmail = email.trim().toLowerCase();

    if (API_CONFIG.useMock) {
      const users = await getMockUsers();
      const existing = users.find(u => u.email.toLowerCase() === normalizedEmail);

      if (existing) {
        throw new Error('An account with this email address already exists. Please sign in or use another email.');
      }

      const pHash = await hashPassword(password);
      const initials = fullName
        .split(' ')
        .map(n => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2) || 'OP';

      const newUser = {
        id: `usr-${Date.now()}`,
        name: fullName.trim(),
        email: normalizedEmail,
        passwordHash: pHash,
        role,
        factory,
        timezone: 'Africa/Cairo',
        status: 'Pending Verification',
        isEmailVerified: false,
        initials,
        createdAt: new Date().toISOString()
      };

      users.push(newUser);
      saveMockUsers(users);

      // Generate 6-digit test code (defaults to 123456 or 6-digit number)
      const code = '123456';
      const verifications = getPendingVerifications();
      verifications[normalizedEmail] = {
        code,
        expiresAt: Date.now() + 15 * 60 * 1000, // 15 mins
        attempts: 0
      };
      savePendingVerifications(verifications);

      console.info(`[Operix Mock Auth] Verification code for ${normalizedEmail}: ${code}`);

      return {
        success: true,
        email: normalizedEmail,
        testVerificationCode: code,
        message: 'Registration successful. Please verify your email.'
      };
    }

    // Live FastAPI Backend: POST /auth/register
    return apiClient.post('/auth/register', {
      full_name: fullName,
      email: normalizedEmail,
      password,
      role,
      factory
    });
  },

  /**
   * Verify email with 6-digit code
   */
  async verifyEmail({ email, code }) {
    const normalizedEmail = email.trim().toLowerCase();
    const cleanCode = code.trim();

    if (API_CONFIG.useMock) {
      const verifications = getPendingVerifications();
      const entry = verifications[normalizedEmail];

      if (!entry) {
        throw new Error('No pending verification code found for this email. Please request a new code.');
      }

      if (Date.now() > entry.expiresAt) {
        delete verifications[normalizedEmail];
        savePendingVerifications(verifications);
        throw new Error('The verification code has expired. Please request a new one.');
      }

      if (entry.code !== cleanCode) {
        entry.attempts = (entry.attempts || 0) + 1;
        savePendingVerifications(verifications);
        throw new Error('Invalid verification code. Please check and try again.');
      }

      // Mark user verified in mock DB
      const users = await getMockUsers();
      const user = users.find(u => u.email.toLowerCase() === normalizedEmail);

      if (!user) {
        throw new Error('User account not found.');
      }

      user.isEmailVerified = true;
      user.status = 'Active'; // Email verified
      saveMockUsers(users);

      // Clean up verification entry
      delete verifications[normalizedEmail];
      savePendingVerifications(verifications);

      return {
        success: true,
        email: normalizedEmail,
        status: user.status,
        message: 'Email verified successfully! You can now sign in.'
      };
    }

    // Live FastAPI Backend: POST /auth/verify-email
    return apiClient.post('/auth/verify-email', {
      email: normalizedEmail,
      code: cleanCode
    });
  },

  /**
   * Resend verification code
   */
  async resendVerificationCode(email) {
    const normalizedEmail = email.trim().toLowerCase();

    if (API_CONFIG.useMock) {
      const users = await getMockUsers();
      const user = users.find(u => u.email.toLowerCase() === normalizedEmail);

      if (!user) {
        throw new Error('No account found with this email address.');
      }

      if (user.isEmailVerified) {
        throw new Error('This email address has already been verified. You can sign in.');
      }

      const code = '123456';
      const verifications = getPendingVerifications();
      verifications[normalizedEmail] = {
        code,
        expiresAt: Date.now() + 15 * 60 * 1000,
        attempts: 0
      };
      savePendingVerifications(verifications);

      console.info(`[Operix Mock Auth] New verification code for ${normalizedEmail}: ${code}`);

      return {
        success: true,
        email: normalizedEmail,
        testVerificationCode: code,
        message: 'A new verification code has been generated.'
      };
    }

    // Live FastAPI Backend: POST /auth/resend-verification
    return apiClient.post('/auth/resend-verification', { email: normalizedEmail });
  },

  /**
   * Authenticate user with credentials
   */
  async login({ email, password, keepSignedIn = true }) {
    const normalizedEmail = email.trim().toLowerCase();

    if (API_CONFIG.useMock) {
      const users = await getMockUsers();
      const user = users.find(u => u.email.toLowerCase() === normalizedEmail);

      if (!user) {
        throw new Error('Invalid email or password.');
      }

      const pHash = await hashPassword(password);
      if (user.passwordHash !== pHash) {
        throw new Error('Invalid email or password.');
      }

      // Enforcement 1: Check Email Verification
      if (!user.isEmailVerified) {
        const error = new Error('Your email address has not been verified yet. Please verify your account before logging in.');
        error.code = 'EMAIL_NOT_VERIFIED';
        error.email = normalizedEmail;
        throw error;
      }

      // Enforcement 2: Check Account Activation Status
      if (user.status === 'Suspended' || user.status === 'Deactivated') {
        throw new Error('Your account is inactive. Please contact your factory administrator.');
      }

      // Create session
      const token = `mock-token-${Date.now()}-${user.id}`;
      const session = {
        user: {
          id: user.id,
          name: user.name,
          email: user.email,
          role: user.role,
          factory: user.factory,
          timezone: user.timezone || 'Africa/Cairo',
          status: user.status,
          initials: user.initials,
          isEmailVerified: true,
          memberships: user.memberships || [
            { factory: user.factory || 'Plant 1', role: user.role || 'Safety Supervisor', status: 'Active' },
            { factory: 'Plant 3', role: user.role || 'Safety Supervisor', status: 'Pending' }
          ],
          notifications: user.notifications || {
            dashboardAlerts: true,
            emailAlerts: true,
            minSeverity: 'Medium'
          }
        },
        token,
        expiresAt: Date.now() + (keepSignedIn ? 7 * 24 * 3600 * 1000 : 8 * 3600 * 1000)
      };

      const storage = keepSignedIn ? localStorage : sessionStorage;
      storage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session));
      localStorage.setItem('operix_token', token);

      return session;
    }

    // Live FastAPI Backend: POST /auth/token (OAuth2 password flow)
    const formData = new URLSearchParams();
    formData.append('username', normalizedEmail);
    formData.append('password', password);

    const data = await apiClient.post('/auth/token', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    });

    localStorage.setItem('operix_token', data.access_token);
    return data;
  },

  /**
   * Restore existing session on page load
   */
  getCurrentSession() {
    let raw = localStorage.getItem(SESSION_STORAGE_KEY) || sessionStorage.getItem(SESSION_STORAGE_KEY);
    if (!raw) return null;

    try {
      const session = JSON.parse(raw);
      if (session.expiresAt && Date.now() > session.expiresAt) {
        this.logout();
        return null;
      }
      return session;
    } catch {
      this.logout();
      return null;
    }
  },

  /**
   * Log out active user
   */
  logout() {
    localStorage.removeItem(SESSION_STORAGE_KEY);
    sessionStorage.removeItem(SESSION_STORAGE_KEY);
    localStorage.removeItem('operix_token');
    return true;
  },

  /**
   * Request password reset link / token
   */
  async requestPasswordReset(email) {
    const normalizedEmail = email.trim().toLowerCase();

    if (API_CONFIG.useMock) {
      const users = await getMockUsers();
      const user = users.find(u => u.email.toLowerCase() === normalizedEmail);

      // Even if user not found, for security return success message, but only generate token if user exists
      if (!user) {
        return {
          success: true,
          email: normalizedEmail,
          message: 'If an account exists with this email, reset instructions have been generated.'
        };
      }

      const token = `rst-${Date.now().toString(36)}-${Math.random().toString(36).substring(2, 8)}`;
      const tokens = getResetTokens();
      tokens[token] = {
        email: normalizedEmail,
        expiresAt: Date.now() + 60 * 60 * 1000, // 1 hour
        used: false
      };
      saveResetTokens(tokens);

      console.info(`[Operix Mock Auth] Reset password token for ${normalizedEmail}: ${token}`);

      return {
        success: true,
        email: normalizedEmail,
        testResetToken: token,
        message: 'Password reset link generated.'
      };
    }

    // Live FastAPI Backend: POST /auth/forgot-password
    return apiClient.post('/auth/forgot-password', { email: normalizedEmail });
  },

  /**
   * Validate a reset token
   */
  async validateResetToken(token) {
    if (!token) return { valid: false, message: 'Missing token' };

    if (API_CONFIG.useMock) {
      const tokens = getResetTokens();
      const entry = tokens[token];

      if (!entry) {
        return { valid: false, message: 'Invalid or unknown reset token.' };
      }
      if (entry.used) {
        return { valid: false, message: 'This reset link has already been used.' };
      }
      if (Date.now() > entry.expiresAt) {
        return { valid: false, message: 'This reset link has expired. Please request a new one.' };
      }

      return { valid: true, email: entry.email };
    }

    return apiClient.get(`/auth/validate-reset-token?token=${encodeURIComponent(token)}`);
  },

  /**
   * Set new password with valid reset token
   */
  async resetPassword({ token, newPassword }) {
    if (API_CONFIG.useMock) {
      const validation = await this.validateResetToken(token);
      if (!validation.valid) {
        throw new Error(validation.message || 'Invalid or expired reset token.');
      }

      const users = await getMockUsers();
      const user = users.find(u => u.email.toLowerCase() === validation.email.toLowerCase());

      if (!user) {
        throw new Error('User account not found.');
      }

      user.passwordHash = await hashPassword(newPassword);
      saveMockUsers(users);

      // Invalidate used token
      const tokens = getResetTokens();
      if (tokens[token]) {
        tokens[token].used = true;
        saveResetTokens(tokens);
      }

      return {
        success: true,
        message: 'Password updated successfully. You can now sign in with your new password.'
      };
    }

    // Live FastAPI Backend: POST /auth/reset-password
    return apiClient.post('/auth/reset-password', {
      token,
      new_password: newPassword
    });
  }
};

export default authService;
