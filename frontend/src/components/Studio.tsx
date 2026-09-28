import { useState, useCallback, useRef, useEffect } from 'react';
import { ReactFlowProvider } from '@xyflow/react';
import type { Node, Edge } from '@xyflow/react';
import { useStore } from '../store';
import { Palette } from './Palette';
import { Canvas } from './Canvas';
import { BottomPanel } from './BottomPanel';
import { GeneratingOverlay } from './GeneratingOverlay';
import { ExportingOverlay } from './ExportingOverlay';
import { IntakePanel } from './IntakePanel';
import { MappingDocumentPanel } from './MappingDocumentPanel';
import { EvalsPanel } from './EvalsPanel';
import { DocsPanel } from './DocsPanel';
import { AboutStudio } from './AboutStudio';
import { SetupPanel } from './SetupPanel';
import { Inspector } from './Inspector';
import { ScaffoldView } from './ScaffoldView';
import { ScaffoldDoneOverlay } from './ScaffoldDoneOverlay';
import { ClassDiagramView } from './ClassDiagramView';
import { ArchGuidePanel } from './ArchGuidePanel';
import type { NodeData, ProjectMeta } from '../types';

type CenterTab = 'about' | 'setup' | 'intake' | 'mapping' | 'evals' | 'canvas' | 'classdiagram' | 'flow' | 'docs' | 'scaffold' | 'archguide';

export function buildProjectPayload(
  project: ProjectMeta,
  nodes: Node<NodeData>[],
  edges: Edge[],
  llmConfig?: any
) {
  const ADAPTER_TYPES = ['messaging_adapter', 'workflow_adapter', 'process_adapter', 'api_adapter', 'bpm_adapter', 'rules_adapter', 'data_adapter'];
  const allEdges = [...edges];

  // Include hidden agent nodes — squads may be collapsed when scaffolding
  const agentNodes   = nodes.filter((n) =>
    ['agent', 'validation_loop', 'critic_actor'].includes(n.data.componentType as string)
  );
  const squadNodes   = nodes.filter((n) => n.data.componentType === 'squad');
  const orchNodes    = nodes.filter((n) => n.data.componentType === 'orchestrator');
  const adapterNodes = nodes.filter((n) => ADAPTER_TYPES.includes(n.data.componentType as string));

  const agents = agentNodes.map((n) => ({
    name: n.data.label, type: n.data.agentType ?? 'BaseAgent',
    model: n.data.model ?? 'general', pattern: n.data.pattern ?? 'reasoning',
    description: n.data.description ?? '',
    temperature: n.data.temperature ?? '0.3',
    max_tokens: n.data.maxTokens ?? '2048',
    llm_provider: n.data.llmProvider ?? 'ollama',
    // Was silently dropped here even though the node itself carries it
    // (Palette.tsx sets data.zone/data.processId from the BPMN suggestion) —
    // the implementation-plan.md generated after Generate Scaffold showed
    // "no zone data" for every row, and every process_id as "—", even
    // though the Traceability tab (built straight from the fresh BPMN
    // parse, never touching this function) showed both correctly. The BPMN
    // parser itself was never the problem — verified directly, still
    // extracts zone from the shape fill color exactly as documented.
    zone: n.data.zone ?? null,
    process_id: n.data.processId ?? null,
  }));

  const squads = squadNodes.map((sq) => ({
    name: sq.data.label,
    agents: agentNodes
      .filter((a) => allEdges.some((e) => e.source === sq.id && e.target === a.id))
      .map((a) => a.data.label),
  })).filter((sq) => sq.agents.length > 0);

  const orchestrators = orchNodes.map((o) => {
    const connectedSquads = squadNodes
      .filter((sq) => allEdges.some((e) => e.source === o.id && e.target === sq.id))
      .map((sq) => sq.data.label);
    return {
      name: o.data.label,
      // No positional fallback here: an orchestrator can legitimately have
      // zero squads (e.g. a GREEN/deterministic lane wired only to adapters)
      // — defaulting to squads[0] silently wires it to an unrelated squad.
      squads: connectedSquads,
      parallel: o.data.parallelSquads ?? false,
      retry_policy: o.data.retryPolicy ?? 'none',
    };
  });

  const adapters = adapterNodes.map((n) => {
    const parentOrch = orchNodes.find((o) => allEdges.some((e) => e.source === o.id && e.target === n.id));
    return {
      name:         n.data.label,
      adapter_type: n.data.componentType as string,
      description:  n.data.description ?? '',
      abbClass:     n.data.abbClass ?? '',
      orchestrator: parentOrch?.data.label ?? null,
      zone:         n.data.zone ?? null,
      process_id:   n.data.processId ?? null,
    };
  });

  return {
    ...project, agents, squads, orchestrators, adapters,
    llm_provider:        llmConfig?.provider ?? '',
    llm_model:           llmConfig?.model ?? '',
    llm_endpoint:        llmConfig?.endpoint ?? '',
    llm_api_key:         llmConfig?.api_key ?? '',
    generation_source:   llmConfig?.model ? 'llm' : 'rule-based',
    generation_scoring:  null,
  };
}

