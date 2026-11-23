// Mock data representing the live Operix Industrial AI platform

export const initialFactory = {
  name: "Plant 1",
  slug: "plant-1",
  shift: "Monday shift, 06:00 – 14:00",
  timezone: "Africa/Cairo (UTC+02:00)",
  evidenceRetentionDays: 30,
  status: "Active",
  departments: ["Production", "Storage", "Security"],
  sourcesTotal: 24,
  sourcesOnline: 24,
};

export const initialMetrics = {
  activeIncidents: 7,
  activeIncidentsDelta: "▲ 2 since 08:00",
  ppeCompliance: "94.2%",
  ppeComplianceDelta: "▲ 1.8% vs yesterday",
  workersOnFloor: 186,
  workersScheduled: 204,
  avgResponse: "2m 14s",
  avgResponseDelta: "▼ 31s faster",
};

export const initialIncidents = [
  {
    id: "INC-2041",
    event: "Missing helmet",
    location: "Zone B · Press Line",
    camera: "CAM-04 · Zone B · Press Line",
    severity: "High",
    status: "Pending Alert",
    timestamp: "09:42:03",
    date: "Today",
    workerId: "Worker #14",
    workerStatus: "No helmet",
    peerWorker: "Worker #22 · PPE OK",
    auditTrail: [
      { time: "09:42:03", text: "Detected", detail: "Vision AI" },
      { time: "09:42:05", text: "Classified as High", detail: "Helmet policy" },
      { time: "09:42:08", text: "Alert sent via WhatsApp, SMS, Telegram", detail: "Safety team notified" }
    ]
  },
  {
    id: "INC-2040",
    event: "Restricted-zone entry",
    location: "Zone D · Furnace",
    camera: "CAM-07 · Furnace",
    severity: "High",
    status: "Dispatched",
    timestamp: "09:18:22",
    date: "Today",
    workerId: "Worker #09",
    workerStatus: "Restricted zone",
    peerWorker: "Authorized crew",
    auditTrail: [
      { time: "09:18:22", text: "Detected", detail: "Vision AI Zone Geofence" },
      { time: "09:18:24", text: "Classified as High", detail: "Restricted Zone Policy" },
      { time: "09:18:26", text: "Security dispatched", detail: "Floor beacon triggered" }
    ]
  },
  {
    id: "INC-2039",
    event: "Fatigue signs",
    location: "Zone A · Assembly",
    camera: "CAM-02 · Assembly",
    severity: "Medium",
    status: "Under Review",
    timestamp: "08:55:10",
    date: "Today",
    workerId: "Worker #07",
    workerStatus: "Fatigue",
    peerWorker: "Assembly Line 2",
    auditTrail: [
      { time: "08:55:10", text: "Detected", detail: "Posture & Micro-pause Analysis" },
      { time: "08:55:12", text: "Classified as Medium", detail: "Fatigue score 84%" },
      { time: "08:55:15", text: "Flagged for Shift Supervisor review", detail: "In queue" }
    ]
  },
  {
    id: "INC-2038",
    event: "Abnormal temperature",
    location: "Zone F · Boiler",
    camera: "THM-01 · Boiler",
    severity: "High",
    status: "Resolved",
    timestamp: "08:31:04",
    date: "Today",
    workerId: "Radiometric Sensor",
    workerStatus: "92°C Boiler Core",
    peerWorker: "Threshold 74°C",
    auditTrail: [
      { time: "08:31:04", text: "Detected", detail: "Thermal camera THM-01" },
      { time: "08:31:06", text: "Exceeded threshold 74°C (Hit 92°C)", detail: "High priority" },
      { time: "08:36:12", text: "Coolant valve engaged automatically", detail: "Resolved" }
    ]
  },
  {
    id: "INC-2037",
    event: "Missing vest",
    location: "Zone C · Loading",
    camera: "CAM-09 · Loading",
    severity: "Low",
    status: "Resolved",
    timestamp: "08:12:45",
    date: "Today",
    workerId: "Worker #44",
    workerStatus: "No vest",
    peerWorker: "Worker #52 · PPE OK",
    auditTrail: [
      { time: "08:12:45", text: "Detected", detail: "Vision AI Hi-Vis detector" },
      { time: "08:12:50", text: "Supervisor warned worker", detail: "Vest provided on site" },
      { time: "08:14:02", text: "Resolved by Safety Supervisor", detail: "Closed" }
    ]
  },
  {
    id: "INC-2036",
    event: "Blocked emergency exit",
    location: "Zone B · Press Line",
    camera: "CAM-04 · Press Line",
    severity: "High",
    status: "Resolved",
    timestamp: "07:45:11",
    date: "Today",
    workerId: "Forklift #3",
    workerStatus: "Obstruction",
    peerWorker: "Zone B North Exit",
    auditTrail: [
      { time: "07:45:11", text: "Detected", detail: "Object recognition on pathway" },
      { time: "07:49:00", text: "Pallet moved by operator", detail: "Pathway clear" }
    ]
  },
  {
    id: "INC-2035",
    event: "Speeding forklift",
    location: "Zone C · Loading",
    camera: "CAM-09 · Loading",
    severity: "Medium",
    status: "Resolved",
    timestamp: "07:12:30",
    date: "Today",
    workerId: "Forklift #1",
    workerStatus: "18 km/h in 10 km/h zone",
    peerWorker: "Zone C Corridor",
    auditTrail: [
      { time: "07:12:30", text: "Detected", detail: "Velocity tracking AI" },
      { time: "07:15:00", text: "Speed warning broadcasted", detail: "Resolved" }
    ]
  }
];

