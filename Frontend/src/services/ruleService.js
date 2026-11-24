import apiClient, { isMockEnabled } from './apiClient.js';
import { initialRules } from '../data/mockData.js';

/**
 * Normalizes backend SafetyRuleResponse into UI friendly object
 */
export function mapBackendRule(r) {
  if (!r) return null;
  const isEnabled = r.is_enabled !== undefined ? Boolean(r.is_enabled) : Boolean(r.enabled);
  return {
    id: r.id,
    name: r.name || 'Unnamed Rule',
    enabled: isEnabled,
    is_enabled: isEnabled,
    type: r.event_type || 'ppe_violation',
    event_type: r.event_type || 'ppe_violation',
    severity: r.severity || 'medium',
    zone_id: r.zone_id || null,
    department_id: r.department_id || null,
    sensor_id: r.sensor_id || null,
    min_confidence: r.min_confidence !== undefined ? r.min_confidence : 0.85,
    min_duration_s: r.min_duration_s !== undefined ? r.min_duration_s : 0,
    threshold_value: r.threshold_value || null,
    notify: r.notify !== undefined ? Boolean(r.notify) : true,
    version: r.version || 1,
    created_at: r.created_at || new Date().toISOString(),
    // Compatibility fields for RuleBuilderPage & EditRulePage
    ifDetection: {
      eventType: r.event_type || 'PPE violation',
      severity: r.severity ? r.severity.charAt(0).toUpperCase() + r.severity.slice(1).toLowerCase() : 'Medium',
      minConfidence: r.min_confidence !== undefined ? r.min_confidence : 0.80,
      minDuration: r.min_duration_s !== undefined ? r.min_duration_s : 0,
      thresholdValue: r.threshold_value || '—'
    },
    inScope: {
      zone: r.zone_id ? `Zone (${String(r.zone_id).slice(0, 8)})` : 'Factory Wide',
      department: r.department_id ? `Dept (${String(r.department_id).slice(0, 8)})` : 'Any',
      sensor: r.sensor_id ? `Sensor (${String(r.sensor_id).slice(0, 8)})` : 'None'
    },
    thenResult: {
      notify: r.notify !== undefined ? Boolean(r.notify) : true,
      channels: r.notify ? 'Alert Notification & SMS' : 'Audit Log Only',
      createAlert: true
    }
  };
}

/**
 * Normalizes UI payload to backend SafetyRuleCreate or SafetyRuleUpdate
 */
export function normalizeRulePayload(payload) {
  const result = {};

  if (payload.name !== undefined) result.name = payload.name;

  if (payload.event_type !== undefined) {
    result.event_type = payload.event_type.toLowerCase().replace(/\s+/g, '_');
  } else if (payload.ifDetection?.eventType) {
    const raw = payload.ifDetection.eventType.toLowerCase();
    if (raw.includes('helmet') || raw.includes('vest') || raw.includes('ppe')) {
      result.event_type = 'ppe_violation';
    } else if (raw.includes('fall')) {
      result.event_type = 'fall';
    } else if (raw.includes('zone') || raw.includes('intrusion') || raw.includes('restricted')) {
      result.event_type = 'restricted_zone_intrusion';
    } else if (raw.includes('fatigue')) {
      result.event_type = 'potential_fatigue';
    } else if (raw.includes('fire')) {
      result.event_type = 'fire';
    } else if (raw.includes('smoke')) {
      result.event_type = 'smoke';
    } else if (raw.includes('temp')) {
      result.event_type = 'temperature_anomaly';
    } else {
      result.event_type = 'ppe_violation';
    }
  }

  if (payload.severity !== undefined) {
    result.severity = payload.severity.toLowerCase();
  } else if (payload.ifDetection?.severity) {
    result.severity = payload.ifDetection.severity.toLowerCase();
  }

  if (payload.is_enabled !== undefined) {
    result.is_enabled = Boolean(payload.is_enabled);
  } else if (payload.enabled !== undefined) {
    result.is_enabled = Boolean(payload.enabled);
  }

  if (payload.min_confidence !== undefined) {
    result.min_confidence = parseFloat(payload.min_confidence);
  } else if (payload.ifDetection?.minConfidence !== undefined) {
    result.min_confidence = parseFloat(payload.ifDetection.minConfidence);
  }

  if (payload.min_duration_s !== undefined) {
    result.min_duration_s = parseInt(payload.min_duration_s, 10);
  } else if (payload.ifDetection?.minDuration !== undefined) {
    result.min_duration_s = parseInt(payload.ifDetection.minDuration, 10);
  }

  if (payload.notify !== undefined) {
    result.notify = Boolean(payload.notify);
  } else if (payload.thenResult?.notify !== undefined) {
    result.notify = Boolean(payload.thenResult.notify);
  }

  // Scopes: ensure exclusivity per schema validator
  if (payload.zone_id) result.zone_id = payload.zone_id;
  else if (payload.department_id) result.department_id = payload.department_id;
  else if (payload.sensor_id) result.sensor_id = payload.sensor_id;

  return result;
}

