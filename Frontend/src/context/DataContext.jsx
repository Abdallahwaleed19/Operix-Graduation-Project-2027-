import React, { createContext, useContext, useState, useEffect } from 'react';
import {
  initialFactory,
  initialMetrics,
  initialIncidents,
  initialCameras,
  initialSensors,
  initialRules,
  initialUsers,
  initialNotificationTargets,
  initialReports
} from '../data/mockData';
import {
  incidentService,
  cameraService,
  sensorService,
  ruleService,
  userService,
  factoryService,
  reportService,
  analyticsService
} from '../services';
import { API_CONFIG } from '../services/apiClient';

const DataContext = createContext();

const EMPTY_FACTORY = {
  name: 'Plant 1 · Menoufia',
  shift: 'Day Shift',
  timezone: 'Africa/Cairo',
};

const EMPTY_METRICS = {
  activeIncidents: 0,
  activeIncidentsDelta: '',
  ppeCompliance: '0%',
  ppeComplianceDelta: '',
  workersOnFloor: 0,
  workersScheduled: 0,
  avgResponse: '—',
  avgResponseDelta: '',
};

const unwrapList = (val) => (Array.isArray(val) ? val : (val?.items || []));

export function DataProvider({ children }) {
  const useMock = API_CONFIG.useMock;
  const [factory, setFactory] = useState(useMock ? initialFactory : EMPTY_FACTORY);
  const [metrics, setMetrics] = useState(useMock ? initialMetrics : EMPTY_METRICS);
  const [incidents, setIncidents] = useState(useMock ? initialIncidents : []);
  const [cameras, setCameras] = useState(useMock ? initialCameras : []);
  const [sensors, setSensors] = useState(useMock ? initialSensors : []);
  const [rules, setRules] = useState(useMock ? initialRules : []);
  const [users, setUsers] = useState(useMock ? initialUsers : []);
  const [notificationTargets, setNotificationTargets] = useState(useMock ? initialNotificationTargets : []);
  const [reports, setReports] = useState(useMock ? initialReports : []);
  const [isLoading, setIsLoading] = useState(false);

  // Synchronize data via the centralized service layer on mount
  useEffect(() => {
    let isMounted = true;
    async function syncServices() {
      const token = typeof localStorage !== 'undefined' ? localStorage.getItem('operix_token') : null;
      if (!useMock && !token) {
        return;
      }
      try {
        const results = await Promise.allSettled([
          factoryService.getFactorySettings(),
          analyticsService.getOverviewMetrics(),
          incidentService.getIncidents(),
          cameraService.getCameras(),
          sensorService.getSensors(),
          ruleService.getRules(),
          userService.getUsers(),
          factoryService.getNotificationTargets(),
          reportService.getReports()
        ]);

        if (!isMounted) return;
        const [factRes, metRes, incRes, camRes, senRes, rulRes, usrRes, notRes, repRes] = results;
        if (factRes.status === 'fulfilled' && factRes.value) setFactory(factRes.value);
        if (metRes.status === 'fulfilled' && metRes.value) setMetrics(metRes.value);
        if (incRes.status === 'fulfilled' && incRes.value) setIncidents(unwrapList(incRes.value));
        if (camRes.status === 'fulfilled' && camRes.value) setCameras(unwrapList(camRes.value));
        if (senRes.status === 'fulfilled' && senRes.value) setSensors(unwrapList(senRes.value));
        if (rulRes.status === 'fulfilled' && rulRes.value) setRules(unwrapList(rulRes.value));
        if (usrRes.status === 'fulfilled' && usrRes.value) setUsers(unwrapList(usrRes.value));
        if (notRes.status === 'fulfilled' && notRes.value) setNotificationTargets(unwrapList(notRes.value));
        if (repRes.status === 'fulfilled' && repRes.value) setReports(unwrapList(repRes.value));
      } catch (err) {
        console.warn('Data sync via services warning:', err);
      }
    }

    syncServices();
    return () => { isMounted = false; };
  }, [useMock]);

  // Incident methods
  const resolveIncident = async (id) => {
    await incidentService.resolveIncident(id);
    setIncidents(prev =>
      prev.map(inc => {
        if (inc.id === id) {
          return {
            ...inc,
            status: 'Resolved',
            auditTrail: [
              ...inc.auditTrail,
              {
                time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                text: 'Resolved by user',
                detail: 'Marked as resolved in dashboard'
              }
            ]
          };
        }
        return inc;
      })
    );
  };

  // Camera methods
  const toggleCamera = async (id) => {
    await cameraService.toggleCamera(id);
    setCameras(prev =>
      prev.map(cam => {
        if (cam.id === id) {
          const isOnline = cam.status === 'Online';
          return {
            ...cam,
            status: isOnline ? 'Disabled' : 'Online',
            activeDetections: !isOnline
          };
        }
        return cam;
      })
    );
  };

  const updateCamera = async (id, updatedFields) => {
    await cameraService.updateCamera(id, updatedFields);
    setCameras(prev =>
      prev.map(cam => (cam.id === id ? { ...cam, ...updatedFields } : cam))
    );
  };

  const addCamera = async (newCam) => {
    await cameraService.addCamera(newCam);
    setCameras(prev => [...prev, newCam]);
  };

  // Sensor methods
  const toggleSensor = async (id) => {
    await sensorService.toggleSensor(id);
    setSensors(prev =>
      prev.map(sen => {
        if (sen.id === id) {
          const isOnline = sen.status === 'Online';
          return {
            ...sen,
            status: isOnline ? 'Disabled' : 'Online',
            active: !isOnline
          };
        }
        return sen;
      })
    );
  };

  const updateSensor = async (id, updatedFields) => {
    await sensorService.updateSensor(id, updatedFields);
    setSensors(prev =>
      prev.map(sen => (sen.id === id ? { ...sen, ...updatedFields } : sen))
    );
  };

  // Rule methods
  const toggleRule = async (id) => {
    const current = rules.find(r => r.id === id);
    const currentStatus = current ? (current.enabled ?? current.is_enabled) : false;
    await ruleService.toggleRule(id, currentStatus);
    setRules(prev =>
      prev.map(r => (r.id === id ? { ...r, enabled: !currentStatus, is_enabled: !currentStatus } : r))
    );
  };

  const updateRule = async (id, updatedFields) => {
    await ruleService.updateRule(id, updatedFields);
    setRules(prev =>
      prev.map(r => (r.id === id ? { ...r, ...updatedFields } : r))
    );
  };

  const deleteRule = async (id) => {
    await ruleService.deleteRule(id);
    setRules(prev => prev.filter(r => r.id !== id));
  };

  // User methods
  const toggleUserAccess = async (id) => {
    const current = users.find(u => u.id === id);
    const updated = await userService.toggleUserAccess(id, current);
    setUsers(prev =>
      prev.map(u => {
        if (u.id === id) {
          if (updated && updated.id) return updated;
          const isActive = u.access === 'Active';
          return {
            ...u,
            access: isActive ? 'Inactive' : 'Active',
            status: isActive ? 'Disabled' : 'Active'
          };
        }
        return u;
      })
    );
  };

  const inviteUser = async (user) => {
    const res = await userService.inviteUser(user);
    setUsers(prev => [res, ...prev]);
    return res;
  };

  const updateUserRole = async (id, newRole) => {
    const updated = await userService.updateUserRole(id, newRole);
    setUsers(prev =>
      prev.map(u => (u.id === id ? (updated?.id ? updated : { ...u, role: newRole }) : u))
    );
  };

  const deleteUser = async (id) => {
    await userService.deleteUser(id);
    setUsers(prev => prev.filter(u => u.id !== id));
  };

  // Notification target methods
  const toggleNotificationTarget = async (id) => {
    await factoryService.toggleNotificationTarget(id);
    setNotificationTargets(prev =>
      prev.map(t => (t.id === id ? { ...t, enabled: !t.enabled } : t))
    );
  };

  const removeNotificationTarget = async (id) => {
    await factoryService.removeNotificationTarget(id);
    setNotificationTargets(prev => prev.filter(t => t.id !== id));
  };

  const addNotificationTarget = async (target) => {
    const res = await factoryService.addNotificationTarget(target);
    setNotificationTargets(prev => [
      ...prev,
      res
    ]);
  };

  // Factory Settings
  const updateFactorySettings = async (settings) => {
    await factoryService.updateFactorySettings(settings);
    setFactory(prev => ({ ...prev, ...settings }));
  };

  return (
    <DataContext.Provider
      value={{
        factory,
        metrics,
        incidents,
        resolveIncident,
        cameras,
        toggleCamera,
        updateCamera,
        addCamera,
        sensors,
        toggleSensor,
        updateSensor,
        rules,
        toggleRule,
        updateRule,
        deleteRule,
        users,
        toggleUserAccess,
        inviteUser,
        updateUserRole,
        deleteUser,
        notificationTargets,
        toggleNotificationTarget,
        removeNotificationTarget,
        addNotificationTarget,
        reports,
        updateFactorySettings,
        isLoading
      }}
    >
      {children}
    </DataContext.Provider>
  );
}

export function useData() {
  const context = useContext(DataContext);
  if (!context) {
    throw new Error('useData must be used within a DataProvider');
  }
  return context;
}
