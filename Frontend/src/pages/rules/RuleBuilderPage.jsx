import React from 'react';
import Navbar from '../../components/common/Navbar';
import { useData } from '../../context/DataContext';
import { useNavigate } from 'react-router-dom';
import { Zap, Plus, Edit2 } from 'lucide-react';

export default function RuleBuilderPage() {
  const { rules, toggleRule } = useData();
  const navigate = useNavigate();

  const handleEditRule = (id) => {
    navigate(`/rules/edit/${id}`);
  };

  const handleOpenZoneEditor = () => {
    navigate('/rules/zones');
  };

  return (
    <>
      <Navbar
        title="No-Code Rule Builder"
        subtitle="Define zones, policies and alerts without writing code"
        rightActions={
          <button
            className="btn btn-primary"
            onClick={() => alert('Rules recompiled and pushed to edge vision nodes!')}
          >
            <Zap size={14} />
            Activate rules
          </button>
        }
      />

      <div className="page-container">
        <div className="grid-2col-settings">
          {/* Safety Rules Policies List */}
          <div className="operix-card">
            <h3 className="card-title">Safety rules</h3>
            <p className="card-subtitle" style={{ marginBottom: '1.25rem' }}>
              {rules.length} policies · {rules.filter(r => r.enabled).length} active
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {rules.map((rule) => (
                <div
                  key={rule.id}
                  style={{
                    backgroundColor: 'var(--bg-card-subtle)',
                    border: '1px solid var(--border-color)',
                    borderRadius: 'var(--radius-md)',
                    padding: '1.25rem',
                    transition: 'border-color 0.15s ease'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontSize: '15px', fontWeight: 700, color: 'var(--text-primary)' }}>
                        {rule.name}
                      </span>
                      <button
                        className="btn-icon"
                        style={{ width: '28px', height: '28px' }}
                        title="Edit rule logic"
                        onClick={() => handleEditRule(rule.id)}
                      >
                        <Edit2 size={13} />
                      </button>
                    </div>

                    <label className="switch-wrapper">
                      <input
                        type="checkbox"
                        className="switch-input"
                        checked={rule.enabled}
                        onChange={() => toggleRule(rule.id)}
                      />
                      <span className="switch-slider" />
                    </label>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '50px 1fr', rowGap: '8px', fontSize: '13px' }}>
                    <span style={{ fontWeight: 800, color: 'var(--primary)', letterSpacing: '0.05em' }}>IF</span>
                    <span style={{ color: 'var(--text-primary)' }}>{rule.ifDetection.eventType}</span>

                    <span style={{ fontWeight: 800, color: 'var(--primary)', letterSpacing: '0.05em' }}>IN</span>
                    <span style={{ color: 'var(--text-primary)' }}>{rule.inScope.zone}</span>

                    <span style={{ fontWeight: 800, color: 'var(--primary)', letterSpacing: '0.05em' }}>THEN</span>
                    <span style={{ color: 'var(--text-primary)' }}>{rule.thenResult.channels}</span>
                  </div>
                </div>
              ))}
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginTop: '1.5rem' }}>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => handleEditRule('RULE-01')}
              >
                <Plus size={14} />
                Add rule
              </button>
              <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                Rules apply to live detections only.
              </span>
            </div>
          </div>

          {/* Right Monitoring Zones Preview */}
          <div className="operix-card">
            <div className="card-header-flex">
              <div>
                <h3 className="card-title">Monitoring zones</h3>
                <span className="card-subtitle">Plant 1 · 3 configured zones</span>
              </div>
              <button className="btn btn-outline btn-sm" onClick={handleOpenZoneEditor}>
                Zone Editor
              </button>
            </div>

            {/* Visual Zones Blueprint preview */}
            <div
              style={{
                height: '240px',
                border: '1px dashed var(--border-color)',
                borderRadius: '8px',
                backgroundColor: 'var(--bg-card-subtle)',
                padding: '16px',
                display: 'flex',
                flexDirection: 'column',
                gap: '12px',
                marginBottom: '1.25rem'
              }}
            >
              <div style={{ display: 'flex', gap: '12px', flex: 1 }}>
                <div style={{ flex: 1, border: '1px solid #64748B', borderRadius: '6px', padding: '8px' }}>
                  <span style={{ fontSize: '11px', fontWeight: 700 }}>Zone A</span>
                  <div style={{ display: 'flex', gap: '6px', marginTop: '16px', opacity: 0.25 }}>
                    <div style={{ width: '24px', height: '24px', background: '#64748B', borderRadius: '4px' }} />
                    <div style={{ width: '24px', height: '24px', background: '#64748B', borderRadius: '4px' }} />
                  </div>
                </div>
                <div style={{ flex: 1, border: '1px solid #64748B', borderRadius: '6px', padding: '8px' }}>
                  <span style={{ fontSize: '11px', fontWeight: 700 }}>Zone B</span>
                  <div style={{ display: 'flex', gap: '6px', marginTop: '16px', opacity: 0.25 }}>
                    <div style={{ width: '24px', height: '24px', background: '#64748B', borderRadius: '4px' }} />
                    <div style={{ width: '24px', height: '24px', background: '#64748B', borderRadius: '4px' }} />
                  </div>
                </div>
              </div>

              <div style={{ border: '1.5px solid #EF4444', borderRadius: '6px', padding: '8px', flex: 1 }}>
                <span style={{ fontSize: '11px', fontWeight: 700, color: '#EF4444' }}>Zone D · Restricted</span>
                <div style={{ display: 'flex', gap: '8px', marginTop: '16px', opacity: 0.35 }}>
                  <div style={{ width: '48px', height: '20px', background: '#EF4444', borderRadius: '4px' }} />
                  <div style={{ width: '48px', height: '20px', background: '#EF4444', borderRadius: '4px' }} />
                  <div style={{ width: '48px', height: '20px', background: '#EF4444', borderRadius: '4px' }} />
                </div>
              </div>
            </div>

            <div style={{ marginTop: '1rem' }}>
              <div style={{ color: '#EF4444', fontWeight: 700, fontSize: '13.5px', marginBottom: '4px' }}>
                Zone D · Restricted
              </div>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                Authorized personnel only. Entry triggers a high-severity incident and an immediate alert.
              </p>
              <div style={{ fontSize: '11.5px', color: 'var(--text-light)', marginTop: '1.25rem' }}>
                Zone boundaries are camera-calibrated.
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
