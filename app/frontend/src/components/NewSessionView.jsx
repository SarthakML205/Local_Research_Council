import React, { useState } from 'react';
import { Search, Sparkles, Terminal, ArrowRight, Layers, CheckCircle2, Loader2, BookOpen, ShieldCheck } from 'lucide-react';

export default function NewSessionView({ onStartSession, pipelineState, onProceedToDiscovery }) {
  const [problemStatement, setProblemStatement] = useState('');
  const [maxPapers, setMaxPapers] = useState(3);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const sampleDoutes = [
    "How to reduce KV-cache memory pressure in long-context transformers on Apple Silicon?",
    "Selective State Space Models (Mamba) vs Quadratic Attention for sequence throughput",
    "Speculative decoding latency improvements using small draft models on unified memory",
    "Direct Preference Optimization (DPO) vs PPO stability in RLHF training",
  ];

  const handleSubmit = async (query = problemStatement) => {
    if (!query.trim() || isSubmitting) return;
    setIsSubmitting(true);
    try {
      await onStartSession(query.trim(), maxPapers);
    } finally {
      setIsSubmitting(false);
    }
  };

  const steps = [
    { id: 1, label: 'Querying arXiv Sovereign Index', desc: 'Filtering peer-reviewed preprints without cloud telemetry' },
    { id: 2, label: 'Streaming PDFs to Local Disk', desc: 'Storing verified binaries into data/papers/<id>/' },
    { id: 3, label: 'Slicing High-Density Pages', desc: 'PyMuPDF cleaning of references, appendices & headers' },
    { id: 4, label: 'Computing MLX Embeddings & Qdrant Collections', desc: '1024-dim Metal-accelerated dense vectors & BM25 sparse index' },
    { id: 5, label: 'Synthesizing Knowledge Graph & Staging Council', desc: 'Inferring typed relations & auto-populating Council Tray' },
  ];

  const currentStep = pipelineState?.step || 0;
  const isCompleted = pipelineState?.completed;

  return (
    <div style={{ maxWidth: '960px', margin: '0 auto', padding: '20px 16px 40px' }}>
      {/* Hero Title */}
      <div style={{ textAlign: 'center', marginBottom: '32px' }}>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
          <span className="badge badge-cyan" style={{ padding: '6px 14px', fontSize: '0.8rem' }}>
            <Sparkles size={14} /> Screen 1: Sovereign Research Session Launcher
          </span>
        </div>
        <h2 style={{ fontSize: '2.2rem', fontWeight: 800, letterSpacing: '-0.03em', marginBottom: '10px' }}>
          What technical problem are we researching today?
        </h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.95rem', maxWidth: '640px', margin: '0 auto' }}>
          Enter a problem statement, technical doubt, or architectural hypothesis. LRC will scrape arXiv, download sovereign PDFs to disk, slice content, embed into Qdrant, and synthesize an interactive mind map.
        </p>
      </div>

      {/* Main Command Input Box */}
      <div className="glass-panel" style={{ padding: '24px', marginBottom: '24px', border: '1px solid rgba(56, 189, 248, 0.25)' }}>
        <div style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
          <div style={{ flex: 1, position: 'relative' }}>
            <textarea
              rows={3}
              placeholder="e.g. How to reduce KV-cache memory pressure in long-context transformers on Apple Silicon without throughput regression?"
              value={problemStatement}
              onChange={e => setProblemStatement(e.target.value)}
              disabled={isSubmitting || (currentStep > 0 && !isCompleted)}
              style={{
                width: '100%',
                background: 'rgba(0, 0, 0, 0.45)',
                border: '1px solid var(--border-color)',
                borderRadius: '10px',
                padding: '14px 16px',
                color: '#fff',
                fontSize: '0.95rem',
                fontFamily: 'var(--font-sans)',
                resize: 'none',
                outline: 'none',
                lineHeight: '1.5',
                boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.5)',
              }}
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit();
                }
              }}
            />
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
          {/* Max Papers Selector (2 to 6 bounds) */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-dim)', fontWeight: 600 }}>
              Council Scope:
            </span>
            {[2, 3, 4, 5, 6].map(num => (
              <button
                key={num}
                type="button"
                onClick={() => setMaxPapers(num)}
                disabled={isSubmitting || (currentStep > 0 && !isCompleted)}
                style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '6px',
                  border: '1px solid',
                  borderColor: maxPapers === num ? '#38bdf8' : 'var(--border-color)',
                  background: maxPapers === num ? 'rgba(56, 189, 248, 0.2)' : 'rgba(255, 255, 255, 0.03)',
                  color: maxPapers === num ? '#38bdf8' : 'var(--text-muted)',
                  fontWeight: 700,
                  fontSize: '0.85rem',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                }}
              >
                {num}
              </button>
            ))}
            <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>papers</span>
          </div>

          <button
            className="btn-primary"
            style={{ padding: '12px 24px', fontSize: '0.95rem' }}
            onClick={() => handleSubmit()}
            disabled={!problemStatement.trim() || isSubmitting || (currentStep > 0 && !isCompleted)}
          >
            {isSubmitting || (currentStep > 0 && !isCompleted) ? (
              <>
                <Loader2 size={18} className="animate-spin" /> Ingesting Sovereign Papers...
              </>
            ) : (
              <>
                <Search size={18} /> Ingest Top Papers & Convene Council
              </>
            )}
          </button>
        </div>
      </div>

      {/* Quick-Pick Problem Statements */}
      {(!currentStep || isCompleted) && (
        <div style={{ marginBottom: '32px' }}>
          <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-dim)', letterSpacing: '0.05em' }}>
            Or select an empirical benchmark question:
          </span>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', marginTop: '10px' }}>
            {sampleDoutes.map((sample, idx) => (
              <button
                key={idx}
                type="button"
                className="btn-secondary"
                style={{
                  fontSize: '0.8rem',
                  padding: '8px 14px',
                  textAlign: 'left',
                  borderRadius: '20px',
                  background: 'rgba(255, 255, 255, 0.03)',
                }}
                onClick={() => {
                  setProblemStatement(sample);
                  handleSubmit(sample);
                }}
              >
                <Sparkles size={12} color="#38bdf8" /> {sample}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Animated Pipeline Execution Terminal */}
      {(currentStep > 0 || isSubmitting) && (
        <div className="glass-panel" style={{ padding: '24px', background: 'rgba(10, 15, 26, 0.95)', border: '1px solid rgba(56, 189, 248, 0.3)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Terminal size={18} color="#38bdf8" />
              <h3 style={{ fontSize: '1rem', fontWeight: 800 }}>Live Ingestion Pipeline</h3>
            </div>
            {isCompleted ? (
              <span className="badge badge-emerald">
                <CheckCircle2 size={12} /> Pipeline Complete
              </span>
            ) : (
              <span className="badge badge-cyan">
                <Loader2 size={12} className="animate-spin" /> Step {currentStep} of 5
              </span>
            )}
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {steps.map(step => {
              const isPast = currentStep > step.id || isCompleted;
              const isCurrent = currentStep === step.id && !isCompleted;
              const isPending = currentStep < step.id && !isCompleted;

              return (
                <div
                  key={step.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '14px',
                    padding: '12px 16px',
                    borderRadius: '8px',
                    background: isCurrent
                      ? 'rgba(56, 189, 248, 0.1)'
                      : isPast
                      ? 'rgba(16, 185, 129, 0.05)'
                      : 'rgba(255, 255, 255, 0.02)',
                    border: `1px solid ${isCurrent ? 'rgba(56, 189, 248, 0.4)' : isPast ? 'rgba(16, 185, 129, 0.2)' : 'var(--border-color)'}`,
                    transition: 'all 0.3s',
                  }}
                >
                  <div style={{
                    width: '28px',
                    height: '28px',
                    borderRadius: '50%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '0.8rem',
                    fontWeight: 800,
                    fontFamily: 'var(--font-mono)',
                    background: isPast ? '#10b981' : isCurrent ? '#38bdf8' : 'rgba(255, 255, 255, 0.1)',
                    color: isPast || isCurrent ? '#07090e' : 'var(--text-dim)',
                  }}>
                    {isPast ? '✓' : step.id}
                  </div>

                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: '0.9rem', fontWeight: 700, color: isCurrent ? '#38bdf8' : isPast ? '#10b981' : 'var(--text-muted)' }}>
                      {step.label}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                      {step.desc}
                    </div>
                  </div>

                  {isCurrent && (
                    <div style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: '#38bdf8' }}>
                      {pipelineState?.message || 'Processing...'}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Completion Action */}
          {isCompleted && (
            <div style={{ marginTop: '24px', textAlign: 'center', paddingTop: '16px', borderTop: '1px solid var(--border-color)' }}>
              <p style={{ fontSize: '0.9rem', color: '#10b981', marginBottom: '16px', fontWeight: 600 }}>
                Successfully ingested and staged {pipelineState?.paper_ids?.length || maxPapers} papers into your Council Tray!
              </p>
              <button
                className="btn-primary"
                style={{ padding: '12px 28px', fontSize: '1rem' }}
                onClick={onProceedToDiscovery}
              >
                Explore Mind Map & Open Council Chamber <ArrowRight size={18} />
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
