import React, { useState } from 'react';
import Navbar from '../../components/common/Navbar';
import MetricCard from '../../components/common/MetricCard';
import WorkforceDeptChart from '../../components/charts/WorkforceDeptChart';
import IdleTimeChart from '../../components/charts/IdleTimeChart';
import { Calendar } from 'lucide-react';
import { useAnalytics } from '../../hooks';

export default function WorkforceAnalyticsPage() {
  const [selectedRange, setSelectedRange] = useState('This week · Nov 8 – 14');
  const { metrics, departments, idleZones } = useAnalytics(selectedRange);

  return (
    <>
      <Navbar
        title="Workforce Analytics"
        subtitle="Net working hours, idle time and breaks"
        rightActions={
          <div className="btn btn-secondary btn-sm" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Calendar size={14} color="var(--text-muted)" />
            <span>{selectedRange}</span>
          </div>
        }
      />

      <div className="page-container">
        {/* Top 4 KPI Metrics */}
        <div className="metrics-grid">
          <MetricCard
            label="Net working hours"
            value={metrics?.netHours || "1,284 h"}
            delta={metrics?.netHoursDelta || "▲ 3.1% vs last week"}
            deltaType="up"
          />
          <MetricCard
            label="Idle time"
            value={metrics?.idleTime || "11.6%"}
            delta={metrics?.idleTimeDelta || "▼ 0.9% vs last week"}
            deltaType="down"
          />
          <MetricCard
            label="Avg. break"
            value={metrics?.avgBreak || "42 min"}
            delta={metrics?.avgBreakDelta || "within policy"}
            deltaType="subtle"
          />
          <MetricCard
            label="Fatigue flags"
            value={metrics?.fatigueFlags || "9"}
            delta={metrics?.fatigueFlagsDelta || "▲ 3 today"}
            deltaType="danger"
          />
        </div>

        {/* 2 Column Charts */}
        <div className="grid-2col-equal">
          {/* Net hours by department */}
          <div className="operix-card">
            <h3 className="card-title">Net hours by department</h3>
            <p className="card-subtitle">Productive time across the current reporting week</p>
            <WorkforceDeptChart data={departments} />
          </div>

          {/* Idle time by zone */}
          <div className="operix-card">
            <h3 className="card-title">Idle time by zone</h3>
            <p className="card-subtitle">Share of observed time · lower is better</p>
            <IdleTimeChart data={idleZones} />
          </div>
        </div>
      </div>
    </>
  );
}
