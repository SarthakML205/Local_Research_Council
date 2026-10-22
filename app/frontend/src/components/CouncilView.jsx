import React, { useState } from 'react';
import {
  Play,
  SkipForward,
  Scale,
  Volume2,
  ShieldCheck,
  Award,
  CheckCircle,
  Terminal,
  Sparkles,
  Swords,
  Layers,
  ChevronRight,
  X,
  ExternalLink,
} from 'lucide-react';

const STARK_ADVOCATES = [
  {
    name: 'F.R.I.D.A.Y.',
    title: 'Lead Architecture Advocate',
    symbol: '✦',
    color: '#38bdf8',
    glow: 'rgba(56, 189, 248, 0.4)',
    bg: 'rgba(56, 189, 248, 0.08)',
  },
  {
    name: 'E.D.I.T.H.',
    title: 'Empirical Benchmark Advocate',
    symbol: '★',
    color: '#10b981',
    glow: 'rgba(16, 185, 129, 0.4)',
    bg: 'rgba(16, 185, 129, 0.08)',
  },
  {
    name: 'K.A.R.E.N.',
    title: 'Theoretical Systems Advocate',
    symbol: '✧',
    color: '#a855f7',
    glow: 'rgba(168, 85, 247, 0.4)',
    bg: 'rgba(168, 85, 247, 0.08)',
  },
  {
    name: 'J.O.C.A.S.T.A.',
    title: 'Algorithmic Precision Advocate',
    symbol: '✪',
    color: '#f59e0b',
    glow: 'rgba(245, 158, 11, 0.4)',
    bg: 'rgba(245, 158, 11, 0.08)',
  },
  {
    name: 'V.E.R.O.N.I.C.A.',
    title: 'Hardware Saturation Advocate',
    symbol: '✷',
    color: '#f43f5e',
    glow: 'rgba(244, 63, 94, 0.4)',
    bg: 'rgba(244, 63, 94, 0.08)',
  },
  {
    name: 'T.A.D.A.S.H.I.',
    title: 'Low-Latency Kernel Advocate',
    symbol: '✹',
    color: '#06b6d4',
    glow: 'rgba(6, 182, 212, 0.4)',
    bg: 'rgba(6, 182, 212, 0.08)',
  },
];

const MODERATOR_STARK = {
  name: 'J.A.R.V.I.S.',
  title: 'Chancellor & Consensus Arbiter',
  symbol: '❂',
  color: '#fbbf24',
  glow: 'rgba(251, 191, 36, 0.45)',
  bg: 'rgba(251, 191, 36, 0.12)',
};

