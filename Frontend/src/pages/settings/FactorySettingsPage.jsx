import React, { useState } from 'react';
import Navbar from '../../components/common/Navbar';
import PendingBackendBadge from '../../components/common/PendingBackendBadge';
import { useData } from '../../context/DataContext';
import { Plus, Trash2, Edit2, Check } from 'lucide-react';

export default function FactorySettingsPage() {
  const {
    factory,
    updateFactorySettings,
    notificationTargets,
    toggleNotificationTarget,
    removeNotificationTarget,
    addNotificationTarget
  } = useData();

  const [factoryName, setFactoryName] = useState(factory.name);
  const [slug, setSlug] = useState(factory.slug);
  const [timezone, setTimezone] = useState(factory.timezone);
  const [retentionDays, setRetentionDays] = useState(factory.evidenceRetentionDays);
  const [departments, setDepartments] = useState(factory.departments || ['Production', 'Storage', 'Security']);
  const [isSaved, setIsSaved] = useState(false);

  const handleSaveChanges = () => {
    updateFactorySettings({
      name: factoryName,
      slug,
      timezone,
      evidenceRetentionDays: parseInt(retentionDays),
      departments
    });
    setIsSaved(true);
    setTimeout(() => setIsSaved(false), 3000);
  };

  const handleAddDept = () => {
    const newDept = prompt('Enter new department name:');
    if (newDept && newDept.trim()) {
      setDepartments([...departments, newDept.trim()]);
    }
  };

  const handleAddTarget = () => {
    const label = prompt('Enter target label (e.g. On-Call Team):');
    if (!label) return;
    const channel = prompt('Enter channel (WhatsApp / Email / Telegram / SMS):', 'Telegram');
    const address = prompt('Enter destination address / number / group:');
    if (label && address) {
      addNotificationTarget({
        label,
        channel: channel || 'Telegram',
        address,
        minSeverity: 'High',
        enabled: true
      });
    }
  };

  return (
    <>
      <Navbar
        title="Factory Settings"
        subtitle="Plant profile, departments and alert targets"
        backTo="/settings"
        backLabel="Back to Settings"
        rightActions={
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <PendingBackendBadge moduleCode="S-4" dependency="Factory Settings API" />
            <button className="btn btn-primary" onClick={handleSaveChanges}>
              <Check size={14} />
              Save changes
            </button>
          </div>
        }
      />

      <div className="page-container">
        {isSaved && (
          <div style={{
            padding: '12px 16px',
            backgroundColor: 'var(--success-bg)',
            border: '1px solid var(--success-border)',
            color: 'var(--success-text)',
            borderRadius: '8px',
            fontSize: '13px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            <Check size={16} />
            <span>Factory configuration updated successfully.</span>
          </div>
        )}

        {/* Top 2 Columns: Profile & Departments */}
        <div className="grid-2col-settings">
          {/* Plant Profile */}
          <div className="operix-card">
            <h3 className="card-title">Plant profile</h3>
            <p className="card-subtitle" style={{ marginBottom: '1.5rem' }}>
              Basic details and data retention
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem' }}>
              <div className="form-group">
                <label className="form-label">Factory name</label>
                <input
                  type="text"
                  className="form-control"
                  value={factoryName}
                  onChange={e => setFactoryName(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Slug</label>
                <input
                  type="text"
                  className="form-control font-mono"
                  value={slug}
                  onChange={e => setSlug(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Timezone</label>
                <select
                  className="form-control form-select"
                  value={timezone}
                  onChange={e => setTimezone(e.target.value)}
                >
                  <option value="Africa/Cairo (UTC+02:00)">Africa/Cairo (UTC+02:00)</option>
                  <option value="Europe/London (UTC+00:00)">Europe/London (UTC+00:00)</option>
                  <option value="America/New_York (UTC-05:00)">America/New_York (UTC-05:00)</option>
                  <option value="Asia/Dubai (UTC+04:00)">Asia/Dubai (UTC+04:00)</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Evidence retention (days)</label>
                <input
                  type="number"
                  className="form-control font-mono"
                  value={retentionDays}
                  onChange={e => setRetentionDays(e.target.value)}
                />
              </div>
            </div>

            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '0.5rem', marginBottom: '1.25rem' }}>
              Evidence files are purged automatically after this period.
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Factory status</span>
              <span className="status-pill online">
                <span className="badge-dot" /> Active
              </span>
            </div>
          </div>

          {/* Departments */}
          <div className="operix-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <div>
              <h3 className="card-title">Departments</h3>
              <p className="card-subtitle" style={{ marginBottom: '1.25rem' }}>
                Group cameras, sensors and zones
              </p>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {departments.map((dept, idx) => (
                  <div
                    key={idx}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '10px 14px',
                      backgroundColor: 'var(--bg-card-subtle)',
                      border: '1px solid var(--border-color)',
                      borderRadius: '8px'
                    }}
                  >
                    <span style={{ fontWeight: 600, fontSize: '13.5px' }}>{dept}</span>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => {
                        const renamed = prompt('Rename department:', dept);
                        if (renamed) {
                          setDepartments(departments.map((d, i) => (i === idx ? renamed : d)));
                        }
                      }}
                    >
                      Edit
                    </button>
                  </div>
                ))}
              </div>
            </div>

            <div style={{ marginTop: '1.5rem' }}>
              <button className="btn btn-secondary btn-sm" onClick={handleAddDept}>
                <Plus size={13} />
                Add department
              </button>
            </div>
          </div>
        </div>

        {/* Bottom Card: Notification Targets */}
        <div className="operix-table-card">
          <div style={{ padding: '1.25rem 1.5rem', borderBottom: '1px solid var(--border-color)' }}>
            <h3 className="card-title">Notification targets</h3>
            <p className="card-subtitle">Who receives alerts, by channel and minimum severity</p>
          </div>

          <div className="table-responsive">
            <table className="operix-table">
              <thead>
                <tr>
                  <th style={{ minWidth: '150px' }}>Label</th>
                  <th style={{ minWidth: '110px' }}>Channel</th>
                  <th style={{ minWidth: '180px' }}>Address</th>
                  <th style={{ minWidth: '110px' }}>Min. severity</th>
                  <th style={{ minWidth: '90px' }}>Enabled</th>
                  <th style={{ minWidth: '140px', textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {notificationTargets.map((target) => (
                  <tr key={target.id}>
                    <td style={{ fontWeight: 700, color: 'var(--text-primary)', whiteSpace: 'nowrap' }}>
                      {target.label}
                    </td>
                    <td style={{ color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
                      {target.channel}
                    </td>
                    <td style={{ fontFamily: 'JetBrains Mono', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                      {target.address}
                    </td>
                    <td>
                      <span className="status-pill neutral font-mono">
                        {target.minSeverity}
                      </span>
                    </td>
                    <td>
                      <label className="switch-wrapper">
                        <input
                          type="checkbox"
                          className="switch-input"
                          checked={target.enabled}
                          onChange={() => toggleNotificationTarget(target.id)}
                        />
                        <span className="switch-slider" />
                      </label>
                    </td>
                    <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
                      <div style={{ display: 'inline-flex', gap: '8px' }}>
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={() => alert(`Editing target: ${target.label}`)}
                        >
                          Edit
                        </button>
                        <button
                          className="btn btn-danger-outline btn-sm"
                          onClick={() => removeNotificationTarget(target.id)}
                        >
                          Remove
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div style={{ padding: '1rem 1.5rem', backgroundColor: 'var(--bg-card)' }}>
            <button className="btn btn-secondary btn-sm" onClick={handleAddTarget}>
              <Plus size={13} />
              Add target
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
