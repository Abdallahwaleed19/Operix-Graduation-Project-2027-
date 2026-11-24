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

const DataContext = createContext();

export function DataProvider({ children }) {
  const [factory, setFactory] = useState(initialFactory);
  const [metrics, setMetrics] = useState(initialMetrics);
  const [incidents, setIncidents] = useState(initialIncidents);
  const [cameras, setCameras] = useState(initialCameras);
  const [sensors, setSensors] = useState(initialSensors);
  const [rules, setRules] = useState(initialRules);
  const [users, setUsers] = useState(initialUsers);
  const [notificationTargets, setNotificationTargets] = useState(initialNotificationTargets);
  const [reports, setReports] = useState(initialReports);
  const [isLoading, setIsLoading] = useState(false);

  // Synchronize data via the centralized service layer on mount
  useEffect(() => {
    let isMounted = true;
    async function syncServices() {
      try {
        const [
          factData,
          metData,
          incData,
          camData,
          senData,
          rulData,
          usrData,
          notData,
          repData
        ] = await Promise.all([
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

        if (isMounted) {
          if (factData) setFactory(factData);
          if (metData) setMetrics(metData);
          if (incData) setIncidents(incData);
          if (camData) setCameras(camData);
          if (senData) setSensors(senData);
          if (rulData) setRules(rulData);
          if (usrData) setUsers(usrData);
          if (notData) setNotificationTargets(notData);
          if (repData) setReports(repData);
        }
      } catch (err) {
        console.warn('Data sync via services warning:', err);
      }
    }

    syncServices();
    return () => { isMounted = false; };
  }, []);

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
    await userService.toggleUserAccess(id);
    setUsers(prev =>
      prev.map(u => {
        if (u.id === id) {
          const isActive = u.access === 'Active';
          return {
            ...u,
            access: isActive ? 'Inactive' : 'Active',
            status: isActive ? 'Inactive' : 'Active'
          };
        }
        return u;
      })
    );
  };

  const inviteUser = async (user) => {
    const res = await userService.inviteUser(user);
    setUsers(prev => [
      ...prev,
      res
    ]);
  };

  const updateUserRole = async (id, newRole) => {
    await userService.updateUserRole(id, newRole);
    setUsers(prev =>
      prev.map(u => (u.id === id ? { ...u, role: newRole } : u))
    );
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
