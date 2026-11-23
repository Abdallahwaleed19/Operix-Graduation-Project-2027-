/**
 * Operix Centralized Services Layer
 * 
 * Aggregates all domain API services for easy import across components and hooks.
 * Connecting to the FastAPI backend requires zero changes to UI components.
 */

export { apiClient, API_CONFIG } from './apiClient';
export { incidentService } from './incidentService';
export { cameraService } from './cameraService';
export { sensorService } from './sensorService';
export { ruleService } from './ruleService';
export { userService } from './userService';
export { analyticsService } from './analyticsService';
export { reportService } from './reportService';
export { assistantService } from './assistantService';
export { factoryService } from './factoryService';
export { authService } from './authService';
