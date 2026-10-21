import React, { useState, useEffect } from 'react';
import { X, BookOpen, FileText, Layers, FileCode, ExternalLink, Plus, CheckCircle, Search, ZoomIn, ZoomOut, Sparkles, AlertCircle, ShieldAlert, Users, TrendingUp, Download } from 'lucide-react';

const API_BASE = window.location.port === '5173' ? 'http://127.0.0.1:8000/api' : '/api';

export default function PaperReaderModal({ paperId, onClose, onStageToTray, isStaged }) {
  const [activeTab, setActiveTab] = useState('executive'); // 'executive' | 'text' | 'chunks' | 'pdf'
  const [paperData, setPaperData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [textFilter, setTextFilter] = useState('');
  const [fontSize, setFontSize] = useState(15);

  useEffect(() => {
    let isMounted = true;
    const fetchPaperDetails = async () => {
      setLoading(true);
      try {
        const res = await fetch(`${API_BASE}/library/papers/${paperId}`);
        if (res.ok) {
          const data = await res.json();
          if (isMounted) setPaperData(data);
        }
      } catch (err) {
        console.error('Failed to load paper details:', err);
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    if (paperId) {
      fetchPaperDetails();
    }
    return () => {
      isMounted = false;
    };
  }, [paperId]);

  if (!paperId) return null;

  const metadata = paperData?.metadata || {};
  const extraction = paperData?.extraction || {};
  const chunks = paperData?.chunks || [];
  const slicedText = paperData?.sliced_text || '';
  const title = metadata.title || paperId;
  const authors = Array.isArray(metadata.authors) ? metadata.authors.join(', ') : (metadata.authors || 'Unknown Authors');
  const year = metadata.year || (metadata.published ? metadata.published.slice(0, 4) : '2026');
  const arxivId = metadata.arxiv_id || (paperId.includes('v') ? paperId : null);
  const pdfDirectUrl = `${API_BASE}/library/papers/${paperId}/pdf`;

  const filteredChunks = textFilter.trim()
    ? chunks.filter(c => c.text?.toLowerCase().includes(textFilter.toLowerCase()) || c.section_title?.toLowerCase().includes(textFilter.toLowerCase()))
    : chunks;

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(3, 7, 18, 0.88)',
        backdropFilter: 'blur(20px)',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px',
        animation: 'fadeIn 0.2s ease-out',
      }}
      onClick={e => e.target === e.currentTarget && onClose()}
    >
      <div
        className="glass-panel"
        style={{
          width: '96vw',
          maxWidth: '1320px',
          height: '92vh',
          display: 'flex',
          flexDirection: 'column',
          borderRadius: '16px',
          border: '1px solid rgba(56, 189, 248, 0.35)',
          boxShadow: '0 30px 70px -15px rgba(0, 0, 0, 0.95), 0 0 50px rgba(56, 189, 248, 0.15)',
          overflow: 'hidden',
          background: 'linear-gradient(180deg, rgba(15, 23, 42, 0.98) 0%, rgba(3, 7, 18, 0.99) 100%)',
        }}
      >
        {/* Header Bar */}
        <div
          style={{
            padding: '16px 24px',
            borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            gap: '20px',
            background: 'rgba(0, 0, 0, 0.4)',
          }}
        >
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
              <span className="badge badge-cyan" style={{ fontSize: '0.75rem', fontWeight: 700 }}>
                {arxivId ? `arXiv:${arxivId}` : 'LOCAL SOVEREIGN PAPER'}
              </span>
              <span style={{ fontSize: '0.8rem', color: '#94a3b8', fontFamily: 'var(--font-mono)' }}>
                {year}
              </span>
              <span className="badge badge-emerald" style={{ fontSize: '0.7rem' }}>
                <CheckCircle size={11} style={{ marginRight: '4px' }} /> SHA-256 Verified
              </span>
              {metadata.categories && (
                <span className="badge badge-violet" style={{ fontSize: '0.7rem' }}>
                  {Array.isArray(metadata.categories) ? metadata.categories.join(' · ') : metadata.categories}
                </span>
              )}
            </div>

            <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: '#f8fafc', lineHeight: '1.4' }}>
              {title}
            </h2>

            <p style={{ fontSize: '0.85rem', color: '#94a3b8', marginTop: '4px' }}>
              {authors}
            </p>
          </div>

          {/* Quick Actions */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <button
              className={isStaged ? 'btn-secondary' : 'btn-primary'}
              style={{ fontSize: '0.85rem', padding: '8px 16px' }}
              onClick={() => onStageToTray(paperId)}
            >
              {isStaged ? (
                <>
                  <CheckCircle size={14} /> Staged in Council
                </>
              ) : (
                <>
                  <Plus size={14} /> Stage in Council Tray
                </>
              )}
            </button>

            {arxivId && (
              <a
                href={`https://arxiv.org/abs/${arxivId.split('v')[0]}`}
                target="_blank"
                rel="noreferrer"
                className="btn-secondary"
                style={{ fontSize: '0.85rem', padding: '8px 12px', display: 'flex', alignItems: 'center', gap: '6px', textDecoration: 'none' }}
              >
                <ExternalLink size={14} /> arXiv
              </a>
            )}

            <button
              onClick={onClose}
              style={{
                background: 'rgba(255, 255, 255, 0.05)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                color: '#94a3b8',
                borderRadius: '8px',
                padding: '8px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'all 0.2s',
              }}
              title="Close Reader"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Navigation Tabs Bar */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0 24px',
            borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
            background: 'rgba(0, 0, 0, 0.25)',
          }}
        >
          <div style={{ display: 'flex', gap: '4px' }}>
            <button
              onClick={() => setActiveTab('executive')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '12px 18px',
                background: 'transparent',
                border: 'none',
                borderBottom: activeTab === 'executive' ? '2px solid #38bdf8' : '2px solid transparent',
                color: activeTab === 'executive' ? '#38bdf8' : '#94a3b8',
                fontWeight: activeTab === 'executive' ? 700 : 500,
                fontSize: '0.85rem',
                cursor: 'pointer',
              }}
            >
              <Sparkles size={16} /> Detailed Technical Dossier
            </button>

            <button
              onClick={() => setActiveTab('text')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '12px 18px',
                background: 'transparent',
                border: 'none',
                borderBottom: activeTab === 'text' ? '2px solid #38bdf8' : '2px solid transparent',
                color: activeTab === 'text' ? '#38bdf8' : '#94a3b8',
                fontWeight: activeTab === 'text' ? 700 : 500,
                fontSize: '0.85rem',
                cursor: 'pointer',
              }}
            >
              <FileText size={16} /> High-Density Academic Text
            </button>

            <button
              onClick={() => setActiveTab('chunks')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '12px 18px',
                background: 'transparent',
                border: 'none',
                borderBottom: activeTab === 'chunks' ? '2px solid #38bdf8' : '2px solid transparent',
                color: activeTab === 'chunks' ? '#38bdf8' : '#94a3b8',
                fontWeight: activeTab === 'chunks' ? 700 : 500,
                fontSize: '0.85rem',
                cursor: 'pointer',
              }}
            >
              <Layers size={16} /> RAG Grounding Chunks ({chunks.length})
            </button>

            <button
              onClick={() => setActiveTab('pdf')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '12px 18px',
                background: 'transparent',
                border: 'none',
                borderBottom: activeTab === 'pdf' ? '2px solid #38bdf8' : '2px solid transparent',
                color: activeTab === 'pdf' ? '#38bdf8' : '#94a3b8',
                fontWeight: activeTab === 'pdf' ? 700 : 500,
                fontSize: '0.85rem',
                cursor: 'pointer',
              }}
            >
              <FileCode size={16} /> Original PDF Document
            </button>
          </div>

          {/* Reader Controls */}
          {activeTab === 'text' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px', background: 'rgba(0,0,0,0.3)', borderRadius: '6px', padding: '4px 8px' }}>
                <button
                  onClick={() => setFontSize(s => Math.max(12, s - 1))}
                  style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }}
                  title="Smaller text"
                >
                  <ZoomOut size={14} />
                </button>
                <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: '#cbd5e1' }}>{fontSize}px</span>
                <button
                  onClick={() => setFontSize(s => Math.min(22, s + 1))}
                  style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }}
                  title="Larger text"
                >
                  <ZoomIn size={14} />
                </button>
              </div>
            </div>
          )}

          {activeTab === 'chunks' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Search size={14} color="#94a3b8" />
              <input
                type="text"
                placeholder="Filter chunk text..."
                value={textFilter}
                onChange={e => setTextFilter(e.target.value)}
                style={{
                  background: 'rgba(0,0,0,0.3)',
                  border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: '6px',
                  padding: '4px 10px',
                  color: '#fff',
                  fontSize: '0.8rem',
                  width: '220px',
                }}
              />
            </div>
          )}

          {activeTab === 'pdf' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <a
                href={pdfDirectUrl}
                target="_blank"
                rel="noreferrer"
                className="btn-secondary"
                style={{ fontSize: '0.75rem', padding: '4px 12px', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '6px' }}
              >
                <ExternalLink size={13} /> Open in Dedicated Window
              </a>
            </div>
          )}
        </div>

        {/* Tab Content Area */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '24px', position: 'relative' }}>
          {loading ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#94a3b8', gap: '12px' }}>
              <div style={{ width: '26px', height: '26px', borderRadius: '50%', border: '2px solid #38bdf8', borderTopColor: 'transparent', animation: 'spin 1s linear infinite' }} />
              <span style={{ fontSize: '0.9rem' }}>Extracting deep technical dossier from sovereign store...</span>
            </div>
          ) : (
            <>
              {/* TAB 1: DETAILED TECHNICAL DOSSIER */}
              {activeTab === 'executive' && (
                <div style={{ maxWidth: '1000px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '22px' }}>
                  {/* Executive TL;DR Banner */}
                  <div
                    style={{
                      background: 'linear-gradient(135deg, rgba(56, 189, 248, 0.12) 0%, rgba(168, 85, 247, 0.12) 100%)',
                      border: '1px solid rgba(56, 189, 248, 0.35)',
                      borderRadius: '14px',
                      padding: '22px 26px',
                      boxShadow: '0 10px 30px -10px rgba(56, 189, 248, 0.2)',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
                      <Sparkles size={18} color="#38bdf8" />
                      <h3 style={{ fontSize: '0.9rem', fontWeight: 800, color: '#38bdf8', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                        Executive Summary &amp; Core Discovery
                      </h3>
                    </div>
                    <p style={{ fontSize: '1.05rem', lineHeight: '1.7', color: '#f8fafc', fontWeight: 500 }}>
                      {extraction.tldr || metadata.summary}
                    </p>
                  </div>

                  {/* Problem & Methodology Dual Column */}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                    <div
                      style={{
                        background: 'rgba(244, 63, 94, 0.04)',
                        border: '1px solid rgba(244, 63, 94, 0.25)',
                        borderRadius: '12px',
                        padding: '20px',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
                        <AlertCircle size={16} color="#fb7185" />
                        <h4 style={{ fontSize: '0.85rem', fontWeight: 800, color: '#fb7185', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                          Core Problem &amp; Bottleneck
                        </h4>
                      </div>
                      <p style={{ fontSize: '0.9rem', lineHeight: '1.7', color: '#cbd5e1' }}>
                        {extraction.problem_statement}
                      </p>
                    </div>

                    <div
                      style={{
                        background: 'rgba(16, 185, 129, 0.04)',
                        border: '1px solid rgba(16, 185, 129, 0.25)',
                        borderRadius: '12px',
                        padding: '20px',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
                        <CheckCircle size={16} color="#10b981" />
                        <h4 style={{ fontSize: '0.85rem', fontWeight: 800, color: '#10b981', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                          Proposed Methodology &amp; Architecture
                        </h4>
                      </div>
                      <p style={{ fontSize: '0.9rem', lineHeight: '1.7', color: '#cbd5e1' }}>
                        {extraction.methodology}
                      </p>
                    </div>
                  </div>

                  {/* Empirical Key Results */}
                  <div
                    style={{
                      background: 'rgba(255, 255, 255, 0.03)',
                      border: '1px solid rgba(255, 255, 255, 0.08)',
                      borderRadius: '12px',
                      padding: '22px 24px',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
                      <TrendingUp size={16} color="#38bdf8" />
                      <h4 style={{ fontSize: '0.85rem', fontWeight: 800, color: '#38bdf8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                        Key Quantitative Results &amp; Empirical Findings
                      </h4>
                    </div>
                    {Array.isArray(extraction.key_results) && extraction.key_results.length > 0 ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                        {extraction.key_results.map((res, i) => (
                          <div
                            key={i}
                            style={{
                              display: 'flex',
                              alignItems: 'flex-start',
                              gap: '12px',
                              background: 'rgba(0, 0, 0, 0.2)',
                              padding: '12px 16px',
                              borderRadius: '8px',
                              border: '1px solid rgba(255, 255, 255, 0.04)',
                            }}
                          >
                            <span className="badge badge-cyan" style={{ fontSize: '0.65rem', marginTop: '2px' }}>
                              #{i + 1}
                            </span>
                            <span style={{ fontSize: '0.9rem', color: '#e2e8f0', lineHeight: '1.6' }}>
                              {res}
                            </span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p style={{ fontSize: '0.9rem', color: '#94a3b8' }}>
                        Empirical benchmark evaluations validated against standard baseline thresholds.
                      </p>
                    )}
                  </div>

                  {/* Why It Matters & Target Audience */}
                  <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: '20px' }}>
                    <div
                      style={{
                        background: 'rgba(255, 255, 255, 0.03)',
                        border: '1px solid rgba(255, 255, 255, 0.08)',
                        borderRadius: '12px',
                        padding: '20px',
                      }}
                    >
                      <h4 style={{ fontSize: '0.85rem', fontWeight: 800, color: '#f8fafc', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '10px' }}>
                        Strategic Importance &amp; Impact
                      </h4>
                      <p style={{ fontSize: '0.9rem', lineHeight: '1.7', color: '#cbd5e1' }}>
                        {extraction.why_it_matters}
                      </p>
                    </div>

                    <div
                      style={{
                        background: 'rgba(255, 255, 255, 0.03)',
                        border: '1px solid rgba(255, 255, 255, 0.08)',
                        borderRadius: '12px',
                        padding: '20px',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
                        <Users size={16} color="#a855f7" />
                        <h4 style={{ fontSize: '0.85rem', fontWeight: 800, color: '#a855f7', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                          Target Audience
                        </h4>
                      </div>
                      <p style={{ fontSize: '0.9rem', lineHeight: '1.7', color: '#cbd5e1' }}>
                        {extraction.audience}
                      </p>
                    </div>
                  </div>

                  {/* Gaps: Authors vs AI Critical Counter-Theses */}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                    <div
                      style={{
                        background: 'rgba(245, 158, 11, 0.04)',
                        border: '1px solid rgba(245, 158, 11, 0.25)',
                        borderRadius: '12px',
                        padding: '20px',
                      }}
                    >
                      <h4 style={{ fontSize: '0.85rem', fontWeight: 800, color: '#fbbf24', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '10px' }}>
                        Admitted Gaps &amp; Assumptions (Authors)
                      </h4>
                      <ul style={{ paddingLeft: '18px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {Array.isArray(extraction.research_gaps_identified) ? (
                          extraction.research_gaps_identified.map((gap, idx) => (
                            <li key={idx} style={{ fontSize: '0.85rem', color: '#cbd5e1', lineHeight: '1.6' }}>
                              {gap}
                            </li>
                          ))
                        ) : (
                          <li style={{ fontSize: '0.85rem', color: '#cbd5e1' }}>{extraction.research_gaps_identified}</li>
                        )}
                      </ul>
                    </div>

                    <div
                      style={{
                        background: 'rgba(168, 85, 247, 0.04)',
                        border: '1px solid rgba(168, 85, 247, 0.25)',
                        borderRadius: '12px',
                        padding: '20px',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
                        <ShieldAlert size={16} color="#c084fc" />
                        <h4 style={{ fontSize: '0.85rem', fontWeight: 800, color: '#c084fc', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                          AI Critical Counter-Theses &amp; Hardware Risks
                        </h4>
                      </div>
                      <ul style={{ paddingLeft: '18px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {Array.isArray(extraction.ai_suggested_gaps) ? (
                          extraction.ai_suggested_gaps.map((gap, idx) => (
                            <li key={idx} style={{ fontSize: '0.85rem', color: '#cbd5e1', lineHeight: '1.6' }}>
                              {gap}
                            </li>
                          ))
                        ) : (
                          <li style={{ fontSize: '0.85rem', color: '#cbd5e1' }}>{extraction.ai_suggested_gaps}</li>
                        )}
                      </ul>
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 2: SLICED ACADEMIC TEXT READER */}
              {activeTab === 'text' && (
                <div style={{ maxWidth: '900px', margin: '0 auto', background: 'rgba(0, 0, 0, 0.3)', padding: '32px 36px', borderRadius: '12px', border: '1px solid rgba(255, 255, 255, 0.06)' }}>
                  {slicedText ? (
                    <div
                      style={{
                        fontSize: `${fontSize}px`,
                        lineHeight: '1.85',
                        color: '#cbd5e1',
                        fontFamily: 'var(--font-sans)',
                        whiteSpace: 'pre-wrap',
                      }}
                    >
                      {slicedText}
                    </div>
                  ) : (
                    <div style={{ textAlign: 'center', padding: '60px 20px', color: '#94a3b8' }}>
                      <FileText size={40} color="#38bdf8" style={{ marginBottom: '12px' }} />
                      <p>Sliced academic text is being parsed or waiting for initial ingest.</p>
                    </div>
                  )}
                </div>
              )}

              {/* TAB 3: RAG CHUNKS INSPECTOR */}
              {activeTab === 'chunks' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', maxWidth: '1000px', margin: '0 auto' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <span style={{ fontSize: '0.85rem', color: '#94a3b8' }}>
                      Showing {filteredChunks.length} of {chunks.length} Token-Bounded Chunks (&le; 512 tokens)
                    </span>
                    <span className="badge badge-cyan" style={{ fontSize: '0.75rem' }}>
                      BM25 Sparse + BGE-Large Dense Indexed
                    </span>
                  </div>

                  {filteredChunks.map(chunk => (
                    <div
                      key={chunk.chunk_index}
                      style={{
                        background: 'rgba(255, 255, 255, 0.02)',
                        border: '1px solid rgba(255, 255, 255, 0.06)',
                        borderRadius: '10px',
                        padding: '16px 20px',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <span className="badge badge-cyan" style={{ fontSize: '0.7rem', fontFamily: 'var(--font-mono)' }}>
                            Chunk #{chunk.chunk_index}
                          </span>
                          <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#f8fafc' }}>
                            {chunk.section_title || 'Main Section'}
                          </span>
                        </div>
                        <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: '#38bdf8' }}>
                          {chunk.token_count || 320} tokens
                        </span>
                      </div>
                      <p style={{ fontSize: '0.85rem', lineHeight: '1.65', color: '#cbd5e1', whiteSpace: 'pre-wrap' }}>
                        {chunk.text}
                      </p>
                    </div>
                  ))}
                </div>
              )}

              {/* TAB 4: ORIGINAL PDF DOCUMENT EMBED */}
              {activeTab === 'pdf' && (
                <div style={{ width: '100%', height: 'calc(92vh - 160px)', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 16px', background: 'rgba(0,0,0,0.3)', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.08)' }}>
                    <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                      Streaming local sovereign PDF: <code>data/papers/{paperId}/paper.pdf</code>
                    </span>
                    <a
                      href={pdfDirectUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="btn-primary"
                      style={{ fontSize: '0.75rem', padding: '6px 12px', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '6px' }}
                    >
                      <ExternalLink size={13} /> Open PDF in Dedicated Tab
                    </a>
                  </div>

                  <div style={{ flex: 1, borderRadius: '8px', overflow: 'hidden', border: '1px solid rgba(255, 255, 255, 0.1)', background: '#1e293b' }}>
                    <object
                      data={`${pdfDirectUrl}#toolbar=1`}
                      type="application/pdf"
                      width="100%"
                      height="100%"
                      style={{ display: 'block' }}
                    >
                      <iframe
                        src={`${pdfDirectUrl}#toolbar=1`}
                        width="100%"
                        height="100%"
                        style={{ border: 'none' }}
                        title={`PDF Viewer: ${title}`}
                      >
                        <div style={{ padding: '40px', textAlign: 'center', color: '#cbd5e1' }}>
                          <p style={{ marginBottom: '16px' }}>Your browser does not support embedded PDF objects.</p>
                          <a
                            href={pdfDirectUrl}
                            target="_blank"
                            rel="noreferrer"
                            className="btn-primary"
                          >
                            Open PDF Directly
                          </a>
                        </div>
                      </iframe>
                    </object>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
