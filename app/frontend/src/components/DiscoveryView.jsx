import React, { useState, useMemo } from 'react';
import { Layers, Sparkles, BookOpen, ExternalLink, ArrowRight, CheckCircle2, ShieldCheck, Network, Info } from 'lucide-react';

export default function DiscoveryView({ graph, onStageToTray, trayPapers }) {
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const [zoomLevel, setZoomLevel] = useState(1);

  const nodes = useMemo(() => {
    if (graph?.nodes && graph.nodes.length > 0) return graph.nodes;
    return [
      { id: 'p_attn', label: 'Attention Is All You Need', type: 'paper', study_rank: 1, color: '#38bdf8', summary: 'Multi-head self-attention replaces recurrence entirely.' },
      { id: 'p_mamba', label: 'Mamba: Linear-Time Sequence Modeling', type: 'paper', study_rank: 2, color: '#a855f7', summary: 'Selective state spaces achieve linear scaling without quadratic attention.' },
      { id: 'prereq_linalg', label: 'Linear Algebra & Projections', type: 'prerequisite', color: '#10b981', summary: 'Fundamental matrix operations and multi-head projections.' },
      { id: 'field_hardware', label: 'Hardware-Aware Deep Learning', type: 'field', color: '#f59e0b', summary: 'Kernel IO efficiency and unified memory cache hierarchies.' },
    ];
  }, [graph]);

  const edges = useMemo(() => {
    if (graph?.edges && graph.edges.length > 0) return graph.edges;
    return [
      { id: 'e1', source: 'prereq_linalg', target: 'p_attn', relation: 'prerequisite_for', confidence: 0.95 },
      { id: 'e2', source: 'p_mamba', target: 'p_attn', relation: 'extends', confidence: 0.88 },
      { id: 'e3', source: 'p_mamba', target: 'field_hardware', relation: 'subfield_of', confidence: 0.82 },
    ];
  }, [graph]);

  // Dynamically compute clean, non-overlapping coordinates for any arbitrary graph
  const nodePositions = useMemo(() => {
    const positions = {};
    const width = 860;
    const height = 580;

    const prerequisites = nodes.filter(n => n.type === 'prerequisite');
    const papers = nodes.filter(n => n.type === 'paper');
    const fields = nodes.filter(n => n.type === 'field');
    const others = nodes.filter(n => !['prerequisite', 'paper', 'field'].includes(n.type));

    // 1. Prerequisites along Top Tier (Y ~ 100-140)
    prerequisites.forEach((n, idx) => {
      const step = width / (prerequisites.length + 1);
      positions[n.id] = {
        x: Math.round(step * (idx + 1)),
        y: 110 + (idx % 2 === 0 ? 0 : 35),
      };
    });

    // 2. Papers across the Central Hero Tier (Y ~ 270-340)
    papers.forEach((n, idx) => {
      const step = width / (papers.length + 1);
      positions[n.id] = {
        x: Math.round(step * (idx + 1)),
        y: 290 + (idx % 2 === 0 ? -25 : 30),
      };
    });

    // 3. Fields along Bottom Tier (Y ~ 470-510)
    fields.forEach((n, idx) => {
      const step = width / (fields.length + 1);
      positions[n.id] = {
        x: Math.round(step * (idx + 1)),
        y: 480 + (idx % 2 === 0 ? 0 : 30),
      };
    });

    // 4. Any remaining nodes
    others.forEach((n, idx) => {
      const step = width / (others.length + 1);
      positions[n.id] = {
        x: Math.round(step * (idx + 1)),
        y: 390,
      };
    });

    return positions;
  }, [nodes]);

  const activeNode = nodes.find(n => n.id === selectedNodeId) || nodes.find(n => n.type === 'paper') || nodes[0];
  const isPaperStaged = activeNode?.type === 'paper' && trayPapers?.includes(activeNode.id);

  // Filter relationships connected to the active node
  const connectedEdges = edges.filter(e => e.source === activeNode?.id || e.target === activeNode?.id);

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 400px', gap: '20px', height: 'calc(100vh - 100px)', padding: '0 16px 16px' }}>
      {/* Left Canvas: Sci-Fi Mind Map */}
      <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden', position: 'relative' }}>
        {/* Pedagogical Study Order Ribbon */}
        <div style={{
          padding: '14px 20px',
          borderBottom: '1px solid var(--border-color)',
          background: 'rgba(0, 0, 0, 0.3)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Network size={18} color="#38bdf8" />
            <span style={{ fontSize: '0.85rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#f8fafc' }}>
              Pedagogical Curriculum Mind Map
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflowX: 'auto', maxWidth: '500px' }}>
            {nodes.filter(n => n.type === 'paper').map((p, idx) => (
              <React.Fragment key={p.id}>
                <button
                  className="badge"
                  style={{
                    background: activeNode?.id === p.id ? 'rgba(56, 189, 248, 0.25)' : 'rgba(255, 255, 255, 0.05)',
                    border: activeNode?.id === p.id ? '1px solid #38bdf8' : '1px solid rgba(255, 255, 255, 0.1)',
                    color: activeNode?.id === p.id ? '#38bdf8' : '#cbd5e1',
                    cursor: 'pointer',
                    fontSize: '0.75rem',
                    padding: '4px 10px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                  }}
                  onClick={() => setSelectedNodeId(p.id)}
                >
                  <span style={{ fontWeight: 800 }}>#{idx + 1}</span>
                  <span>{p.label.length > 20 ? `${p.label.slice(0, 20)}...` : p.label}</span>
                </button>
                {idx < nodes.filter(n => n.type === 'paper').length - 1 && (
                  <ArrowRight size={12} color="var(--text-dim)" />
                )}
              </React.Fragment>
            ))}
          </div>
        </div>

        {/* Dynamic SVG Mind Map Canvas */}
        <div style={{ flex: 1, position: 'relative', overflow: 'hidden', background: 'radial-gradient(ellipse at 50% 50%, rgba(15, 23, 42, 0.6) 0%, rgba(3, 7, 18, 0.95) 100%)' }}>
          <svg
            viewBox="0 0 860 580"
            style={{ width: '100%', height: '100%', display: 'block' }}
          >
            <defs>
              <linearGradient id="edge-paper-grad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.85" />
                <stop offset="100%" stopColor="#a855f7" stopOpacity="0.85" />
              </linearGradient>
              <linearGradient id="edge-prereq-grad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#10b981" stopOpacity="0.8" />
                <stop offset="100%" stopColor="#38bdf8" stopOpacity="0.8" />
              </linearGradient>
              <filter id="neon-glow" x="-30%" y="-30%" width="160%" height="160%">
                <feGaussianBlur stdDeviation="4" result="blur" />
                <feComposite in="SourceGraphic" in2="blur" operator="over" />
              </filter>
            </defs>

            {/* Background Grid Pattern */}
            <g opacity="0.08">
              {[...Array(9)].map((_, i) => (
                <line key={`vl-${i}`} x1={i * 100} y1="0" x2={i * 100} y2="580" stroke="#38bdf8" strokeWidth="1" />
              ))}
              {[...Array(6)].map((_, i) => (
                <line key={`hl-${i}`} x1="0" y1={i * 100} x2="860" y2={i * 100} stroke="#38bdf8" strokeWidth="1" />
              ))}
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
                <g key={e.id} opacity={isSelected ? 1 : 0.65}>
                  <path
                    d={`M ${src.x} ${src.y} Q ${midX} ${midY} ${dst.x} ${dst.y}`}
                    fill="none"
                    stroke={strokeColor}
                    strokeWidth={isSelected ? '3' : '2'}
                    strokeDasharray={e.relation === 'prerequisite_for' ? '6 4' : 'none'}
                    filter={isSelected ? 'url(#neon-glow)' : 'none'}
                  />
                  {/* Edge Relation Pill */}
                  <rect
                    x={midX - 44}
                    y={midY - 10}
                    width="88"
                    height="18"
                    rx="9"
                    fill="rgba(15, 23, 42, 0.9)"
                    stroke="rgba(56, 189, 248, 0.4)"
                    strokeWidth="1"
                  />
                  <text
                    x={midX}
                    y={midY + 3}
                    fill="#94a3b8"
                    fontSize="9"
                    fontFamily="var(--font-mono)"
                    textAnchor="middle"
                  >
                    {e.relation}
                  </text>
                </g>
              );
            })}

            {/* Render Nodes */}
            {nodes.map(n => {
              const pos = nodePositions[n.id] || { x: 430, y: 290 };
              const isSelected = activeNode?.id === n.id;
              const isPaper = n.type === 'paper';
              const isPrereq = n.type === 'prerequisite';

              const radius = isPaper ? 28 : (isPrereq ? 20 : 18);
              const baseColor = n.color || (isPaper ? '#38bdf8' : (isPrereq ? '#10b981' : '#f59e0b'));

              return (
                <g
                  key={n.id}
                  transform={`translate(${pos.x}, ${pos.y})`}
                  onClick={() => setSelectedNodeId(n.id)}
                  style={{ cursor: 'pointer' }}
                >
                  {/* Outer Pulsing Halo when selected */}
                  {isSelected && (
                    <circle
                      r={radius + 12}
                      fill="none"
                      stroke={baseColor}
                      strokeWidth="2"
                      opacity="0.5"
                      filter="url(#neon-glow)"
                    />
                  )}

                  {/* Node Background Disc */}
                  <circle
                    r={radius}
                    fill="rgba(15, 23, 42, 0.95)"
                    stroke={baseColor}
                    strokeWidth={isSelected ? '3' : '2'}
                  />

                  {/* Inner Node Accent */}
                  <circle
                    r={radius - 6}
                    fill={baseColor}
                    opacity={isSelected ? 0.35 : 0.15}
                  />

                  {/* Icon / Glyph */}
                  <text
                    y="4"
                    fill="#ffffff"
                    fontSize={isPaper ? '12' : '10'}
                    fontFamily="var(--font-sans)"
                    fontWeight="800"
                    textAnchor="middle"
                  >
                    {isPaper ? `P${n.study_rank || ''}` : (isPrereq ? 'REQ' : 'FLD')}
                  </text>

                  {/* Node Label Text */}
                  <text
                    y={radius + 18}
                    fill={isSelected ? '#ffffff' : '#cbd5e1'}
                    fontSize="11"
                    fontFamily="var(--font-sans)"
                    fontWeight={isSelected ? '700' : '500'}
                    textAnchor="middle"
                    style={{ textShadow: '0 2px 4px rgba(0,0,0,0.8)' }}
                  >
                    {n.label.length > 28 ? `${n.label.slice(0, 26)}...` : n.label}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>
      </div>

      {/* Right Rail: Interactive Node Dossier */}
      <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-color)', background: 'rgba(0, 0, 0, 0.2)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
            <span
              className="badge"
              style={{
                background: `${activeNode?.color || '#38bdf8'}22`,
                borderColor: activeNode?.color || '#38bdf8',
                color: activeNode?.color || '#38bdf8',
                fontSize: '0.75rem',
                textTransform: 'uppercase',
                fontWeight: 700,
              }}
            >
              {activeNode?.type || 'Node'}
            </span>
            {activeNode?.study_rank && (
              <span className="badge badge-cyan" style={{ fontSize: '0.7rem' }}>
                Study Step #{activeNode.study_rank}
              </span>
            )}
          </div>
          <h3 style={{ fontSize: '1.05rem', fontWeight: 800, color: '#f8fafc', lineHeight: '1.4' }}>
            {activeNode?.label}
          </h3>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: '20px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Node Summary */}
          <div>
            <h4 style={{ fontSize: '0.8rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-dim)', marginBottom: '8px' }}>
              Synthesized Thesis / Concept
            </h4>
            <p style={{ fontSize: '0.9rem', lineHeight: '1.6', color: '#cbd5e1', background: 'rgba(255, 255, 255, 0.02)', padding: '14px', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
              {activeNode?.summary || 'Core academic contribution within the synthesized curriculum graph.'}
            </p>
          </div>

          {/* Graph Relationships */}
          <div>
            <h4 style={{ fontSize: '0.8rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-dim)', marginBottom: '10px' }}>
              Connected Relationships ({connectedEdges.length})
            </h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {connectedEdges.map(e => {
                const otherId = e.source === activeNode?.id ? e.target : e.source;
                const otherNode = nodes.find(n => n.id === otherId);
                const isOutgoing = e.source === activeNode?.id;

                return (
                  <div
                    key={e.id}
                    style={{
                      background: 'rgba(255, 255, 255, 0.02)',
                      border: '1px solid rgba(255, 255, 255, 0.06)',
                      borderRadius: '8px',
                      padding: '10px 12px',
                      fontSize: '0.8rem',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                      <span className="badge badge-violet" style={{ fontSize: '0.65rem' }}>
                        {e.relation}
                      </span>
                      <span style={{ fontSize: '0.7rem', color: '#10b981', fontFamily: 'var(--font-mono)' }}>
                        {Math.round((e.confidence || 0.85) * 100)}% match
                      </span>
                    </div>
                    <p style={{ color: '#f8fafc', fontWeight: 600 }}>
                      {isOutgoing ? '↳ ' : '↰ '} {otherNode?.label || otherId}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        {activeNode?.type === 'paper' && (
          <div style={{ padding: '16px 20px', borderTop: '1px solid var(--border-color)', background: 'rgba(0, 0, 0, 0.3)' }}>
            <button
              className={isPaperStaged ? 'btn-secondary' : 'btn-primary'}
              style={{ width: '100%', fontSize: '0.85rem' }}
              onClick={() => onStageToTray(activeNode.id)}
            >
              {isPaperStaged ? '✓ Staged in Council Tray' : '+ Stage in Council Tray'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
