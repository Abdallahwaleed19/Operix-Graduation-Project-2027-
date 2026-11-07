%% ==========================================
%% 1. SEQUENCE DIAGRAM (تسلسل معالجة الفيديو والأحداث)
%% ==========================================
sequenceDiagram
    autonumber
    actor CCTV as CCTV Camera
    participant Ingestion as Video Ingestion
    participant AI as AI Analysis
    participant Rules as Rules Engine
    participant AlertStorage as Alert & Storage
    participant Dashboard as Dashboard
    participant StreamCheck as Check Stream
    participant ViolCheck as Check Violation
    participant QueryCheck as Check Manager Query

    CCTV->>Ingestion: Stream live video
    activate Ingestion
    Ingestion->>Ingestion: Receive video stream
    Ingestion->>Ingestion: Extract frames
    Ingestion->>Ingestion: Add metadata
    Ingestion->>Ingestion: Send to queue
    deactivate Ingestion

    alt [Stream Available?]
        StreamCheck-->>Ingestion: Yes
    else [Stream Unavailable]
        StreamCheck-->>Ingestion: No
        AlertStorage->>AlertStorage: Mark 'Unobserved gap'
    end

    par [Parallel Detection]
        Ingestion->>AI: Send frame batch
        activate AI
        AI->>AI: Detect workers & PPE
        AI->>AI: Track workers
        AI->>AI: Record position
        deactivate AI
    end

    AI->>Rules: Match position to zone
    activate Rules
    Rules->>Rules: Apply zone rules
    Rules->>Rules: Evaluate compliance
    deactivate Rules

    alt [Violation Detected]
        ViolCheck-->>Rules: Yes
        Rules->>AlertStorage: Save event
        AlertStorage->>AlertStorage: Feature evidence
        AlertStorage->>AlertStorage: Send alert
    else [Compliant]
        ViolCheck-->>Rules: No
    end

    AlertStorage->>AlertStorage: Calculate working hours
    AlertStorage->>Dashboard: Display evidence
    AlertStorage->>Dashboard: Show alerts
    AlertStorage->>Dashboard: Display working hours
    AlertStorage->>Dashboard: Show heatmaps

    alt [Manager Has Question?]
        QueryCheck-->>Dashboard: Yes
        Dashboard->>Dashboard: Query AI Assistant
        Dashboard->>Dashboard: Retrieve records
        Dashboard->>Dashboard: Display answer
    else [No Question]
        QueryCheck-->>Dashboard: No
    end

%% ==========================================
%% 2. STATE DIAGRAM (دورة حياة حالة العامل)
%% ==========================================
stateDiagram-v2
    [*] --> Detected
    Detected --> Tracked: trackIDAssigned

    state Present {
        [*] --> rulesEvaluated
        rulesEvaluated --> accumulateWorkingTime: [allRulesSatisfied] / do

        state accumulateWorkingTime {
            accumulateWorkingTime --> Warning: minorBreachDetected /
            Warning --> accumulateWorkingTime: workerCorrectsBehavior /
            
            accumulateWorkingTime --> accumulateIdleTime: noActivityDetected [idleThresholdReached] / do
            accumulateIdleTime --> accumulateWorkingTime: activityResumes /

            accumulateWorkingTime --> pauseWorkingTime: breakTimeStarts [approvedBreak] / do
            pauseWorkingTime --> accumulateWorkingTime: breakTimeEnds / resumeWorkingTime
        }

        Warning --> sendAlert: breachContinues [durationExceedsLimit] / entry / saveEvidenceSnapshot, sendAlert
        sendAlert --> accumulateWorkingTime: workerCorrectsBehavior /
    }

    Present --> markTimeAsUnobserved: streamLostOrBlocked / entry
    markTimeAsUnobserved --> Tracked: streamRestored
    markTimeAsUnobserved --> Exited: workerLeavesArea

    Present --> Exited: workerLeavesArea
    Exited --> [*]

%% ==========================================
%% 3. SYSTEM ARCHITECTURE & TOOLS DIAGRAM (المعمارية البرمجية)
%% ==========================================
graph LR
    subgraph DE ["Data Engineering (RTSP • Message Queue • PostgreSQL)"]
        DE_Resp["<b>Responsibilities</b><br/>• Ingest live CCTV streams<br/>• Extract frames & metadata<br/>• Buffer in message queue<br/>• Store events & evidence<br/>• Calculate net working hours<br/>• Mark unobserved gaps"]
    end

    subgraph CV ["Computer Vision (YOLOv8/v9 • MediaPipe/OpenPose • ByteTrack/DeepSORT • KDE)"]
        CV_Resp["<b>Responsibilities</b><br/>• Detect workers & PPE<br/>• Estimate body pose<br/>• Track with Track ID<br/>• Record foot positions<br/>• Generate heatmaps<br/>• Unobserved interval log"]
    end

    subgraph BR ["Backend & Rules (FastAPI • WebSockets • PostgreSQL)"]
        BR_Resp["<b>Responsibilities</b><br/>• Match worker to zone<br/>• Apply safety rules<br/>• Classify status<br/>• Filter alerts<br/>• Route by severity<br/>• Real-time notifications"]
    end

    subgraph AI_Ast ["AI Assistant (LLM • Database Query Layer)"]
        AI_Resp["<b>Responsibilities</b><br/>• Natural language Q&A<br/>• Database retrieval<br/>• Operations summaries"]
    end

    subgraph FD ["Frontend Dashboard (React • WebSockets)"]
        FD_Resp["<b>Responsibilities</b><br/>• Live attendance alerts<br/>• Net hours reports<br/>• Department statistics<br/>• Interactive heatmaps<br/>• Violation review<br/>• Incident history"]
    end

    DE -->|Frames + metadata| CV
    CV -->|Tracked workers + pose| BR
    BR -->|Alerts & notifications| FD
    BR -->|Database access| AI_Ast
    AI_Ast -->|Signals| FD

%% ==========================================
%% 4. USE CASE DIAGRAM (حالات الاستخدام حسب أدوار المستخدمين)
%% ==========================================
graph TD
    subgraph Actors ["المستخدمون / Actors"]
        Executive["Executive Manager"]
        DeptManager["Department Manager"]
        SafetyOfficer["Safety Officer"]
        SysAdmin["System Administrator"]
    end

    subgraph Executive_UC ["Executive View"]
        E1["Cross-Site Overview"]
        E2["Executive Summaries"]
        E3["Access All Analytics"]
        E4["Access Multi-Department Attendance"]
    end

    subgraph Dept_UC ["Department Management"]
        D1["Monitor Worker Attendance"]
        D2["Assign Shifts & Breaks"]
        D3["View Department Heatmaps"]
        D4["Filter Department Reports"]
        D5["Query AI Operations Assistant"]
    end

    subgraph Safety_UC ["Safety Management"]
        S1["Configure Safety Rules"]
        S2["Review Safety Snapshots"]
    end

    subgraph Admin_UC ["System Administration"]
        A1["Configure Site & Department Zones"]
        A2["Assign Cameras to Zones"]
        A3["Manage User Roles"]
        A4["Manage System Settings"]
        A5["Check Stream Health & Logs"]
    end

    Executive --> E1
    Executive --> E2
    Executive --> E3
    Executive --> E4

    DeptManager --> D1
    DeptManager --> D2
    DeptManager --> D3
    DeptManager --> D4
    DeptManager --> D5

    SafetyOfficer --> S1
    SafetyOfficer --> S2

    SysAdmin --> A1
    SysAdmin --> A2
    SysAdmin --> A3
    SysAdmin --> A4
    SysAdmin --> A5
