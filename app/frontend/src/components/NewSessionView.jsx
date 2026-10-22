import React, { useState, useRef } from 'react';
import {
  Search,
  Sparkles,
  Terminal,
  ArrowRight,
  Layers,
  CheckCircle2,
  Loader2,
  BookOpen,
  ShieldCheck,
  Zap,
  Brain,
  Cpu,
  Sliders,
  Play,
  Award,
  Clock,
  Coins,
  Gauge,
  HelpCircle,
  FileUp,
  FileText,
  Upload,
  X,
  Trash2,
} from 'lucide-react';

export default function NewSessionView({
  onStartSession,
  onUploadPapers,
  pipelineState,
  onProceedToDiscovery,
  onProceedToShelf,
  onConveneCouncil,
  trayPapers = [],
  apiBase = 'http://127.0.0.1:8000/api',
}) {
  const [problemStatement, setProblemStatement] = useState('');
  const [maxPapers, setMaxPapers] = useState(3);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Direct PDF Upload State
  const [inputMode, setInputMode] = useState('arxiv'); // 'arxiv' | 'upload'
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const fileInputRef = useRef(null);

  // Strategy comparison state
  const [compareMode, setCompareMode] = useState(false);
  const [isComparing, setIsComparing] = useState(false);
  const [comparisonData, setComparisonData] = useState(null);
  const [compareError, setCompareError] = useState('');

  const sampleDoutes = [
    "How to reduce KV-cache memory pressure in long-context transformers on Apple Silicon?",
    "Selective State Space Models (Mamba) vs Quadratic Attention for sequence throughput",
    "Speculative decoding latency improvements using small draft models on unified memory",
    "Direct Preference Optimization (DPO) vs PPO stability in RLHF training",
  ];

  const handleFilesAdded = (incomingFiles) => {
    if (!incomingFiles || incomingFiles.length === 0) return;
    const pdfs = Array.from(incomingFiles).filter(f => f.name.toLowerCase().endsWith('.pdf'));
    if (pdfs.length === 0) {
      setUploadError('Only .pdf files are accepted for sovereign local ingestion.');
      return;
    }
    setUploadError('');
    setUploadedFiles(prev => {
      const existingNames = new Set(prev.map(f => f.name));
      const newlyAdded = pdfs.filter(f => !existingNames.has(f.name));
      return [...prev, ...newlyAdded].slice(0, 6);
    });
    setInputMode('upload');
  };

  const handleUploadSubmit = async (autoStage = true) => {
    if (uploadedFiles.length === 0 || isSubmitting) return;
    setIsSubmitting(true);
    setUploadError('');
    try {
      if (onUploadPapers) {
        await onUploadPapers(uploadedFiles, problemStatement.trim() || 'Direct Local PDF Research Council', autoStage);
      }
    } catch (err) {
      setUploadError(String(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return '0 B';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  // Default execution: Uses Strategy C (Flagship Hybrid Rerank)
  const handleSubmit = async (
    query = problemStatement,
    strategy = 'strategy_c_hybrid_rerank',
    selectedPaperIds = []
  ) => {
    if (!query.trim() || isSubmitting) return;
    setIsSubmitting(true);
    try {
      await onStartSession(query.trim(), maxPapers, strategy, selectedPaperIds);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Run 3-Way Strategy Benchmark in Parallel
  const handleRunComparison = async () => {
    if (!problemStatement.trim() || isComparing) return;
    setIsComparing(true);
    setCompareError('');
    try {
      const res = await fetch(`${apiBase}/library/research/compare`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: problemStatement.trim(),
          max_papers: maxPapers,
        }),
      });
      if (!res.ok) {
        throw new Error(`Comparison API returned HTTP ${res.status}`);
      }
      const data = await res.json();
      setComparisonData(data);
    } catch (err) {
      setCompareError(String(err));
    } finally {
      setIsComparing(false);
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
    <div style={{ maxWidth: '1100px', margin: '0 auto', padding: '20px 16px 40px' }}>
      {/* Hero Title */}
      <div style={{ textAlign: 'center', marginBottom: '28px' }}>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
          <span className="badge badge-cyan" style={{ padding: '6px 14px', fontSize: '0.8rem' }}>
            <Sparkles size={14} /> Screen 1: Sovereign Research Session Launcher
          </span>
        </div>
        <h2 style={{ fontSize: '2.2rem', fontWeight: 800, letterSpacing: '-0.03em', marginBottom: '10px' }}>
          What technical problem are we researching today?
        </h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.95rem', maxWidth: '680px', margin: '0 auto' }}>
          Enter a problem statement, technical doubt, or architectural hypothesis. LRC will scrape arXiv, download sovereign PDFs to disk, slice content, embed into Qdrant, and synthesize an interactive mind map.
        </p>
      </div>

      {/* Main Command Input Box */}
      <div className="glass-panel" style={{ padding: '24px', marginBottom: '20px', border: '1px solid rgba(56, 189, 248, 0.25)' }}>
        {/* Input Mode Selector */}
        <div style={{ display: 'flex', gap: '8px', marginBottom: '18px', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', paddingBottom: '12px' }}>
          <button
            type="button"
            onClick={() => setInputMode('arxiv')}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 16px',
              borderRadius: '6px',
              border: '1px solid',
              borderColor: inputMode === 'arxiv' ? '#00f2fe' : 'transparent',
              background: inputMode === 'arxiv' ? 'rgba(0, 242, 254, 0.12)' : 'transparent',
              color: inputMode === 'arxiv' ? '#00f2fe' : 'var(--text-dim)',
              fontSize: '0.82rem',
              fontWeight: 700,
              cursor: 'pointer',
              fontFamily: 'var(--font-mono)',
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
              transition: 'all 0.15s ease',
            }}
          >
            <Search size={14} /> 01 // arXiv Sovereign Query
          </button>

          <button
            type="button"
            onClick={() => setInputMode('upload')}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 16px',
              borderRadius: '6px',
              border: '1px solid',
              borderColor: inputMode === 'upload' ? '#ffaa00' : 'transparent',
              background: inputMode === 'upload' ? 'rgba(255, 153, 0, 0.12)' : 'transparent',
              color: inputMode === 'upload' ? '#ffaa00' : 'var(--text-dim)',
              fontSize: '0.82rem',
              fontWeight: 700,
              cursor: 'pointer',
              fontFamily: 'var(--font-mono)',
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
              transition: 'all 0.15s ease',
            }}
          >
            <FileUp size={14} /> 02 // Direct Local PDF Upload
            {uploadedFiles.length > 0 && (
              <span style={{ background: '#ffaa00', color: '#030405', borderRadius: '10px', padding: '1px 7px', fontSize: '0.7rem', fontWeight: 800 }}>
                {uploadedFiles.length}
              </span>
            )}
          </button>
        </div>

        {uploadError && (
          <div style={{ padding: '10px 14px', borderRadius: '6px', background: 'rgba(239, 68, 68, 0.15)', border: '1px solid #ef4444', color: '#fca5a5', fontSize: '0.82rem', marginBottom: '14px' }}>
            {uploadError}
          </div>
        )}

        {inputMode === 'arxiv' ? (
          <>
            <div style={{ display: 'flex', gap: '12px', marginBottom: '14px' }}>
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
                      if (compareMode) {
                        handleRunComparison();
                      } else {
                        handleSubmit();
                      }
                    }
                  }}
                />
              </div>
            </div>

            {/* Quick drag & drop bar while in arXiv mode */}
            <div
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={(e) => { e.preventDefault(); setIsDragging(false); }}
              onDrop={(e) => {
                e.preventDefault();
                setIsDragging(false);
                handleFilesAdded(e.dataTransfer.files);
              }}
              onClick={() => {
                setInputMode('upload');
                if (fileInputRef.current) fileInputRef.current.click();
              }}
              style={{
                border: isDragging ? '1px dashed #00f2fe' : '1px dashed rgba(255, 255, 255, 0.12)',
                borderRadius: '8px',
                padding: '8px 14px',
                marginBottom: '16px',
                background: isDragging ? 'rgba(0, 242, 254, 0.08)' : 'rgba(255, 255, 255, 0.02)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8rem', color: isDragging ? '#00f2fe' : 'var(--text-dim)' }}>
                <FileUp size={15} color={isDragging ? '#00f2fe' : '#708090'} />
                <span>Have local papers? <strong>Drop PDF files here</strong> or switch to Direct Upload</span>
              </div>
              <span style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: '#708090' }}>
                BYPASS ARXIV // LOCAL-ONLY
              </span>
            </div>

            {/* Action Controls & Strategy Comparison Switch */}
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

              {/* Toggle Strategy Comparison Mode */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <button
                  type="button"
                  onClick={() => {
                    const next = !compareMode;
                    setCompareMode(next);
                    if (next && problemStatement.trim() && !comparisonData) {
                      handleRunComparison();
                    }
                  }}
                  disabled={isSubmitting || (currentStep > 0 && !isCompleted)}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '8px 14px',
                    borderRadius: '20px',
                    border: '1px solid',
                    borderColor: compareMode ? '#a855f7' : 'rgba(255, 255, 255, 0.15)',
                    background: compareMode ? 'rgba(168, 85, 247, 0.18)' : 'rgba(255, 255, 255, 0.03)',
                    color: compareMode ? '#c084fc' : 'var(--text-dim)',
                    fontSize: '0.8rem',
                    fontWeight: 700,
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                  }}
                >
                  <Sliders size={14} color={compareMode ? '#c084fc' : 'var(--text-dim)'} />
                  <span>Compare Strategies (Code vs LLM vs Rerank)</span>
                  <span
                    style={{
                      display: 'inline-block',
                      width: '8px',
                      height: '8px',
                      borderRadius: '50%',
                      background: compareMode ? '#a855f7' : 'rgba(255, 255, 255, 0.2)',
                      boxShadow: compareMode ? '0 0 8px #a855f7' : 'none',
                    }}
                  />
                </button>

                {compareMode ? (
                  <button
                    className="btn-secondary"
                    style={{ padding: '10px 18px', fontSize: '0.9rem', borderColor: '#a855f7', color: '#c084fc' }}
                    onClick={handleRunComparison}
                    disabled={!problemStatement.trim() || isComparing || isSubmitting}
                  >
                    {isComparing ? (
                      <>
                        <Loader2 size={16} className="animate-spin" /> Benchmarking 3 Pipelines...
                      </>
                    ) : (
                      <>
                        <Play size={16} /> Run 3-Way Benchmark
                      </>
                    )}
                  </button>
                ) : (
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
                )}
              </div>
            </div>
          </>
        ) : (
          /* Direct PDF Upload Mode */
          <div>
            {/* Hidden File Input */}
            <input
              type="file"
              ref={fileInputRef}
              onChange={(e) => handleFilesAdded(e.target.files)}
              accept=".pdf,application/pdf"
              multiple
              style={{ display: 'none' }}
            />

            {/* Stark UI 26 Mechanical Drag-and-Drop Dropzone */}
            <div
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={(e) => { e.preventDefault(); setIsDragging(false); }}
              onDrop={(e) => {
                e.preventDefault();
                setIsDragging(false);
                handleFilesAdded(e.dataTransfer.files);
              }}
              onClick={() => fileInputRef.current && fileInputRef.current.click()}
              style={{
                position: 'relative',
                border: isDragging ? '1px dashed #00f2fe' : '1px dashed rgba(255, 170, 0, 0.4)',
                borderRadius: '8px',
                padding: '28px 20px',
                textAlign: 'center',
                background: isDragging ? 'rgba(0, 242, 254, 0.08)' : 'rgba(8, 12, 18, 0.75)',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                marginBottom: '16px',
              }}
            >
              {/* Corner registration ticks */}
              <div style={{ position: 'absolute', top: 4, left: 4, width: 8, height: 8, borderTop: '2px solid #ffaa00', borderLeft: '2px solid #ffaa00' }} />
              <div style={{ position: 'absolute', top: 4, right: 4, width: 8, height: 8, borderTop: '2px solid #ffaa00', borderRight: '2px solid #ffaa00' }} />
              <div style={{ position: 'absolute', bottom: 4, left: 4, width: 8, height: 8, borderBottom: '2px solid #ffaa00', borderLeft: '2px solid #ffaa00' }} />
              <div style={{ position: 'absolute', bottom: 4, right: 4, width: 8, height: 8, borderBottom: '2px solid #ffaa00', borderRight: '2px solid #ffaa00' }} />

              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
                <div style={{
                  width: '46px',
                  height: '46px',
                  borderRadius: '50%',
                  background: 'rgba(255, 170, 0, 0.12)',
                  border: '1px solid rgba(255, 170, 0, 0.35)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginBottom: '2px',
                }}>
                  <FileUp size={22} color="#ffaa00" />
                </div>
                <div style={{ fontSize: '0.98rem', fontWeight: 700, color: '#f8fafc' }}>
                  Drop PDF Research Papers Here or <span style={{ color: '#ffaa00', textDecoration: 'underline' }}>Browse Local Files</span>
                </div>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)', maxWidth: '560px', lineHeight: '1.4' }}>
                  Direct PDF ingestion slices dense content with PyMuPDF, batches MLX Metal embeddings into Qdrant collections, and auto-stages to the Council Tray.
                </div>
                <div style={{ display: 'flex', gap: '10px', marginTop: '6px' }}>
                  <span className="badge badge-amber" style={{ fontSize: '0.7rem', padding: '3px 8px' }}>
                    Multi-PDF Supported (2-6 papers)
                  </span>
                  <span className="badge badge-cyan" style={{ fontSize: '0.7rem', padding: '3px 8px' }}>
                    Zero Cloud Egress
                  </span>
                </div>
              </div>
            </div>

            {/* Staged Files Cards */}
            {uploadedFiles.length > 0 && (
              <div style={{ marginBottom: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', textTransform: 'uppercase' }}>
                    Staged Papers ({uploadedFiles.length} of 6):
                  </span>
                  <button
                    type="button"
                    onClick={() => setUploadedFiles([])}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#ef4444',
                      fontSize: '0.72rem',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                    }}
                  >
                    <Trash2 size={12} /> Clear Staged
                  </button>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '8px' }}>
                  {uploadedFiles.map((file, idx) => (
                    <div
                      key={idx}
                      style={{
                        background: 'rgba(15, 23, 42, 0.85)',
                        border: '1px solid rgba(255, 170, 0, 0.3)',
                        borderRadius: '6px',
                        padding: '8px 12px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        gap: '8px',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
                        <FileText size={16} color="#ffaa00" style={{ flexShrink: 0 }} />
                        <div style={{ minWidth: 0 }}>
                          <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#f8fafc', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {file.name}
                          </div>
                          <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                            {formatFileSize(file.size)} • PDF
                          </div>
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setUploadedFiles(prev => prev.filter((_, i) => i !== idx));
                        }}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: 'var(--text-dim)',
                          cursor: 'pointer',
                          padding: '4px',
                          display: 'flex',
                          alignItems: 'center',
                        }}
                      >
                        <X size={14} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Inquest Query / Topic Input for Uploaded Papers */}
            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', textTransform: 'uppercase', marginBottom: '6px' }}>
                Debate Query / Research Topic:
              </label>
              <input
                type="text"
                placeholder="e.g. Cross-examine architectural trade-offs, empirical speedups, and memory bottlenecks across these uploaded papers..."
                value={problemStatement}
                onChange={(e) => setProblemStatement(e.target.value)}
                disabled={isSubmitting || (currentStep > 0 && !isCompleted)}
                style={{
                  width: '100%',
                  background: 'rgba(0, 0, 0, 0.45)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '8px',
                  padding: '10px 14px',
                  color: '#fff',
                  fontSize: '0.88rem',
                  outline: 'none',
                }}
              />
            </div>

            {/* Action Buttons for Upload */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '12px' }}>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => handleUploadSubmit(false)}
                disabled={uploadedFiles.length === 0 || isSubmitting || (currentStep > 0 && !isCompleted)}
                style={{ fontSize: '0.85rem', padding: '10px 16px' }}
              >
                <BookOpen size={14} /> Upload to Library Only
              </button>

              <button
                type="button"
                className="btn-primary"
                onClick={() => handleUploadSubmit(true)}
                disabled={uploadedFiles.length === 0 || isSubmitting || (currentStep > 0 && !isCompleted)}
                style={{
                  fontSize: '0.9rem',
                  padding: '10px 20px',
                  background: '#ffaa00',
                  color: '#030405',
                  fontWeight: 800,
                  borderColor: '#ffaa00',
                }}
              >
                {isSubmitting || (currentStep > 0 && !isCompleted) ? (
                  <>
                    <Loader2 size={16} className="animate-spin" /> Ingesting & Slicing PDFs...
                  </>
                ) : (
                  <>
                    <FileUp size={16} /> Ingest & Convene Council ({uploadedFiles.length} Papers)
                  </>
                )}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Quick-Pick Problem Statements */}
      {(!currentStep || isCompleted) && (
        <div style={{ marginBottom: '24px' }}>
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
                  if (compareMode) {
                    setTimeout(() => handleRunComparison(), 50);
                  } else {
                    handleSubmit(sample);
                  }
                }}
              >
                <Sparkles size={12} color="#38bdf8" /> {sample}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* COMPARISON MODE VIEW: Side-by-Side 3-Way Architectural Showdown */}
      {compareMode && (
        <div style={{ marginBottom: '32px' }}>
          {/* Header Banner */}
          <div
            style={{
              padding: '16px 20px',
              borderRadius: '10px',
              background: 'linear-gradient(90deg, rgba(56, 189, 248, 0.1) 0%, rgba(168, 85, 247, 0.1) 100%)',
              border: '1px solid rgba(168, 85, 247, 0.3)',
              marginBottom: '16px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '12px',
            }}
          >
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                <Gauge size={18} color="#a855f7" />
                <h4 style={{ fontSize: '1rem', fontWeight: 800, color: '#f8fafc' }}>
                  The 3-Way Search & Reranking Strategy Matrix
                </h4>
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Compare latency, token costs, VRAM footprint, and retrieval precision across Code-Only Regex, Local LLaMA 8B, and Apple M5 Hybrid Reranking.
              </p>
            </div>

            {comparisonData && (
              <div style={{ display: 'flex', gap: '16px', alignItems: 'center', fontSize: '0.8rem', fontFamily: 'var(--font-mono)' }}>
                <span className="badge badge-cyan">
                  Pool: {comparisonData.total_candidates_analyzed} preprints
                </span>
                <span className="badge badge-emerald">
                  <Clock size={12} /> Parallel Wall Time: {comparisonData.parallel_execution_wall_time_ms}ms
                </span>
              </div>
            )}
          </div>

          {compareError && (
            <div style={{ padding: '12px 16px', borderRadius: '8px', background: 'rgba(239, 68, 68, 0.15)', border: '1px solid #ef4444', color: '#fca5a5', fontSize: '0.85rem', marginBottom: '16px' }}>
              Comparison failed: {compareError}. Make sure the backend server is running.
            </div>
          )}

          {isComparing && (
            <div className="glass-panel" style={{ padding: '40px', textAlign: 'center', border: '1px dashed rgba(168, 85, 247, 0.4)' }}>
              <Loader2 size={32} className="animate-spin" color="#a855f7" style={{ margin: '0 auto 16px' }} />
              <h4 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '6px' }}>
                Executing 3 Strategies Concurrently in Parallel...
              </h4>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                Querying arXiv API, evaluating exact regex heuristics, prompting local LLaMA-3.1-8B, and running MLX bge-reranker on Metal.
              </p>
            </div>
          )}

          {/* 3 Columns Display */}
          {comparisonData && !isComparing && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px' }}>
              {/* Strategy A: Code-Only Logic (The Literal Librarian) */}
              {renderStrategyColumn(
                comparisonData.strategies.strategy_a_code_only,
                'rgba(148, 163, 184, 0.25)',
                '#94a3b8',
                <Zap size={16} color="#94a3b8" />,
                handleSubmit,
                problemStatement
              )}

              {/* Strategy B: Local LLM Call (The Heavy Thinker) */}
              {renderStrategyColumn(
                comparisonData.strategies.strategy_b_local_llm,
                'rgba(245, 158, 11, 0.3)',
                '#f59e0b',
                <Brain size={16} color="#f59e0b" />,
                handleSubmit,
                problemStatement
              )}

              {/* Strategy C: Hybrid Reranking (The Smart Context Assistant) [FLAGSHIP] */}
              {renderStrategyColumn(
                comparisonData.strategies.strategy_c_hybrid_rerank,
                'rgba(56, 189, 248, 0.5)',
                '#38bdf8',
                <Sparkles size={16} color="#38bdf8" />,
                handleSubmit,
                problemStatement,
                true
              )}
            </div>
          )}
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
              <div style={{ display: 'flex', gap: '12px', justifyContent: 'center', flexWrap: 'wrap' }}>
                {onConveneCouncil && (
                  <button
                    className="btn-primary"
                    style={{ padding: '12px 24px', fontSize: '0.95rem', background: '#00f2fe', color: '#030405', fontWeight: 800 }}
                    onClick={onConveneCouncil}
                  >
                    Enter Council Chamber <ArrowRight size={16} />
                  </button>
                )}
                {onProceedToShelf && (
                  <button
                    className="btn-secondary"
                    style={{ padding: '12px 20px', fontSize: '0.95rem' }}
                    onClick={onProceedToShelf}
                  >
                    Inspect in 3D Shelf
                  </button>
                )}
                <button
                  className="btn-secondary"
                  style={{ padding: '12px 20px', fontSize: '0.95rem' }}
                  onClick={onProceedToDiscovery}
                >
                  Explore Mind Map
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Render individual Strategy Column in 3-Way Comparison
function renderStrategyColumn(
  strat,
  borderColor,
  accentColor,
  icon,
  onConvene,
  problemStatement,
  isFlagship = false
) {
  if (!strat) return null;

  const paperIds = (strat.papers || []).map(p => p.paper_id);

  return (
    <div
      className="glass-panel"
      style={{
        display: 'flex',
        flexDirection: 'column',
        padding: '20px',
        border: `1px solid ${borderColor}`,
        background: isFlagship
          ? 'radial-gradient(circle at top right, rgba(56, 189, 248, 0.12), rgba(15, 23, 42, 0.95))'
          : 'rgba(15, 23, 42, 0.75)',
        boxShadow: isFlagship ? '0 8px 32px rgba(56, 189, 248, 0.15)' : 'none',
        position: 'relative',
        borderRadius: '12px',
      }}
    >
      {/* Flagship Badge */}
      {isFlagship && (
        <div style={{ position: 'absolute', top: '-11px', right: '16px' }}>
          <span className="badge badge-cyan" style={{ fontSize: '0.7rem', padding: '4px 10px', boxShadow: '0 0 10px rgba(56, 189, 248, 0.4)' }}>
            <Award size={12} /> LRC Flagship Engine
          </span>
        </div>
      )}

      {/* Column Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
        {icon}
        <h4 style={{ fontSize: '1.05rem', fontWeight: 800, color: '#f8fafc' }}>
          {strat.strategy_name}
        </h4>
      </div>
      <div style={{ fontSize: '0.8rem', fontWeight: 700, color: accentColor, marginBottom: '10px' }}>
        {strat.tagline}
      </div>

      {/* Narrative Block */}
      <div
        style={{
          padding: '10px 12px',
          borderRadius: '8px',
          background: 'rgba(0, 0, 0, 0.35)',
          borderLeft: `3px solid ${accentColor}`,
          fontSize: '0.78rem',
          color: 'var(--text-muted)',
          fontStyle: 'italic',
          lineHeight: '1.4',
          marginBottom: '14px',
        }}
      >
        "{strat.narrative}"
      </div>

      {/* Telemetry Metrics Pill Bar */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: '8px',
          padding: '10px',
          borderRadius: '8px',
          background: 'rgba(255, 255, 255, 0.03)',
          border: '1px solid rgba(255, 255, 255, 0.06)',
          marginBottom: '16px',
          textAlign: 'center',
          fontFamily: 'var(--font-mono)',
        }}
      >
        <div>
          <div style={{ fontSize: '0.65rem', textTransform: 'uppercase', color: 'var(--text-dim)', fontWeight: 600 }}>
            Latency
          </div>
          <div style={{ fontSize: '0.85rem', fontWeight: 800, color: strat.latency_ms < 50 ? '#10b981' : strat.latency_ms < 500 ? '#38bdf8' : '#f59e0b' }}>
            {strat.latency_ms} ms
          </div>
        </div>
        <div>
          <div style={{ fontSize: '0.65rem', textTransform: 'uppercase', color: 'var(--text-dim)', fontWeight: 600 }}>
            Context Cost
          </div>
          <div style={{ fontSize: '0.85rem', fontWeight: 800, color: strat.token_cost === 0 ? '#10b981' : '#f59e0b' }}>
            {strat.token_cost} tok
          </div>
        </div>
        <div>
          <div style={{ fontSize: '0.65rem', textTransform: 'uppercase', color: 'var(--text-dim)', fontWeight: 600 }}>
            VRAM / RAM
          </div>
          <div style={{ fontSize: '0.85rem', fontWeight: 800, color: strat.vram_mb === 0 ? '#10b981' : '#38bdf8' }}>
            {strat.vram_mb > 0 ? `${(strat.vram_mb / 1024).toFixed(1)} GB` : '0 MB'}
          </div>
        </div>
      </div>

      {/* Retrieved Paper Cards List */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '16px' }}>
        <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-dim)', fontWeight: 700, letterSpacing: '0.05em' }}>
          Top Retrieved Preprints ({strat.papers.length}):
        </div>

        {strat.papers.map((p, idx) => (
          <div
            key={idx}
            style={{
              padding: '10px 12px',
              borderRadius: '8px',
              background: 'rgba(0, 0, 0, 0.3)',
              border: '1px solid rgba(255, 255, 255, 0.05)',
              display: 'flex',
              flexDirection: 'column',
              gap: '4px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' }}>
              <span style={{ fontSize: '0.7rem', fontWeight: 800, fontFamily: 'var(--font-mono)', color: accentColor }}>
                #{p.rank} • arXiv:{p.arxiv_id}
              </span>
              {p.score !== undefined && (
                <span className="badge badge-cyan" style={{ fontSize: '0.65rem', padding: '2px 6px' }}>
                  Score: {p.score}
                </span>
              )}
            </div>

            <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#f8fafc', lineHeight: '1.3' }}>
              {p.title}
            </div>

            {/* Why it chose this paper */}
            <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginTop: '2px', lineHeight: '1.3' }}>
              <span style={{ color: accentColor, fontWeight: 600 }}>Why: </span>
              {p.match_reason}
            </div>
          </div>
        ))}
      </div>

      {/* Convene Action Button */}
      <button
        type="button"
        className={isFlagship ? 'btn-primary' : 'btn-secondary'}
        style={{
          width: '100%',
          padding: '10px 14px',
          fontSize: '0.85rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '8px',
          borderColor: isFlagship ? undefined : borderColor,
        }}
        onClick={() => onConvene(problemStatement, strat.strategy_id, paperIds)}
      >
        <span>Convene with {strat.tagline}</span>
        <ArrowRight size={14} />
      </button>
    </div>
  );
}
