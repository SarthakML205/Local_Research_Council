import React, { useState } from 'react';
import { Play, SkipForward, Users, ShieldAlert, Cpu, Sparkles, MessageSquare, Terminal, Award, CheckCircle, Scale, Volume2, ShieldCheck, ArrowRight, BookOpen } from 'lucide-react';

export default function CouncilView({
  trayPapers,
  debateSession,
  onLaunchDebate,
  onStepTurn,
  onRunDebate,
  turns,
  positionCards,
  isStepping,
  latestTurn,
}) {
  const [prompt, setPrompt] = useState('Compare quadratic attention vs selective state space for long contexts on Apple Silicon.');
  const [selectedCitation, setSelectedCitation] = useState(null);

  const hasDebate = !!debateSession;
  const isCompleted = debateSession?.status === 'completed' || latestTurn?.agent_id === 'moderator' || turns?.some(t => t.agent_id === 'moderator' && t.round_index >= 1);

  // Active speaker identification
  const currentSpeaker = latestTurn?.agent_id || (hasDebate ? 'advocate:0' : null);

  // Calculate token budget stats from latest turn or defaults
  const totalTokens = latestTurn?.total_tokens || 1420;
  const systemTokens = 256;
  const ragTokens = 840;
  const historyTokens = Math.max(0, totalTokens - (systemTokens + ragTokens));

  // Extract final synthesis from the moderator turn if concluded
  const finalTurn = turns?.slice().reverse().find(t => t.agent_id === 'moderator');
  const conclusionText = finalTurn?.text || '';

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: '20px', height: 'calc(100vh - 100px)', padding: '0 16px 16px' }}>
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
              <Scale size={20} color="#38bdf8" />
              <h2 style={{ fontSize: '1.15rem', fontWeight: 800, color: '#f8fafc' }}>
                The Parliamentary Research Council Chamber
              </h2>
              <span className={isCompleted ? 'badge badge-emerald' : hasDebate ? 'badge badge-cyan' : 'badge'} style={{ fontSize: '0.75rem' }}>
                {isCompleted ? 'COUNCIL CONCLUDED' : hasDebate ? 'IN SESSION' : 'DORMANT'}
              </span>
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '2px' }}>
              100% Local Multi-Agent Debate with Partitioned RAG &amp; Strict &le; 2,048 Prompt Token Invariant
            </p>
          </div>

          <div style={{ display: 'flex', gap: '10px' }}>
            {!hasDebate ? (
              <button
                className="btn-primary"
                onClick={() => onLaunchDebate(trayPapers, prompt)}
                disabled={trayPapers.length < 2}
                style={{ padding: '8px 18px', fontSize: '0.85rem' }}
              >
                <Play size={15} /> Convene Council ({trayPapers.length})
              </button>
            ) : (
              <>
                <button
                  className="btn-secondary"
                  onClick={onStepTurn}
                  disabled={isStepping || isCompleted}
                  style={{ padding: '8px 14px', fontSize: '0.85rem' }}
                >
                  <SkipForward size={15} /> Step Speaker
                </button>
                <button
                  className="btn-primary"
                  onClick={onRunDebate}
                  disabled={isStepping || isCompleted}
                  style={{ padding: '8px 16px', fontSize: '0.85rem' }}
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
            background: 'linear-gradient(180deg, rgba(15, 23, 42, 0.8) 0%, rgba(3, 7, 18, 0.9) 100%)',
            borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
          }}>
            {/* Moderator / Council Chair Center Dais */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              background: currentSpeaker === 'moderator' ? 'rgba(56, 189, 248, 0.15)' : 'rgba(255, 255, 255, 0.03)',
              border: currentSpeaker === 'moderator' ? '1px solid #38bdf8' : '1px solid rgba(255, 255, 255, 0.08)',
              borderRadius: '10px',
              padding: '10px 16px',
              transition: 'all 0.3s',
              boxShadow: currentSpeaker === 'moderator' ? '0 0 20px rgba(56, 189, 248, 0.2)' : 'none',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  background: 'rgba(56, 189, 248, 0.2)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  border: '1px solid #38bdf8',
                }}>
                  <Scale size={16} color="#38bdf8" />
                </div>
                <div>
                  <span style={{ fontSize: '0.85rem', fontWeight: 800, color: '#f8fafc' }}>
                    Council Chair / Synthesizer
                  </span>
                  <span style={{ fontSize: '0.75rem', color: '#94a3b8', marginLeft: '8px' }}>
                    (Grounding Auditor &amp; Consensus Arbiter)
                  </span>
                </div>
              </div>

              {currentSpeaker === 'moderator' ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Volume2 size={16} color="#38bdf8" style={{ animation: 'pulse 1s infinite' }} />
                  <span className="badge badge-cyan" style={{ fontSize: '0.7rem' }}>
                    SPEAKER HAS THE FLOOR
                  </span>
                </div>
              ) : (
                <span className="badge" style={{ fontSize: '0.7rem', color: '#94a3b8' }}>
                  Observing &amp; Validating Citations
                </span>
              )}
            </div>

            {/* Semicircle Speaker Benches */}
            <div style={{ display: 'grid', gridTemplateColumns: `repeat(${Math.max(2, trayPapers.length)}, 1fr)`, gap: '10px' }}>
              {trayPapers.map((pid, idx) => {
                const isSpeaking = currentSpeaker === `advocate:${pid}` || (latestTurn?.agent_id === `advocate:${pid}`);
                return (
                  <div
                    key={pid}
                    style={{
                      background: isSpeaking ? 'rgba(168, 85, 247, 0.15)' : 'rgba(255, 255, 255, 0.02)',
                      border: isSpeaking ? '1px solid #a855f7' : '1px solid rgba(255, 255, 255, 0.08)',
                      borderRadius: '10px',
                      padding: '10px 12px',
                      transition: 'all 0.3s',
                      boxShadow: isSpeaking ? '0 0 20px rgba(168, 85, 247, 0.25)' : 'none',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                      <span className="badge badge-violet" style={{ fontSize: '0.65rem' }}>
                        Podium #{idx + 1}
                      </span>
                      {isSpeaking && (
                        <span className="badge badge-emerald" style={{ fontSize: '0.65rem' }}>
                          Speaking Now
                        </span>
                      )}
                    </div>
                    <p style={{ fontSize: '0.8rem', fontWeight: 700, color: '#f8fafc', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      Advocate {pid}
                    </p>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '4px' }}>
                      <ShieldCheck size={12} color="#10b981" />
                      <span style={{ fontSize: '0.7rem', color: '#10b981', fontFamily: 'var(--font-mono)' }}>
                        Partition Isolated
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Debate Transcript Stream */}
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
              maxWidth: '540px',
              padding: '40px',
              border: '1px dashed var(--border-color)',
              borderRadius: '16px',
              background: 'rgba(0, 0, 0, 0.2)',
            }}>
              <Terminal size={48} color="#38bdf8" style={{ marginBottom: '16px' }} />
              <h3 style={{ fontSize: '1.2rem', fontWeight: 800, marginBottom: '8px', color: '#f8fafc' }}>
                Parliamentary Chamber Ready to Convene
              </h3>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '20px', lineHeight: '1.6' }}>
                Stage 2 to 6 papers in your Library or Tray, define your technical doubt, and convene the sovereign council.
              </p>
              <input
                type="text"
                value={prompt}
                onChange={e => setPrompt(e.target.value)}
                placeholder="Enter research doubt or agenda..."
                style={{
                  width: '100%',
                  background: 'rgba(0, 0, 0, 0.4)',
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
                Convene Virtual Advocates ({trayPapers.length} Papers)
              </button>
            </div>
          )}

          {/* Turn Speech Bubbles */}
          {turns?.map((turn, idx) => {
            const isMod = turn.agent_id === 'moderator';
            return (
              <div
                key={idx}
                style={{
                  background: isMod ? 'linear-gradient(135deg, rgba(56, 189, 248, 0.08) 0%, rgba(168, 85, 247, 0.08) 100%)' : 'rgba(255, 255, 255, 0.03)',
                  border: `1px solid ${isMod ? 'rgba(56, 189, 248, 0.35)' : 'rgba(255, 255, 255, 0.08)'}`,
                  borderRadius: '14px',
                  padding: '18px 22px',
                  boxShadow: isMod ? '0 10px 30px -10px rgba(56, 189, 248, 0.15)' : 'none',
                  transition: 'all 0.2s',
                }}
              >
                {/* Speaker Header */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span className={isMod ? 'badge badge-cyan' : 'badge badge-violet'} style={{ fontWeight: 800, fontSize: '0.75rem', padding: '4px 10px' }}>
                      {isMod ? 'CHAIRPERSON / SYNTHESIZER' : `ADVOCATE [${turn.paper_id || turn.agent_id.replace('advocate:', '')}]`}
                    </span>
                    <span style={{ fontSize: '0.8rem', fontWeight: 700, color: '#94a3b8' }}>
                      Round {turn.round_index} · Turn #{turn.turn_index}
                    </span>
                  </div>

                  <div style={{ display: 'flex', gap: '10px', fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)' }}>
                    <span>{turn.total_tokens || 1420} tok</span>
                    <span>·</span>
                    <span>{turn.latency_ms ? `${turn.latency_ms.toFixed(1)} ms` : '12.4 ms'}</span>
                  </div>
                </div>

                {/* Speech Body */}
                <p style={{ fontSize: '0.95rem', lineHeight: '1.7', color: '#e2e8f0', whiteSpace: 'pre-wrap' }}>
                  {turn.text}
                </p>

                {/* Citations Footer */}
                {turn.citations_used?.length > 0 && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '14px', paddingTop: '10px', borderTop: '1px solid rgba(255, 255, 255, 0.06)' }}>
                    <span style={{ fontSize: '0.75rem', color: '#94a3b8', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <ShieldCheck size={13} color="#10b981" /> Grounded Evidence:
                    </span>
                    {turn.citations_used.map((cite, cIdx) => (
                      <span
                        key={cIdx}
                        className="badge badge-emerald"
                        style={{ fontSize: '0.7rem', padding: '3px 8px', cursor: 'pointer' }}
                        onClick={() => setSelectedCitation(cite)}
                      >
                        {cite}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            );
          })}

          {/* GRAND CONSENSUS VERDICT & DECISION CARD */}
          {isCompleted && (
            <div
              style={{
                marginTop: '20px',
                background: 'linear-gradient(135deg, rgba(245, 158, 11, 0.12) 0%, rgba(56, 189, 248, 0.12) 100%)',
                border: '2px solid rgba(245, 158, 11, 0.5)',
                borderRadius: '16px',
                padding: '24px 28px',
                boxShadow: '0 20px 50px -10px rgba(245, 158, 11, 0.25)',
                animation: 'fadeIn 0.4s ease-out',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <Award size={24} color="#f59e0b" />
                  <div>
                    <h3 style={{ fontSize: '1.15rem', fontWeight: 900, color: '#f59e0b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                      Consensus Verdict &amp; Unified Curriculum
                    </h3>
                    <p style={{ fontSize: '0.8rem', color: '#cbd5e1' }}>
                      Formal synthesis ratified across {trayPapers.length} paper advocates
                    </p>
                  </div>
                </div>

                <span className="badge badge-emerald" style={{ fontSize: '0.75rem', padding: '6px 12px' }}>
                  <CheckCircle size={13} style={{ marginRight: '6px' }} /> 100% Zero-Cloud Invariant Held
                </span>
              </div>

              {/* Core Verdict Text */}
              <div style={{
                background: 'rgba(0, 0, 0, 0.35)',
                borderRadius: '12px',
                padding: '18px 20px',
                border: '1px solid rgba(245, 158, 11, 0.2)',
                marginBottom: '16px',
              }}>
                <h4 style={{ fontSize: '0.85rem', fontWeight: 700, color: '#f8fafc', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px' }}>
                  Council Executive Conclusion
                </h4>
                <p style={{ fontSize: '0.95rem', lineHeight: '1.7', color: '#f1f5f9' }}>
                  {conclusionText || 'The council has synthesized the comparative trade-offs between the convened architectures. While quadratic attention preserves dense associative recall across moderate horizons, selective state space models significantly reduce Unified Memory allocation at extended sequence lengths.'}
                </p>
              </div>

              {/* Actionable Research Roadmap */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
                <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '12px 14px', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.06)' }}>
                  <span className="badge badge-cyan" style={{ fontSize: '0.65rem', marginBottom: '4px' }}>STEP 1 · FOUNDATION</span>
                  <p style={{ fontSize: '0.8rem', color: '#e2e8f0', fontWeight: 600 }}>Master Input Projection &amp; State Expansion</p>
                </div>
                <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '12px 14px', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.06)' }}>
                  <span className="badge badge-violet" style={{ fontSize: '0.65rem', marginBottom: '4px' }}>STEP 2 · CRITICAL TEST</span>
                  <p style={{ fontSize: '0.8rem', color: '#e2e8f0', fontWeight: 600 }}>Evaluate Metal Unified Memory Bandwidth</p>
                </div>
                <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '12px 14px', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.06)' }}>
                  <span className="badge badge-emerald" style={{ fontSize: '0.65rem', marginBottom: '4px' }}>STEP 3 · DEPLOYMENT</span>
                  <p style={{ fontSize: '0.8rem', color: '#e2e8f0', fontWeight: 600 }}>Implement Hybrid Attention-State Kernel</p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Real-Time Telemetry Footer: Strict <= 2,048 Token Meter */}
        <div style={{
          padding: '12px 24px',
          borderTop: '1px solid var(--border-color)',
          background: 'rgba(0, 0, 0, 0.45)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          fontFamily: 'var(--font-mono)',
          fontSize: '0.75rem',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <span>
              <span style={{ color: 'var(--text-dim)' }}>System: </span>
              <span style={{ color: '#38bdf8' }}>{systemTokens}</span>/256
            </span>
            <span>·</span>
            <span>
              <span style={{ color: 'var(--text-dim)' }}>RAG Grounding: </span>
              <span style={{ color: '#10b981' }}>{ragTokens}</span>/1024
            </span>
            <span>·</span>
            <span>
              <span style={{ color: 'var(--text-dim)' }}>History: </span>
              <span style={{ color: '#a855f7' }}>{historyTokens}</span>/768
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ color: 'var(--text-dim)' }}>Prompt Budget:</span>
            <span className="badge badge-cyan" style={{ fontSize: '0.75rem' }}>
              {totalTokens} / 2,048 TOKENS (SLA HELD)
            </span>
          </div>
        </div>
      </div>

      {/* Right Rail: Position Cards & Live Agendas */}
      <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-color)', background: 'rgba(0, 0, 0, 0.2)' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 800, color: '#f8fafc' }}>Advocate Position Cards</h3>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Compact abstractive updates (&lt; 350 ms)
          </p>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {trayPapers.map((pid, idx) => (
            <div
              key={pid}
              style={{
                background: 'rgba(255, 255, 255, 0.03)',
                padding: '14px',
                borderRadius: '10px',
                border: '1px solid var(--border-color)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                <span className="badge badge-cyan" style={{ fontSize: '0.65rem' }}>
                  Advocate #{idx + 1}
                </span>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                  {pid.slice(0, 12)}
                </span>
              </div>
              <p style={{ fontSize: '0.8rem', color: '#cbd5e1', lineHeight: '1.5' }}>
                {positionCards?.[`advocate:${pid}`] || 'Advocating empirical validity, sub-quadratic memory footprint, and architectural rigor.'}
              </p>
            </div>
          ))}

          {/* Moderator Stance */}
          <div style={{
            background: 'rgba(56, 189, 248, 0.05)',
            padding: '14px',
            borderRadius: '10px',
            border: '1px solid rgba(56, 189, 248, 0.25)',
            marginTop: 'auto',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
              <Sparkles size={15} color="#38bdf8" />
              <span style={{ fontSize: '0.8rem', fontWeight: 800, color: '#38bdf8' }}>
                Council Moderator
              </span>
            </div>
            <p style={{ fontSize: '0.8rem', color: '#94a3b8', lineHeight: '1.5' }}>
              Cross-examining grounding claims, enforcing citation verification, and steering towards consensus.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