/**
 * No-Code Safety Rules & Vision Geofences Service
 * Connects to FastAPI endpoint `/rules`
 */
export const ruleService = {
  async getRules(filters = {}) {
    if (isMockEnabled('rules')) {
      let result = [...initialRules];
      if (filters.type && filters.type !== 'All') {
        result = result.filter(r => (r.type || '').toLowerCase() === filters.type.toLowerCase());
      }
      return result;
    }

    const query = new URLSearchParams();
    if (filters.is_enabled !== undefined) query.set('is_enabled', filters.is_enabled);
    if (filters.event_type) query.set('event_type', filters.event_type);
    if (filters.limit) query.set('limit', filters.limit);
    if (filters.offset) query.set('offset', filters.offset);

    const queryString = query.toString();
    const endpoint = `/rules${queryString ? `?${queryString}` : ''}`;
    const response = await apiClient.get(endpoint);

    const items = response?.items || (Array.isArray(response) ? response : []);
    return items.map(mapBackendRule);
  },

  async getRuleById(id) {
    if (isMockEnabled('rules')) {
      return initialRules.find(r => r.id === id) || null;
    }
    const data = await apiClient.get(`/rules/${id}`);
    return mapBackendRule(data);
  },

  async toggleRule(id, currentStatus) {
    if (isMockEnabled('rules')) {
      const rule = initialRules.find(r => r.id === id);
      if (rule) {
        rule.enabled = !rule.enabled;
      }
      return { success: true, id, enabled: rule ? rule.enabled : !currentStatus };
    }
    const desiredState = currentStatus !== undefined ? !currentStatus : true;
    return apiClient.patch(`/rules/${id}/status`, { is_enabled: desiredState });
  },

  async updateRule(id, updatedFields) {
    if (isMockEnabled('rules')) {
      const rule = initialRules.find(r => r.id === id);
      if (rule) {
        Object.assign(rule, updatedFields);
      }
      return { success: true, ...rule };
    }
    const payload = normalizeRulePayload(updatedFields);
    return apiClient.put(`/rules/${id}`, payload);
  },

  async createRule(newRule) {
    if (isMockEnabled('rules')) {
      const created = { id: `rule-${Date.now()}`, ...newRule };
      initialRules.push(created);
      return { success: true, ...created };
    }
    const payload = normalizeRulePayload(newRule);
    return apiClient.post('/rules', payload);
  },

  async deleteRule(id) {
    if (isMockEnabled('rules')) {
      const index = initialRules.findIndex(r => r.id === id);
      if (index !== -1) initialRules.splice(index, 1);
      return { success: true, id };
    }
    return apiClient.delete(`/rules/${id}`);
  }
};

export default ruleService;
