import React, { useState, useEffect } from 'react';
import Navbar from '../../components/common/Navbar';
import { Download, Plus, Check, AlertCircle, FileText, FileSpreadsheet } from 'lucide-react';
import { reportService } from '../../services';

export default function ReportsPage() {
  const [reportsList, setReportsList] = useState([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [feedback, setFeedback] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [downloadingId, setDownloadingId] = useState(null);

  // Generation Form State
  const [reportType, setReportType] = useState('workforce');
  const [reportFormat, setReportFormat] = useState('pdf');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  const loadReports = async () => {
    try {
      const data = await reportService.getReports();
      setReportsList(data || []);
    } catch (err) {
      console.warn('Failed to fetch reports list:', err.message);
    }
  };

  useEffect(() => {
    loadReports();
  }, []);

  const handleDownload = async (rep) => {
    setDownloadingId(rep.id || rep.report_id);
    try {
      const ext = rep.format?.toLowerCase() === 'excel' ? 'xlsx' : 'pdf';
      const cleanTitle = (rep.title || 'Operix_Safety_Report').replace(/[^a-zA-Z0-9_-]/g, '_');
      await reportService.downloadReport(rep.id || rep.report_id, `${cleanTitle}.${ext}`);
      setFeedback({ type: 'success', text: `Downloaded ${rep.title || 'report'}.${ext}` });
    } catch (err) {
      setFeedback({ type: 'error', text: err.message || 'Download failed.' });
    } finally {
      setDownloadingId(null);
      setTimeout(() => setFeedback(null), 4000);
    }
  };

  const handleGenerate = async (e) => {
    e.preventDefault();
    setIsGenerating(true);
    setFeedback(null);

    const typeLabels = {
      workforce: 'Workforce Safety Compliance Report',
      incident: 'Incident Register Audit Report',
      camera_coverage: 'Camera Coverage & Uptime Report',
      comprehensive_safety: 'Comprehensive Plant Safety Report'
    };

    try {
      const created = await reportService.generateReport({
        reportType,
        format: reportFormat,
        dateFrom: dateFrom || null,
        dateTo: dateTo || null,
        title: typeLabels[reportType] || 'Safety Compliance Report'
      });
      setModalOpen(false);
      setFeedback({ type: 'success', text: 'New report generated successfully and ready for export.' });
      loadReports();
    } catch (err) {
      setFeedback({ type: 'error', text: err.message || 'Report generation failed.' });
    } finally {
      setIsGenerating(false);
      setTimeout(() => setFeedback(null), 4000);
    }
  };

  return (
    <>
      <Navbar
        title="Reports"
        subtitle="Generate and export operational compliance and safety reports"
        rightActions={
          <button
            className="btn btn-primary"
            onClick={() => setModalOpen(true)}
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <Plus size={15} />
            <span>Generate report</span>
          </button>
        }
      />

      <div className="page-container">
        {feedback && (
          <div style={{
            marginBottom: '1rem',
            padding: '12px 16px',
            backgroundColor: feedback.type === 'success' ? 'var(--success-bg)' : 'rgba(239, 68, 68, 0.1)',
            border: `1px solid ${feedback.type === 'success' ? 'var(--success-border)' : 'rgba(239, 68, 68, 0.3)'}`,
            color: feedback.type === 'success' ? 'var(--success-text)' : '#EF4444',
            borderRadius: '8px',
            fontSize: '13px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            {feedback.type === 'success' ? <Check size={16} /> : <AlertCircle size={16} />}
            <span>{feedback.text}</span>
          </div>
        )}

        <div className="operix-table-card">
          <div style={{ padding: '1.5rem', borderBottom: '1px solid var(--border-color)' }}>
            <h3 className="card-title">Report library</h3>
            <p className="card-subtitle">Safety, workforce, camera uptime and evidence exports in one place</p>
          </div>

          <table className="operix-table">
            <thead>
              <tr>
                <th>Report</th>
                <th>Period / Reference</th>
                <th>Format</th>
                <th style={{ textAlign: 'right' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {reportsList.map((rep) => (
                <tr key={rep.id || rep.report_id}>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <div className="btn-icon" style={{ backgroundColor: 'var(--bg-active-nav)', border: 'none', flexShrink: 0 }}>
                        {rep.format?.toLowerCase() === 'excel' ? (
                          <FileSpreadsheet size={16} color="#10B981" />
                        ) : (
                          <FileText size={16} color="var(--primary)" />
                        )}
                      </div>
                      <div>
                        <div style={{ fontWeight: 700, fontSize: '13.5px', color: 'var(--text-primary)' }}>
                          {rep.title}
                        </div>
                        <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
                          {rep.description || `${rep.type || 'Safety Audit'} · Generated ${rep.date || 'Today'}`}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
                    {rep.period || rep.date || 'Current Shift'}
                  </td>
                  <td>
                    <span
                      className="status-pill neutral font-mono"
                      style={{ fontSize: '11px', padding: '3px 8px', textTransform: 'uppercase' }}
                    >
                      {rep.format}
                    </span>
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <button
                      className="btn btn-secondary btn-sm"
                      disabled={downloadingId === (rep.id || rep.report_id)}
                      onClick={() => handleDownload(rep)}
                      style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                    >
                      <Download size={13} />
                      <span>{downloadingId === (rep.id || rep.report_id) ? 'Downloading...' : 'Download'}</span>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="table-footer-meta">
            <span>{reportsList.length} reports available</span>
            <span>Exports follow your factory's RBAC access permissions.</span>
          </div>
        </div>
      </div>

      {/* Generate Report Modal */}
      {modalOpen && (
        <div className="modal-overlay" onClick={() => setModalOpen(false)}>
          <div className="modal-dialog" onClick={e => e.stopPropagation()} style={{ maxWidth: '460px' }}>
            <div className="modal-header">
              <h3 className="modal-title">Generate Operational Report</h3>
              <button className="btn-icon" onClick={() => setModalOpen(false)}>✕</button>
            </div>
            <form onSubmit={handleGenerate}>
              <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div className="form-group" style={{ margin: 0 }}>
                  <label className="form-label">Report Type</label>
                  <select
                    className="form-control form-select"
                    value={reportType}
                    onChange={e => setReportType(e.target.value)}
                  >
                    <option value="workforce">Workforce Safety Compliance</option>
                    <option value="incident">Incident Register Audit</option>
                    <option value="camera_coverage">Camera Coverage & Uptime</option>
                    <option value="comprehensive_safety">Comprehensive Safety Report</option>
                  </select>
                </div>

                <div className="form-group" style={{ margin: 0 }}>
                  <label className="form-label">Export Format</label>
                  <div style={{ display: 'flex', gap: '12px' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', cursor: 'pointer' }}>
                      <input
                        type="radio"
                        name="format"
                        value="pdf"
                        checked={reportFormat === 'pdf'}
                        onChange={() => setReportFormat('pdf')}
                      />
                      <span>PDF Document (.pdf)</span>
                    </label>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', cursor: 'pointer' }}>
                      <input
                        type="radio"
                        name="format"
                        value="excel"
                        checked={reportFormat === 'excel'}
                        onChange={() => setReportFormat('excel')}
                      />
                      <span>Excel Spreadsheet (.xlsx)</span>
                    </label>
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                  <div className="form-group" style={{ margin: 0 }}>
                    <label className="form-label">From Date (Optional)</label>
                    <input
                      type="date"
                      className="form-control"
                      value={dateFrom}
                      onChange={e => setDateFrom(e.target.value)}
                    />
                  </div>
                  <div className="form-group" style={{ margin: 0 }}>
                    <label className="form-label">To Date (Optional)</label>
                    <input
                      type="date"
                      className="form-control"
                      value={dateTo}
                      onChange={e => setDateTo(e.target.value)}
                    />
                  </div>
                </div>
              </div>

              <div className="modal-footer" style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setModalOpen(false)}>
                  Cancel
                </button>
                <button type="submit" disabled={isGenerating} className="btn btn-primary">
                  {isGenerating ? 'Generating...' : 'Start Generation'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
