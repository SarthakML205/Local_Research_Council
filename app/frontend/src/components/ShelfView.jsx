import React, { useState, useEffect, useRef } from 'react';
import {
  ChevronLeft,
  ChevronRight,
  Play,
  Database,
  ExternalLink,
  ShieldCheck,
  Sparkles,
  Layers,
  ArrowRight,
  Maximize2,
  X,
} from 'lucide-react';

export default function ShelfView({
  papers = [],
  trayPapers = [],
  onStageToTray,
  onConveneCouncil,
}) {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [filter, setFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const canvasRef = useRef(null);

  // Fallback sample papers if tray/library is empty
  const displayPapers = papers.length > 0 ? papers : [
    {
      paper_id: '2405.21060',
      title: 'Transformers are SSMs: Generalized Models and Efficient Kernels',
      authors: 'Tri Dao, Albert Gu, et al.',
      category: 'cs.LG',
      form: 'mobius',
      stack: 'PyTorch · MLX',
      status: 'SOTA Kernel',
      tldr: 'Unifies selective state spaces and structured masked attention into structured semi-separable matrices on Apple Silicon.',
      abstract: 'We present a theoretical and empirical unification of state space models and attention mechanisms, proving linear complexity under unified memory constraints.',
    },
    {
      paper_id: '2312.00752',
      title: 'Mamba: Linear-Time Sequence Modeling with Selective State Spaces',
      authors: 'Albert Gu, Tri Dao',
      category: 'cs.AI',
      form: 'helix',
      stack: 'MLX · Hardware-Aware',
      status: 'Linear Time',
      tldr: 'Selective state space models achieve 5x higher throughput than Transformers and scale linearly in sequence length.',
      abstract: 'Foundational selective state space architecture that discards quadratic KV-cache memory allocation for long-context sequences.',
    },
    {
      paper_id: '1706.03762',
      title: 'Attention Is All You Need',
      authors: 'Vaswani et al.',
      category: 'cs.CL',
      form: 'torus',
      stack: 'Transformer Baseline',
      status: 'Foundational',
      tldr: 'The foundational multi-head self-attention architecture that spawned modern large language models.',
      abstract: 'Dominant sequence transduction models based entirely on multi-head attention without recurrence or convolutions.',
    },
    {
      paper_id: '2404.09562',
      title: 'Hardware-Aware Deep Learning on Apple Metal Unified Memory',
      authors: 'LRC Systems Group',
      category: 'cs.DC',
      form: 'brain',
      stack: 'Metal · C++ Kernels',
      status: 'Hardware Tier',
      tldr: 'Eliminating PCIe bus overhead via unified zero-copy host-device tensor buffers on Apple M5.',
      abstract: 'Comprehensive memory bandwidth analysis of contiguous Metal array allocation under high multi-agent concurrent loads.',
    },
  ];

  const filteredPapers = displayPapers.filter(p => {
    const matchesFilter = filter === 'ALL' || (p.category && p.category.toUpperCase().includes(filter));
    const matchesSearch = !searchQuery || p.title.toLowerCase().includes(searchQuery.toLowerCase()) || (p.paper_id && p.paper_id.includes(searchQuery));
    return matchesFilter && matchesSearch;
  });

  const activePaper = filteredPapers[selectedIndex] || filteredPapers[0] || displayPapers[0];
  const isStaged = trayPapers.includes(activePaper?.paper_id);

  // Animated 3D Möbius / Particle Mesh Canvas (Stark UI 26)
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animationFrameId;
    let time = 0;

    const N = 360;
    const render = () => {
      time += 0.02;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const W = canvas.width;
      const H = canvas.height;
      const cx = W / 2;
      const cy = H / 2;
      const R = Math.min(W, H) * 0.32;

      // Draw particle form based on active card form
      for (let i = 0; i < N; i++) {
        const u = (i / N) * Math.PI * 2;
        const v = Math.sin(u * 3 + time) * 0.4;

        // 3D Möbius transformation
        const x = (1 + v * Math.cos(u / 2)) * Math.cos(u + time * 0.5) * R;
        const y = v * Math.sin(u / 2) * R * 1.2;
        const z = (1 + v * Math.cos(u / 2)) * Math.sin(u + time * 0.5) * R;

        const fov = 400;
        const scale = fov / (fov + z + 100);
        const px = cx + x * scale;
        const py = cy + y * scale;

        const alpha = Math.max(0.15, Math.min(0.9, (z + R) / (2 * R)));
        ctx.fillStyle = i % 5 === 0 ? `rgba(200, 16, 46, ${alpha})` : `rgba(228, 235, 241, ${alpha * 0.8})`;
        ctx.fillRect(px, py, 1.8 * scale, 1.8 * scale);
      }

      animationFrameId = requestAnimationFrame(render);
    };

    render();
    return () => cancelAnimationFrame(animationFrameId);
  }, [activePaper]);

  const handlePrev = () => {
    setSelectedIndex(prev => (prev > 0 ? prev - 1 : filteredPapers.length - 1));
  };

  const handleNext = () => {
    setSelectedIndex(prev => (prev < filteredPapers.length - 1 ? prev + 1 : 0));
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 100px)', padding: '0 16px 16px', position: 'relative' }}>
      {/* Top Filter Chips & Search Bar (Augma Spec) */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '16px',
        zIndex: 5,
      }}>
        {/* Category Filters */}
        <div style={{ display: 'flex', gap: '8px' }}>
          {['ALL', 'CS.LG', 'CS.AI', 'CS.CL', 'CS.DC'].map(cat => (
            <button
              key={cat}
              className={`chip ${filter === cat ? 'on' : ''}`}
              onClick={() => { setFilter(cat); setSelectedIndex(0); }}
              style={{ fontSize: '0.72rem', padding: '6px 14px' }}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* Position Counter & Arcs */}
        <div className="plate" style={{
          height: '36px',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          padding: '0 16px',
          borderRadius: '4px',
        }}>
          <span style={{ fontSize: '0.7rem', color: 'var(--mute)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase' }}>
            Shelf
          </span>
          <div style={{ width: '120px', height: '2px', background: 'var(--line-faint)', position: 'relative' }}>
            <div style={{
              position: 'absolute',
              top: '-3px',
              left: `${(selectedIndex / Math.max(1, filteredPapers.length - 1)) * 100}%`,
              width: '8px',
              height: '8px',
              border: '1px solid var(--red)',
              transform: 'rotate(45deg)',
              transition: 'left 0.3s ease',
            }} />
          </div>
          <span style={{ fontSize: '0.72rem', color: 'var(--hi)', fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
            0{selectedIndex + 1} / 0{filteredPapers.length}
          </span>
        </div>

        {/* Search Input */}
        <div className="plate" style={{
          height: '36px',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '0 12px',
          width: '260px',
          borderRadius: '4px',
        }}>
          <span style={{ color: 'var(--mute)', fontSize: '0.8rem' }}>🔍</span>
          <input
            type="text"
            value={searchQuery}
            onChange={e => { setSearchQuery(e.target.value); setSelectedIndex(0); }}
            placeholder="SEARCH PAPERS..."
            style={{
              background: 'none',
              border: 'none',
              outline: 'none',
              color: 'var(--hi)',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.72rem',
              letterSpacing: 'var(--track-wide)',
              width: '100%',
              textTransform: 'uppercase',
            }}
          />
        </div>
      </div>

      {/* The Central 3D Revolving Shelf Arena */}
      <div style={{
        flex: 1,
        position: 'relative',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        perspective: '1200px',
        overflow: 'hidden',
      }}>
        {/* Left / Right Carousel Controls */}
        <button
          className="chip"
          onClick={handlePrev}
          style={{
            position: 'absolute',
            left: '20px',
            top: '50%',
            transform: 'translateY(-50%)',
            width: '46px',
            height: '46px',
            justifyContent: 'center',
            zIndex: 10,
          }}
        >
          <ChevronLeft size={22} color="var(--hi)" />
        </button>

        <button
          className="chip"
          onClick={handleNext}
          style={{
            position: 'absolute',
            right: '20px',
            top: '50%',
            transform: 'translateY(-50%)',
            width: '46px',
            height: '46px',
            justifyContent: 'center',
            zIndex: 10,
          }}
        >
          <ChevronRight size={22} color="var(--hi)" />
        </button>

        {/* 3D Arc of Revolving Cards */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '24px',
          width: '100%',
          height: '100%',
          position: 'relative',
        }}>
          {filteredPapers.map((paper, idx) => {
            const offset = idx - selectedIndex;
            const isCenter = offset === 0;
            const isNear = Math.abs(offset) === 1;
            const isVisible = Math.abs(offset) <= 2;

            if (!isVisible) return null;

            const rotateY = offset * -26;
            const translateZ = isCenter ? 80 : -140 * Math.abs(offset);
            const translateX = offset * 280;
            const opacity = isCenter ? 1 : isNear ? 0.6 : 0.25;

            return (
              <div
                key={paper.paper_id || idx}
                onClick={() => setSelectedIndex(idx)}
                className="plate"
                style={{
                  position: 'absolute',
                  width: '380px',
                  height: '240px',
                  borderRadius: '6px',
                  padding: '20px 24px',
                  cursor: 'pointer',
                  transform: `translateX(${translateX}px) translateZ(${translateZ}px) rotateY(${rotateY}deg)`,
                  transition: 'all 0.5s cubic-bezier(0.16, 1, 0.3, 1)',
                  opacity,
                  border: isCenter ? '1.5px solid var(--red)' : '1px solid var(--line)',
                  boxShadow: isCenter ? '0 0 35px rgba(200, 16, 46, 0.4)' : 'none',
                  background: isCenter ? 'rgba(3, 4, 5, 0.88)' : 'rgba(3, 4, 5, 0.65)',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  userSelect: 'none',
                }}
              >
                {/* Top Row: Index & Category */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '1.2rem', fontFamily: 'var(--font-display)', color: isCenter ? 'var(--red)' : 'var(--hi)', fontWeight: 500 }}>
                      0{idx + 1}
                    </span>
                    <span style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: 'var(--mute)', letterSpacing: '0.08em' }}>
                      {paper.paper_id?.slice(0, 12) || 'LRC-REPO'}
                    </span>
                  </div>

                  <span className="chip" style={{
                    fontSize: '0.65rem',
                    padding: '2px 8px',
                    borderColor: isCenter ? 'var(--red)' : 'var(--line)',
                    color: isCenter ? 'var(--red)' : 'var(--mute)',
                  }}>
                    {paper.status || 'READY'}
                  </span>
                </div>

                {/* Center Canvas Particles on active card */}
                {isCenter && (
                  <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', opacity: 0.45 }}>
                    <canvas ref={canvasRef} width={380} height={240} style={{ width: '100%', height: '100%' }} />
                  </div>
                )}

                {/* Card Title & Abstract */}
                <div style={{ position: 'relative', zIndex: 2 }}>
                  <h3 style={{
                    fontSize: '1.1rem',
                    fontWeight: 600,
                    color: 'var(--hi)',
                    letterSpacing: '0.02em',
                    lineHeight: '1.3',
                    marginBottom: '8px',
                  }}>
                    {paper.title.length > 55 ? `${paper.title.slice(0, 55)}...` : paper.title}
                  </h3>
                  <p style={{
                    fontSize: '0.78rem',
                    color: 'var(--txt)',
                    lineHeight: '1.5',
                    fontFamily: 'var(--font-sans)',
                  }}>
                    {paper.tldr || paper.abstract?.slice(0, 95) + '...'}
                  </p>
                </div>

                {/* Card Bottom Meta */}
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  borderTop: '1px solid var(--line-faint)',
                  paddingTop: '8px',
                  fontSize: '0.7rem',
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--dim)',
                  position: 'relative',
                  zIndex: 2,
                }}>
                  <span>STACK <b style={{ color: 'var(--hi)', fontWeight: 400 }}>{paper.stack || 'MLX · M5'}</b></span>
                  <span>CATEGORY <b style={{ color: 'var(--red)', fontWeight: 600 }}>{paper.category || 'cs.AI'}</b></span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Orbit position marker below card */}
        <div style={{
          position: 'absolute',
          bottom: '15px',
          left: '50%',
          transform: 'translateX(-50%)',
          textAlign: 'center',
        }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--red)', fontFamily: 'var(--font-mono)', fontWeight: 700, letterSpacing: 'var(--track-wide)' }}>
            LRC-SHELF-0{selectedIndex + 1}
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--hi)', textTransform: 'uppercase', letterSpacing: 'var(--track-wide)', marginTop: '2px' }}>
            {activePaper.title.slice(0, 35)}...
          </div>
        </div>
      </div>

      {/* Floating Bottom Inspector Panel (#panel from Augma Spec) */}
      <div className="plate" style={{
        marginTop: '10px',
        padding: '16px 24px',
        borderRadius: '6px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        zIndex: 5,
      }}>
        <div style={{ maxWidth: '75%' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--red)', fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
              LRC-SHELF-0{selectedIndex + 1}
            </span>
            <span style={{ fontSize: '0.65rem', border: '1px solid var(--hair)', padding: '2px 6px', color: 'var(--hi)', fontFamily: 'var(--font-mono)' }}>
              100% LOCAL
            </span>
            <span style={{ fontSize: '0.72rem', color: 'var(--mute)', fontFamily: 'var(--font-mono)' }}>
              {activePaper.category || 'cs.AI'}
            </span>
          </div>

          <h2 style={{ fontSize: '1.2rem', fontWeight: 600, color: 'var(--hi)', letterSpacing: '0.03em', marginBottom: '4px' }}>
            {activePaper.title}
          </h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--txt)', lineHeight: '1.5' }}>
            {activePaper.tldr || activePaper.abstract}
          </p>
        </div>

        {/* Action Buttons */}
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <button
            className={`btn-stark ${isStaged ? '' : 'pri'}`}
            onClick={() => onStageToTray && onStageToTray(activePaper.paper_id)}
            disabled={isStaged}
          >
            <Database size={13} />
            {isStaged ? 'STAGED IN TRAY' : 'STAGE TO TRAY'}
          </button>

          <button
            className="btn-stark pri"
            onClick={onConveneCouncil}
            disabled={trayPapers.length < 2}
          >
            <Play size={13} /> CONVENE COUNCIL ({trayPapers.length})
          </button>

          <a
            href={`https://arxiv.org/abs/${activePaper.paper_id}`}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-stark"
          >
            <ExternalLink size={13} /> ARXIV
          </a>
        </div>
      </div>
    </div>
  );
}
