import React, { useState } from 'react';
import Navbar from '../../components/common/Navbar';
import CameraFeedCard from '../../components/common/CameraFeedCard';
import { useData } from '../../context/DataContext';
import { useAuth } from '../../context/AuthContext';
import { Download, CheckCircle, ExternalLink } from 'lucide-react';

export default function IncidentsPage() {
  const { incidents, resolveIncident } = useData();
  const { hasPermission } = useAuth();
  const [selectedIncidentId, setSelectedIncidentId] = useState(incidents[0]?.id || 'INC-2041');
  const [statusFilter, setStatusFilter] = useState('All');
  const [currentPage, setCurrentPage] = useState(1);
  const [evidenceModalOpen, setEvidenceModalOpen] = useState(false);

  const selectedIncident = incidents.find(i => i.id === selectedIncidentId) || incidents[0];

  const filteredIncidents = incidents.filter(i => {
    if (statusFilter === 'All') return true;
    return i.status.toLowerCase().includes(statusFilter.toLowerCase());
  });

  const canResolve = hasPermission('incident.resolve');
  const canViewEvidence = hasPermission('evidence.view');

  return (
    <>
      <Navbar
        title="Incidents"
        subtitle="Review events, evidence and alert status"
        rightActions={
          <button className="btn btn-secondary" onClick={() => alert('Exporting incident log (CSV)...')}>
            <Download size={14} />
            Export
          </button>
        }
      />

      <div className="page-container">
        <div className="grid-2col-settings">
          {/* Left Table Panel */}
          <div className="operix-card" style={{ padding: 0, overflow: 'hidden' }}>
            <div style={{ padding: '1.25rem 1.5rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)' }}>
              <div>
                <h3 className="card-title">Recent incidents</h3>
                <span className="card-subtitle">{filteredIncidents.length} events · Current shift</span>
              </div>

              <select
                className="form-control form-select"
                style={{ width: '140px', padding: '0.45rem 0.8rem', fontSize: '12px' }}
                value={statusFilter}
                onChange={e => setStatusFilter(e.target.value)}
              >
                <option value="All">All statuses</option>
                <option value="Pending">Pending</option>
                <option value="Dispatched">Dispatched</option>
                <option value="Review">Under Review</option>
                <option value="Resolved">Resolved</option>
              </select>
            </div>

            <div className="table-responsive">
              <table className="operix-table">
                <thead>
                  <tr>
                    <th style={{ minWidth: '90px' }}>ID</th>
                    <th style={{ minWidth: '150px' }}>Event</th>
                    <th style={{ minWidth: '140px' }}>Location</th>
                    <th style={{ minWidth: '95px' }}>Severity</th>
                    <th style={{ minWidth: '110px' }}>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredIncidents.slice(0, 5).map(inc => {
                    const isSelected = inc.id === selectedIncidentId;
                    const severityClass = inc.severity.toLowerCase();

                    return (
                      <tr
                        key={inc.id}
                        onClick={() => setSelectedIncidentId(inc.id)}
                        style={{
                          cursor: 'pointer',
                          backgroundColor: isSelected ? 'var(--bg-active-nav)' : undefined
                        }}
                      >
                        <td style={{ fontWeight: 600, whiteSpace: 'nowrap' }}>{inc.id}</td>
                        <td style={{ fontWeight: 700, whiteSpace: 'nowrap' }}>{inc.event}</td>
                        <td style={{ color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>{inc.location}</td>
                        <td style={{ whiteSpace: 'nowrap' }}>
                          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                            <span
                              className="badge-dot"
                              style={{
                                backgroundColor:
                                  inc.severity === 'High' ? '#EF4444' : inc.severity === 'Medium' ? '#F59E0B' : '#10B981'
                              }}
                            />
                            <span style={{ fontSize: '12.5px' }}>{inc.severity}</span>
                          </span>
                        </td>
                        <td style={{ whiteSpace: 'nowrap' }}>
                          <span className={`status-pill ${inc.status.toLowerCase().replace(' ', '-')}`}>
                            {inc.status}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <div className="table-footer-meta">
              <span>Showing 5 of {incidents.length} incidents</span>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <button
                  className="btn btn-outline btn-sm"
                  disabled={currentPage === 1}
                  onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                >
                  &larr;
                </button>
                <span style={{ fontWeight: 700 }}>1</span>
                <span>2</span>
                <span>3</span>
                <button
                  className="btn btn-outline btn-sm"
                  onClick={() => setCurrentPage(prev => prev + 1)}
                >
                  &rarr;
                </button>
              </div>
            </div>
          </div>

          {/* Right Incident Detail & Evidence Inspector */}
          {selectedIncident && (
            <div className="operix-card">
              <div style={{ marginBottom: '1rem' }}>
                <h3 className="card-title" style={{ fontSize: '18px' }}>
                  {selectedIncident.id} · {selectedIncident.event}
                </h3>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: '6px', fontSize: '12.5px' }}>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', color: '#EF4444', fontWeight: 700 }}>
                    <span className="badge-dot" style={{ backgroundColor: '#EF4444' }} />
                    {selectedIncident.severity} severity
                  </span>
                  <span style={{ color: 'var(--text-light)' }}>·</span>
                  <span style={{ color: selectedIncident.status === 'Resolved' ? '#10B981' : '#F59E0B', fontWeight: 600 }}>
                    {selectedIncident.status}
                  </span>
                </div>
              </div>

              {/* Live/Evidence Snapshot */}
              <div style={{ borderRadius: '10px', overflow: 'hidden', marginBottom: '1.25rem' }}>
                <CameraFeedCard
                  camId={selectedIncident.camera.split(' · ')[0]}
                  title={selectedIncident.location}
                  isLive={true}
                  timestamp={`${selectedIncident.timestamp} / PLANT 1`}
                  isThermal={selectedIncident.event.includes('temperature')}
                  detections={[
                    { label: `${selectedIncident.workerId} · ${selectedIncident.workerStatus}`, type: 'danger', left: '18%', top: '25%', width: '90px', height: '110px' },
                    { label: selectedIncident.peerWorker, type: 'success', left: '60%', top: '28%', width: '85px', height: '105px' }
                  ]}
                  height={190}
                />
              </div>

              {/* Audit Trail */}
              <div>
                <h4 style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '0.75rem' }}>
                  Audit trail
                </h4>

                <div className="audit-trail-timeline">
                  {selectedIncident.auditTrail.map((step, idx) => (
                    <div key={idx} className="audit-step">
                      <div className="audit-step-title">{step.text}</div>
                      <div className="audit-step-meta">{step.time} · {step.detail}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Action Buttons */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginTop: '1.5rem' }}>
                <button
                  className="btn btn-primary"
                  disabled={selectedIncident.status === 'Resolved' || !canResolve}
                  onClick={() => resolveIncident(selectedIncident.id)}
                >
                  <CheckCircle size={15} />
                  {selectedIncident.status === 'Resolved' ? 'Resolved' : 'Mark as resolved'}
                </button>

                <button
                  className="btn btn-secondary"
                  disabled={!canViewEvidence}
                  onClick={() => setEvidenceModalOpen(true)}
                >
                  <ExternalLink size={15} />
                  Open evidence
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Evidence Modal */}
      {evidenceModalOpen && (
        <div className="modal-overlay" onClick={() => setEvidenceModalOpen(false)}>
          <div className="modal-dialog" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3 className="modal-title">Evidence Packet · {selectedIncident?.id}</h3>
              <button className="btn-icon" onClick={() => setEvidenceModalOpen(false)}>✕</button>
            </div>
            <div className="modal-body">
              <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '12px' }}>
                High-definition snapshot, detected bounding box metadata, and signed SHA-256 evidence record.
              </p>
              <div style={{ padding: '1rem', backgroundColor: 'var(--bg-card-subtle)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                <div style={{ fontSize: '12px', fontFamily: 'JetBrains Mono', color: 'var(--text-secondary)' }}>
                  HASH: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855<br />
                  TIMESTAMP: {selectedIncident?.timestamp} UTC+2<br />
                  SOURCE: {selectedIncident?.camera}<br />
                  CONFIDENCE: 98.4%
                </div>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-primary" onClick={() => setEvidenceModalOpen(false)}>
                Close Evidence
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
