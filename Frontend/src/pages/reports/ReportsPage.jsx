import React, { useState } from 'react';
import Navbar from '../../components/common/Navbar';
import { useData } from '../../context/DataContext';
import { Download, Plus, FileText, Check } from 'lucide-react';

export default function ReportsPage() {
  const { reports } = useData();
  const [isGenerating, setIsGenerating] = useState(false);
  const [downloadSuccess, setDownloadSuccess] = useState('');

  const handleDownload = (title, format) => {
    setDownloadSuccess(`Downloaded ${title}.${format.toLowerCase()}`);
    setTimeout(() => setDownloadSuccess(''), 3000);
  };

  const handleGenerate = () => {
    setIsGenerating(true);
    setTimeout(() => {
      setIsGenerating(false);
      setDownloadSuccess('New report generated successfully and ready for export.');
      setTimeout(() => setDownloadSuccess(''), 4000);
    }, 1200);
  };

  return (
    <>
      <Navbar
        title="Reports"
        subtitle="Generate and review operational reports"
        rightActions={
          <button
            className="btn btn-primary"
            disabled={isGenerating}
            onClick={handleGenerate}
          >
            <Plus size={15} />
            {isGenerating ? 'Generating...' : 'Generate report'}
          </button>
        }
      />

      <div className="page-container">
        {downloadSuccess && (
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
            <span>{downloadSuccess}</span>
          </div>
        )}

        <div className="operix-table-card">
          <div style={{ padding: '1.5rem', borderBottom: '1px solid var(--border-color)' }}>
            <h3 className="card-title">Report library</h3>
            <p className="card-subtitle">Safety, workforce and evidence exports in one place</p>
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
              {reports.map((rep) => (
                <tr key={rep.id}>
                  <td>
                    <div style={{ fontWeight: 700, fontSize: '13.5px', color: 'var(--text-primary)' }}>
                      {rep.title}
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
                      {rep.description}
                    </div>
                  </td>
                  <td style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
                    {rep.period}
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
                      onClick={() => handleDownload(rep.title, rep.format)}
                    >
                      <Download size={13} />
                      Download
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="table-footer-meta">
            <span>{reports.length} reports available</span>
            <span>Exports follow your plant's access permissions.</span>
          </div>
        </div>
      </div>
    </>
  );
}
