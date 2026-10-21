import React, { useState } from 'react';
import { Layers, Sparkles, BookOpen, ExternalLink, ArrowRight, CheckCircle2 } from 'lucide-react';

export default function DiscoveryView({ graph, onStageToTray, trayPapers }) {
  const [selectedNode, setSelectedNode] = useState(null);

  // Fallback demo graph if backend is still initializing
  const nodes = graph?.nodes || [
    { id: 'p_attn', label: 'Attention Is All You Need', type: 'paper', study_rank: 1, color: '#38bdf8', summary: 'Multi-head self-attention replaces recurrence entirely.' },
    { id: 'p_mamba', label: 'Mamba: Linear-Time Sequence Modeling', type: 'paper', study_rank: 2, color: '#a855f7', summary: 'Selective state spaces achieve linear scaling without quadratic attention.' },
    { id: 'prereq_linalg', label: 'Linear Algebra & Projections', type: 'prerequisite', color: '#10b981', summary: 'Fundamental matrix operations and multi-head projections.' },
    { id: 'field_hardware', label: 'Hardware-Aware Deep Learning', type: 'field', color: '#f59e0b', summary: 'Kernel IO efficiency and unified memory cache hierarchies.' },
  ];

  const edges = graph?.edges || [
    { id: 'e1', source: 'prereq_linalg', target: 'p_attn', relation: 'prerequisite_for', confidence: 0.95 },
    { id: 'e2', source: 'p_mamba', target: 'p_attn', relation: 'extends', confidence: 0.88 },
    { id: 'e3', source: 'p_mamba', target: 'field_hardware', relation: 'subfield_of', confidence: 0.82 },
  ];

  // Coordinates mapping for clean force layout simulation
  const nodePositions = {
    'p_attn': { x: 280, y: 180 },
    'p_mamba': { x: 540, y: 260 },
    'prereq_linalg': { x: 120, y: 320 },
    'field_hardware': { x: 680, y: 120 },
  };

  const activeNode = selectedNode || nodes[0];

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 420px', gap: '20px', height: 'calc(100vh - 100px)', padding: '0 16px 16px' }}>
      {/* Left Canvas: Sci-Fi Mind Map */}
      <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden', position: 'relative' }}>
        {/* Pedagogical Study Order Ribbon */}
        <div style={{
          padding: '12px 20px',
          borderBottom: '1px solid var(--border-color)',
          background: 'rgba(0, 0, 0, 0.25)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Layers size={16} color="#38bdf8" />
            <span style={{ fontSize: '0.85rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Pedagogical Study Order
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {nodes.filter(n => n.type === 'paper').map((p, idx) => (
              <React.Fragment key={p.id}>
                <span className="badge badge-cyan" style={{ cursor: 'pointer' }} onClick={() => setSelectedNode(p)}>
                  #{idx + 1} {p.label.slice(0, 16)}...
                </span>
                {idx < nodes.filter(n => n.type === 'paper').length - 1 && (
                  <ArrowRight size={12} color="var(--text-dim)" />
                )}
              </React.Fragment>
            ))}
          </div>
        </div>

        {/* Dynamic SVG Mind Map Canvas */}
        <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
          <svg style={{ width: '100%', height: '100%', minHeight: '500px' }}>
            <defs>
              <linearGradient id="edge-cyan" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.8" />
                <stop offset="100%" stopColor="#a855f7" stopOpacity="0.8" />
              </linearGradient>
              <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur stdDeviation="3" result="blur" />
                <feComposite in="SourceGraphic" in2="blur" operator="over" />
              </filter>
            </defs>

            {/* Edges */}
            {edges.map(e => {
              const src = nodePositions[e.source] || { x: 200, y: 200 };
              const dst = nodePositions[e.target] || { x: 400, y: 300 };
              const midX = (src.x + dst.x) / 2;
              const midY = (src.y + dst.y) / 2 - 30;

              return (
                <g key={e.id}>
                  <path
                    d={`M ${src.x} ${src.y} Q ${midX} ${midY} ${dst.x} ${dst.y}`}
                    fill="none"
                    stroke="url(#edge-cyan)"
                    strokeWidth="2.5"
                    strokeDasharray={e.relation === 'prerequisite_for' ? '4 4' : 'none'}
                    filter="url(#glow)"
                  />
                  <text
                    x={midX}
                    y={midY}
                    fill="#94a3b8"
                    fontSize="10"
                    fontFamily="var(--font-mono)"
                    textAnchor="middle"
                    style={{ background: '#07090e', padding: '2px 6px' }}
                  >
                    {e.relation} ({(e.confidence * 100).toFixed(0)}%)
                  </text>
                </g>
              );
            })}

            {/* Nodes */}
            {nodes.map(n => {
              const pos = nodePositions[n.id] || { x: 300, y: 300 };
              const isSelected = activeNode?.id === n.id;

              return (
                <g
                  key={n.id}
                  transform={`translate(${pos.x}, ${pos.y})`}
                  style={{ cursor: 'pointer' }}
                  onClick={() => setSelectedNode(n)}
                >
                  <circle
                    r={isSelected ? 32 : 26}
                    fill="#0f172a"
                    stroke={n.color}
                    strokeWidth={isSelected ? 3 : 2}
                    filter="url(#glow)"
                    style={{ transition: 'all 0.3s' }}
                  />
                  <text
                    textAnchor="middle"
                    dy="4"
                    fill={n.color}
                    fontSize={isSelected ? '14' : '12'}
                    fontWeight="800"
                    fontFamily="var(--font-display)"
                  >
                    {n.type === 'paper' ? `P${n.study_rank || 1}` : n.type === 'prerequisite' ? 'PR' : 'FL'}
                  </text>
                  <text
                    textAnchor="middle"
                    dy="45"
                    fill="#f1f5f9"
                    fontSize="11"
                    fontWeight="600"
                    fontFamily="var(--font-sans)"
                  >
                    {n.label.length > 24 ? n.label.slice(0, 22) + '...' : n.label}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>
      </div>

      {/* Right Panel: Modular 8-Tile Paper HUD */}
      <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <span className="badge badge-cyan" style={{ marginBottom: '4px' }}>
              {activeNode.type.toUpperCase()} INSPECTOR
            </span>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 800 }}>{activeNode.label}</h3>
          </div>
          {activeNode.type === 'paper' && (
            <button
              className="btn-primary"
              style={{ fontSize: '0.8rem', padding: '6px 12px' }}
              onClick={() => onStageToTray(activeNode.id)}
            >
              {trayPapers?.includes(activeNode.id) ? (
                <>
                  <CheckCircle2 size={14} /> Staged in Council
                </>
              ) : (
                'Stage in Council'
              )}
            </button>
          )}
        </div>

        {/* 8 Modular Tiles Grid */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {/* Tile 1: TLDR & Study Rank */}
          <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
            <span style={{ fontSize: '0.7rem', color: '#38bdf8', fontWeight: 700, textTransform: 'uppercase' }}>Tile 1: TLDR & Rank</span>
            <p style={{ fontSize: '0.85rem', marginTop: '4px' }}>
              {activeNode.summary || 'Grounding findings indicate superior scaling throughput without cache memory degradation.'}
            </p>
          </div>

          {/* Tile 2: Core Problem Statement */}
          <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
            <span style={{ fontSize: '0.7rem', color: '#f43f5e', fontWeight: 700, textTransform: 'uppercase' }}>Tile 2: Core Problem</span>
            <p style={{ fontSize: '0.85rem', marginTop: '4px' }}>
              Overcoming the quadratic $O(N^2)$ computational and memory bottleneck in multi-head attention on unified memory.
            </p>
          </div>

          {/* Tile 3: Methodology & Architecture */}
          <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
            <span style={{ fontSize: '0.7rem', color: '#a855f7', fontWeight: 700, textTransform: 'uppercase' }}>Tile 3: Methodology</span>
            <p style={{ fontSize: '0.85rem', marginTop: '4px' }}>
              Selective state-space parameters dynamically modulated by current input tokens, implemented via hardware-aware scan kernels.
            </p>
          </div>

          {/* Tile 4: Key Quantitative Results */}
          <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
            <span style={{ fontSize: '0.7rem', color: '#10b981', fontWeight: 700, textTransform: 'uppercase' }}>Tile 4: Quantitative Results</span>
            <p style={{ fontSize: '0.85rem', marginTop: '4px' }}>
              5x higher throughput compared to standard Transformers, constant memory decoding footprint across 100k+ token contexts.
            </p>
          </div>

          {/* Tile 5: Significance */}
          <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
            <span style={{ fontSize: '0.7rem', color: '#f59e0b', fontWeight: 700, textTransform: 'uppercase' }}>Tile 5: Significance</span>
            <p style={{ fontSize: '0.85rem', marginTop: '4px' }}>
              Demonstrates that recurrent linear scaling matches or exceeds dense attention quality when selection dynamics are hardware-aligned.
            </p>
          </div>

          {/* Tile 6: Research Gaps */}
          <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)', fontWeight: 700, textTransform: 'uppercase' }}>Tile 7: Admitted Gaps</span>
            <p style={{ fontSize: '0.85rem', marginTop: '4px' }}>
              Requires fast SRAM cache buffers; continuous associative recall can regress on synthetic needle-in-haystack lookups.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
