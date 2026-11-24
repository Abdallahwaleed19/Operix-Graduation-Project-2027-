import apiClient, { isMockEnabled } from './apiClient';
import { initialCameras } from '../data/mockData';

/**
 * Camera Streams Service
 * Connects to FastAPI endpoint `/devices/cameras`
 */
export const cameraService = {
  async getCameras(filters = {}) {
    if (isMockEnabled('cameras')) {
      let result = [...initialCameras];
      if (filters.zone && filters.zone !== 'All') {
        result = result.filter(c => c.zone === filters.zone);
      }
      if (filters.status && filters.status !== 'All') {
        result = result.filter(c => c.status.toLowerCase() === filters.status.toLowerCase());
      }
      return result;
    }
    const params = new URLSearchParams(filters).toString();
    return apiClient.get(`/devices/cameras${params ? `?${params}` : ''}`);
  },

  async getCameraById(id) {
    if (isMockEnabled('cameras')) {
      return initialCameras.find(c => c.id === id) || null;
    }
    return apiClient.get(`/devices/cameras/${id}`);
  },

  async toggleCamera(id) {
    if (isMockEnabled('cameras')) {
      const cam = initialCameras.find(c => c.id === id);
      if (cam) {
        const isOnline = cam.status === 'Online';
        cam.status = isOnline ? 'Disabled' : 'Online';
        cam.activeDetections = !isOnline;
      }
      return { success: true, id };
    }
    return apiClient.post(`/devices/cameras/${id}/toggle`);
  },

  async updateCamera(id, updatedFields) {
    if (isMockEnabled('cameras')) {
      const cam = initialCameras.find(c => c.id === id);
      if (cam) {
        Object.assign(cam, updatedFields);
      }
      return { success: true, ...cam };
    }
    return apiClient.patch(`/devices/cameras/${id}`, updatedFields);
  },

  async addCamera(newCam) {
    if (isMockEnabled('cameras')) {
      initialCameras.push(newCam);
      return { success: true, ...newCam };
    }
    return apiClient.post('/devices/cameras', newCam);
  }
};

export default cameraService;
