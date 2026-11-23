import React, { useState } from 'react';
import Navbar from '../../components/common/Navbar';
import { useParams, useNavigate } from 'react-router-dom';
import { useData } from '../../context/DataContext';
import { ArrowLeft, Trash2, Check } from 'lucide-react';

export default function EditRulePage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { rules, updateRule, deleteRule } = useData();

  const rule = rules.find(r => r.id === id) || rules[0] || {
    id: 'RULE-01',
    name: 'Helmet compliance',
    enabled: true,
    version: 3,
    ifDetection: {
      eventType: 'Helmet missing',
      severity: 'High',
      minConfidence: 0.80,
      minDuration: 5,
      thresholdValue: '—'
    },
    inScope: {
      zone: 'Zone B · Press Line',
      department: 'Any',
      sensor: 'None'
    },
    thenResult: {
      notify: true,
      channels: 'Notify safety supervisor',
      createAlert: true
    }
  };

  const [name, setName] = useState(rule.name);
  const [eventType, setEventType] = useState(rule.ifDetection.eventType);
  const [severity, setSeverity] = useState(rule.ifDetection.severity);
  const [minConfidence, setMinConfidence] = useState(rule.ifDetection.minConfidence);
  const [minDuration, setMinDuration] = useState(rule.ifDetection.minDuration);
  const [thresholdValue, setThresholdValue] = useState(rule.ifDetection.thresholdValue);
  const [zone, setZone] = useState(rule.inScope.zone);
  const [department, setDepartment] = useState(rule.inScope.department);
  const [sensor, setSensor] = useState(rule.inScope.sensor);
  const [notify, setNotify] = useState(rule.thenResult.notify);
  const [enabled, setEnabled] = useState(rule.enabled);

  const handleSave = (e) => {
    e.preventDefault();
    updateRule(rule.id, {
      name,
      enabled,
      ifDetection: {
        eventType,
        severity,
        minConfidence: parseFloat(minConfidence),
        minDuration: parseInt(minDuration),
        thresholdValue
      },
      inScope: {
        zone,
        department,
        sensor
      },
      thenResult: {
        notify,
        channels: `${severity} severity · notify`,
        createAlert: true
      }
    });
    navigate('/rules');
  };

  const handleDelete = () => {
    if (confirm(`Are you sure you want to delete rule "${rule.name}"?`)) {
      deleteRule(rule.id);
      navigate('/rules');
    }
  };

  return (
    <>
      <Navbar
        title={`Edit rule · ${rule.name}`}
        subtitle="Change the event, scope and result of this rule"
        rightActions={
          <button className="btn btn-secondary btn-sm" onClick={() => navigate('/rules')}>
            <ArrowLeft size={14} />
            Back to rules
          </button>
        }
      />

      <div className="page-container">
        <form onSubmit={handleSave} className="grid-2col-settings">
          {/* Left: Rule Logic Fields */}
          <div className="operix-card">
            <h3 className="card-title">Rule logic</h3>
            <p className="card-subtitle" style={{ marginBottom: '1.5rem' }}>
              When this rule fires, and how severe the result is
            </p>

            <div className="form-group">
              <label className="form-label">Rule name</label>
              <input
                type="text"
                className="form-control"
                value={name}
                onChange={e => setName(e.target.value)}
                required
              />
            </div>

            {/* IF · DETECTION */}
            <div style={{ marginTop: '1.75rem', marginBottom: '1rem' }}>
              <span style={{ fontSize: '11px', fontWeight: 800, letterSpacing: '0.08em', color: 'var(--text-light)', textTransform: 'uppercase' }}>
                IF · DETECTION
              </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <div className="form-group">
                <label className="form-label">Event type</label>
                <select
                  className="form-control form-select"
                  value={eventType}
                  onChange={e => setEventType(e.target.value)}
                >
                  <option value="Helmet missing">Helmet missing</option>
                  <option value="Unauthorized worker detected">Unauthorized worker detected</option>
                  <option value="Fatigue score > 80%">Fatigue signs</option>
                  <option value="Vest missing">Vest missing</option>
                  <option value="Abnormal temperature">Abnormal temperature</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Severity</label>
                <select
                  className="form-control form-select"
                  value={severity}
                  onChange={e => setSeverity(e.target.value)}
                >
                  <option value="High">High</option>
                  <option value="Medium">Medium</option>
                  <option value="Low">Low</option>
                </select>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
              <div className="form-group">
                <label className="form-label">Min. confidence (optional)</label>
                <input
                  type="number"
                  step="0.05"
                  max="1.0"
                  min="0.5"
                  className="form-control font-mono"
                  value={minConfidence}
                  onChange={e => setMinConfidence(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Min. duration, seconds (optional)</label>
                <input
                  type="number"
                  className="form-control font-mono"
                  value={minDuration}
                  onChange={e => setMinDuration(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Threshold value (optional)</label>
                <input
                  type="text"
                  className="form-control font-mono"
                  value={thresholdValue}
                  onChange={e => setThresholdValue(e.target.value)}
                />
              </div>
            </div>

            {/* IN · SCOPE */}
            <div style={{ marginTop: '1.75rem', marginBottom: '1rem' }}>
              <span style={{ fontSize: '11px', fontWeight: 800, letterSpacing: '0.08em', color: 'var(--text-light)', textTransform: 'uppercase' }}>
                IN · SCOPE (ALL OPTIONAL)
              </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
              <div className="form-group">
                <label className="form-label">Zone</label>
                <select
                  className="form-control form-select"
                  value={zone}
                  onChange={e => setZone(e.target.value)}
                >
                  <option value="Zone B · Press Line">Zone B · Press Line</option>
                  <option value="Zone D · Restricted">Zone D · Restricted</option>
                  <option value="Zone A · Assembly">Zone A · Assembly</option>
                  <option value="Zone C · Loading">Zone C · Loading</option>
                  <option value="Any zone">Any zone</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Department</label>
                <select
                  className="form-control form-select"
                  value={department}
                  onChange={e => setDepartment(e.target.value)}
                >
                  <option value="Any">Any</option>
                  <option value="Production">Production</option>
                  <option value="Storage">Storage</option>
                  <option value="Security">Security</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Sensor</label>
                <select
                  className="form-control form-select"
                  value={sensor}
                  onChange={e => setSensor(e.target.value)}
                >
                  <option value="None">None</option>
                  <option value="TMP-01">TMP-01 · Boiler</option>
                  <option value="TMP-02">TMP-02 · Furnace</option>
                </select>
              </div>
            </div>

            {/* THEN · RESULT */}
            <div style={{ marginTop: '1.75rem', marginBottom: '1rem' }}>
              <span style={{ fontSize: '11px', fontWeight: 800, letterSpacing: '0.08em', color: 'var(--text-light)', textTransform: 'uppercase' }}>
                THEN · RESULT
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <label className="switch-wrapper">
                <input
                  type="checkbox"
                  className="switch-input"
                  checked={notify}
                  onChange={e => setNotify(e.target.checked)}
                />
                <span className="switch-slider" />
              </label>
              <span style={{ fontSize: '13px', fontWeight: 600 }}>
                Notify · create an alert when the rule fires
              </span>
            </div>
          </div>

          {/* Right Column: Summary Box & Actions */}
          <div className="operix-card">
            <h3 className="card-title">Summary</h3>
            <p className="card-subtitle" style={{ marginBottom: '1.25rem' }}>
              How the rule reads
            </p>

            {/* Live Summary Box */}
            <div style={{
              backgroundColor: 'var(--bg-active-nav)',
              border: '1px solid var(--border-color)',
              borderRadius: '10px',
              padding: '1.25rem',
              marginBottom: '1.5rem'
            }}>
              <div style={{ fontWeight: 800, fontSize: '14.5px', marginBottom: '1rem', color: 'var(--text-primary)' }}>
                {name}
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '50px 1fr', rowGap: '10px', fontSize: '13px' }}>
                <span style={{ fontWeight: 800, color: 'var(--primary)', letterSpacing: '0.05em' }}>IF</span>
                <span style={{ color: 'var(--text-primary)' }}>
                  {eventType} · confidence ≥ {minConfidence} · for {minDuration} s
                </span>

                <span style={{ fontWeight: 800, color: 'var(--primary)', letterSpacing: '0.05em' }}>IN</span>
                <span style={{ color: 'var(--text-primary)' }}>{zone}</span>

                <span style={{ fontWeight: 800, color: 'var(--primary)', letterSpacing: '0.05em' }}>THEN</span>
                <span style={{ color: 'var(--text-primary)' }}>{severity} severity · notify</span>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <span style={{ fontWeight: 600, fontSize: '13.5px' }}>Enabled</span>
              <label className="switch-wrapper">
                <input
                  type="checkbox"
                  className="switch-input"
                  checked={enabled}
                  onChange={e => setEnabled(e.target.checked)}
                />
                <span className="switch-slider" />
              </label>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem', fontSize: '13px', color: 'var(--text-muted)' }}>
              <span>Version</span>
              <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{rule.version}</span>
            </div>

            <div style={{ display: 'flex', gap: '10px', marginBottom: '1rem' }}>
              <button type="submit" className="btn btn-primary" style={{ flex: 1 }}>
                Save rule
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => navigate('/rules')}
              >
                Cancel
              </button>
            </div>

            <button
              type="button"
              className="btn btn-danger-outline"
              style={{ width: '100%' }}
              onClick={handleDelete}
            >
              Delete rule
            </button>
          </div>
        </form>
      </div>
    </>
  );
}
