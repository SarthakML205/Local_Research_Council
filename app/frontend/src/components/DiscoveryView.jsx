import React, { useState, useMemo, useEffect } from 'react';
import {
  Layers,
  Sparkles,
  BookOpen,
  ExternalLink,
  ArrowRight,
  CheckCircle2,
  ShieldCheck,
  Network,
  Info,
  Maximize2,
  Clock,
  Cpu,
  Terminal,
  ChevronRight,
  Database,
  Flame,
} from 'lucide-react';

export default function DiscoveryView({ graph, onStageToTray, trayPapers = [] }) {
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const [zoomLevel, setZoomLevel] = useState(1);
  const [currentTime, setCurrentTime] = useState('--:--:--');

  // Live HUD clock
  useEffect(() => {
    const updateClock = () => {
      const now = new Date();
      setCurrentTime(now.toTimeString().split(' ')[0]);
    };
    updateClock();
    const timer = setInterval(updateClock, 1000);
    return () => clearInterval(timer);
  }, []);

  const nodes = useMemo(() => {
    if (graph?.nodes && graph.nodes.length > 0) return graph.nodes;
    return [
      {
        id: 'p_attn',
        label: 'Attention Is All You Need',
        type: 'paper',
        study_rank: 1,
        color: '#38bdf8',
        idc: 'LRC-P-01',
        summary: 'Multi-head self-attention replaces recurrence entirely, enabling dense global associative recall.',
        stack: 'PyTorch · Attention',
        status: 'Foundational',
      },
      {
        id: 'p_mamba',
        label: 'Mamba: Linear-Time Sequence Modeling',
        type: 'paper',
        study_rank: 2,
        color: '#a855f7',
        idc: 'LRC-P-02',
        summary: 'Selective state spaces achieve linear-time scaling without maintaining quadratic KV-cache.',
        stack: 'MLX · Selective SSM',
        status: 'SOTA Recurrence',
      },
      {
        id: 'prereq_linalg',
        label: 'Linear Algebra & State Space Projections',
        type: 'prerequisite',
        color: '#10b981',
        idc: 'LRC-REQ-01',
        summary: 'Continuous-to-discrete bilinear transforms (zero-order hold discretization) and matrix exponentials.',
        stack: 'Math Foundation',
        status: 'Prerequisite',
      },
      {
        id: 'field_hardware',
        label: 'Hardware-Aware Deep Learning on Apple Metal',
        type: 'field',
        color: '#f59e0b',
        idc: 'LRC-SYS-01',
        summary: 'Unified Memory architecture, eliminating PCIe host-to-device copying and maximizing Metal L2 cache residency.',
        stack: 'Apple Silicon M5',
        status: 'Core Target',
      },
    ];
  }, [graph]);

  const edges = useMemo(() => {
    if (graph?.edges && graph.edges.length > 0) return graph.edges;
    return [
      { id: 'e1', source: 'prereq_linalg', target: 'p_attn', relation: 'prerequisite_for', confidence: 0.96 },
      { id: 'e2', source: 'p_mamba', target: 'p_attn', relation: 'extends', confidence: 0.89 },
      { id: 'e3', source: 'p_mamba', target: 'field_hardware', relation: 'subfield_of', confidence: 0.84 },
    ];
  }, [graph]);

  // Compute neat 2D grid coordinates for graph nodes
  const nodePositions = useMemo(() => {
    const positions = {};
    const width = 860;

    const prerequisites = nodes.filter(n => n.type === 'prerequisite');
    const papers = nodes.filter(n => n.type === 'paper');
    const fields = nodes.filter(n => n.type === 'field');
    const others = nodes.filter(n => !['prerequisite', 'paper', 'field'].includes(n.type));

    // 1. Prerequisites along Top Tier (Y ~ 100)
    prerequisites.forEach((n, idx) => {
      const step = width / (prerequisites.length + 1);
      positions[n.id] = {
        x: Math.round(step * (idx + 1)),
        y: 110 + (idx % 2 === 0 ? 0 : 30),
      };
    });

    // 2. Papers across the Central Hero Tier (Y ~ 270)
    papers.forEach((n, idx) => {
      const step = width / (papers.length + 1);
      positions[n.id] = {
        x: Math.round(step * (idx + 1)),
        y: 280 + (idx % 2 === 0 ? -20 : 25),
      };
    });

    // 3. Fields along Bottom Tier (Y ~ 460)
    fields.forEach((n, idx) => {
      const step = width / (fields.length + 1);
      positions[n.id] = {
        x: Math.round(step * (idx + 1)),
        y: 460 + (idx % 2 === 0 ? 0 : 25),
      };
    });

    // 4. Others
    others.forEach((n, idx) => {
      const step = width / (others.length + 1);
      positions[n.id] = {
        x: Math.round(step * (idx + 1)),
        y: 370,
      };
    });

    return positions;
  }, [nodes]);

  const activeNode = nodes.find(n => n.id === selectedNodeId) || nodes.find(n => n.type === 'paper') || nodes[0];
  const isPaperStaged = activeNode?.type === 'paper' && trayPapers?.includes(activeNode.id);
  const connectedEdges = edges.filter(e => e.source === activeNode?.id || e.target === activeNode?.id);

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 420px', gap: '20px', height: 'calc(100vh - 100px)', padding: '0 16px 16px' }}>
      {/* Left Canvas: Minimalist Sci-Fi Operator Console */}
      <div className="plate" style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden', position: 'relative', borderRadius: '12px' }}>
        {/* Top Header / Operator Strip */}
        <div style={{
          padding: '12px 20px',
          borderBottom: '1px solid var(--line-faint)',
          background: 'rgba(3, 4, 5, 0.75)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '0.75rem',
              color: 'var(--red)',
              letterSpacing: 'var(--track-wide)',
              fontWeight: 700,
            }}>
              LRC // OPERATOR CONSOLE
            </span>
            <span style={{ color: 'var(--dim)' }}>·</span>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--hi)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              Pedagogical Curriculum &amp; Mind Map
            </span>
          </div>

          {/* Quick study rank pills */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', overflowX: 'auto', maxWidth: '480px' }}>
            {nodes.filter(n => n.type === 'paper').map((p, idx) => (
              <button
                key={p.id}
                className={`chip ${activeNode?.id === p.id ? 'on' : ''}`}
                style={{ fontSize: '0.7rem', padding: '4px 10px', height: '28px' }}
                onClick={() => setSelectedNodeId(p.id)}
              >
                <b>0{idx + 1}</b>
                <span>{p.label.length > 18 ? `${p.label.slice(0, 18)}...` : p.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Dynamic SVG Mind Map Canvas with Stark UI 26 Aesthetics */}
        <div style={{
          flex: 1,
          position: 'relative',
          overflow: 'hidden',
          background: 'radial-gradient(ellipse at 50% 50%, rgba(13, 18, 26, 0.6) 0%, rgba(3, 4, 5, 0.98) 100%)',
        }}>
          <svg
            viewBox="0 0 860 560"
            style={{ width: '100%', height: '100%', display: 'block' }}
          >
            <defs>
              <linearGradient id="edge-paper-grad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.85" />
                <stop offset="100%" stopColor="#a855f7" stopOpacity="0.85" />
              </linearGradient>
              <linearGradient id="edge-prereq-grad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#10b981" stopOpacity="0.85" />
                <stop offset="100%" stopColor="#38bdf8" stopOpacity="0.85" />
              </linearGradient>
              <filter id="neon-glow" x="-30%" y="-30%" width="160%" height="160%">
                <feGaussianBlur stdDeviation="5" result="blur" />
                <feComposite in="SourceGraphic" in2="blur" operator="over" />
              </filter>
            </defs>

            {/* Precision Grid Crosses */}
            <g opacity="0.3">
              {[120, 260, 400, 540, 680].map((x) =>
                [100, 220, 340, 460].map((y) => (
                  <path
                    key={`cross-${x}-${y}`}
                    d={`M ${x} ${y - 4} v 8 M ${x - 4} ${y} h 8`}
                    stroke="rgba(200, 214, 226, 0.25)"
                    strokeWidth="1"
                  />
                ))
              )}
            </g>

            {/* Connecting Curved Edges */}
            {edges.map(e => {
              const src = nodePositions[e.source] || { x: 200, y: 150 };
              const dst = nodePositions[e.target] || { x: 600, y: 350 };
              const midX = (src.x + dst.x) / 2;
              const midY = (src.y + dst.y) / 2 - 25;
              const isSelected = activeNode?.id === e.source || activeNode?.id === e.target;
              const strokeColor = e.relation === 'prerequisite_for' ? 'url(#edge-prereq-grad)' : 'url(#edge-paper-grad)';

              return (
                <g key={e.id} opacity={isSelected ? 1 : 0.45}>
                  <path
                    d={`M ${src.x} ${src.y} Q ${midX} ${midY} ${dst.x} ${dst.y}`}
                    fill="none"
                    stroke={strokeColor}
                    strokeWidth={isSelected ? '2.5' : '1.5'}
                    strokeDasharray={e.relation === 'prerequisite_for' ? '5 4' : 'none'}
                    filter={isSelected ? 'url(#neon-glow)' : 'none'}
                  />
                  {/* Relation Tag Pill */}
                  <rect
                    x={midX - 42}
                    y={midY - 9}
                    width="84"
                    height="18"
                    rx="3"
                    fill="rgba(3, 4, 5, 0.95)"
                    stroke="rgba(200, 214, 226, 0.3)"
                    strokeWidth="1"
                  />
                  <text
                    x={midX}
                    y={midY + 4}
                    fill="#e4ebf1"
                    fontSize="9"
                    fontFamily="var(--font-mono)"
                    textAnchor="middle"
                    letterSpacing="0.05em"
                  >
                    {e.relation}
                  </text>
                </g>
              );
            })}

            {/* Render Nodes with Stark Glowing Borders */}
            {nodes.map(n => {
              const pos = nodePositions[n.id] || { x: 430, y: 280 };
              const isSelected = activeNode?.id === n.id;
              const isPaper = n.type === 'paper';
              const isPrereq = n.type === 'prerequisite';

              const width = isPaper ? 140 : 120;
              const height = isPaper ? 54 : 44;
              const baseColor = n.color || (isPaper ? '#38bdf8' : isPrereq ? '#10b981' : '#f59e0b');

              return (
                <g
                  key={n.id}
                  transform={`translate(${pos.x - width / 2}, ${pos.y - height / 2})`}
                  onClick={() => setSelectedNodeId(n.id)}
                  style={{ cursor: 'pointer' }}
                >
                  {/* Outer Glowing Halo */}
                  {isSelected && (
                    <rect
                      x="-4"
                      y="-4"
                      width={width + 8}
                      height={height + 8}
                      rx="6"
                      fill="none"
                      stroke={baseColor}
                      strokeWidth="1.5"
                      opacity="0.75"
                      filter="url(#neon-glow)"
                    />
                  )}

                  {/* Node Rect Plate */}
                  <rect
                    width={width}
                    height={height}
                    rx="4"
                    fill="rgba(13, 18, 26, 0.9)"
                    stroke={isSelected ? baseColor : 'rgba(200, 214, 226, 0.22)'}
                    strokeWidth={isSelected ? '1.5' : '1'}
                  />

                  {/* Corner Accent Ticks (Stark UI style) */}
                  <line x1="0" y1="0" x2="8" y2="0" stroke={baseColor} strokeWidth="2" />
                  <line x1="0" y1="0" x2="0" y2="8" stroke={baseColor} strokeWidth="2" />
                  <line x1={width - 8} y1={height} x2={width} y2={height} stroke={baseColor} strokeWidth="2" />
                  <line x1={width} y1={height - 8} x2={width} y2={height} stroke={baseColor} strokeWidth="2" />

                  {/* Node Content */}
                  <text
                    x="10"
                    y="16"
                    fill={baseColor}
                    fontSize="9"
                    fontFamily="var(--font-mono)"
                    fontWeight="700"
                    letterSpacing="0.08em"
                  >
                    {n.idc || (isPaper ? `P-0${n.study_rank || 1}` : 'NODE')}
                  </text>

                  <text
                    x="10"
                    y="32"
                    fill="#e4ebf1"
                    fontSize="11"
                    fontFamily="var(--font-sans)"
                    fontWeight="600"
                  >
                    {n.label.length > 16 ? `${n.label.slice(0, 16)}...` : n.label}
                  </text>

                  <text
                    x="10"
                    y="45"
                    fill="var(--txt)"
                    fontSize="8"
                    fontFamily="var(--font-mono)"
                  >
                    {n.type.toUpperCase()}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>

        {/* Tabular Inspector HUD Bar across bottom (Augma Spec #info) */}
        <div className="hud-bar">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="idc">{activeNode?.idc || 'LRC-OP-01'}</span>
            <span className="nm">{activeNode?.label || 'Curriculum Node'}</span>
            <span className="chip" style={{ height: '22px', padding: '0 8px', fontSize: '0.65rem' }}>
              {activeNode?.type || 'paper'}
            </span>
          </div>

          <div className="stat">
            <span>Stack <b>{activeNode?.stack || 'Python 3.11 · MLX'}</b></span>
            <span>Status <b>{activeNode?.status || 'Active'}</b></span>
            <span>Security <b>100% LOCAL ZERO-CLOUD</b></span>
            <span>CLOCK <b style={{ color: 'var(--red)' }}>{currentTime}</b></span>
          </div>
        </div>
      </div>

      {/* Right Inspector Panel (Augma Spec #panel plate) */}
      <div className="plate" style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden', borderRadius: '12px', padding: '24px 22px' }}>
        {/* Panel Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{
              width: '26px',
              height: '26px',
              border: '1px solid var(--hair)',
              display: 'grid',
              placeItems: 'center',
              color: 'var(--hi)',
              background: 'rgba(200, 214, 226, 0.05)',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.75rem',
            }}>
              ⬡
            </div>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: 'var(--red)', letterSpacing: 'var(--track-wide)', fontWeight: 700 }}>
              {activeNode?.idc || 'AUG-LAB-01'}
            </span>
          </div>

          <span style={{ fontFamily: 'var(--font-display)', fontSize: '1.4rem', color: 'var(--red)', fontWeight: 300 }}>
            0{activeNode?.study_rank || 1}
          </span>
        </div>

        {/* Title & Technical Summary */}
        <h1 style={{
          fontSize: '1.4rem',
          fontWeight: 500,
          color: 'var(--hi)',
          letterSpacing: '0.04em',
          lineHeight: '1.2',
          marginBottom: '10px',
        }}>
          {activeNode?.label}
        </h1>

        <p style={{
          fontSize: '0.85rem',
          lineHeight: '1.6',
          color: 'var(--txt)',
          marginBottom: '20px',
        }}>
          {activeNode?.summary || 'Foundational architectural primitive providing theoretical boundaries for multi-agent academic debate.'}
        </p>

        {/* Tabular Metadata List (Augma DL style) */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '12px 16px',
          marginBottom: '24px',
          padding: '14px',
          background: 'rgba(3, 4, 5, 0.5)',
          border: '1px solid var(--line-faint)',
          borderRadius: '8px',
        }}>
          <div>
            <span style={{ fontSize: '0.7rem', color: 'var(--dim)', textTransform: 'uppercase', letterSpacing: 'var(--track-wide)' }}>Type</span>
            <p style={{ fontSize: '0.82rem', color: 'var(--hi)', fontWeight: 600, marginTop: '2px' }}>{activeNode?.type?.toUpperCase()}</p>
          </div>
          <div>
            <span style={{ fontSize: '0.7rem', color: 'var(--dim)', textTransform: 'uppercase', letterSpacing: 'var(--track-wide)' }}>Study Order</span>
            <p style={{ fontSize: '0.82rem', color: 'var(--hi)', fontWeight: 600, marginTop: '2px' }}>Rank #{activeNode?.study_rank || 1}</p>
          </div>
          <div>
            <span style={{ fontSize: '0.7rem', color: 'var(--dim)', textTransform: 'uppercase', letterSpacing: 'var(--track-wide)' }}>Qdrant Partition</span>
            <p style={{ fontSize: '0.82rem', color: '#10b981', fontWeight: 600, marginTop: '2px' }}>Isolated (gRPC 6334)</p>
          </div>
          <div>
            <span style={{ fontSize: '0.7rem', color: 'var(--dim)', textTransform: 'uppercase', letterSpacing: 'var(--track-wide)' }}>Memory Tier</span>
            <p style={{ fontSize: '0.82rem', color: 'var(--hi)', fontWeight: 600, marginTop: '2px' }}>&lt; 12.0 GB SLA</p>
          </div>
        </div>

        {/* Connected Relational Edges */}
        <div style={{ marginBottom: 'auto' }}>
          <span style={{ fontSize: '0.72rem', color: 'var(--mute)', textTransform: 'uppercase', letterSpacing: 'var(--track-wide)', display: 'block', marginBottom: '8px' }}>
            Connected Relational Graph ({connectedEdges.length})
          </span>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {connectedEdges.map(e => (
              <div
                key={e.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '8px 12px',
                  background: 'rgba(200, 214, 226, 0.04)',
                  border: '1px solid var(--line-faint)',
                  borderRadius: '6px',
                  fontSize: '0.75rem',
                  fontFamily: 'var(--font-mono)',
                }}
              >
                <span style={{ color: 'var(--hi)' }}>{e.source} ➔ {e.target}</span>
                <span style={{ color: 'var(--red)', fontWeight: 700 }}>{e.relation}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Action Buttons (Augma .btn.pri with corner brackets) */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '24px' }}>
          {activeNode?.type === 'paper' && (
            <button
              className={`btn-stark ${isPaperStaged ? '' : 'pri'}`}
              onClick={() => onStageToTray && onStageToTray(activeNode.id)}
              disabled={isPaperStaged}
              style={{ width: '100%', justifyContent: 'center' }}
            >
              <Database size={14} />
              {isPaperStaged ? 'Already Staged in Council Tray' : 'Stage to Council Tray'}
            </button>
          )}

          <a
            href={`https://arxiv.org/abs/${activeNode?.id?.replace('p_', '')}`}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-stark"
            style={{ width: '100%', justifyContent: 'center' }}
          >
            <ExternalLink size={14} /> View ArXiv Source Paper
          </a>
        </div>
      </div>
    </div>
  );
}
