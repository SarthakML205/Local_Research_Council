import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  Network,
  Users,
  BookOpen,
  Activity,
  Layers,
  ShieldCheck,
  Cpu,
  Clock,
  Flame,
  AlertTriangle,
} from 'lucide-react';

export default function Navigation({ activeTab, setActiveTab, health, memoryMb, errorCount, trayCount = 0 }) {
  const [clock, setClock] = useState('--:--');

  useEffect(() => {
    const update = () => {
      const now = new Date();
      setClock(now.toTimeString().split(' ')[0].slice(0, 5));
    };
    update();
    const timer = setInterval(update, 1000);
    return () => clearInterval(timer);
  }, []);

  const navItems = [
    { id: 'session', num: '01', label: 'INQUIRY LAUNCHER', icon: Sparkles, desc: 'Query arXiv & Ingest' },
    { id: 'shelf', num: '02', label: '3D ROTATING SHELF', icon: Layers, desc: 'Visual 3D Paper Shelf' },
    { id: 'discovery', num: '03', label: 'OPERATOR MIND MAP', icon: Network, desc: 'Curriculum & Graph' },
    { id: 'council', num: '04', label: 'DEBATE COUNCIL', icon: Users, desc: 'Stark AI Dialogue', badge: trayCount > 0 ? `${trayCount}P` : null },
    { id: 'library', num: '05', label: 'LIBRARY ARCHIVE', icon: BookOpen, desc: 'Paper Sovereign Store' },
    { id: 'dashboard', num: '06', label: 'HARDWARE M5 HUD', icon: Activity, desc: 'Memory & Telemetry', alert: errorCount > 0 ? errorCount : null },
  ];

  const ramGb = (memoryMb / 1024.0).toFixed(2);

  return (
    <aside
      className="plate"
      style={{
        width: '260px',
        height: 'calc(100vh - 24px)',
        margin: '12px 0 12px 12px',
        borderRadius: '6px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        padding: '20px 16px',
        zIndex: 50,
        flexShrink: 0,
      }}
    >
      {/* Top Brand & Identity */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
          <div style={{
            width: '32px',
            height: '32px',
            border: '1.5px solid var(--red)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--red)',
            fontFamily: 'var(--font-mono)',
            fontWeight: 900,
            fontSize: '1rem',
            background: 'rgba(200, 16, 46, 0.1)',
          }}>
            ⚛
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{
                fontFamily: 'var(--font-display)',
                fontSize: '1.1rem',
                fontWeight: 600,
                color: 'var(--hi)',
                letterSpacing: '0.1em',
              }}>
                LRC REPO
              </span>
              <span style={{
                fontSize: '0.8rem',
                color: 'var(--red)',
                fontFamily: 'var(--font-mono)',
                fontWeight: 700,
              }}>
                04
              </span>
            </div>
            <p style={{
              fontSize: '0.68rem',
              color: 'var(--dim)',
              fontFamily: 'var(--font-mono)',
              letterSpacing: 'var(--track-wide)',
            }}>
              STARK UI 26 · SOVEREIGN
            </p>
          </div>
        </div>

        {/* Status Line */}
        <div style={{
          borderTop: '1px solid var(--line-faint)',
          paddingTop: '8px',
          marginBottom: '20px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          fontSize: '0.65rem',
          fontFamily: 'var(--font-mono)',
          color: 'var(--mute)',
        }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#10b981', display: 'inline-block' }} />
            100% LOCAL
          </span>
          <span style={{ color: 'var(--red)' }}>APPLE M5 24GB</span>
        </div>

        {/* Navigation Option Chips with Corner Brackets */}
        <nav style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {navItems.map(item => {
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`chip ${isActive ? 'on' : ''}`}
                style={{
                  width: '100%',
                  height: '46px',
                  justifyContent: 'flex-start',
                  padding: '0 12px',
                  borderRadius: '0px',
                  position: 'relative',
                  border: isActive ? '1px solid var(--red)' : '1px solid var(--line)',
                  background: isActive ? 'rgba(200, 16, 46, 0.12)' : 'rgba(3, 4, 5, 0.5)',
                  textAlign: 'left',
                }}
              >
                <span style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  color: isActive ? 'var(--red)' : 'var(--mute)',
                  minWidth: '22px',
                }}>
                  {item.num}
                </span>

                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{
                    fontSize: '0.78rem',
                    fontWeight: 600,
                    color: isActive ? 'var(--hi)' : 'var(--txt)',
                    letterSpacing: '0.04em',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  }}>
                    {item.label}
                  </div>
                </div>

                {item.badge && (
                  <span style={{
                    fontSize: '0.62rem',
                    background: 'var(--red)',
                    color: '#fff',
                    padding: '1px 5px',
                    fontFamily: 'var(--font-mono)',
                    fontWeight: 700,
                  }}>
                    {item.badge}
                  </span>
                )}

                {item.alert && (
                  <span style={{
                    fontSize: '0.62rem',
                    background: 'rgba(244, 63, 94, 0.2)',
                    color: '#fb7185',
                    border: '1px solid #f43f5e',
                    padding: '1px 5px',
                    fontFamily: 'var(--font-mono)',
                  }}>
                    {item.alert}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Bottom Sidebar HUD Bar */}
      <div style={{
        borderTop: '1px solid var(--line-faint)',
        paddingTop: '14px',
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
        fontSize: '0.7rem',
        fontFamily: 'var(--font-mono)',
      }}>
        {/* Memory Bar */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px', color: 'var(--dim)' }}>
            <span>RAM (M5 ENVELOPE)</span>
            <span style={{ color: 'var(--hi)' }}>{ramGb} / 12.0 GB</span>
          </div>
          <div style={{ width: '100%', height: '3px', background: 'var(--line-faint)', position: 'relative' }}>
            <div style={{
              width: `${Math.min(100, (parseFloat(ramGb) / 12.0) * 100)}%`,
              height: '100%',
              background: parseFloat(ramGb) > 16.0 ? 'var(--red)' : '#10b981',
            }} />
          </div>
        </div>

        {/* Live Clock & Node Info */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: 'var(--dim)', paddingTop: '4px' }}>
          <span>NODE <b>LRC-01</b></span>
          <span>BKK <b>{clock}</b></span>
        </div>
      </div>
    </aside>
  );
}
