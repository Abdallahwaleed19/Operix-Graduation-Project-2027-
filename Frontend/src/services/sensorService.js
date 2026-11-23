import apiClient, { API_CONFIG } from './apiClient';
import { initialSensors, initialThermalReadings } from '../data/mockData';

/**
 * Environmental & Thermal Sensors Service
 * Connects to FastAPI endpoint `/devices/sensors`
 */
export const sensorService = {
  async getSensors(filters = {}) {
    if (API_CONFIG.useMock) {
      let result = [...initialSensors];
      if (filters.type && filters.type !== 'All') {
        result = result.filter(s => s.type.toLowerCase().includes(filters.type.toLowerCase()));
      }
      return result;
    }
    const params = new URLSearchParams(filters).toString();
    return apiClient.get(`/devices/sensors${params ? `?${params}` : ''}`);
  },

  async getSensorById(id) {
    if (API_CONFIG.useMock) {
      return initialSensors.find(s => s.id === id) || null;
    }
    return apiClient.get(`/devices/sensors/${id}`);
  },

  async toggleSensor(id) {
    if (API_CONFIG.useMock) {
      const sensor = initialSensors.find(s => s.id === id);
      if (sensor) {
        const isOnline = sensor.status === 'Online';
        sensor.status = isOnline ? 'Disabled' : 'Online';
        sensor.active = !isOnline;
      }
      return { success: true, id };
    }
    return apiClient.post(`/devices/sensors/${id}/toggle`);
  },

  async updateSensor(id, updatedFields) {
    if (API_CONFIG.useMock) {
      const sensor = initialSensors.find(s => s.id === id);
      if (sensor) {
        Object.assign(sensor, updatedFields);
      }
      return { success: true, ...sensor };
    }
    return apiClient.patch(`/devices/sensors/${id}`, updatedFields);
  },

  async getThermalReadings() {
    if (API_CONFIG.useMock) {
      return initialThermalReadings;
    }
    return apiClient.get('/devices/sensors/thermal-readings');
  }
};

export default sensorService;
