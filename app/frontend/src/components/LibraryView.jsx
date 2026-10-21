import React, { useState } from 'react';
import { BookOpen, Download, FolderInput, Plus, Trash2, CheckCircle, ExternalLink, Eye, Sparkles } from 'lucide-react';
import PaperReaderModal from './PaperReaderModal';

export default function LibraryView({
  papers,
  trayPapers,
  onStageToTray,
  onRemoveFromTray,
  onFetchArxiv,
  onScanInbox,
  onConveneCouncil,
}) {
  const [arxivInput, setArxivInput] = useState('');
  const [isFetching, setIsFetching] = useState(false);
  const [readingPaperId, setReadingPaperId] = useState(null);

  const handleFetch = async () => {
    if (!arxivInput.trim()) return;
    setIsFetching(true);
    try {
      await onFetchArxiv(arxivInput.trim());
      setArxivInput('');
    } finally {
      setIsFetching(false);
    }
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '20px', height: 'calc(100vh - 100px)', padding: '0 16px 16px' }}>
      {/* Main Bookshelf */}
      <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {/* Top Controls: arXiv Fetcher & Inbox Scanner */}
        <div style={{
          padding: '16px 20px',
          borderBottom: '1px solid var(--border-color)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '16px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <BookOpen size={20} color="#38bdf8" />
            <h2 style={{ fontSize: '1.1rem', fontWeight: 800 }}>Sovereign Paper Bookshelf</h2>
            <span className="badge badge-cyan" style={{ fontSize: '0.75rem' }}>
              {papers.length} Papers Archived
            </span>
          </div>

          <div style={{ display: 'flex', gap: '10px', flex: 1, maxWidth: '520px' }}>
            <input
              type="text"
              placeholder="Fetch arXiv ID (e.g., 2301.07041 or 1706.03762)..."
              value={arxivInput}
              onChange={e => setArxivInput(e.target.value)}
              style={{
                flex: 1,
                background: 'rgba(0, 0, 0, 0.4)',
                border: '1px solid var(--border-color)',
                borderRadius: '8px',
                padding: '8px 14px',
                color: '#fff',
                fontSize: '0.85rem',
                fontFamily: 'var(--font-sans)',
              }}
              onKeyDown={e => e.key === 'Enter' && handleFetch()}
            />
            <button
              className="btn-primary"
              style={{ padding: '8px 14px', fontSize: '0.8rem' }}
              onClick={handleFetch}
              disabled={isFetching || !arxivInput.trim()}
            >
              <Download size={14} /> {isFetching ? 'Fetching...' : 'Download'}
            </button>
            <button
              className="btn-secondary"
              style={{ padding: '8px 14px', fontSize: '0.8rem' }}
              onClick={onScanInbox}
            >
              <FolderInput size={14} /> Scan Inbox
            </button>
          </div>
        </div>

        {/* Papers Grid */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '20px' }}>
          {papers.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--text-muted)' }}>
              <BookOpen size={48} color="#38bdf8" style={{ marginBottom: '16px' }} />
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '6px' }}>No Papers Ingested Yet</h3>
              <p style={{ fontSize: '0.85rem', maxWidth: '420px', margin: '0 auto' }}>
                Download a research paper from arXiv above or start a research query from the New Session screen.
              </p>
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '16px' }}>
              {papers.map(p => {
                const isStaged = trayPapers.includes(p.paper_id);
                const authorsList = Array.isArray(p.authors) ? p.authors.join(', ') : (p.authors || 'Lead Authors');

                return (
                  <div
                    key={p.paper_id}
                    style={{
                      background: 'rgba(255, 255, 255, 0.03)',
                      border: '1px solid var(--border-color)',
                      borderRadius: '12px',
                      padding: '18px',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                      transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
                      cursor: 'pointer',
                      position: 'relative',
                    }}
                    className="paper-card-hover"
                    onClick={() => setReadingPaperId(p.paper_id)}
                  >
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                        <span className="badge badge-cyan" style={{ fontSize: '0.7rem' }}>
                          {p.arxiv_id || 'LOCAL IMPORT'}
                        </span>
                        <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)' }}>
                          {p.year || '2026'}
                        </span>
                      </div>

                      <h4 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '8px', lineHeight: '1.4', color: '#f8fafc' }}>
                        {p.title || p.paper_id}
                      </h4>

                      <p style={{ fontSize: '0.8rem', color: '#94a3b8', lineHeight: '1.5', marginBottom: '14px' }}>
                        {authorsList}
                      </p>
                    </div>

                    <div style={{
                      paddingTop: '12px',
                      borderTop: '1px solid rgba(255, 255, 255, 0.06)',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <button
                          className="btn-secondary"
                          style={{ fontSize: '0.75rem', padding: '6px 10px', display: 'flex', alignItems: 'center', gap: '4px' }}
                          onClick={(e) => {
                            e.stopPropagation();
                            setReadingPaperId(p.paper_id);
                          }}
                        >
                          <Eye size={13} /> Read Paper
                        </button>
                        <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                          {p.chunk_count || 32} chunks
                        </span>
                      </div>

                      <button
                        className={isStaged ? 'btn-secondary' : 'btn-primary'}
                        style={{ fontSize: '0.75rem', padding: '6px 12px' }}
                        onClick={(e) => {
                          e.stopPropagation();
                          if (isStaged) {
                            onRemoveFromTray(p.paper_id);
                          } else {
                            onStageToTray(p.paper_id);
                          }
                        }}
                      >
                        {isStaged ? 'Staged' : '+ Stage in Tray'}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Right Rail: Council Tray Staging */}
      <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-color)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 800 }}>Council Tray</h3>
            <span className="badge badge-emerald">
              {trayPapers.length} / 6 Papers
            </span>
          </div>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
            Requires between 2 and 6 papers to convene.
          </p>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {trayPapers.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px 10px', color: 'var(--text-dim)' }}>
              <p style={{ fontSize: '0.8rem' }}>Stage papers from the bookshelf to convene a council debate.</p>
            </div>
          ) : (
            trayPapers.map((pid, idx) => (
              <div
                key={pid}
                style={{
                  background: 'rgba(255, 255, 255, 0.03)',
                  padding: '10px 12px',
                  borderRadius: '8px',
                  border: '1px solid var(--border-color)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}
              >
                <div>
                  <span className="badge badge-cyan" style={{ fontSize: '0.65rem', marginBottom: '2px' }}>
                    Slot #{idx + 1}
                  </span>
                  <p style={{ fontSize: '0.8rem', fontWeight: 600 }}>{pid}</p>
                </div>
                <button
                  onClick={() => onRemoveFromTray(pid)}
                  style={{ background: 'none', border: 'none', color: '#f43f5e', cursor: 'pointer', padding: '4px' }}
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))
          )}
        </div>

        <div style={{ padding: '16px', borderTop: '1px solid var(--border-color)', background: 'rgba(0, 0, 0, 0.2)' }}>
          <button
            className="btn-primary"
            style={{ width: '100%' }}
            onClick={onConveneCouncil}
            disabled={trayPapers.length < 2 || trayPapers.length > 6}
          >
            Convene Council Debate ({trayPapers.length} Papers)
          </button>
        </div>
      </div>

      {/* Reader Modal */}
      {readingPaperId && (
        <PaperReaderModal
          paperId={readingPaperId}
          onClose={() => setReadingPaperId(null)}
          onStageToTray={onStageToTray}
          isStaged={trayPapers.includes(readingPaperId)}
        />
      )}
    </div>
  );
}