export const initialCameras = [
  {
    id: "CAM-01",
    name: "CAM-01 · Gate",
    department: "Security",
    type: "CCTV",
    location: "Main entrance",
    zones: 1,
    status: "Online",
    streamUrl: "rtsp://10.0.1.10:554/stream1",
    activeDetections: true,
    lastChecked: "Online · 08:12 today"
  },
  {
    id: "CAM-04",
    name: "CAM-04 · Press Line",
    department: "Production",
    type: "CCTV",
    location: "Press hall",
    zones: 2,
    status: "Online",
    streamUrl: "rtsp://10.0.4.24:554/stream1",
    activeDetections: true,
    lastChecked: "Online · 08:12 today"
  },
  {
    id: "CAM-07",
    name: "CAM-07 · Furnace",
    department: "Production",
    type: "CCTV",
    location: "Furnace bay",
    zones: 1,
    status: "Online",
    streamUrl: "rtsp://10.0.7.12:554/stream1",
    activeDetections: true,
    lastChecked: "Online · 08:12 today"
  },
  {
    id: "CAM-09",
    name: "CAM-09 · Loading",
    department: "—",
    type: "CCTV",
    location: "Loading dock",
    zones: 0,
    status: "Disabled",
    streamUrl: "rtsp://10.0.9.15:554/stream1",
    activeDetections: false,
    lastChecked: "Disabled"
  },
  {
    id: "THM-01",
    name: "THM-01 · Boiler",
    department: "Production",
    type: "Thermal",
    location: "Boiler room",
    zones: 1,
    status: "Online",
    streamUrl: "rtsp://10.0.1.8:554/stream1",
    activeDetections: true,
    lastChecked: "Online · 08:12 today"
  },
  {
    id: "CAM-12",
    name: "CAM-12 · Yard",
    department: "Storage",
    type: "CCTV",
    location: "North yard",
    zones: 0,
    status: "Offline",
    streamUrl: "rtsp://10.0.12.3:554/stream1",
    activeDetections: false,
    lastChecked: "Offline · 06:40 today"
  }
];

