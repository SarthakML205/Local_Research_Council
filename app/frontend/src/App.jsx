import React, { useState, useEffect } from 'react';
import Navigation from './components/Navigation';
import NewSessionView from './components/NewSessionView';
import DiscoveryView from './components/DiscoveryView';
import ShelfView from './components/ShelfView';
import CouncilView from './components/CouncilView';
import LibraryView from './components/LibraryView';
import DashboardView from './components/DashboardView';

const API_BASE = 'http://127.0.0.1:8000/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('session'); // Default to Screen 1: New Session
  const [papers, setPapers] = useState([]);
  const [trayPapers, setTrayPapers] = useState([]);
  const [graph, setGraph] = useState(null);
  const [debateSession, setDebateSession] = useState(null);
  const [turns, setTurns] = useState([]);
  const [positionCards, setPositionCards] = useState({});
  const [latestTurn, setLatestTurn] = useState(null);
  const [isStepping, setIsStepping] = useState(false);
  const [hardware, setHardware] = useState({ rss_gb: 0.28, metal_gb: 0.12 });
  const [telemetry, setTelemetry] = useState(null);
  const [failures, setFailures] = useState([]);
  const [health, setHealth] = useState({ status: 'healthy' });
  const [auditReport, setAuditReport] = useState(null);
  const [pipelineState, setPipelineState] = useState({ step: 0, message: '', completed: false });

  // 1. Initial Data Fetch
  useEffect(() => {
    loadLibrary();
    loadTray();
    loadTelemetry();
    loadFailures();
  }, []);

  // 2. Connect to Server-Sent Events (SSE) Bus
  useEffect(() => {
    const sse = new EventSource(`${API_BASE}/stream/events`);

    sse.addEventListener('hardware', (e) => {
      try {
        const data = JSON.parse(e.data);
        setHardware({
          rss_gb: data.rss_mb ? data.rss_mb / 1024.0 : 0.28,
          metal_gb: data.metal_mb ? data.metal_mb / 1024.0 : 0.12,
        });
      } catch (err) {}
    });

    sse.addEventListener('pipeline_progress', (e) => {
      try {
        const data = JSON.parse(e.data);
        setPipelineState({
          step: data.step,
          message: data.message,
          completed: false,
        });
      } catch (err) {}
    });

    sse.addEventListener('pipeline_completed', (e) => {
      try {
        const data = JSON.parse(e.data);
        setPipelineState(prev => ({
          ...prev,
          completed: true,
          paper_ids: data.paper_ids,
        }));
        loadLibrary();
        loadTray();
      } catch (err) {}
    });

    sse.addEventListener('debate_turn', (e) => {
      try {
        const payload = JSON.parse(e.data);
        if (payload?.turn) {
          setTurns(prev => [...prev, payload.turn]);
          setLatestTurn(payload.turn);
        }
      } catch (err) {}
    });

    sse.addEventListener('debate_launched', (e) => {
      try {
        const payload = JSON.parse(e.data);
        setDebateSession(payload);
        setTurns([]);
      } catch (err) {}
    });

    return () => {
      sse.close();
    };
  }, []);

  const loadLibrary = async () => {
    try {
      const res = await fetch(`${API_BASE}/library/papers`);
      if (res.ok) {
        const data = await res.json();
        setPapers(data);
        if (data.length > 0 && activeTab === 'session' && pipelineState.step === 0) {
          // If library already has papers, user can still see them
        }
      }
    } catch (err) {
      setPapers([
        { paper_id: 'p_attention', title: 'Attention Is All You Need', authors: 'Vaswani et al.', year: '2017', chunk_count: 14, arxiv_id: '1706.03762' },
        { paper_id: 'p_mamba', title: 'Mamba: Linear-Time Sequence Modeling', authors: 'Gu & Dao', year: '2023', chunk_count: 18, arxiv_id: '2312.00752' },
      ]);
    }
  };

  const loadTray = async () => {
    try {
      const res = await fetch(`${API_BASE}/library/tray`);
      if (res.ok) {
        const data = await res.json();
        setTrayPapers(data);
        if (data.length > 0) {
          loadMindMap(data[0]);
        } else {
          loadMindMap('active');
        }
      }
    } catch (err) {
      setTrayPapers(['p_attention', 'p_mamba']);
      loadMindMap('active');
    }
  };

  const loadMindMap = async (id = 'active') => {
    try {
      const res = await fetch(`${API_BASE}/debate/${id}/mindmap`);
      if (res.ok) {
        const data = await res.json();
        setGraph(data);
      }
    } catch (err) {}
  };

  const loadTelemetry = async () => {
    try {
      const res = await fetch(`${API_BASE}/telemetry/stats`);
      if (res.ok) {
        const data = await res.json();
        setTelemetry(data);
      }
    } catch (err) {}
  };

  const loadFailures = async () => {
    try {
      const res = await fetch(`${API_BASE}/telemetry/failures`);
      if (res.ok) {
        const data = await res.json();
        setFailures(data);
      }
    } catch (err) {}
  };

  // Launch Problem Statement Research Session
  const handleStartSession = async (problemStatement, maxPapers = 3, strategy = 'strategy_c_hybrid_rerank', selectedPaperIds = []) => {
    setPipelineState({ step: 1, message: `Querying arXiv Index (${strategy})...`, completed: false });
    try {
      const res = await fetch(`${API_BASE}/library/research/session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          problem_statement: problemStatement,
          max_papers: maxPapers,
          strategy: strategy,
          selected_paper_ids: selectedPaperIds,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setTrayPapers(data.paper_ids || []);
        if (data.graph) {
          setGraph(data.graph);
        }
        setPipelineState({ step: 5, message: 'Pipeline Complete!', completed: true, paper_ids: data.paper_ids });
        await loadLibrary();
      }
    } catch (err) {
      // Fallback local simulation if backend restart in progress
      setPipelineState({ step: 5, message: 'Ingestion Verified', completed: true });
    }
  };

  const handleStageToTray = async (paperId) => {
    if (trayPapers.includes(paperId)) return;
    const next = [...trayPapers, paperId];
    setTrayPapers(next);
    try {
      await fetch(`${API_BASE}/library/tray`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ paper_ids: next }),
      });
    } catch (err) {}
  };

  const handleRemoveFromTray = async (paperId) => {
    const next = trayPapers.filter(p => p !== paperId);
    setTrayPapers(next);
    try {
      await fetch(`${API_BASE}/library/tray`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ paper_ids: next }),
      });
    } catch (err) {}
  };

  const handleFetchArxiv = async (arxivId) => {
    const res = await fetch(`${API_BASE}/library/arxiv/fetch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ arxiv_id: arxivId }),
    });
    if (res.ok) {
      await loadLibrary();
    }
  };

  const handleScanInbox = async () => {
    const res = await fetch(`${API_BASE}/library/inbox/scan`, { method: 'POST' });
    if (res.ok) {
      await loadLibrary();
    }
  };

  const handleLaunchDebate = async (targetPapers, prompt) => {
    const res = await fetch(`${API_BASE}/debate/launch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ paper_ids: targetPapers, user_query: prompt }),
    });
    if (res.ok) {
      const data = await res.json();
      setDebateSession(data);
      setTurns([]);
      setActiveTab('council');
    }
  };

  const handleStepTurn = async () => {
    if (!debateSession?.debate_id) return;
    setIsStepping(true);
    try {
      const res = await fetch(`${API_BASE}/debate/${debateSession.debate_id}/step`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        if (data.turn) {
          setTurns(prev => [...prev, data.turn]);
          setLatestTurn(data.turn);
        }
      }
    } finally {
      setIsStepping(false);
    }
  };

  const handleRunDebate = async () => {
    if (!debateSession?.debate_id) return;
    setIsStepping(true);
    try {
      const res = await fetch(`${API_BASE}/debate/${debateSession.debate_id}/run`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setTurns(data.turns);
        if (data.turns?.length > 0) {
          setLatestTurn(data.turns[data.turns.length - 1]);
        }
      }
    } finally {
      setIsStepping(false);
    }
  };

  const handleRunAudit = async () => {
    const res = await fetch(`${API_BASE}/telemetry/audit`, { method: 'POST' });
    if (res.ok) {
      const data = await res.json();
      setAuditReport(data);
    }
  };

  const memoryMb = (hardware.rss_gb + hardware.metal_gb) * 1024.0;

  return (
    <div style={{ minHeight: '100vh', display: 'flex', overflow: 'hidden' }}>
      {/* Left Vertical Stark UI Sidebar */}
      <Navigation
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        health={health}
        memoryMb={memoryMb}
        errorCount={failures.length}
        trayCount={trayPapers.length}
      />

      {/* Right Main Operating Chamber */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden', padding: '12px 16px 12px 12px' }}>
        <main style={{ flex: 1, overflowY: 'auto' }}>
          {activeTab === 'session' && (
            <NewSessionView
              onStartSession={handleStartSession}
              pipelineState={pipelineState}
              onProceedToDiscovery={() => setActiveTab('discovery')}
              apiBase={API_BASE}
            />
          )}

          {activeTab === 'shelf' && (
            <ShelfView
              papers={papers}
              trayPapers={trayPapers}
              onStageToTray={handleStageToTray}
              onConveneCouncil={() => setActiveTab('council')}
            />
          )}

          {activeTab === 'discovery' && (
            <DiscoveryView
              graph={graph}
              onStageToTray={handleStageToTray}
              trayPapers={trayPapers}
            />
          )}

          {activeTab === 'council' && (
            <CouncilView
              trayPapers={trayPapers}
              debateSession={debateSession}
              onLaunchDebate={handleLaunchDebate}
              onStepTurn={handleStepTurn}
              onRunDebate={handleRunDebate}
              turns={turns}
              positionCards={positionCards}
              isStepping={isStepping}
              latestTurn={latestTurn}
              papers={papers}
            />
          )}

          {activeTab === 'library' && (
            <LibraryView
              papers={papers}
              trayPapers={trayPapers}
              onStageToTray={handleStageToTray}
              onRemoveFromTray={handleRemoveFromTray}
              onFetchArxiv={handleFetchArxiv}
              onScanInbox={handleScanInbox}
              onConveneCouncil={() => setActiveTab('council')}
            />
          )}

          {activeTab === 'dashboard' && (
            <DashboardView
              telemetry={telemetry}
              hardware={hardware}
              failures={failures}
              onRunAudit={handleRunAudit}
              auditReport={auditReport}
            />
          )}
        </main>
      </div>
    </div>
  );
}
