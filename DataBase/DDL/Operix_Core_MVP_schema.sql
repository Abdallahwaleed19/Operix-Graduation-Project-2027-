-- =============================================================================
-- Operix - Core MVP database (PostgreSQL 16+)        PRELIMINARY / reviewable
-- Companion to Operix_Core_MVP_ERD.svg
--
-- Conventions
--   * Keys are UUID (gen_random_uuid(); switch the default to uuidv7() on PG 18+
--     for time-ordered keys). Time columns are timestamptz (UTC).
--   * Multi-tenancy = shared schema. Every tenant-owned table carries
--     factory_id NOT NULL. Every parent exposes UNIQUE (factory_id, id) and every
--     FK between tenant tables is COMPOSITE (factory_id, parent_id), so a child
--     can never reference a row that belongs to another factory.
--   * Row-Level Security (ENABLE + FORCE) is the second, independent guard.
--   * Items marked ASSUMPTION are design choices, not confirmed requirements.
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS citext;

-- ----------------------------------------------------------------------------- enums
CREATE TYPE factory_status        AS ENUM ('active', 'suspended');
CREATE TYPE user_status           AS ENUM ('invited', 'active', 'disabled');
CREATE TYPE token_purpose         AS ENUM ('activation', 'password_reset', 'refresh');
CREATE TYPE camera_type           AS ENUM ('cctv', 'thermal');                       -- ASSUMPTION: thermal cameras are cameras
CREATE TYPE sensor_type           AS ENUM ('temperature');
CREATE TYPE source_status         AS ENUM ('configured', 'connecting', 'available', 'unavailable', 'recovering'); -- State diagram (source lifecycle)
CREATE TYPE zone_type             AS ENUM ('restricted', 'ppe_required', 'monitored'); -- ASSUMPTION
CREATE TYPE event_type            AS ENUM ('ppe_violation', 'fall', 'restricted_zone_intrusion', 'potential_fatigue',
                                           'fire', 'smoke', 'temperature_anomaly', 'source_failure');
CREATE TYPE severity_level        AS ENUM ('low', 'medium', 'high', 'critical');     -- ASSUMPTION (documentation D22 still open)
CREATE TYPE incident_state        AS ENUM ('detected', 'classified', 'recorded', 'alert_pending',
                                           'alert_dispatched', 'under_review', 'resolved'); -- State diagram (incident lifecycle)
CREATE TYPE evidence_kind         AS ENUM ('snapshot', 'clip');
CREATE TYPE alert_status          AS ENUM ('pending', 'dispatched', 'failed');
CREATE TYPE notification_channel  AS ENUM ('dashboard', 'sms', 'whatsapp', 'telegram');
CREATE TYPE delivery_status       AS ENUM ('queued', 'sent', 'failed', 'abandoned');
CREATE TYPE gap_reason            AS ENUM ('stream_lost', 'camera_blocked', 'poor_quality', 'other');

-- ============================================================================= TENANT & ACCESS
CREATE TABLE factories (
    id                       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name                     varchar(120) NOT NULL,
    slug                     varchar(60)  NOT NULL UNIQUE,
    status                   factory_status NOT NULL DEFAULT 'active',
    timezone                 varchar(40)  NOT NULL DEFAULT 'UTC',
    evidence_retention_days  integer      NOT NULL DEFAULT 30 CHECK (evidence_retention_days > 0),
    created_at               timestamptz  NOT NULL DEFAULT now(),
    updated_at               timestamptz  NOT NULL DEFAULT now()
);

-- Global identity (a person can belong to several factories). Passwords are stored as
-- an Argon2id/bcrypt hash produced by the backend - never in clear text.
CREATE TABLE users (
    id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email                 citext       NOT NULL UNIQUE,
    password_hash         text         NOT NULL,
    full_name             varchar(120) NOT NULL,
    status                user_status  NOT NULL DEFAULT 'invited',
    is_platform_admin     boolean      NOT NULL DEFAULT false,   -- ASSUMPTION: Operix operators who onboard factories
    failed_login_count    smallint     NOT NULL DEFAULT 0,
    locked_until          timestamptz,
    last_login_at         timestamptz,
    activated_at          timestamptz,
    password_changed_at   timestamptz  NOT NULL DEFAULT now(),
    created_at            timestamptz  NOT NULL DEFAULT now(),
    CONSTRAINT users_active_has_activation CHECK (status <> 'active' OR activated_at IS NOT NULL)
);