export const initialSensors = [
  {
    id: "TMP-01",
    name: "TMP-01 · Boiler",
    department: "Production",
    type: "Temperature",
    unit: "°C",
    sampling: "every 10 s",
    samplingSeconds: 10,
    location: "Boiler room",
    status: "Online",
    deviceKey: "•••••••••••• (stored as a hash)",
    active: true,
    lastReading: "92.0 °C · 09:42"
  },
  {
    id: "TMP-02",
    name: "TMP-02 · Furnace",
    department: "Production",
    type: "Temperature",
    unit: "°C",
    sampling: "every 10 s",
    samplingSeconds: 10,
    location: "Furnace bay",
    status: "Online",
    deviceKey: "•••••••••••• (stored as a hash)",
    active: true,
    lastReading: "74.0 °C · 09:40"
  },
  {
    id: "TMP-05",
    name: "TMP-05 · Storage",
    department: "Storage",
    type: "Temperature",
    unit: "°C",
    sampling: "every 30 s",
    samplingSeconds: 30,
    location: "Cold warehouse",
    status: "Online",
    deviceKey: "•••••••••••• (stored as a hash)",
    active: true,
    lastReading: "31.0 °C · 09:35"
  },
  {
    id: "TMP-07",
    name: "TMP-07 · Furnace",
    department: "Production",
    type: "Temperature",
    unit: "°C",
    sampling: "every 10 s",
    samplingSeconds: 10,
    location: "Furnace bay",
    status: "Offline",
    deviceKey: "•••••••••••• (stored as a hash)",
    active: true,
    lastReading: "71.4 °C · 06:39"
  },
  {
    id: "TMP-09",
    name: "TMP-09 · Gate",
    department: "Security",
    type: "Temperature",
    unit: "°C",
    sampling: "every 60 s",
    samplingSeconds: 60,
    location: "Gate station",
    status: "Disabled",
    deviceKey: "•••••••••••• (stored as a hash)",
    active: false,
    lastReading: "24.0 °C · yesterday"
  }
];

export const initialRules = [
  {
    id: "RULE-01",
    name: "Helmet compliance",
    enabled: true,
    version: 3,
    ifDetection: {
      eventType: "Helmet missing",
      severity: "High",
      minConfidence: 0.80,
      minDuration: 5,
      thresholdValue: "—"
    },
    inScope: {
      zone: "Zone B · Press Line",
      department: "Any",
      sensor: "None"
    },
    thenResult: {
      notify: true,
      channels: "Notify safety supervisor",
      createAlert: true
    }
  },
  {
    id: "RULE-02",
    name: "Restricted access",
    enabled: true,
    version: 2,
    ifDetection: {
      eventType: "Unauthorized worker detected",
      severity: "High",
      minConfidence: 0.85,
      minDuration: 1,
      thresholdValue: "Zone D Perimeter"
    },
    inScope: {
      zone: "Zone D · Restricted",
      department: "Production",
      sensor: "None"
    },
    thenResult: {
      notify: true,
      channels: "WhatsApp + SMS + Telegram",
      createAlert: true
    }
  },
  {
    id: "RULE-03",
    name: "Fatigue prevention",
    enabled: false,
    version: 1,
    ifDetection: {
      eventType: "Fatigue score > 80%",
      severity: "Medium",
      minConfidence: 0.75,
      minDuration: 15,
      thresholdValue: "80%"
    },
    inScope: {
      zone: "Zone A · Assembly",
      department: "Production",
      sensor: "None"
    },
    thenResult: {
      notify: true,
      channels: "Create incident for review",
      createAlert: true
    }
  }
];

export const initialUsers = [
  {
    id: "usr-1",
    name: "Mona Hassan",
    email: "mona@plant1.example",
    role: "Administrator",
    status: "Active",
    access: "Active"
  },
  {
    id: "usr-2",
    name: "Omar Khaled",
    email: "omar@plant1.example",
    role: "Safety Supervisor",
    status: "Active",
    access: "Active"
  },
  {
    id: "usr-3",
    name: "Sara Nabil",
    email: "sara@plant1.example",
    role: "Factory Manager",
    status: "Active",
    access: "Active"
  },
  {
    id: "usr-4",
    name: "Youssef Adel",
    email: "youssef@plant1.example",
    role: "Viewer",
    status: "Invited",
    access: "Inactive"
  }
];

export const initialNotificationTargets = [
  {
    id: "notif-1",
    label: "Safety supervisor",
    channel: "WhatsApp",
    address: "+20 •• ••• ••82",
    minSeverity: "High",
    enabled: true
  },
  {
    id: "notif-2",
    label: "Plant manager",
    channel: "Email",
    address: "manager@plant1.example",
    minSeverity: "Critical",
    enabled: true
  },
  {
    id: "notif-3",
    label: "Ops channel",
    channel: "Telegram",
    address: "@operix_ops",
    minSeverity: "Medium",
    enabled: false
  }
];