export function Studio() {
  const {
    project, nodes, edges, clearCanvas, clearProject, generating,
    history, future, undo, redo, layoutCanvas, setScreen, addGeneratedDoc,
    lastTemplateSuggestion, triggerReapply, clearSession, llmConfig, setLlmConfig, llmActive, setLlmActive,
    selectedNodeId, availableModels, setAvailableModels, lastSpecFile, canvasIsRuleBased, addLog, setPendingCanvasSuggestion, setGenerating, genResult,
    setScaffoldFiles, centerTab: storedCenterTab, setCenterTab: setStoredCenterTab, clientId,
    hasGeneratedScaffold, setHasGeneratedScaffold,
  } = useStore();

  const handleLogout = () => {
    sessionStorage.removeItem('k9x_authed');
    clearSession();
    setScreen('splash');
  };

  // ── Granite Guardian "live" indicator — Ravi: "wire to this under the
  // hood. and display on studio top line to indicate guardian is live."
  // The server prefers its own GOVERNANCE_LLM_ENDPOINT/MODEL env config
  // over anything sent here (see routes.py's _guardian_config), so this
  // still reports the real deployed Guardian even when Setup is untouched
  // — the query params are just a local-dev fallback.
  const [guardianLive, setGuardianLive] = useState<boolean | null>(null);
  const [guardianEnabled, setGuardianEnabled] = useState(true);
  useEffect(() => {
    const params = new URLSearchParams({
      endpoint: llmConfig?.endpoint ?? '', provider: llmConfig?.provider ?? '',
      model: llmConfig?.guardianModel ?? '', api_key: llmConfig?.api_key ?? '',
    });
    fetch(`/api/guardian/status?${params}`)
      .then((r) => r.json())
      .then((data) => { setGuardianEnabled(data.enabled !== false); setGuardianLive(Boolean(data.live)); })
      .catch(() => setGuardianLive(false));
  }, [llmConfig?.endpoint, llmConfig?.guardianModel]);

  // ── Keyboard shortcuts ───────────────────────────────────────
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const mod = e.metaKey || e.ctrlKey;
      if (!mod) return;
      if (!e.shiftKey && e.key === 'z') { e.preventDefault(); undo(); }
      else if ((e.shiftKey && e.key === 'z') || e.key === 'y') { e.preventDefault(); redo(); }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [undo, redo]);

  // llmConfig persists across a page refresh (store.ts partialize), but
  // availableModels deliberately doesn't (it's a live fetch result, not
  // stable state worth resurrecting stale) — so after a refresh the header
  // model picker falls back to plain text instead of the <select> below
  // (Ravi: "previously, we were used to pick the model from a drop-down
  // there and I can pick ... I am not able to choose any other model").
  // Re-fetch once on mount whenever we come back with a connected Ollama
  // config but an empty model list, so the dropdown reappears without
  // forcing a manual re-visit to Setup + Test Connection.
  useEffect(() => {
    if (llmConfig?.provider === 'ollama' && llmConfig?.endpoint && availableModels.length === 0) {
      fetch('/api/llm/models', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(llmConfig),
      })
        .then((res) => (res.ok ? res.json() : null))
        .then((data) => {
          // Ravi: "the LLM model is ignored I think. it shows wrong model
          // name" — a <select> whose value doesn't match any of its own
          // <option>s silently renders the first option instead (e.g. this
          // machine's own local Ollama has different models installed than
          // the configured one, like qwen3.8:27b on PowerAI). Only turn on
          // the dropdown when the configured model is actually one of the
          // fetched options — otherwise the plain-text fallback (which
          // always shows the real configured name, probe or no probe) is
          // strictly more correct than a dropdown that can't represent it.
          if (data?.models?.length && data.models.includes(llmConfig?.model)) {
            setAvailableModels(data.models);
          }
        })
        .catch(() => { /* silent — header just stays on plain-text fallback */ });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Resizable panes ──────────────────────────────────────────
  const [leftWidth,  setLeftWidth]  = useState(290);
  const [rightWidth, setRightWidth] = useState(260);
  const isDraggingRight = useRef(false);
  const isDraggingLeft  = useRef(false);
  // Collapse the palette sidebar for a wider canvas (Ravi: "the canvas can
  // be wider?"). Distinct from the existing drag-to-resize (220-500px) --
  // that already existed but couldn't go below 220px; this is a one-click
  // full collapse/restore, remembering the width to snap back to.
  const [leftCollapsed, setLeftCollapsed] = useState(false);
  const leftWidthBeforeCollapse = useRef(290);
  const toggleLeftCollapsed = useCallback(() => {
    setLeftCollapsed((collapsed) => {
      if (!collapsed) {
        leftWidthBeforeCollapse.current = leftWidth;
        setLeftWidth(0);
      } else {
        setLeftWidth(leftWidthBeforeCollapse.current);
      }
      return !collapsed;
    });
  }, [leftWidth]);

  const startResizeLeft = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    isDraggingLeft.current = true;
    const startX = e.clientX;
    const startW = leftWidth;
    const onMove = (ev: MouseEvent) =>
      setLeftWidth(Math.max(220, Math.min(500, startW + ev.clientX - startX)));
    const onUp = () => {
      isDraggingLeft.current = false;
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  }, [leftWidth]);

  const startResizeRight = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    isDraggingRight.current = true;
    const startX = e.clientX;
    const startW = rightWidth;
    const onMove = (ev: MouseEvent) =>
      setRightWidth(Math.max(200, Math.min(400, startW - (ev.clientX - startX))));
    const onUp = () => {
      isDraggingRight.current = false;
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  }, [rightWidth]);

  // ── Runtime config (projects_root) ──────────────────────────
  const [projectsRoot, setProjectsRoot] = useState('');
  useEffect(() => {
    fetch('/api/config').then((r) => r.json()).then((cfg) => {
      if (cfg.projects_root) setProjectsRoot(cfg.projects_root);
    }).catch(() => {});
  }, []);


  const toHostPath = (containerPath: string) => {
    if (!projectsRoot || !containerPath.startsWith(projectsRoot)) return containerPath;
    const rel = containerPath.slice(projectsRoot.length).replace(/^\//, '');
    return `~/k9x-studio-working/${rel}`;
  };

  // ── Export scaffold ──────────────────────────────────────────
  const [exporting, setExporting] = useState(false);
  const exportingRef = useRef(false);
  const [exportMsg, setExportMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [showScaffoldDone, setShowScaffoldDone] = useState(false);
  const [lastZipName, setLastZipName] = useState('');
  // LLM narration pass (doc_narration_service.py) — Ravi: "I just went to
  // setup and adding an LLM. I then clicked on Generate Scaffold... but it
  // did not even use the LLM. when that button is clicked, a check has to
  // be made to see if LLM is available." No separate opt-in toggle any
  // more: if Setup has a real LLM configured, narration just runs;
  // otherwise the plain deterministic docs are the (still fully good)
  // output. Simpler than the checkbox this replaced, and matches "if I set
  // it up, of course use it" — narration remains additive-safe either way
  // (falls back silently on any failure, never blocks the download).
  const hasLlmConfigured = Boolean(llmConfig?.endpoint?.trim() && llmConfig?.model?.trim());
  const richDocs = hasLlmConfigured;

  const handleExport = async () => {
    if (exportingRef.current) return;
    exportingRef.current = true;
    setExporting(true);
    setExportMsg(null);
    // Ravi: "I want to know when the backend LLM is being used. Display
    // while processing... it will be nice to see." The single /api/generate
    // request internally calls the narration LLM when richDocs is on — the
    // frontend can't see exactly when within that request, but knows
    // reliably that it will happen somewhere in it, so this reuses the same
    // llmActive flag (and header dot) canvas generation already uses.
    if (richDocs) setLlmActive(true);
    try {
      const payload = { ...buildProjectPayload(project, nodes as Node<NodeData>[], edges, llmConfig), generate_rich_docs: richDocs, client_id: clientId };
      const res = await fetch('/api/generate', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(await res.text());
      // Ravi: "download does not download fully... it is incomplete" —
      // the old fetch()+res.blob()+URL.createObjectURL()+<a>.click() path
      // buffers the whole zip into one JS Blob, then hands Chrome's
      // download manager a from-memory write-to-disk instead of a normal
      // streamed network download; that's the likely source of the
      // download getting stuck as "<name>.zip.crdownload" while the UI
      // claims it's done. Fix: /api/generate now just builds the zip
      // server-side and hands back a token; the actual save is a plain GET
      // the browser downloads the ordinary way (streamed straight to disk).
      const { token, filename: zipName } = await res.json();
      const a = document.createElement('a');
      a.href = `/api/generate/download/${token}`;
      a.download = zipName;
      a.click();
      addGeneratedDoc(zipName, a.href);
      setLastZipName(zipName);
      setShowScaffoldDone(true);
      // Ravi: "after a Scaffold is generated... I should not be able to
      // Generate Scaffold again... The button should be Regenerate?" then
      // softened to "Regenerate is ok (if someone deleted it from the
      // Generated Docs folder... or want to play around to check the
      // behaviour" — so this only relabels the button, never disables it.
      setHasGeneratedScaffold(true);
      // Also fetch file tree for View Scaffold tab — reads straight out of
      // the zip /api/generate already built (same token) rather than
      // re-posting the whole project, which used to trigger a completely
      // independent second generate_scaffold() call — with Rich Docs now
      // always on, that meant a second ~60-70s narration LLM call every
      // single time, right after the download had already started. Ravi:
      // "the original studio does not use LLM. This one does. This is the
      // difference" — halving the LLM exposure here removes one major
      // contributor to that gap.
      try {
        const previewRes = await fetch(`/api/generate/preview/${token}`);
        if (previewRes.ok) {
          const previewData = await previewRes.json();
          setScaffoldFiles(previewData.files ?? []);
          setCenterTab('scaffold');
        }
      } catch { /* silent */ }
      setExportMsg({ ok: true, text: '✦ Scaffold downloaded' });
      setTimeout(() => setExportMsg(null), 4000);
    } catch (err) {
      setExportMsg({ ok: false, text: 'Export failed: ' + err });
      setTimeout(() => setExportMsg(null), 6000);
    } finally {
      setExporting(false);
      setLlmActive(false);
      exportingRef.current = false;
    }
  };

  const [showBottom, setShowBottom] = useState(false);
  // Backed by the persisted store (see store.ts's `centerTab`), not local
  // useState — otherwise a refresh restores the canvas but still dumps the
  // user on "About", which reads as "still broken" even though the actual
  // data survived.
  const centerTab = storedCenterTab as CenterTab;
  const setCenterTab = setStoredCenterTab as (t: CenterTab) => void;
  const [draggedComponent, setDraggedComponent] = useState<any>(null);

  // Class Diagram needs the full center pane height — auto-hide the bottom
  // files panel while it's active, and restore whatever state it was in
  // when switching to any other tab.
  const prevShowBottomRef = useRef<boolean | null>(null);
  useEffect(() => {
    if (centerTab === 'classdiagram') {
      setShowBottom((current) => {
        prevShowBottomRef.current = current;
        return false;
      });
    } else if (prevShowBottomRef.current !== null) {
      setShowBottom(prevShowBottomRef.current);
      prevShowBottomRef.current = null;
    }
  }, [centerTab]);

  const onDragStart = useCallback((e: React.DragEvent, comp: any) => {
    e.dataTransfer.setData('application/k9node', JSON.stringify(comp));
    e.dataTransfer.effectAllowed = 'move';
    setDraggedComponent(comp);
  }, []);

  return (
    <div className="studio">

      {/* ── Header ─────────────────────────────────────────── */}
      <header className="studio-header">
        <div className="header-left">
          <button
            className="header-back"
            onClick={() => setScreen('landing')}
            title="Back to landing page"
          >←</button>
          <a className="logo-k9" href="https://k9x.ai" target="_blank" rel="noopener noreferrer">K9X</a>
          <span className="logo-studio">Studio</span>
          <span className="header-beta-tag">(Beta)</span>
          {guardianEnabled ? (
            <span
              className={`header-guardian-tag ${guardianLive ? 'header-guardian-live' : 'header-guardian-off'}`}
              title={guardianLive ? 'Granite Guardian is reachable — every Intake upload is screened before it\'s staged.' : 'Granite Guardian unreachable — Intake uploads will be blocked until it\'s configured (see Setup), or set GUARDIAN_ENABLED=false in .env.'}
            >
              🛡 Guardian {guardianLive === null ? '…' : guardianLive ? 'Live' : 'Offline'}
            </span>
          ) : (
            <span className="header-guardian-tag header-guardian-off" title="Guardian screening is turned off (GUARDIAN_ENABLED=false in .env).">
              🛡 Guardian Off
            </span>
          )}
          {project.project_name && (
            <>
              <span className="header-divider">|</span>
              <span className="header-project">{project.project_name}</span>
            </>
          )}
          {project.domain && <span className="header-domain">{project.domain}</span>}
        </div>

        <div className="header-center">
          <span className="header-framework">K9X Studio</span>
          <span className="header-tagline">BPMN, process specs and agent evaluation plans → governed K9-AIF scaffolds</span>
          {project.project_folder && project.project_name && (
            <span className="header-workdir" title={project.project_folder}>
              Working folder: <code>{toHostPath(project.project_folder)}</code>
            </span>
          )}
        </div>

        <div className="header-right">
          <div className={`llm-status-dot ${llmActive ? 'llm-dot-active' : llmConfig?.model ? 'llm-dot-on' : 'llm-dot-off'}`}
            title={llmActive ? 'LLM active' : llmConfig?.model ? 'LLM connected' : 'No LLM'} />
          {llmConfig?.model && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11,
              background: 'rgba(16,185,129,0.08)', border: '1px solid #065f46',
              borderRadius: 5, padding: '3px 6px 3px 10px', color: '#10b981' }}>
              <span style={{ opacity: 0.7 }}>{llmConfig.provider}</span>
              <span style={{ color: '#475569' }}>·</span>
              {availableModels.length > 0 ? (
                <select
                  value={llmConfig.model}
                  onChange={(e) => setLlmConfig({ ...llmConfig, model: e.target.value })}
                  style={{ background: 'transparent', border: 'none', color: '#10b981',
                    fontSize: 11, fontWeight: 600, cursor: 'pointer', outline: 'none' }}
                >
                  {availableModels.map((m) => <option key={m} value={m} style={{ background: '#1a1d27', color: '#e2e8f0' }}>{m}</option>)}
                </select>
              ) : (
                <span style={{ fontWeight: 600 }}>{llmConfig.model}</span>
              )}
              <span>✓</span>
            </div>
          )}
          <div className="header-sep" />
          {/* Undo / Redo */}
          <button
            className="btn-icon"
            onClick={undo}
            disabled={history.length === 0}
            title="Undo (⌘Z)"
          >↩</button>
          <button
            className="btn-icon"
            onClick={redo}
            disabled={future.length === 0}
            title="Redo (⌘⇧Z)"
          >↪</button>

          <div className="header-sep" />

          <button
            className="btn-icon"
            onClick={layoutCanvas}
            disabled={nodes.length === 0}
            title="Auto-arrange layout (⊞)"
          >⊞</button>

          <div className="header-sep" />

          <button className="btn-secondary" onClick={() => setShowBottom((v) => !v)} title="Toggle config files & activity log panel">
            {showBottom ? '▾ Config & Log' : '▸ Config & Log'}
          </button>
          <button className="btn-secondary" onClick={() => { clearProject(); addLog('Cleared — ready for new project'); }} title="Clear everything and start a new project">Clear</button>

          <div className="header-sep" />
          <div className="header-user">
            <span className="header-username">demo</span>
            <button className="header-logout" onClick={handleLogout} title="Sign out">↪ Sign out</button>
          </div>
        </div>
      </header>

      {/* ── Body ───────────────────────────────────────────── */}
      <div className="studio-body">

        {/* Left pane */}
        <div className="studio-left" style={{ width: leftWidth, minWidth: leftWidth, maxWidth: leftWidth, overflow: 'hidden' }}>
          {!leftCollapsed && <Palette onDragStart={onDragStart} onSwitchToCanvas={() => setCenterTab('canvas')} />}
        </div>

        {/* Left resize handle + collapse toggle */}
        {!leftCollapsed && (
          <div className="pane-resizer" onMouseDown={startResizeLeft} title="Drag to resize" />
        )}
        <button
          onClick={toggleLeftCollapsed}
          title={leftCollapsed ? 'Show palette' : 'Collapse palette for a wider canvas'}
          style={{
            position: 'absolute', left: leftWidth + (leftCollapsed ? 0 : 4), top: 70, zIndex: 20,
            width: 18, height: 36, display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: '#1e1e2e', border: '1px solid #2a2a35', borderRadius: '0 5px 5px 0',
            color: '#8892a4', cursor: 'pointer', fontSize: 11, padding: 0,
          }}
        >
          {leftCollapsed ? '▶' : '◀'}
        </button>

        {/* Export toast */}
        {exportMsg && (
          <div className={`export-toast ${exportMsg.ok ? 'export-toast-ok' : 'export-toast-err'}`}>
            {exportMsg.ok ? '✓' : '✕'} {exportMsg.text}
          </div>
        )}

        {/* Center */}
        <ReactFlowProvider>
          <div className="studio-center">

            {/* Center tabs */}
            <div className="center-tabs">
              {([
                { id: 'about',        label: 'About' },
                { id: 'archguide',    label: 'Arch Guide' },
                { id: 'setup',        label: 'Setup' },
                { id: 'intake',       label: 'Intake' },
                { id: 'mapping',      label: 'Traceability' },
                { id: 'evals',        label: 'Evals' },
                { id: 'canvas',       label: 'Canvas' },
                { id: 'flow',         label: 'Graph' },
                { id: 'docs',         label: 'Generated Docs' },
                { id: 'scaffold',     label: 'View Scaffold' },
                { id: 'classdiagram', label: 'Class Diagram' },
              ] as { id: CenterTab; label: string }[]).map(({ id, label }) => (
                <button
                  key={id}
                  className={`center-tab ${centerTab === id ? 'center-tab-active' : ''} ${id === 'intake' ? 'center-tab-intake' : ''}`}
                  onClick={() => setCenterTab(id)}
                >
                  {label}
                </button>
              ))}
            </div>

            {centerTab === 'about' && (
              <div style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: '28px 36px' }}>
                <AboutStudio />
              </div>
            )}
            {centerTab === 'setup' && (
              <div style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: '28px 36px' }}>
                <SetupPanel />
              </div>
            )}
            {centerTab === 'canvas' && (
              <>
                <div className="canvas-area">
                  <Canvas draggedComponent={draggedComponent} generating={generating} />
                  <GeneratingOverlay visible={generating} result={genResult} />
                  <ExportingOverlay visible={exporting} usingLlm={richDocs} />
                  {nodes.length > 0 && (
                    <button
                      className="canvas-reset-btn"
                      onClick={() => lastTemplateSuggestion ? triggerReapply() : clearCanvas()}
                      title={lastTemplateSuggestion ? 'Reset to template' : 'Clear canvas'}
                    >↺ Reset</button>
                  )}
                  {/* Ravi: Regenerate after a BPMN import was silently using
                      the generic /api/suggest LLM path (lastSpecFile is never
                      set by a BPMN import) and produced unrelated, generic
                      output. Regenerate's only paths are LLM-based
                      (/api/spec/import with force_llm, or /api/suggest) — the
                      mapping-document-first architecture requires BPMN/
                      restored canvases to stay rule-based, so this button
                      simply doesn't offer itself for those; re-edit via the
                      Traceability tab (CSV or inline) and Confirm instead.
                      Gated on the persisted canvasIsRuleBased flag, not the
                      lastBpmnFile object itself — a File can't survive a
                      page refresh (correctly excluded from persisted
                      storage), so gating on it directly let Regenerate
                      silently reappear for a still-BPMN-derived canvas after
                      any refresh (Ravi caught this via a live screenshot). */}
                  {/* Template canvases are rule-only: Regenerate rebuilds from
                      the original template (same as Reset) and never calls
                      an LLM, even when one is configured. The LLM paths below
                      only run for spec-upload / manual-entry canvases. */}
                  {nodes.length > 0 && !canvasIsRuleBased && (lastTemplateSuggestion || llmConfig?.model) && (
                    <button
                      onClick={async () => {
                        if (lastTemplateSuggestion) {
                          addLog('⟳ Rebuilt from the original template (rule-based, no LLM)');
                          triggerReapply();
                          return;
                        }
                        setGenerating(true); setLlmActive(true);
                        addLog(`Regenerating with ${llmConfig?.model}…`);
                        clearCanvas();
                        try {
                          if (lastSpecFile) {
                            // Re-run spec import with force_llm
                            const fd = new FormData();
                            fd.append('file', lastSpecFile);
                            fd.append('llm_config', JSON.stringify(llmConfig));
                            fd.append('force_llm', 'true');
                            const res = await fetch('/api/spec/import', { method: 'POST', body: fd });
                            const data = await res.json();
                            if (data.suggestion) { setPendingCanvasSuggestion(data.suggestion); }
                            const sc = data.scoring;
                            if (sc) {
                              const w = sc[sc.winner]; const l = sc.winner === 'llm' ? sc.rule_based : sc.llm;
                              addLog(`✓ ${sc.winner === 'llm' ? 'LLM' : 'Rule-based'} won — score: ${w?.score} (${w?.agent_count} agents, ${w?.squad_count} squads)`);
                              addLog(`  ${sc.winner === 'llm' ? 'Rule-based' : 'LLM'} score: ${l?.score} (${l?.agent_count} agents) — not selected`);
                            } else {
                              addLog(`✓ Reprocessed · ${(data.suggestion?.agents ?? []).length} agents · ${data.source}`);
                            }
                          } else {
                            // No spec file — re-run /api/suggest with intake fields
                            const payload: any = { ...project, llm: llmConfig };
                            const res = await fetch('/api/suggest', {
                              method: 'POST', headers: { 'Content-Type': 'application/json' },
                              body: JSON.stringify(payload),
                            });
                            const data = await res.json();
                            if (data.suggestion) { setPendingCanvasSuggestion(data.suggestion); }
                            addLog(`✓ Regenerated · source: ${data.source ?? 'llm'} · ${(data.suggestion?.agents ?? []).length} agents`);
                          }
                        } catch (err: any) {
                          addLog(`Regenerate failed: ${err.message}`, 'error');
                        } finally { setGenerating(false); setLlmActive(false); }
                      }}
                      title={lastTemplateSuggestion ? 'Rebuild the canvas from the original template (no LLM)' : 'Pick a different model from the header and click to regenerate the flow'}
                      style={{
                        position: 'absolute', bottom: 100, right: 16, zIndex: 10,
                        padding: '6px 14px', fontSize: 12, fontWeight: 600,
                        background: 'rgba(0,0,0,0.5)', border: '1px solid #2d6a4f',
                        color: '#52b788', borderRadius: 6, cursor: 'pointer',
                        letterSpacing: '0.5px', opacity: 0.9,
                      }}
                    >
                      ⟳ Regenerate
                    </button>
                  )}
                  <div
                    title={
                      hasLlmConfigured
                        ? `Will narrate README/MANIFEST/ARCHITECTURE/implementation-plan.md into two polished documents via ${llmConfig?.model} (${llmConfig?.provider}) in a consistent documentation style. Slower — not instant; falls back to the plain docs if that LLM isn't reachable. Configured in Setup.`
                        : 'Plain deterministic docs — configure an LLM in Setup to have Generate Scaffold automatically narrate them instead.'
                    }
                    style={{
                      position: 'absolute', bottom: 52, right: 16, zIndex: 10,
                      display: 'flex', alignItems: 'center', gap: 6,
                      padding: '5px 10px', fontSize: 11, fontWeight: 500,
                      background: 'rgba(0,0,0,0.5)', borderRadius: 6,
                      color: hasLlmConfigured ? '#a78bfa' : '#94a3b8',
                    }}
                  >
                    {hasLlmConfigured ? '✨ Rich LLM-narrated docs' : 'Plain docs (no LLM configured)'}
                  </div>
                  <button
                    onClick={handleExport}
                    disabled={exporting || nodes.length === 0 || !project.project_name.trim()}
                    title={
                      !project.project_name.trim()
                        ? 'Set a project name first'
                        : hasGeneratedScaffold
                          ? 'A scaffold was already generated for this project — click to regenerate'
                          : 'Generate and download scaffold ZIP'
                    }
                    style={{
                      position: 'absolute', bottom: 16, right: 16, zIndex: 10,
                      padding: '8px 16px', fontSize: 13, fontWeight: 600,
                      background: 'rgba(0,0,0,0.5)', border: 'none',
                      color: '#f59e0b', borderRadius: 6, cursor: 'pointer',
                      letterSpacing: '0.5px', transition: 'opacity 0.15s',
                      opacity: (nodes.length === 0 || !project.project_name.trim()) ? 0.25 : 0.85,
                    }}
                  >
                    {exporting
                      ? (richDocs ? '⟳ Narrating (may take a minute)…' : '⟳ Generating…')
                      : (hasGeneratedScaffold ? '↻ Regenerate Scaffold' : '⬇ Generate Scaffold')}
                  </button>
                </div>
              </>
            )}

            {centerTab === 'intake' && <IntakePanel onSwitchTab={(t) => setCenterTab(t as any)} />}

            {centerTab === 'mapping' && <MappingDocumentPanel onConfirm={() => setCenterTab('canvas')} />}
            {centerTab === 'evals' && <EvalsPanel />}

            {centerTab === 'flow' && (
              <div className="center-placeholder">Visual Flow — coming soon</div>
            )}

            {centerTab === 'docs' && <DocsPanel />}
            {centerTab === 'scaffold' && <ScaffoldView />}
            {centerTab === 'classdiagram' && <ClassDiagramView />}
            {centerTab === 'archguide' && <ArchGuidePanel />}

          </div>
        </ReactFlowProvider>

        {/* Right pane — appears only when a node is selected */}
        {selectedNodeId && (
          <>
            <div className="pane-resizer" onMouseDown={startResizeRight} title="Drag to resize" />
            <div className="studio-right" style={{ width: rightWidth, minWidth: rightWidth, maxWidth: rightWidth }}>
              <Inspector />
            </div>
          </>
        )}

      </div>

      {showBottom && <BottomPanel />}

      <ScaffoldDoneOverlay
        visible={showScaffoldDone}
        zipName={lastZipName}
        onClose={() => setShowScaffoldDone(false)}
        onViewScaffold={() => { setCenterTab('scaffold'); setShowScaffoldDone(false); }}
        onViewGeneratedDocs={() => { setCenterTab('docs'); setShowScaffoldDone(false); }}
      />

    </div>
  );
}