-- Activation links, password resets and refresh tokens (only the SHA-256 hash is stored).
CREATE TABLE auth_tokens (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     uuid          NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    purpose     token_purpose NOT NULL,
    token_hash  char(64)      NOT NULL UNIQUE,
    expires_at  timestamptz   NOT NULL,
    used_at     timestamptz,
    revoked_at  timestamptz,
    created_at  timestamptz   NOT NULL DEFAULT now()
);
CREATE INDEX auth_tokens_user_idx ON auth_tokens (user_id, purpose) WHERE used_at IS NULL AND revoked_at IS NULL;

-- Global RBAC catalogues (system roles; per-factory custom roles are a future extension).
CREATE TABLE roles (
    id    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code  varchar(40)  NOT NULL UNIQUE,
    name  varchar(80)  NOT NULL
);
CREATE TABLE permissions (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code         varchar(60)  NOT NULL UNIQUE,
    description  varchar(200) NOT NULL
);
CREATE TABLE role_permissions (
    role_id        uuid NOT NULL REFERENCES roles (id) ON DELETE CASCADE,
    permission_id  uuid NOT NULL REFERENCES permissions (id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

-- User <-> factory membership with one role per factory (ASSUMPTION; multi-role is a later extension).
CREATE TABLE factory_memberships (
    factory_id  uuid NOT NULL REFERENCES factories (id) ON DELETE CASCADE,
    user_id     uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    role_id     uuid NOT NULL REFERENCES roles (id),
    is_active   boolean     NOT NULL DEFAULT true,
    created_at  timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (factory_id, user_id)
);
CREATE INDEX factory_memberships_user_idx ON factory_memberships (user_id);

-- ============================================================================= OPERATIONAL RESOURCES
CREATE TABLE departments (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    factory_id  uuid NOT NULL REFERENCES factories (id) ON DELETE CASCADE,
    name        varchar(100) NOT NULL,
    created_at  timestamptz  NOT NULL DEFAULT now(),
    UNIQUE (factory_id, id),
    UNIQUE (factory_id, name)
);

CREATE TABLE cameras (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    factory_id      uuid NOT NULL REFERENCES factories (id) ON DELETE CASCADE,
    department_id   uuid,
    name            varchar(100) NOT NULL,
    camera_type     camera_type  NOT NULL DEFAULT 'cctv',
    location_label  varchar(200),
    stream_url_ref  text         NOT NULL,         -- secret-store reference or encrypted RTSP URL, never a plain password
    status          source_status NOT NULL DEFAULT 'configured',
    status_since    timestamptz   NOT NULL DEFAULT now(),
    is_active       boolean       NOT NULL DEFAULT true,
    created_at      timestamptz   NOT NULL DEFAULT now(),
    updated_at      timestamptz   NOT NULL DEFAULT now(),
    UNIQUE (factory_id, id),
    UNIQUE (factory_id, name),
    FOREIGN KEY (factory_id, department_id) REFERENCES departments (factory_id, id) ON DELETE SET NULL (department_id)
);
CREATE INDEX cameras_status_idx ON cameras (factory_id, status);

CREATE TABLE sensors (
    id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    factory_id           uuid NOT NULL REFERENCES factories (id) ON DELETE CASCADE,
    department_id        uuid,
    name                 varchar(100) NOT NULL,
    sensor_type          sensor_type  NOT NULL DEFAULT 'temperature',
    unit                 varchar(8)   NOT NULL DEFAULT 'C',
    location_label       varchar(200),
    sampling_interval_s  integer      NOT NULL DEFAULT 60 CHECK (sampling_interval_s > 0),
    device_key_hash      char(64),                 -- hash of the device key used by the sensor gateway
    status               source_status NOT NULL DEFAULT 'configured',
    status_since         timestamptz   NOT NULL DEFAULT now(),
    is_active            boolean       NOT NULL DEFAULT true,
    created_at           timestamptz   NOT NULL DEFAULT now(),
    updated_at           timestamptz   NOT NULL DEFAULT now(),
    UNIQUE (factory_id, id),
    UNIQUE (factory_id, name),
    FOREIGN KEY (factory_id, department_id) REFERENCES departments (factory_id, id) ON DELETE SET NULL (department_id)
);

CREATE TABLE monitoring_zones (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    factory_id     uuid NOT NULL REFERENCES factories (id) ON DELETE CASCADE,
    camera_id      uuid NOT NULL,
    department_id  uuid,
    name           varchar(100) NOT NULL,
    zone_type      zone_type    NOT NULL,
    polygon        jsonb        NOT NULL,           -- normalised [[x,y],...]; variable length, validated, no GIS needed for MVP
    version        integer      NOT NULL DEFAULT 1,
    is_active      boolean      NOT NULL DEFAULT true,
    created_at     timestamptz  NOT NULL DEFAULT now(),
    updated_at     timestamptz  NOT NULL DEFAULT now(),
    UNIQUE (factory_id, id),
    CHECK (jsonb_typeof(polygon) = 'array' AND jsonb_array_length(polygon) >= 3),
    FOREIGN KEY (factory_id, camera_id)     REFERENCES cameras (factory_id, id) ON DELETE CASCADE,
    FOREIGN KEY (factory_id, department_id) REFERENCES departments (factory_id, id) ON DELETE SET NULL (department_id)
);
CREATE INDEX monitoring_zones_camera_idx ON monitoring_zones (factory_id, camera_id) WHERE is_active;

CREATE TABLE safety_rules (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    factory_id       uuid NOT NULL REFERENCES factories (id) ON DELETE CASCADE,
    name             varchar(120) NOT NULL,
    event_type       event_type     NOT NULL,
    severity         severity_level NOT NULL,
    zone_id          uuid,
    department_id    uuid,
    sensor_id        uuid,
    min_confidence   real          CHECK (min_confidence BETWEEN 0 AND 1),
    min_duration_s   integer       CHECK (min_duration_s >= 0),
    threshold_value  numeric(8,3),                  -- e.g. temperature limit for temperature_anomaly
    notify           boolean       NOT NULL DEFAULT true,   -- "is an alert required?" decision from the Activity diagram
    is_enabled       boolean       NOT NULL DEFAULT true,
    version          integer       NOT NULL DEFAULT 1,
    created_at       timestamptz   NOT NULL DEFAULT now(),
    updated_at       timestamptz   NOT NULL DEFAULT now(),
    UNIQUE (factory_id, id),
    CHECK (num_nonnulls(zone_id, department_id, sensor_id) <= 1),   -- one scope at most; none = factory-wide
    FOREIGN KEY (factory_id, zone_id)       REFERENCES monitoring_zones (factory_id, id) ON DELETE CASCADE,
    FOREIGN KEY (factory_id, department_id) REFERENCES departments (factory_id, id)      ON DELETE CASCADE,
    FOREIGN KEY (factory_id, sensor_id)     REFERENCES sensors (factory_id, id)          ON DELETE CASCADE
);

-- Camera outage intervals only (selective): a camera gap is the "Unobserved Data Gap".
-- Sensor gaps are detectable from missing sensor_readings.
CREATE TABLE unobserved_gaps (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    factory_id  uuid NOT NULL REFERENCES factories (id) ON DELETE CASCADE,
    camera_id   uuid NOT NULL,
    started_at  timestamptz NOT NULL,
    ended_at    timestamptz,
    reason      gap_reason  NOT NULL DEFAULT 'stream_lost',
    created_at  timestamptz NOT NULL DEFAULT now(),
    CHECK (ended_at IS NULL OR ended_at >= started_at),
    FOREIGN KEY (factory_id, camera_id) REFERENCES cameras (factory_id, id) ON DELETE CASCADE
);
CREATE INDEX unobserved_gaps_camera_idx ON unobserved_gaps (factory_id, camera_id, started_at DESC);
CREATE UNIQUE INDEX unobserved_gaps_one_open ON unobserved_gaps (camera_id) WHERE ended_at IS NULL;

-- ============================================================================= SENSOR MEASUREMENTS
-- High volume but tiny rows: one value per sampling interval, monthly range partitions.
CREATE TABLE sensor_readings (
    sensor_id    uuid        NOT NULL,
    recorded_at  timestamptz NOT NULL,
    factory_id   uuid        NOT NULL REFERENCES factories (id) ON DELETE CASCADE,
    value        numeric(8,3) NOT NULL,
    ingested_at  timestamptz  NOT NULL DEFAULT now(),
    PRIMARY KEY (sensor_id, recorded_at),
    FOREIGN KEY (factory_id, sensor_id) REFERENCES sensors (factory_id, id) ON DELETE CASCADE
) PARTITION BY RANGE (recorded_at);
CREATE TABLE sensor_readings_2026_11 PARTITION OF sensor_readings FOR VALUES FROM ('2026-11-01') TO ('2026-12-01');
CREATE TABLE sensor_readings_2026_12 PARTITION OF sensor_readings FOR VALUES FROM ('2026-12-01') TO ('2027-01-01');
-- Create future partitions with a scheduled job (pg_partman or cron) and detach/drop old ones for retention.

-- ============================================================================= INCIDENTS & EVENTS
-- An incident groups one or more events that need human attention. Not every event becomes an incident.
CREATE TABLE incidents (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    factory_id     uuid NOT NULL REFERENCES factories (id) ON DELETE CASCADE,
    incident_type  event_type     NOT NULL,
    severity       severity_level NOT NULL,
    state          incident_state NOT NULL DEFAULT 'detected',
    opened_at      timestamptz    NOT NULL DEFAULT now(),
    last_event_at  timestamptz    NOT NULL DEFAULT now(),
    reviewed_by    uuid,
    reviewed_at    timestamptz,
    resolved_by    uuid,
    resolved_at    timestamptz,
    resolution_note text,
    updated_at     timestamptz    NOT NULL DEFAULT now(),
    UNIQUE (factory_id, id),
    CHECK (state <> 'resolved' OR resolved_at IS NOT NULL),
    FOREIGN KEY (factory_id, reviewed_by) REFERENCES factory_memberships (factory_id, user_id) ON DELETE SET NULL (reviewed_by),
    FOREIGN KEY (factory_id, resolved_by) REFERENCES factory_memberships (factory_id, user_id) ON DELETE SET NULL (resolved_by)
);
CREATE INDEX incidents_open_idx ON incidents (factory_id, state, opened_at DESC) WHERE state <> 'resolved';
CREATE INDEX incidents_time_idx ON incidents (factory_id, opened_at DESC);

-- An AI-detected (or threshold-detected) event. id is supplied by the producer => idempotent retries.
CREATE TABLE events (
    id           uuid PRIMARY KEY,
    factory_id   uuid NOT NULL REFERENCES factories (id) ON DELETE CASCADE,
    event_type   event_type NOT NULL,
    camera_id    uuid,
    zone_id      uuid,
    rule_id      uuid,
    sensor_id    uuid,
    incident_id  uuid,
    detected_at  timestamptz NOT NULL,
    ingested_at  timestamptz NOT NULL DEFAULT now(),
    confidence   real CHECK (confidence BETWEEN 0 AND 1),
    track_ref    integer,                         -- transient tracker id; not a worker identity (privacy)
    bbox_x       real CHECK (bbox_x BETWEEN 0 AND 1),
    bbox_y       real CHECK (bbox_y BETWEEN 0 AND 1),
    bbox_w       real CHECK (bbox_w BETWEEN 0 AND 1),
    bbox_h       real CHECK (bbox_h BETWEEN 0 AND 1),
    details      jsonb,                           -- type-specific payload (missing items, measured temperature, ...)
    UNIQUE (factory_id, id),
    CHECK (num_nonnulls(camera_id, sensor_id) = 1),   -- exactly one source
    FOREIGN KEY (factory_id, camera_id)   REFERENCES cameras (factory_id, id)          ON DELETE CASCADE,
    FOREIGN KEY (factory_id, zone_id)     REFERENCES monitoring_zones (factory_id, id) ON DELETE SET NULL (zone_id),
    FOREIGN KEY (factory_id, rule_id)     REFERENCES safety_rules (factory_id, id)     ON DELETE SET NULL (rule_id),
    FOREIGN KEY (factory_id, sensor_id)   REFERENCES sensors (factory_id, id)          ON DELETE CASCADE,
    FOREIGN KEY (factory_id, incident_id) REFERENCES incidents (factory_id, id)        ON DELETE SET NULL (incident_id)
);
CREATE INDEX events_time_idx     ON events (factory_id, detected_at DESC);
CREATE INDEX events_type_idx     ON events (factory_id, event_type, detected_at DESC);
CREATE INDEX events_camera_idx   ON events (factory_id, camera_id, detected_at DESC) WHERE camera_id IS NOT NULL;
CREATE INDEX events_incident_idx ON events (factory_id, incident_id) WHERE incident_id IS NOT NULL;

-- ============================================================================= EVIDENCE
-- Files live in object storage (S3/MinIO/local volume). PostgreSQL keeps the reference only.
CREATE TABLE evidence_files (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    factory_id    uuid NOT NULL REFERENCES factories (id) ON DELETE CASCADE,
    event_id      uuid NOT NULL,
    kind          evidence_kind NOT NULL,
    storage_key   text          NOT NULL UNIQUE,    -- f/<factory_id>/evidence/<event_id>/<file>
    content_type  varchar(60)   NOT NULL,
    size_bytes    bigint        NOT NULL CHECK (size_bytes > 0),
    sha256        char(64),
    duration_s    numeric(6,2),
    captured_at   timestamptz   NOT NULL,
    expires_at    timestamptz,                      -- from factories.evidence_retention_days
    purged_at     timestamptz,                      -- set when the object was deleted by the retention job
    created_at    timestamptz   NOT NULL DEFAULT now(),
    CHECK (kind = 'snapshot' OR duration_s IS NOT NULL),
    CHECK (storage_key LIKE 'f/' || factory_id::text || '/%'),
    FOREIGN KEY (factory_id, event_id) REFERENCES events (factory_id, id) ON DELETE CASCADE
);
CREATE INDEX evidence_event_idx  ON evidence_files (factory_id, event_id);
CREATE INDEX evidence_expiry_idx ON evidence_files (expires_at) WHERE purged_at IS NULL AND expires_at IS NOT NULL;

-- ============================================================================= ALERTS & NOTIFICATIONS
CREATE TABLE alerts (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    factory_id    uuid NOT NULL REFERENCES factories (id) ON DELETE CASCADE,
    incident_id   uuid NOT NULL,
    severity      severity_level NOT NULL,
    message       text           NOT NULL,
    status        alert_status   NOT NULL DEFAULT 'pending',
    created_at    timestamptz    NOT NULL DEFAULT now(),
    dispatched_at timestamptz,
    UNIQUE (factory_id, id),
    FOREIGN KEY (factory_id, incident_id) REFERENCES incidents (factory_id, id) ON DELETE CASCADE
);
CREATE INDEX alerts_time_idx     ON alerts (factory_id, created_at DESC);
CREATE INDEX alerts_incident_idx ON alerts (factory_id, incident_id);

-- Who receives external notifications (ASSUMPTION: factory-level destinations with a minimum severity;
-- recipient-by-role / department is a later extension because documentation D23 is still open).
CREATE TABLE notification_targets (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    factory_id    uuid NOT NULL REFERENCES factories (id) ON DELETE CASCADE,
    label         varchar(100) NOT NULL,
    channel       notification_channel NOT NULL,
    address       varchar(255) NOT NULL,            -- phone number or Telegram chat id (personal data: restrict access)
    min_severity  severity_level NOT NULL DEFAULT 'high',
    is_enabled    boolean        NOT NULL DEFAULT true,
    created_at    timestamptz    NOT NULL DEFAULT now(),
    UNIQUE (factory_id, id)
);

CREATE TABLE alert_deliveries (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    factory_id       uuid NOT NULL REFERENCES factories (id) ON DELETE CASCADE,
    alert_id         uuid NOT NULL,
    target_id        uuid,                           -- NULL for the dashboard channel
    channel          notification_channel NOT NULL,
    status           delivery_status NOT NULL DEFAULT 'queued',
    attempt_count    smallint        NOT NULL DEFAULT 0,
    last_attempt_at  timestamptz,
    sent_at          timestamptz,
    provider_ref     varchar(120),
    error_detail     text,
    created_at       timestamptz     NOT NULL DEFAULT now(),
    FOREIGN KEY (factory_id, alert_id)  REFERENCES alerts (factory_id, id) ON DELETE CASCADE,
    FOREIGN KEY (factory_id, target_id) REFERENCES notification_targets (factory_id, id) ON DELETE SET NULL (target_id)
);
CREATE INDEX alert_deliveries_alert_idx ON alert_deliveries (factory_id, alert_id);
CREATE INDEX alert_deliveries_retry_idx ON alert_deliveries (status, last_attempt_at) WHERE status IN ('queued', 'failed');

-- ============================================================================= ROW-LEVEL SECURITY
-- The API opens a transaction, verifies factory_memberships for the authenticated user and then runs:
--     SELECT set_config('app.factory_id', '<uuid>', true), set_config('app.user_id', '<uuid>', true);
-- The application role must be neither owner nor BYPASSRLS; onboarding of new factories uses a separate
-- platform role (BYPASSRLS) behind the platform-admin API.
CREATE FUNCTION app_factory_id() RETURNS uuid LANGUAGE sql STABLE AS
$$ SELECT NULLIF(current_setting('app.factory_id', true), '')::uuid $$;
CREATE FUNCTION app_user_id() RETURNS uuid LANGUAGE sql STABLE AS
$$ SELECT NULLIF(current_setting('app.user_id', true), '')::uuid $$;

DO $$
DECLARE t text;
BEGIN
    FOREACH t IN ARRAY ARRAY['departments','cameras','sensors','monitoring_zones','safety_rules','unobserved_gaps',
                             'sensor_readings','incidents','events','evidence_files','alerts','notification_targets',
                             'alert_deliveries']
    LOOP
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
        EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', t);
        EXECUTE format('CREATE POLICY tenant_isolation ON %I USING (factory_id = app_factory_id()) WITH CHECK (factory_id = app_factory_id())', t);
    END LOOP;
END $$;

ALTER TABLE factories ENABLE ROW LEVEL SECURITY;
ALTER TABLE factories FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON factories USING (id = app_factory_id()) WITH CHECK (id = app_factory_id());

-- Memberships must also be readable by the user themself before a factory is selected (login, factory switcher).
ALTER TABLE factory_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE factory_memberships FORCE ROW LEVEL SECURITY;
CREATE POLICY membership_read ON factory_memberships FOR SELECT
    USING (factory_id = app_factory_id() OR user_id = app_user_id());
CREATE POLICY membership_write ON factory_memberships FOR ALL
    USING (factory_id = app_factory_id()) WITH CHECK (factory_id = app_factory_id());

-- ============================================================================= SEED (ASSUMPTION - permission matrix D10 is still open)
INSERT INTO roles (code, name) VALUES
    ('factory_admin',     'System Administrator'),
    ('factory_manager',   'Factory Manager'),
    ('safety_supervisor', 'Safety Supervisor');

INSERT INTO permissions (code, description) VALUES
    ('users.manage',        'Create and manage users and memberships of the factory'),
    ('resources.manage',    'Manage departments, cameras, sensors and zones'),
    ('rules.manage',        'Manage safety rules and notification targets'),
    ('events.view',         'View events'),
    ('incidents.view',      'View incidents and alerts'),
    ('incidents.review',    'Review and resolve incidents'),
    ('evidence.view',       'View evidence files'),
    ('analytics.view',      'View dashboards and statistics');

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r JOIN permissions p ON
    (r.code = 'factory_admin'     AND p.code IN ('users.manage','resources.manage','rules.manage','events.view','incidents.view','analytics.view'))
 OR (r.code = 'factory_manager'   AND p.code IN ('events.view','incidents.view','evidence.view','analytics.view'))
 OR (r.code = 'safety_supervisor' AND p.code IN ('events.view','incidents.view','incidents.review','evidence.view'));





 SELECT *
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_type = 'BASE TABLE';