export const roleMatrixData = [
  { code: "dashboard.view", description: "Dashboard", admin: true, manager: true, supervisor: true, viewer: true },
  { code: "monitoring.view", description: "Live monitoring", admin: true, manager: true, supervisor: true, viewer: true },
  { code: "incident.view", description: "View incidents", admin: true, manager: true, supervisor: true, viewer: true },
  { code: "incident.resolve", description: "Review and resolve", admin: true, manager: true, supervisor: true, viewer: false },
  { code: "evidence.view", description: "Open evidence files", admin: true, manager: true, supervisor: true, viewer: false },
  { code: "analytics.view", description: "Workforce, heatmaps, thermal", admin: true, manager: true, supervisor: true, viewer: false },
  { code: "report.view", description: "Reports", admin: true, manager: true, supervisor: true, viewer: true },
  { code: "rule.manage", description: "Safety rules and zones", admin: true, manager: true, supervisor: false, viewer: false },
  { code: "device.manage", description: "Cameras and sensors", admin: true, manager: true, supervisor: false, viewer: false },
  { code: "notification.manage", description: "Notification targets", admin: true, manager: true, supervisor: false, viewer: false },
  { code: "user.manage", description: "Users and roles", admin: true, manager: false, supervisor: false, viewer: false },
  { code: "factory.manage", description: "Factory settings", admin: true, manager: false, supervisor: false, viewer: false },
];

export const initialReports = [
  {
    id: "rep-1",
    title: "Weekly safety summary",
    description: "Incidents, compliance and response performance",
    period: "Nov 8 – 14",
    format: "PDF",
    size: "2.4 MB"
  },
  {
    id: "rep-2",
    title: "Workforce hours",
    description: "Net hours, idle time and departmental activity",
    period: "October",
    format: "XLSX",
    size: "840 KB"
  },
  {
    id: "rep-3",
    title: "Incident evidence pack",
    description: "Snapshots, audit trail and alert delivery records",
    period: "INC-2038",
    format: "ZIP",
    size: "14.8 MB"
  }
];

export const initialTrackedWorkers = [
  {
    id: 'WORKER #14',
    route: 'CAM-04 → CAM-02',
    status: 'Helmet violation · 09:42',
    statusType: 'danger'
  },
  {
    id: 'WORKER #22',
    route: 'CAM-01 → CAM-09',
    status: 'PPE compliant · 09:40',
    statusType: 'success'
  },
  {
    id: 'WORKER #07',
    route: 'CAM-02',
    status: 'Fatigue flag · 08:55',
    statusType: 'warning'
  }
];

export const initialThermalReadings = [
  { label: 'Boiler core', temp: '92°C', percent: 92, status: 'danger', color: '#EF4444' },
  { label: 'Press motor', temp: '68°C', percent: 68, status: 'warning', color: '#D97706' },
  { label: 'Furnace wall', temp: '74°C', percent: 74, status: 'warning', color: '#D97706' },
  { label: 'Storage', temp: '31°C', percent: 31, status: 'success', color: '#10B981' }
];

export const initialQuickPrompts = [
  'How many helmet violations today?',
  'Which zone has most idle time?',
  'Summarize this week'
];

export const initialWorkforceDepartments = [
  { name: 'Assembly', hours: 356, heightPercent: 89 },
  { name: 'Press', hours: 298, heightPercent: 74 },
  { name: 'Paint', hours: 246, heightPercent: 61 },
  { name: 'Store', hours: 204, heightPercent: 51 },
  { name: 'QA', hours: 180, heightPercent: 45 }
];

export const initialIdleTimeZones = [
  { name: 'Zone A', percent: 18, isHigh: false },
  { name: 'Zone B', percent: 9, isHigh: false },
  { name: 'Zone C', percent: 24, isHigh: true },
  { name: 'Zone D', percent: 6, isHigh: false }
];

export const initialWorkforceMetrics = {
  netHours: "1,284 h",
  netHoursDelta: "▲ 3.1% vs last week",
  idleTime: "11.6%",
  idleTimeDelta: "▼ 0.9% vs last week",
  avgBreak: "42 min",
  avgBreakDelta: "within policy",
  fatigueFlags: "9",
  fatigueFlagsDelta: "▲ 3 today"
};

export const initialShiftIncidents = [
  { time: '06:00', count: 4 },
  { time: '07:00', count: 6 },
  { time: '08:00', count: 5 },
  { time: '09:00', count: 8 },
  { time: '10:00', count: 12 },
  { time: '11:00', count: 6 },
  { time: '12:00', count: 6 },
  { time: '13:00', count: 10 },
  { time: '14:00', count: 7 }
];