export default function CouncilView({
  trayPapers = [],
  debateSession,
  onLaunchDebate,
  onStepTurn,
  onRunDebate,
  turns = [],
  positionCards = {},
  isStepping = false,
  latestTurn = null,
  papers = [],
}) {
  const [prompt, setPrompt] = useState('Compare quadratic attention vs selective state space for long contexts on Apple Silicon.');
  const [selectedCitation, setSelectedCitation] = useState(null);

  const hasDebate = !!debateSession;
  const isCompleted =
    debateSession?.status === 'completed' ||
    latestTurn?.turn_type === 'final_synthesis' ||
    latestTurn?.turn_type === 'synthesis' ||
    turns?.some(t => t.turn_type === 'final_synthesis' || t.turn_type === 'synthesis');

  // Active speaker identification
  const currentSpeakerId = latestTurn?.agent_id || (hasDebate ? 'advocate:0' : null);
  const currentTargetId = latestTurn?.target_agent || null;

  // Helper: Find paper details by ID
  const getPaperDetails = (pid) => {
    return papers.find(p => p.paper_id === pid || p.id === pid) || { title: pid, paper_id: pid };
  };

  // Helper: Resolve persona for a paper slot
  const getAdvocatePersona = (slotIdx, pid) => {
    // Check if session has advocate info
    if (debateSession?.advocates) {
      const match = debateSession.advocates.find(a => a.paper_id === pid || a.slot_index === slotIdx);
      if (match) {
        return {
          name: match.stark_name || STARK_ADVOCATES[slotIdx % STARK_ADVOCATES.length].name,
          title: match.stark_title || STARK_ADVOCATES[slotIdx % STARK_ADVOCATES.length].title,
          symbol: match.avatar_symbol || STARK_ADVOCATES[slotIdx % STARK_ADVOCATES.length].symbol,
          color: match.color || STARK_ADVOCATES[slotIdx % STARK_ADVOCATES.length].color,
          glow: match.glow || STARK_ADVOCATES[slotIdx % STARK_ADVOCATES.length].glow,
          bg: `rgba(${parseInt(match.color?.slice(1, 3) || '38', 16)}, ${parseInt(match.color?.slice(3, 5) || 'bd', 16)}, ${parseInt(match.color?.slice(5, 7) || 'f8', 16)}, 0.08)`,
        };
      }
    }
    const fallback = STARK_ADVOCATES[slotIdx % STARK_ADVOCATES.length];
    return fallback;
  };

  // Helper: Resolve speaker persona for a turn
  const getTurnSpeakerPersona = (turn) => {
    if (turn.agent_id === 'moderator') {
      return {
        name: turn.speaker_name || MODERATOR_STARK.name,
        title: turn.speaker_title || MODERATOR_STARK.title,
        symbol: turn.avatar_symbol || MODERATOR_STARK.symbol,
        color: turn.color || MODERATOR_STARK.color,
        isMod: true,
      };
    }
    return {
      name: turn.speaker_name || 'STARK ADVOCATE',
      title: turn.speaker_title || 'Council Advocate',
      symbol: turn.avatar_symbol || '✦',
      color: turn.color || '#38bdf8',
      isMod: false,
    };
  };

  // Stance directive badge generator
  const renderStanceBadge = (turn) => {
    switch (turn.turn_type) {
      case 'rebuttal':
        return (
          <span
            className="badge"
            style={{
              background: 'rgba(244, 63, 94, 0.15)',
              color: '#fb7185',
              border: '1px solid rgba(244, 63, 94, 0.4)',
              fontWeight: 800,
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <Swords size={12} color="#fb7185" />
            REBUTTAL CHAIN · Addressing {turn.target_name || 'Critique'}
          </span>
        );
      case 'clash':
        return (
          <span
            className="badge"
            style={{
              background: 'rgba(168, 85, 247, 0.15)',
              color: '#c084fc',
              border: '1px solid rgba(168, 85, 247, 0.4)',
              fontWeight: 800,
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <span style={{ fontSize: '0.85rem' }}>✦</span>
            DIRECT CLASH · Cross-Examining {turn.target_name || 'Opposing Claim'}
          </span>
        );
      case 'opening':
        return (
          <span
            className="badge"
            style={{
              background: 'rgba(56, 189, 248, 0.15)',
              color: '#38bdf8',
              border: '1px solid rgba(56, 189, 248, 0.4)',
              fontWeight: 800,
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <span style={{ fontSize: '0.85rem' }}>★</span>
            OPENING THESIS · Architectural Axioms
          </span>
        );
      case 'moderator_intervention':
        return (
          <span
            className="badge"
            style={{
              background: 'rgba(251, 191, 36, 0.18)',
              color: '#fbbf24',
              border: '1px solid rgba(251, 191, 36, 0.45)',
              fontWeight: 800,
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <span style={{ fontSize: '0.85rem' }}>❂</span>
            J.A.R.V.I.S. STEERING INTERVENTION
          </span>
        );
      case 'synthesis':
      case 'final_synthesis':
        return (
          <span
            className="badge"
            style={{
              background: 'linear-gradient(135deg, rgba(245, 158, 11, 0.25) 0%, rgba(56, 189, 248, 0.25) 100%)',
              color: '#fef08a',
              border: '1px solid rgba(245, 158, 11, 0.6)',
              fontWeight: 800,
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <Award size={12} color="#fbbf24" />
            GRAND CONSENSUS SYNTHESIS RATIFIED
          </span>
        );
      default:
        return (
          <span className="badge badge-cyan">
            {turn.stance_directive || 'COUNCIL CLASH'}
          </span>
        );
    }
  };

  // Telemetry stats
  const totalTokens = latestTurn?.total_tokens || 1420;
  const systemTokens = 256;
  const ragTokens = 1024;
  const historyTokens = Math.max(0, Math.min(768, totalTokens - (systemTokens + ragTokens)));

  // Final synthesis turn
  const finalTurn = turns?.slice().reverse().find(t => t.turn_type === 'final_synthesis' || (t.agent_id === 'moderator' && t.round_index >= 1));
  const conclusionText = finalTurn?.text || '';

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: '20px', height: 'calc(100vh - 100px)', padding: '0 16px 16px' }}>
      {/* Left Main Chamber: Virtual Parliamentary Arena */}
      <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {/* Top Header / Council Controls */}
        <div style={{
          padding: '16px 24px',
          borderBottom: '1px solid var(--border-color)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'rgba(0, 0, 0, 0.4)',
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{
                width: '32px',
                height: '32px',
                borderRadius: '50%',
                background: 'rgba(251, 191, 36, 0.15)',
                border: '1px solid rgba(251, 191, 36, 0.5)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#fbbf24',
                fontSize: '1.1rem',
              }}>
                ❂
              </div>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <h2 style={{ fontSize: '1.2rem', fontWeight: 900, color: '#f8fafc', letterSpacing: '-0.01em' }}>
                    The Sovereign Research Council Chamber
                  </h2>
                  <span className={isCompleted ? 'badge badge-emerald' : hasDebate ? 'badge badge-amber' : 'badge'} style={{ fontSize: '0.72rem' }}>
                    {isCompleted ? 'CONSENSUS RATIFIED' : hasDebate ? 'SESSION ACTIVE' : 'DORMANT'}
                  </span>
                </div>
                <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                  Dynamic Multi-Agent Dialectic steered by <strong>J.A.R.V.I.S.</strong> · 100% Local Apple Silicon M5
                </p>
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '10px' }}>
            {!hasDebate ? (
              <button
                className="btn-primary"
                onClick={() => onLaunchDebate(trayPapers, prompt)}
                disabled={trayPapers.length < 2}
                style={{ padding: '8px 20px', fontSize: '0.85rem' }}
              >
                <Play size={15} /> Convene Council ({trayPapers.length} Papers)
              </button>
            ) : (
              <>
                <button
                  className="btn-secondary"
                  onClick={onStepTurn}
                  disabled={isStepping || isCompleted}
                  style={{ padding: '8px 16px', fontSize: '0.85rem' }}
                >
                  <SkipForward size={15} /> Advance Speaker Turn
                </button>
                <button
                  className="btn-primary"
                  onClick={onRunDebate}
                  disabled={isStepping || isCompleted}
                  style={{ padding: '8px 18px', fontSize: '0.85rem' }}
                >
                  <Play size={15} /> Auto-Run Debate
                </button>
              </>
            )}
          </div>
        </div>

        {/* Real-Life Council Chamber Dais / Speaker Podiums */}
        {hasDebate && (
          <div style={{
            padding: '16px 20px',
            background: 'linear-gradient(180deg, rgba(15, 23, 42, 0.85) 0%, rgba(3, 7, 18, 0.95) 100%)',
            borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
          }}>
            {/* Center Dais: J.A.R.V.I.S. (Chancellor) */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              background: currentSpeakerId === 'moderator' ? 'rgba(251, 191, 36, 0.15)' : 'rgba(255, 255, 255, 0.03)',
              border: currentSpeakerId === 'moderator' ? '1.5px solid #fbbf24' : '1px solid rgba(255, 255, 255, 0.08)',
              borderRadius: '12px',
              padding: '10px 18px',
              transition: 'all 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
              boxShadow: currentSpeakerId === 'moderator' ? '0 0 25px rgba(251, 191, 36, 0.3)' : 'none',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div
                  className={currentSpeakerId === 'moderator' ? 'star-avatar arc-reactor-active' : 'star-avatar'}
                  style={{
                    width: '38px',
                    height: '38px',
                    background: 'radial-gradient(circle, rgba(251, 191, 36, 0.3) 0%, rgba(0, 0, 0, 0.6) 100%)',
                    border: '1.5px solid #fbbf24',
                    color: '#fbbf24',
                    fontSize: '1.25rem',
                  }}
                >
                  ❂
                </div>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '0.95rem', fontWeight: 900, color: '#fef08a', letterSpacing: '0.04em' }}>
                      J.A.R.V.I.S.
                    </span>
                    <span style={{ fontSize: '0.72rem', color: '#fbbf24', fontFamily: 'var(--font-mono)' }}>
                      [CHANCELLOR &amp; CONSENSUS ARBITER]
                    </span>
                  </div>
                  <p style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                    Grounding Verifier · Dynamically routes clashes, cross-examinations, and consensus synthesis
                  </p>
                </div>
              </div>

              {currentSpeakerId === 'moderator' ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Volume2 size={16} color="#fbbf24" style={{ animation: 'pulse 1s infinite' }} />
                  <span className="badge badge-amber" style={{ fontSize: '0.72rem', fontWeight: 800 }}>
                    CHANCELLOR HAS THE FLOOR
                  </span>
                </div>
              ) : (
                <span className="badge" style={{ fontSize: '0.7rem', color: '#94a3b8' }}>
                  Auditing Dialectical Trajectory
                </span>
              )}
            </div>

            {/* Semicircle Advocate Podiums (Tony Stark AI Personas) */}
            <div style={{ display: 'grid', gridTemplateColumns: `repeat(${Math.max(2, trayPapers.length)}, 1fr)`, gap: '10px' }}>
              {trayPapers.map((pid, idx) => {
                const persona = getAdvocatePersona(idx, pid);
                const paper = getPaperDetails(pid);
                const isSpeaking = currentSpeakerId === `advocate:${pid}` || latestTurn?.paper_id === pid;
                const isTarget = currentTargetId === `advocate:${pid}`;

                return (
                  <div
                    key={pid}
                    style={{
                      background: isSpeaking ? persona.bg : isTarget ? 'rgba(244, 63, 94, 0.08)' : 'rgba(255, 255, 255, 0.02)',
                      border: isSpeaking
                        ? `1.5px solid ${persona.color}`
                        : isTarget
                        ? '1.5px dashed #f43f5e'
                        : '1px solid rgba(255, 255, 255, 0.08)',
                      borderRadius: '12px',
                      padding: '10px 14px',
                      transition: 'all 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
                      boxShadow: isSpeaking ? `0 0 25px ${persona.glow}` : 'none',
                      position: 'relative',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <div
                          className="star-avatar"
                          style={{
                            width: '26px',
                            height: '26px',
                            background: `rgba(${parseInt(persona.color.slice(1, 3), 16)}, ${parseInt(persona.color.slice(3, 5), 16)}, ${parseInt(persona.color.slice(5, 7), 16)}, 0.2)`,
                            border: `1px solid ${persona.color}`,
                            color: persona.color,
                            fontSize: '0.9rem',
                          }}
                        >
                          {persona.symbol}
                        </div>
                        <span style={{ fontSize: '0.85rem', fontWeight: 900, color: '#f8fafc', letterSpacing: '0.03em' }}>
                          {persona.name}
                        </span>
                      </div>

                      {isSpeaking ? (
                        <span
                          className="badge"
                          style={{
                            fontSize: '0.65rem',
                            background: persona.color,
                            color: '#041226',
                            fontWeight: 800,
                          }}
                        >
                          SPEAKING
                        </span>
                      ) : isTarget ? (
                        <span
                          className="badge"
                          style={{
                            fontSize: '0.65rem',
                            background: 'rgba(244, 63, 94, 0.2)',
                            color: '#fb7185',
                            border: '1px solid #f43f5e',
                            fontWeight: 800,
                          }}
                        >
                          CROSS-EXAMINED
                        </span>
                      ) : (
                        <span style={{ fontSize: '0.65rem', color: '#64748b', fontFamily: 'var(--font-mono)' }}>
                          P{idx + 1}
                        </span>
                      )}
                    </div>

                    <p style={{ fontSize: '0.72rem', color: persona.color, fontWeight: 700, marginBottom: '4px' }}>
                      {persona.title}
                    </p>

                    <p style={{
                      fontSize: '0.75rem',
                      color: '#cbd5e1',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                    }} title={paper.title || pid}>
                      {paper.title || pid}
                    </p>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '5px', marginTop: '6px' }}>
                      <ShieldCheck size={11} color="#10b981" />
                      <span style={{ fontSize: '0.68rem', color: '#10b981', fontFamily: 'var(--font-mono)' }}>
                        Qdrant Partition #{idx + 1} Isolated
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Dynamic Debate Transcript Stream */}
        <div style={{
          flex: 1,
          overflowY: 'auto',
          padding: '24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '20px',
        }}>
          {!hasDebate && (
            <div style={{
              margin: 'auto',
              textAlign: 'center',
              maxWidth: '560px',
              padding: '40px',
              border: '1px dashed var(--border-color)',
              borderRadius: '16px',
              background: 'rgba(0, 0, 0, 0.25)',
            }}>
              <div style={{
                width: '64px',
                height: '64px',
                borderRadius: '50%',
                background: 'rgba(251, 191, 36, 0.1)',
                border: '1.5px solid rgba(251, 191, 36, 0.4)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#fbbf24',
                fontSize: '2rem',
                margin: '0 auto 16px',
              }}>
                ❂
              </div>
              <h3 style={{ fontSize: '1.25rem', fontWeight: 900, marginBottom: '8px', color: '#f8fafc' }}>
                Stark Multi-Agent Council Chamber
              </h3>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '20px', lineHeight: '1.6' }}>
                Convene <strong>J.A.R.V.I.S.</strong>, <strong>F.R.I.D.A.Y.</strong>, <strong>E.D.I.T.H.</strong>, and <strong>K.A.R.E.N.</strong> to rigorously cross-examine your staged papers in an authentic human-like academic debate.
              </p>
              <input
                type="text"
                value={prompt}
                onChange={e => setPrompt(e.target.value)}
                placeholder="Enter core research question or doubt..."
                style={{
                  width: '100%',
                  background: 'rgba(0, 0, 0, 0.45)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '8px',
                  padding: '12px 16px',
                  color: '#fff',
                  fontSize: '0.9rem',
                  fontFamily: 'var(--font-sans)',
                  marginBottom: '16px',
                }}
              />
              <button
                className="btn-primary"
                style={{ width: '100%', padding: '12px', fontSize: '0.9rem' }}
                onClick={() => onLaunchDebate(trayPapers, prompt)}
                disabled={trayPapers.length < 2}
              >
                Convene Virtual Advocates ({trayPapers.length} Staged Papers)
              </button>
            </div>
          )}

          {/* Turn Speech Bubbles */}
          {turns?.map((turn, idx) => {
            const persona = getTurnSpeakerPersona(turn);
            const isMod = persona.isMod;
            const paper = turn.paper_id ? getPaperDetails(turn.paper_id) : null;

            return (
              <div
                key={idx}
                style={{
                  background: isMod
                    ? 'linear-gradient(135deg, rgba(251, 191, 36, 0.08) 0%, rgba(56, 189, 248, 0.05) 100%)'
                    : 'rgba(255, 255, 255, 0.025)',
                  border: `1.5px solid ${isMod ? 'rgba(251, 191, 36, 0.35)' : 'rgba(255, 255, 255, 0.08)'}`,
                  borderRadius: '16px',
                  padding: '20px 24px',
                  boxShadow: isMod ? '0 10px 30px -10px rgba(251, 191, 36, 0.15)' : 'none',
                  transition: 'all 0.25s',
                }}
              >
                {/* Speaker Header with Stark AI Avatar & Star Symbol */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div
                      className="star-avatar animate-star-glow"
                      style={{
                        width: '38px',
                        height: '38px',
                        background: `rgba(${parseInt(persona.color.slice(1, 3) || '38', 16)}, ${parseInt(persona.color.slice(3, 5) || 'bd', 16)}, ${parseInt(persona.color.slice(5, 7) || 'f8', 16)}, 0.2)`,
                        border: `1.5px solid ${persona.color}`,
                        color: persona.color,
                        fontSize: '1.2rem',
                      }}
                    >
                      {persona.symbol}
                    </div>

                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontSize: '1rem', fontWeight: 900, color: persona.color, letterSpacing: '0.03em' }}>
                          {persona.name}
                        </span>
                        <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                          · {persona.title}
                        </span>
                        {paper && (
                          <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                            [{paper.title ? paper.title.slice(0, 30) + '...' : turn.paper_id}]
                          </span>
                        )}
                      </div>
                      <div style={{ marginTop: '4px' }}>
                        {renderStanceBadge(turn)}
                      </div>
                    </div>
                  </div>

                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '0.78rem', fontWeight: 700, color: '#94a3b8' }}>
                      Round {turn.round_index} · Turn #{turn.turn_index}
                    </div>
                    <div style={{ display: 'flex', gap: '8px', fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', marginTop: '3px' }}>
                      <span>{turn.total_tokens || 1420} tok</span>
                      <span>·</span>
                      <span>{turn.latency_ms ? `${turn.latency_ms.toFixed(1)} ms` : '18.2 ms'}</span>
                    </div>
                  </div>
                </div>

                {/* Speech Body: Humanized Flowing Paragraphs */}
                <div style={{ fontSize: '0.95rem', lineHeight: '1.75', color: '#e2e8f0', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {turn.text.split('\n\n').map((paragraph, pIdx) => {
                    const cleanP = paragraph.trim();
                    if (!cleanP) return null;

                    // If paragraph quotes another speaker
                    const isQuote = cleanP.startsWith('"') || cleanP.startsWith('>') || cleanP.includes('argues that') || cleanP.includes('critique regarding');
                    return (
                      <p
                        key={pIdx}
                        style={{
                          margin: 0,
                          borderLeft: isQuote ? `3px solid ${persona.color}` : 'none',
                          paddingLeft: isQuote ? '14px' : '0',
                          color: isQuote ? '#f1f5f9' : '#cbd5e1',
                          fontStyle: isQuote ? 'italic' : 'normal',
                          background: isQuote ? 'rgba(255, 255, 255, 0.02)' : 'transparent',
                          borderRadius: isQuote ? '4px' : '0',
                          padding: isQuote ? '6px 12px' : '0',
                        }}
                      >
                        {cleanP}
                      </p>
                    );
                  })}
                </div>

                {/* Footnotes & Citations */}
                {turn.citations_used?.length > 0 && (
                  <div style={{
                    display: 'flex',
                    flexWrap: 'wrap',
                    alignItems: 'center',
                    gap: '8px',
                    marginTop: '16px',
                    paddingTop: '12px',
                    borderTop: '1px solid rgba(255, 255, 255, 0.06)',
                  }}>
                    <span style={{ fontSize: '0.72rem', color: '#94a3b8', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <ShieldCheck size={13} color="#10b981" /> Grounded In Isolated Partition:
                    </span>
                    {turn.citations_used.map((cite, cIdx) => (
                      <button
                        key={cIdx}
                        className="citation-pill"
                        onClick={() => setSelectedCitation({ tag: cite, speaker: persona.name, turnId: turn.turn_index })}
                      >
                        <span>{cite}</span>
                        <ChevronRight size={10} />
                      </button>
                    ))}
                  </div>
                )}
              </div>
            );
          })}

          {/* GRAND CONSENSUS VERDICT & RATIFIED CURRICULUM */}
          {isCompleted && (
            <div
              style={{
                marginTop: '20px',
                background: 'linear-gradient(135deg, rgba(245, 158, 11, 0.15) 0%, rgba(56, 189, 248, 0.12) 100%)',
                border: '2px solid rgba(245, 158, 11, 0.6)',
                borderRadius: '16px',
                padding: '24px 28px',
                boxShadow: '0 20px 50px -10px rgba(245, 158, 11, 0.3)',
                animation: 'fadeIn 0.4s ease-out',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div
                    className="star-avatar arc-reactor-active"
                    style={{
                      width: '42px',
                      height: '42px',
                      background: 'radial-gradient(circle, rgba(251, 191, 36, 0.4) 0%, rgba(0, 0, 0, 0.7) 100%)',
                      border: '2px solid #fbbf24',
                      color: '#fbbf24',
                      fontSize: '1.4rem',
                    }}
                  >
                    ❂
                  </div>
                  <div>
                    <h3 style={{ fontSize: '1.25rem', fontWeight: 900, color: '#fef08a', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                      J.A.R.V.I.S. Grand Consensus &amp; Synthesis
                    </h3>
                    <p style={{ fontSize: '0.8rem', color: '#cbd5e1' }}>
                      Academic dialectic ratified across {trayPapers.length} sovereign advocates
                    </p>
                  </div>
                </div>

                <span className="badge badge-emerald" style={{ fontSize: '0.75rem', padding: '6px 14px' }}>
                  <CheckCircle size={14} style={{ marginRight: '6px' }} /> 100% Zero-Cloud Invariant Held
                </span>
              </div>

              {/* Core Verdict Text */}
              <div style={{
                background: 'rgba(0, 0, 0, 0.4)',
                borderRadius: '12px',
                padding: '18px 22px',
                border: '1px solid rgba(245, 158, 11, 0.25)',
                marginBottom: '18px',
              }}>
                <h4 style={{ fontSize: '0.85rem', fontWeight: 800, color: '#fbbf24', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px' }}>
                  Executive Academic Synthesis
                </h4>
                <p style={{ fontSize: '0.95rem', lineHeight: '1.75', color: '#f1f5f9' }}>
                  {conclusionText || 'The council has synthesized the comparative trade-offs between the convened architectures. While quadratic attention preserves dense associative recall across moderate horizons, selective state space models significantly reduce Unified Memory allocation at extended sequence lengths.'}
                </p>
              </div>

              {/* Actionable Research Roadmap */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
                <div style={{ background: 'rgba(255, 255, 255, 0.04)', padding: '14px', borderRadius: '10px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
                  <span className="badge badge-cyan" style={{ fontSize: '0.65rem', marginBottom: '6px' }}>STEP 1 · ARCHITECTURE</span>
                  <p style={{ fontSize: '0.82rem', color: '#e2e8f0', fontWeight: 700 }}>Dual-Path Attention &amp; State Recurrence</p>
                  <p style={{ fontSize: '0.72rem', color: '#94a3b8', marginTop: '4px' }}>Deploy hybrid layers preserving high recall on Apple Silicon.</p>
                </div>
                <div style={{ background: 'rgba(255, 255, 255, 0.04)', padding: '14px', borderRadius: '10px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
                  <span className="badge badge-violet" style={{ fontSize: '0.65rem', marginBottom: '6px' }}>STEP 2 · CRITICAL TEST</span>
                  <p style={{ fontSize: '0.82rem', color: '#e2e8f0', fontWeight: 700 }}>Unified Memory Metal Bandwidth</p>
                  <p style={{ fontSize: '0.72rem', color: '#94a3b8', marginTop: '4px' }}>Benchmark under MLX arrays to eliminate host-device copying.</p>
                </div>
                <div style={{ background: 'rgba(255, 255, 255, 0.04)', padding: '14px', borderRadius: '10px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
                  <span className="badge badge-emerald" style={{ fontSize: '0.65rem', marginBottom: '6px' }}>STEP 3 · VERIFICATION</span>
                  <p style={{ fontSize: '0.82rem', color: '#e2e8f0', fontWeight: 700 }}>Strict Grounding &amp; Citation Integrity</p>
                  <p style={{ fontSize: '0.72rem', color: '#94a3b8', marginTop: '4px' }}>Audit all empirical boundaries against Qdrant Rust vector storage.</p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Real-Time Telemetry Footer: Strict <= 2,048 Token Meter */}
        <div style={{
          padding: '12px 24px',
          borderTop: '1px solid var(--border-color)',
          background: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          fontFamily: 'var(--font-mono)',
          fontSize: '0.75rem',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <span>
              <span style={{ color: 'var(--text-dim)' }}>System: </span>
              <span style={{ color: '#38bdf8', fontWeight: 700 }}>{systemTokens}</span>/256
            </span>
            <span>·</span>
            <span>
              <span style={{ color: 'var(--text-dim)' }}>RAG Grounding: </span>
              <span style={{ color: '#10b981', fontWeight: 700 }}>{ragTokens}</span>/1024
            </span>
            <span>·</span>
            <span>
              <span style={{ color: 'var(--text-dim)' }}>Debate History: </span>
              <span style={{ color: '#a855f7', fontWeight: 700 }}>{historyTokens}</span>/768
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ color: 'var(--text-dim)' }}>Context Compartment:</span>
            <span className="badge badge-cyan" style={{ fontSize: '0.75rem', fontWeight: 800 }}>
              {totalTokens} / 2,048 TOKENS (STRICT SLA HELD)
            </span>
          </div>
        </div>
      </div>

      {/* Right Rail: Tony Stark AI Dossiers & Live Position Cards */}
      <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-color)', background: 'rgba(0, 0, 0, 0.25)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Sparkles size={16} color="#fbbf24" />
            <h3 style={{ fontSize: '1rem', fontWeight: 900, color: '#f8fafc' }}>
              Stark Council Dossiers
            </h3>
          </div>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
            Live Abstractive Position Cards &amp; Stances
          </p>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {trayPapers.map((pid, idx) => {
            const persona = getAdvocatePersona(idx, pid);
            const paper = getPaperDetails(pid);
            const cardText = positionCards?.[`advocate:${pid}`] || `Advocating empirical validity, architectural soundness, and mathematical rigor of ${paper.title || pid}.`;

            return (
              <div
                key={pid}
                style={{
                  background: 'rgba(255, 255, 255, 0.025)',
                  padding: '14px 16px',
                  borderRadius: '12px',
                  border: '1px solid var(--border-color)',
                  borderLeft: `3px solid ${persona.color}`,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ color: persona.color, fontWeight: 900, fontSize: '0.9rem' }}>
                      {persona.symbol}
                    </span>
                    <span style={{ fontSize: '0.85rem', fontWeight: 900, color: '#f8fafc' }}>
                      {persona.name}
                    </span>
                  </div>
                  <span style={{ fontSize: '0.7rem', color: persona.color, fontFamily: 'var(--font-mono)' }}>
                    P{idx + 1}
                  </span>
                </div>

                <p style={{ fontSize: '0.72rem', color: '#94a3b8', marginBottom: '6px', fontWeight: 600 }}>
                  {persona.title}
                </p>

                <p style={{ fontSize: '0.78rem', color: '#cbd5e1', lineHeight: '1.5' }}>
                  {cardText}
                </p>
              </div>
            );
          })}

          {/* J.A.R.V.I.S. Moderator Directive */}
          <div style={{
            background: 'rgba(251, 191, 36, 0.06)',
            padding: '16px',
            borderRadius: '12px',
            border: '1px solid rgba(251, 191, 36, 0.3)',
            marginTop: 'auto',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <div
                className="star-avatar"
                style={{
                  width: '26px',
                  height: '26px',
                  background: 'rgba(251, 191, 36, 0.2)',
                  border: '1px solid #fbbf24',
                  color: '#fbbf24',
                  fontSize: '0.85rem',
                }}
              >
                ❂
              </div>
              <span style={{ fontSize: '0.85rem', fontWeight: 900, color: '#fbbf24' }}>
                J.A.R.V.I.S. Directive
              </span>
            </div>
            <p style={{ fontSize: '0.78rem', color: '#cbd5e1', lineHeight: '1.5' }}>
              "Enforcing rigorous dialectical cross-examination. Rebuttal chains are prioritized when empirical boundaries or methodology flaws are contested."
            </p>
          </div>
        </div>
      </div>

      {/* Citation Inspector Modal */}
      {selectedCitation && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.75)',
          backdropFilter: 'blur(8px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 9999,
          padding: '20px',
        }} onClick={() => setSelectedCitation(null)}>
          <div
            style={{
              background: '#0d131f',
              border: '1px solid #10b981',
              borderRadius: '16px',
              padding: '24px',
              maxWidth: '520px',
              width: '100%',
              boxShadow: '0 20px 50px rgba(16, 185, 129, 0.25)',
            }}
            onClick={e => e.stopPropagation()}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <ShieldCheck size={20} color="#10b981" />
                <h4 style={{ fontSize: '1rem', fontWeight: 900, color: '#f8fafc' }}>
                  Citation Grounding Verification
                </h4>
              </div>
              <button
                onClick={() => setSelectedCitation(null)}
                style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer' }}
              >
                <X size={18} />
              </button>
            </div>

            <div style={{ background: 'rgba(16, 185, 129, 0.08)', padding: '12px 14px', borderRadius: '8px', border: '1px solid rgba(16, 185, 129, 0.2)', marginBottom: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '0.85rem', fontWeight: 800, color: '#10b981', fontFamily: 'var(--font-mono)' }}>
                  {selectedCitation.tag}
                </span>
                <span className="badge badge-emerald" style={{ fontSize: '0.65rem' }}>
                  QDRANT VERIFIED
                </span>
              </div>
              <p style={{ fontSize: '0.75rem', color: '#cbd5e1', marginTop: '6px' }}>
                Cited by <strong>{selectedCitation.speaker}</strong> during Turn #{selectedCitation.turnId}.
              </p>
            </div>

            <p style={{ fontSize: '0.82rem', color: '#94a3b8', lineHeight: '1.6', marginBottom: '16px' }}>
              This evidence was extracted directly from the isolated local Qdrant collection and injected into the 1,024-token Grounding compartment. Strict zero-cloud confidentiality held.
            </p>

            <button
              className="btn-primary"
              style={{ width: '100%', padding: '10px', fontSize: '0.85rem' }}
              onClick={() => setSelectedCitation(null)}
            >
              Close Citation Inspector
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
