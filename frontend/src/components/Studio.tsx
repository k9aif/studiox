import { useState, useCallback, useRef, useEffect } from 'react';
import { ReactFlowProvider } from '@xyflow/react';
import type { Node, Edge } from '@xyflow/react';
import { useStore } from '../store';
import { Palette } from './Palette';
import { Canvas } from './Canvas';
import { BottomPanel } from './BottomPanel';
import { GeneratingOverlay } from './GeneratingOverlay';
import { IntakePanel } from './IntakePanel';
import { DocsPanel } from './DocsPanel';
import { AboutStudio } from './AboutStudio';
import { SetupPanel } from './SetupPanel';
import { Inspector } from './Inspector';
import { ScaffoldView } from './ScaffoldView';
import { ClassDiagramView } from './ClassDiagramView';
import type { NodeData, ProjectMeta } from '../types';

type CenterTab = 'about' | 'setup' | 'intake' | 'canvas' | 'classdiagram' | 'flow' | 'docs' | 'scaffold';

export function buildProjectPayload(
  project: ProjectMeta,
  nodes: Node<NodeData>[],
  edges: Edge[],
  llmConfig?: any
) {
  // Include hidden agent nodes — squads may be collapsed when scaffolding
  const agentNodes = nodes.filter((n) =>
    ['agent', 'validation_loop', 'critic_actor'].includes(n.data.componentType as string)
  );
  const squadNodes = nodes.filter((n) => n.data.componentType === 'squad');
  const orchNodes  = nodes.filter((n) => n.data.componentType === 'orchestrator');

  const agents = agentNodes.map((n) => ({
    name: n.data.label, type: n.data.agentType ?? 'BaseAgent',
    model: n.data.model ?? 'general', pattern: n.data.pattern ?? 'reasoning',
    description: n.data.description ?? '',
    temperature: n.data.temperature ?? '0.3',
    max_tokens: n.data.maxTokens ?? '2048',
    llm_provider: n.data.llmProvider ?? 'ollama',
  }));

  // Include ALL edges (hidden or visible) — squads may be collapsed when scaffolding
  const allEdges = [...edges];
  const squads = squadNodes.map((sq) => ({
    name: sq.data.label,
    agents: agentNodes
      .filter((a) => allEdges.some((e) => e.source === sq.id && e.target === a.id))
      .map((a) => a.data.label),
  })).filter((sq) => sq.agents.length > 0);

  const orchestrators = orchNodes.map((o) => {
    const connectedSquad = squadNodes.find((sq) =>
      edges.some((e) => e.source === o.id && e.target === sq.id)
    );
    return {
      name: o.data.label,
      squad: connectedSquad?.data.label ?? (squads[0]?.name ?? 'DefaultSquad'),
      retry_policy: o.data.retryPolicy ?? 'none',
    };
  });

  return {
    ...project, agents, squads, orchestrators,
    llm_provider:        llmConfig?.provider ?? '',
    llm_model:           llmConfig?.model ?? '',
    generation_source:   llmConfig?.model ? 'llm' : 'rule-based',
    generation_scoring:  null,
  };
}

