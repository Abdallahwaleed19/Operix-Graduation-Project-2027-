import { isMockEnabled } from './apiClient.js';
import authService from './authService.js';

export const WS_STATUS = {
  DISCONNECTED: 'DISCONNECTED',
  CONNECTING: 'CONNECTING',
  CONNECTED: 'CONNECTED',
  RECONNECTING: 'RECONNECTING',
};

class WebSocketService {
  constructor() {
    this.ws = null;
    this.status = WS_STATUS.DISCONNECTED;
    this.statusListeners = new Set();
    this.eventListeners = new Map();
    this.pingInterval = null;
    this.reconnectTimeout = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.baseReconnectDelayMs = 2000;
    this.enabled = true;
  }

  getWsBaseUrl() {
    if (import.meta.env?.VITE_WS_URL) {
      return import.meta.env.VITE_WS_URL.replace(/\/+$/, '');
    }
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname || 'localhost';
    const port = '8000';
    return `${protocol}//${host}:${port}`;
  }

  setStatus(newStatus) {
    if (this.status !== newStatus) {
      this.status = newStatus;
      this.statusListeners.forEach((listener) => {
        try {
          listener(newStatus);
        } catch (err) {
          console.error('[WebSocket] Status listener error:', err);
        }
      });
    }
  }

  onStatusChange(callback) {
    this.statusListeners.add(callback);
    callback(this.status);
    return () => this.statusListeners.delete(callback);
  }

  on(eventType, callback) {
    if (!this.eventListeners.has(eventType)) {
      this.eventListeners.set(eventType, new Set());
    }
    this.eventListeners.get(eventType).add(callback);
    return () => {
      const set = this.eventListeners.get(eventType);
      if (set) set.delete(callback);
    };
  }

  off(eventType, callback) {
    const set = this.eventListeners.get(eventType);
    if (set) set.delete(callback);
  }

  dispatch(event) {
    const { type } = event;
    if (type && this.eventListeners.has(type)) {
      this.eventListeners.get(type).forEach((cb) => {
        try {
          cb(event);
        } catch (err) {
          console.error(`[WebSocket] Error in handler for '${type}':`, err);
        }
      });
    }
    // Generic wildcard listeners
    if (this.eventListeners.has('*')) {
      this.eventListeners.get('*').forEach((cb) => {
        try {
          cb(event);
        } catch (err) {
          console.error('[WebSocket] Error in wildcard handler:', err);
        }
      });
    }
  }

  async connect() {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    if (isMockEnabled('websockets')) {
      this.setStatus(WS_STATUS.CONNECTED);
      return;
    }

    const session = authService.getCurrentSession();
    const token = session?.token || session?.accessToken;
    const user = session?.user;
    if (!token) {
      this.setStatus(WS_STATUS.DISCONNECTED);
      return;
    }

    this.setStatus(this.reconnectAttempts > 0 ? WS_STATUS.RECONNECTING : WS_STATUS.CONNECTING);

    const baseUrl = this.getWsBaseUrl();
    let wsUrl = null;

    // Phase 2: Attempt ticket-based auth via /api/v1/auth/ws-ticket
    try {
      const factoryId = user?.factory_id || user?.factoryId;
      const ticketRes = await authService.getWsTicket(factoryId);
      const ticket = ticketRes?.ticket || ticketRes?.data?.ticket;
      if (ticket) {
        wsUrl = `${baseUrl}/ws/v2/events?ticket=${encodeURIComponent(ticket)}`;
      }
    } catch (ticketErr) {
      console.warn('[WebSocket] Ticket acquisition failed, attempting fallback to legacy WS endpoint:', ticketErr);
    }

    // Legacy fallback: /ws/events?token=<jwt>&factory_id=<uuid>
    if (!wsUrl) {
      const factoryId = user?.factory_id || user?.factoryId || '';
      wsUrl = `${baseUrl}/ws/events?token=${encodeURIComponent(token)}${factoryId ? `&factory_id=${encodeURIComponent(factoryId)}` : ''}`;
    }

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
        this.setStatus(WS_STATUS.CONNECTED);
        this.startHeartbeat();
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'pong') {
            return;
          }
          this.dispatch(data);
        } catch (err) {
          console.warn('[WebSocket] Non-JSON payload received:', event.data);
        }
      };

      this.ws.onerror = (err) => {
        console.warn('[WebSocket] Connection error:', err);
      };

      this.ws.onclose = (event) => {
        this.stopHeartbeat();
        this.ws = null;
        this.setStatus(WS_STATUS.DISCONNECTED);

        // Schedule reconnection unless explicitly closed with code 1000
        if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
          const delay = Math.min(this.baseReconnectDelayMs * Math.pow(2, this.reconnectAttempts), 30000);
          this.reconnectAttempts += 1;
          this.reconnectTimeout = setTimeout(() => this.connect(), delay);
        }
      };
    } catch (err) {
      console.error('[WebSocket] Initialization error:', err);
      this.setStatus(WS_STATUS.DISCONNECTED);
    }
  }

  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const payload = typeof data === 'string' ? data : JSON.stringify(data);
      this.ws.send(payload);
      return true;
    }
    return false;
  }

  startHeartbeat() {
    this.stopHeartbeat();
    this.pingInterval = setInterval(() => {
      this.send({ type: 'ping' });
    }, 25000);
  }

  stopHeartbeat() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  disconnect() {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    this.stopHeartbeat();
    if (this.ws) {
      this.ws.close(1000, 'User logged out or client disconnected');
      this.ws = null;
    }
    this.reconnectAttempts = 0;
    this.setStatus(WS_STATUS.DISCONNECTED);
  }
}

export const websocketService = new WebSocketService();
export default websocketService;
