import React from 'react';
import { Network, Users, BookOpen, Activity, ShieldCheck, Sparkles, Plus } from 'lucide-react';

export default function Navigation({ activeTab, setActiveTab, health, memoryMb, errorCount }) {
  // Determine LED status
  const isHealthy = health?.status === 'healthy';
  const isWarning = memoryMb > 16000 || errorCount > 0;
  const isCeiling = memoryMb > 18000;

  const ledColor = isCeiling ? '#f43f5e' : isWarning ? '#f59e0b' : '#10b981';

  return (
    <header className="glass-panel" style={{
      position: 'sticky',
      top: 0,
      zIndex: 50,
      margin: '12px 16px',
      padding: '12px 24px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      border: '1px solid rgba(255, 255, 255, 0.1)',
    }}>
      {/* Brand & Sovereign Identity */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <div style={{
          width: '36px',
          height: '36px',
          borderRadius: '10px',
          background: 'linear-gradient(135deg, #0284c7 0%, #38bdf8 100%)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#07090e',
          fontWeight: '900',
          boxShadow: '0 0 16px rgba(56, 189, 248, 0.4)',
        }}>
          ⚛️
        </div>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h1 style={{ fontSize: '1.15rem', fontWeight: 800, letterSpacing: '-0.02em' }}>
              Local Research Council
            </h1>
            <span className="badge badge-cyan" style={{ fontSize: '0.65rem', padding: '2px 8px' }}>
              <ShieldCheck size={12} /> Apple Silicon M5
            </span>
          </div>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Zero-Cloud Sovereign Multi-Agent Debate Engine
          </p>
        </div>
      </div>

      {/* Navigation Tabs */}
      <nav style={{ display: 'flex', gap: '8px' }}>
        {[
          { id: 'session', label: 'New Session', icon: Sparkles, highlight: true },
          { id: 'discovery', label: 'Discovery Mind Map', icon: Network },
          { id: 'council', label: 'Council Chamber', icon: Users },
          { id: 'library', label: 'Library Bookshelf', icon: BookOpen },
          { id: 'dashboard', label: 'Telemetry & Physics', icon: Activity, badge: errorCount > 0 ? errorCount : null },
        ].map(tab => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '8px 16px',
                borderRadius: '8px',
                border: 'none',
                background: isActive
                  ? 'rgba(56, 189, 248, 0.15)'
                  : tab.highlight
                  ? 'rgba(56, 189, 248, 0.05)'
                  : 'transparent',
                color: isActive ? '#38bdf8' : tab.highlight ? '#7dd3fc' : 'var(--text-muted)',
                fontWeight: isActive ? 700 : 500,
                fontSize: '0.875rem',
                cursor: 'pointer',
                transition: 'all 0.2s',
                boxShadow: isActive ? 'inset 0 0 0 1px rgba(56, 189, 248, 0.4)' : 'none',
              }}
            >
              <Icon size={16} />
              <span>{tab.label}</span>
              {tab.badge && (
                <span className="badge badge-rose" style={{ padding: '1px 6px', fontSize: '0.65rem' }}>
                  {tab.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Physics Health LED & Action Button */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          background: 'rgba(0, 0, 0, 0.4)',
          padding: '6px 14px',
          borderRadius: '9999px',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          fontSize: '0.75rem',
          fontFamily: 'var(--font-mono)',
        }}>
          <span style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            backgroundColor: ledColor,
            boxShadow: `0 0 10px ${ledColor}`,
          }} />
          <span style={{ color: 'var(--text-dim)' }}>RAM:</span>
          <span style={{ color: memoryMb > 16000 ? '#f43f5e' : '#38bdf8', fontWeight: 700 }}>
            {(memoryMb / 1024).toFixed(2)} GB
          </span>
          <span style={{ color: 'var(--text-dim)' }}>/ 18.0 GB</span>
        </div>

        {activeTab !== 'session' && (
          <button
            className="btn-primary"
            style={{ padding: '8px 14px', fontSize: '0.8rem' }}
            onClick={() => setActiveTab('session')}
          >
            <Plus size={14} /> New Query
          </button>
        )}
      </div>
    </header>
  );
}