export function Studio() {
  const {
    project, nodes, edges, clearCanvas, generating,
    history, future, undo, redo, layoutCanvas, setScreen, addGeneratedDoc,
    lastTemplateSuggestion, triggerReapply, clearSession, llmConfig, setLlmConfig, llmActive, setLlmActive,
    selectedNodeId, availableModels, lastSpecFile, addLog, setPendingCanvasSuggestion, setGenerating, genResult,
    setScaffoldFiles,
  } = useStore();

  const handleLogout = () => {
    sessionStorage.removeItem('k9x_authed');
    clearSession();
    setScreen('splash');
  };

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

  // ── Resizable panes ──────────────────────────────────────────
  const [leftWidth,  setLeftWidth]  = useState(290);
  const [rightWidth, setRightWidth] = useState(260);
  const isDraggingRight = useRef(false);
  const isDraggingLeft  = useRef(false);

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

  const handleExport = async () => {
    if (exportingRef.current) return;
    exportingRef.current = true;
    setExporting(true);
    setExportMsg(null);
    try {
      const payload = buildProjectPayload(project, nodes as Node<NodeData>[], edges, llmConfig);
      const res = await fetch('/api/generate', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(await res.text());
      const blob = await res.blob();
      const url  = URL.createObjectURL(blob);
      const zipName = `${project.project_name.toLowerCase().replace(/\s+/g, '_')}_scaffold.zip`;
      const a    = document.createElement('a');
      a.href = url;
      a.download = zipName;
      a.click();
      addGeneratedDoc(zipName, url);
      // Also fetch file tree for View Scaffold tab
      try {
        const previewRes = await fetch('/api/scaffold-preview', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
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
      exportingRef.current = false;
    }
  };

  const [showBottom, setShowBottom] = useState(true);
  const [centerTab, setCenterTab] = useState<CenterTab>('about');
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
          <a className="logo-k9" href="https://k9x.ai" target="_blank" rel="noopener noreferrer">K9X</a>
          <span className="logo-studio">Studio</span>
          {project.project_name && (
            <>
              <span className="header-divider">|</span>
              <span className="header-project">{project.project_name}</span>
            </>
          )}
          {project.domain && <span className="header-domain">{project.domain}</span>}
        </div>

        <div className="header-center">
          <span className="header-framework">k9-AIF Framework</span>
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

          <button className="btn-secondary" onClick={() => setShowBottom((v) => !v)}>
            {showBottom ? 'Hide Files' : 'Show Files'}
          </button>
          <button className="btn-secondary" onClick={clearCanvas}>Clear</button>

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
        <div className="studio-left" style={{ width: leftWidth, minWidth: leftWidth, maxWidth: leftWidth }}>
          <Palette onDragStart={onDragStart} onSwitchToCanvas={() => setCenterTab('canvas')} />
        </div>

        {/* Left resize handle */}
        <div className="pane-resizer" onMouseDown={startResizeLeft} title="Drag to resize" />

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
                { id: 'about',    label: 'About' },
                { id: 'setup',    label: 'Setup' },
                { id: 'intake',   label: 'Intake' },
                { id: 'canvas',   label: 'Canvas' },
                { id: 'flow',     label: 'Graph' },
                { id: 'docs',     label: 'Generated Docs' },
                { id: 'scaffold', label: 'View Scaffold' },
                { id: 'classdiagram', label: 'Class Diagram' },
              ] as { id: CenterTab; label: string }[]).map(({ id, label }) => (
                <button
                  key={id}
                  className={`center-tab ${centerTab === id ? 'center-tab-active' : ''}`}
                  onClick={() => setCenterTab(id)}
                >
                  {label}
                </button>
              ))}
            </div>

            {centerTab === 'about' && (
              <div style={{ flex: 1, overflow: 'auto', padding: '28px 36px' }}>
                <AboutStudio />
              </div>
            )}
            {centerTab === 'setup' && (
              <div style={{ flex: 1, overflow: 'auto', padding: '28px 36px' }}>
                <SetupPanel />
              </div>
            )}
            {centerTab === 'canvas' && (
              <>
                <div className="canvas-area">
                  {project.project_name && (
                    <div style={{
                      position: 'absolute', top: 10, left: '50%', transform: 'translateX(-50%)',
                      fontSize: 12, fontWeight: 500, color: 'rgba(239,68,68,0.6)',
                      letterSpacing: '0.5px', pointerEvents: 'none', zIndex: 5,
                      userSelect: 'none', whiteSpace: 'nowrap',
                      background: 'rgba(239,68,68,0.06)',
                      border: '1px solid rgba(239,68,68,0.15)',
                      borderRadius: 5, padding: '3px 12px',
                    }}>
                      {project.project_name}
                    </div>
                  )}
                  <Canvas draggedComponent={draggedComponent} generating={generating} />
                  <GeneratingOverlay visible={generating} result={genResult} />
                  {nodes.length > 0 && (
                    <button
                      className="canvas-reset-btn"
                      onClick={() => lastTemplateSuggestion ? triggerReapply() : clearCanvas()}
                      title={lastTemplateSuggestion ? 'Reset to template' : 'Clear canvas'}
                    >↺ Reset</button>
                  )}
                  {llmConfig?.model && nodes.length > 0 && (
                    <button
                      onClick={async () => {
                        setGenerating(true); setLlmActive(true);
                        addLog(`Regenerating with ${llmConfig.model}…`);
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
                      title="Pick a different model from the header and click to regenerate the flow"
                      style={{
                        position: 'absolute', bottom: 56, right: 16, zIndex: 10,
                        padding: '6px 14px', fontSize: 12, fontWeight: 600,
                        background: 'rgba(0,0,0,0.5)', border: '1px solid #2d6a4f',
                        color: '#52b788', borderRadius: 6, cursor: 'pointer',
                        letterSpacing: '0.5px', opacity: 0.9,
                      }}
                    >
                      ⟳ Regenerate
                    </button>
                  )}
                  <button
                    onClick={handleExport}
                    disabled={exporting || nodes.length === 0 || !project.project_name.trim()}
                    title={!project.project_name.trim() ? 'Set a project name first' : 'Generate and download scaffold ZIP'}
                    style={{
                      position: 'absolute', bottom: 16, right: 16, zIndex: 10,
                      padding: '8px 16px', fontSize: 13, fontWeight: 600,
                      background: 'rgba(0,0,0,0.5)', border: 'none',
                      color: '#f59e0b', borderRadius: 6, cursor: 'pointer',
                      letterSpacing: '0.5px', transition: 'opacity 0.15s',
                      opacity: (nodes.length === 0 || !project.project_name.trim()) ? 0.25 : 0.85,
                    }}
                  >
                    {exporting ? '⟳ Generating…' : '⬇ Generate Scaffold'}
                  </button>
                </div>
              </>
            )}

            {centerTab === 'intake' && <IntakePanel onSwitchTab={(t) => setCenterTab(t as any)} />}

            {centerTab === 'flow' && (
              <div className="center-placeholder">Visual Flow — coming soon</div>
            )}

            {centerTab === 'docs' && <DocsPanel />}
            {centerTab === 'scaffold' && <ScaffoldView />}
            {centerTab === 'classdiagram' && <ClassDiagramView />}

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

    </div>
  );
}
