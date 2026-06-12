import { useEffect, useRef, useState } from 'react';
import type { PaletteComponent, ComponentType, NodeData } from '../types';
import { useStore } from '../store';
import { VALID_TARGETS, VALID_NEXT_LABEL } from '../rules';
import { PROJECT_TEMPLATES } from '../templates';
import type { ProjectTemplate } from '../templates';

const COMPONENT_COLORS: Record<string, string> = {
  intent_squad: '#06b6d4',
  router: '#6366f1', orchestrator: '#8b5cf6', squad: '#0ea5e9',
  agent: '#10b981', validation_loop: '#f59e0b', critic_actor: '#ef4444', guard: '#64748b',
};
const AGENT_TYPE_MAP: Record<string, string> = {
  BaseAgent: 'agent', K9ValidationLoopAgent: 'validation_loop', K9CriticActorAgent: 'critic_actor',
};
const ABB_MAP: Record<string, string> = {
  BaseAgent: 'BaseAgent', K9ValidationLoopAgent: 'K9ValidationLoopAgent', K9CriticActorAgent: 'K9CriticActorAgent',
};
const ICONS: Record<string, string> = {
  intent_squad: '⊕',
  router: '⇄', orchestrator: '◈', squad: '◫', agent: '◉',
  validation_loop: '↻', critic_actor: '⇌', guard: '⊛',
};

let _pid = 200;
const uid2 = () => `regen-${_pid++}`;

interface PaletteProps {
  onDragStart: (e: React.DragEvent, component: PaletteComponent) => void;
  onSwitchToCanvas?: () => void;
}

type PaletteTab = 'components' | 'project';


function slugify(s: string) {
  return s.toLowerCase().trim().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '');
}

export function Palette({ onDragStart, onSwitchToCanvas }: PaletteProps) {
  const [tab, setTab] = useState<PaletteTab>('project');
  const [components, setComponents] = useState<PaletteComponent[]>([]);
  const [projectsRoot, setProjectsRoot] = useState('');
  const [lastTemplate, setLastTemplate] = useState<ProjectTemplate | null>(null);
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({});
  const toggleSection = (id: string) => setExpandedSections((s) => ({ ...s, [id]: !s[id] }));
  const isFirstRender = useRef(true);
  const { project, setProject, clearCanvas, addNode, onConnect,
          nodes, selectedNodeId, setGenerating, layoutCanvas, collapseAllSquads,
          addLog, setLastTemplateSuggestion, setLastTemplateId,
          reapplyTemplate, pendingCanvasSuggestion, setPendingCanvasSuggestion,
          setLastSpecFile, setSpecImported } = useStore();


  useEffect(() => {
    fetch('/api/config')
      .then((r) => r.json())
      .then((cfg) => {
        if (cfg.projects_root) setProjectsRoot(cfg.projects_root);
      })
      .catch(() => {});
  }, []);


  // When container root loads, fix project_folder if it's wrong or empty
  useEffect(() => {
    if (!projectsRoot) return;
    const root = projectsRoot.endsWith('/') ? projectsRoot : `${projectsRoot}/`;
    const currentFolder = project.project_folder;
    if (!currentFolder || !currentFolder.startsWith(root)) {
      setProject({ ...project, project_folder: containerOutputPath(project.project_name) });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectsRoot]);

  const containerOutputPath = (name: string) => {
    const root = projectsRoot.endsWith('/') ? projectsRoot : `${projectsRoot}/`;
    const slug = slugify(name);
    return slug ? `${root}k9_projects/${slug}/` : `${root}k9_projects/`;
  };

  const setField = (key: string, val: string) => {
    const updated = { ...project, [key]: val };
    if (key === 'project_name') updated.project_folder = containerOutputPath(val);
    setProject(updated);
  };
  void setField; // used by BPMN import path via setProject indirectly

  const selectedNode = nodes.find((n) => n.id === selectedNodeId);
  const selectedType = selectedNode ? (selectedNode.data as NodeData).componentType : null;
  const validNextTypes: ComponentType[] | null = selectedType ? VALID_TARGETS[selectedType] : null;

  useEffect(() => {
    if (isFirstRender.current) { isFirstRender.current = false; return; }
    if (lastTemplate?.suggestion) {
      buildCanvas(lastTemplate.suggestion);
      addLog(`↺ Reset to template: ${lastTemplate.name}`);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reapplyTemplate]);

  useEffect(() => {
    if (!pendingCanvasSuggestion) return;
    buildCanvas(pendingCanvasSuggestion);
    setPendingCanvasSuggestion(null);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pendingCanvasSuggestion]);

  useEffect(() => {
    fetch('/api/components')
      .then((r) => r.json())
      .then((d) => setComponents(d.components))
      .catch(() => setComponents([
        { type: 'intent_squad',    label: 'Intent Orchestrator', abbClass: 'IntentOrchestrator', color: '#06b6d4', description: 'Kafka consumer on intent.in — classifies unknown events and re-routes to domain topic', singleton: true },
        { type: 'router',          label: 'Router',          abbClass: 'K9EventRouter',        color: '#6366f1', description: 'Routes events to orchestrators', singleton: true },
        { type: 'orchestrator',    label: 'Orchestrator',    abbClass: 'BaseOrchestrator',      color: '#8b5cf6', description: 'Coordinates squad execution' },
        { type: 'squad',           label: 'Squad',           abbClass: 'BaseSquad',             color: '#0ea5e9', description: 'Executes agent flow in sequence' },
        { type: 'agent',           label: 'Agent',           abbClass: 'BaseAgent',             color: '#10b981', description: 'One-shot BaseAgent' },
        { type: 'validation_loop', label: 'Validation Loop', abbClass: 'K9ValidationLoopAgent', color: '#f59e0b', description: 'Iterative reasoning loop' },
        { type: 'critic_actor',    label: 'Critic-Actor',    abbClass: 'K9CriticActorAgent',    color: '#ef4444', description: 'Generate-critique-refine' },
        { type: 'guard',           label: 'Guard',           abbClass: 'BaseGovernance',        color: '#64748b', description: 'Governance / zero-trust' },
      ]));
  }, []);

  const buildCanvas = (suggestion: any) => {
    clearCanvas();
    const cx = 480;
    const routerId = uid2();
    addNode({ id: routerId, type: 'k9node', position: { x: cx - 90, y: 60 },
      data: { label: 'K9EventRouter', componentType: 'router' as ComponentType, color: COMPONENT_COLORS.router, abbClass: 'K9EventRouter', description: 'Routes events by event_type' } });

    const kafkaId = 'system-kafka';
    addNode({ id: kafkaId, type: 'k9node', position: { x: cx + 160, y: 60 },
      data: { label: 'Message Bus', componentType: 'system' as ComponentType, color: '#334155', abbClass: 'Apache Kafka', description: 'Event streaming backbone', system: true } });
    onConnect({ source: routerId, target: kafkaId, sourceHandle: 's-right', targetHandle: 't-left' });

    suggestion.orchestrators?.forEach((o: any, oi: number) => {
      const orchId = uid2();
      const orchX = cx - 90 + oi * 300;
      addNode({ id: orchId, type: 'k9node', position: { x: orchX, y: 220 },
        data: { label: o.name, componentType: 'orchestrator' as ComponentType, color: COMPONENT_COLORS.orchestrator, abbClass: 'BaseOrchestrator', description: `Orchestrator for ${o.name}` } });
      onConnect({ source: routerId, target: orchId, sourceHandle: 's-right', targetHandle: 't-left' });
      onConnect({ source: kafkaId, target: orchId, sourceHandle: 's-right', targetHandle: 't-left' });

      const orchSquads = suggestion.squads?.slice(oi, oi + 1) ?? [];
      orchSquads.forEach((sq: any) => {
        const squadId = uid2();
        addNode({ id: squadId, type: 'k9node', position: { x: orchX - 20, y: 400 },
          data: { label: sq.name, componentType: 'squad' as ComponentType, color: COMPONENT_COLORS.squad, abbClass: 'BaseSquad', description: `Squad: ${sq.name}` } });
        onConnect({ source: orchId, target: squadId, sourceHandle: 's-right', targetHandle: 't-left' });

        const count = (sq.agents ?? []).length;
        const spacing = Math.min(210, 800 / Math.max(count, 1));
        const startX = (orchX - 20) - ((count - 1) * spacing) / 2;
        sq.agents?.forEach((name: string, ai: number) => {
          const def = suggestion.agents?.find((a: any) => a.name === name);
          const atype = def?.type ?? 'BaseAgent';
          const ntype = AGENT_TYPE_MAP[atype] ?? 'agent';
          const agId = uid2();
          addNode({ id: agId, type: 'k9node', position: { x: startX + ai * spacing, y: 580 },
            data: { label: name, componentType: ntype as ComponentType, color: COMPONENT_COLORS[ntype], abbClass: ABB_MAP[atype] ?? 'BaseAgent',
              agentType: atype, model: def?.model ?? 'general', pattern: 'reasoning', description: def?.description ?? '' } });
          onConnect({ source: squadId, target: agId, sourceHandle: 's-right', targetHandle: 't-left' });
        });
      });
    });
    // Auto-layout, then collapse all squads so default view is clean
    setTimeout(() => {
      layoutCanvas();
      setTimeout(() => collapseAllSquads(), 60);
    }, 50);
  };

  return (
    <aside className="palette">

      {/* ── Tab bar ────────────────────────────────── */}
      <div className="palette-tabs" style={{ display: 'flex', alignItems: 'center' }}>
        <button
          className={`palette-tab ${tab === 'project' ? 'active' : ''}`}
          onClick={() => setTab('project')}
        >
          Project Info
        </button>
        <button
          className={`palette-tab ${tab === 'components' ? 'active' : ''}`}
          onClick={() => setTab('components')}
        >
          Components
        </button>
      </div>


      {/* ── Components tab ─────────────────────────── */}
      {tab === 'components' && (
        <>
          {selectedType && (
            <div className="palette-context-hint">
              <span className="hint-arrow">→</span> Next valid: <strong>{VALID_NEXT_LABEL[selectedType]}</strong>
            </div>
          )}
          {!selectedType && <div className="palette-hint">Drag onto canvas</div>}

          <div className="palette-list">
            {(() => {
              const singletonUsed = new Set(
                nodes
                  .filter((n) => {
                    const ct = (n.data as NodeData).componentType;
                    return components.some((c) => c.type === ct && (c as any).singleton);
                  })
                  .map((n) => (n.data as NodeData).componentType as string)
              );
              return components.map((c) => {
              const isSingletonUsed = !!(c as any).singleton && singletonUsed.has(c.type as string);
              if (isSingletonUsed) return null;
              const isValidNext = !isSingletonUsed && (validNextTypes === null || validNextTypes.includes(c.type as ComponentType));
              return (
                <div
                  key={c.type}
                  className={`palette-item ${isValidNext ? '' : 'palette-item-dimmed'} ${validNextTypes && isValidNext ? 'palette-item-highlighted' : ''}`}
                  style={{ borderLeft: `3px solid ${isValidNext ? c.color : '#2a2a35'}` }}
                  draggable={isValidNext}
                  onDragStart={(e) => isValidNext && onDragStart(e, c)}
                  title={isValidNext ? c.description : `Cannot connect here — ${selectedType} only connects to: ${VALID_NEXT_LABEL[selectedType ?? 'router']}`}
                >
                  <span className="palette-icon" style={{ color: isValidNext ? c.color : '#3a3a4a' }}>
                    {ICONS[c.type] ?? '◉'}
                  </span>
                  <div className="palette-item-text">
                    <div className="palette-label" style={{ color: isValidNext ? '' : '#3a3a4a' }}>{c.label}</div>
                    <div className="palette-class">{c.abbClass}</div>
                  </div>
                  {validNextTypes && isValidNext && (
                    <span className="palette-valid-badge" style={{ color: c.color }}>✓</span>
                  )}
                  {validNextTypes && !isValidNext && (
                    <span className="palette-invalid-badge">✗</span>
                  )}
                </div>
              );
            });
            })()}
          </div>

          <div className="palette-section-title">
            K9-AIF Hierarchy
            <span className="palette-hint-icon" tabIndex={-1}>
              ⓘ
              <span className="palette-hint-tooltip">
                Intent Squad is optional — use before Router for non-deterministic routing.<br />
                Squad nodes start collapsed.<br />
                Click <strong>▶ N agents</strong> on a squad to expand its agents.<br />
                Click <strong>▼</strong> to collapse again.
              </span>
            </span>
          </div>
          <div className="palette-hierarchy">
            <div className="hier-line" style={{ color: COMPONENT_COLORS.intent_squad }}>⊕ Intent Orchestrator <span style={{ color: '#4a4a6a', fontSize: 9 }}>optional</span></div>
            <div className="hier-line hier-indent" style={{ color: COMPONENT_COLORS.squad }}>└ ◫ IntentSquad</div>
            <div className="hier-line hier-indent-2" style={{ color: COMPONENT_COLORS.agent }}>└ ◉ K9IntentAgent</div>
            <div className="hier-line" style={{ color: COMPONENT_COLORS.router }}>⇄ Router</div>
            <div className="hier-line hier-indent" style={{ color: COMPONENT_COLORS.orchestrator }}>└ ◈ Orchestrator</div>
            <div className="hier-line hier-indent-2" style={{ color: COMPONENT_COLORS.squad }}>└ ◫ Squad  ▶</div>
            <div className="hier-line hier-indent-3" style={{ color: COMPONENT_COLORS.agent }}>└ ◉ Agent</div>
          </div>
        </>
      )}

      {/* ── Project Info tab ───────────────────────── */}
      {tab === 'project' && (
        <>
          {/* Template picker */}
          <div className="palette-templates" style={{ paddingTop: 12 }}>
            <div className="palette-project-label">Start from template</div>
            <select
              className="palette-template-select"
              defaultValue=""
              onChange={async (e) => {
                const val = e.target.value;
                e.target.value = '';
                const t = val === 'surprise'
                  ? PROJECT_TEMPLATES[Math.floor(Math.random() * PROJECT_TEMPLATES.length)]
                  : PROJECT_TEMPLATES.find((x) => x.id === val);
                if (!t) return;
                setLastTemplate(t);
                setLastTemplateId(t.id);
                if (t.suggestion) setLastTemplateSuggestion(t.suggestion);
                // Reset spec state when picking a template
                setLastSpecFile(null);
                setSpecImported(false);
                const updated = { ...project, project_name: t.name, domain: t.domain, description: t.description,
                  ...(t.vision       ? { vision:       t.vision }       : {}),
                  ...(t.current_state ? { current_state: t.current_state } : {}),
                  ...(t.target_goals  ? { target_goals:  t.target_goals }  : {}),
                };
                setProject(updated);
                setTab('components');
                setGenerating(true);
                try {
                  if (t.suggestion) {
                    buildCanvas(t.suggestion);
                    onSwitchToCanvas?.();
                  } else {
                    const res = await fetch('/api/suggest', {
                      method: 'POST', headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify(updated),
                    });
                    const data = await res.json();
                    if (data.suggestion) { buildCanvas(data.suggestion); onSwitchToCanvas?.(); }
                  }
                } catch { /* keep canvas */ }
                finally { setGenerating(false); }
              }}
            >
              <option value="" disabled>— pick a template —</option>
              <option value="surprise">🎲  Surprise me</option>
              {PROJECT_TEMPLATES.map((t: ProjectTemplate) => (
                <option key={t.id} value={t.id}>{t.icon}  {t.name}</option>
              ))}
            </select>
          </div>

          <div className="palette-platforms">
            <div className="palette-project-label">Platforms &amp; Frameworks</div>
            <div style={{ fontSize: 11, color: '#94a3b8', marginBottom: 4, marginTop: 8 }}>
              Pick current products in use — solution aligns with your stack
            </div>
            {/* IBM watsonx */}
            <button onClick={() => toggleSection('watsonx')} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', background: 'none', border: 'none', cursor: 'pointer', padding: '6px 0', marginTop: 8 }}>
              <span className="platform-group-label" style={{ color: '#4589ff', margin: 0 }}>IBM watsonx</span>
              <span style={{ color: '#475569', fontSize: 10 }}>{expandedSections['watsonx'] ? '▲' : '▼'}</span>
            </button>
            {expandedSections['watsonx'] && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 4, paddingLeft: 4 }}>
                {([
                  { id: 'watsonx-assistant',   label: 'Assistant'   },
                  { id: 'watsonx-orchestrate', label: 'Orchestrate' },
                  { id: 'watsonx-governance',  label: 'Governance'  },
                  { id: 'watsonx-data',        label: 'Data'        },
                ] as const).map((p) => {
                  const active = project.platforms.includes(p.id);
                  return (
                    <label key={p.id} style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 12, color: active ? '#8892a4' : '#64748b' }}>
                      <input type="checkbox" checked={active} onChange={() => setProject({ ...project, platforms: active ? project.platforms.filter((x) => x !== p.id) : [...project.platforms, p.id] })} style={{ accentColor: '#4589ff', cursor: 'pointer' }} />
                      {p.label}
                    </label>
                  );
                })}
              </div>
            )}

            {/* Agent Frameworks */}
            <button onClick={() => toggleSection('frameworks')} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', background: 'none', border: 'none', cursor: 'pointer', padding: '6px 0', marginTop: 8 }}>
              <span className="platform-group-label" style={{ color: '#4a9660', margin: 0 }}>Agent Frameworks</span>
              <span style={{ color: '#475569', fontSize: 10 }}>{expandedSections['frameworks'] ? '▲' : '▼'}</span>
            </button>
            {expandedSections['frameworks'] && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 4, paddingLeft: 4 }}>
                {([
                  { id: 'crewai',    label: 'CrewAI'    },
                  { id: 'langchain', label: 'LangChain' },
                ] as const).map((p) => {
                  const active = project.platforms.includes(p.id);
                  return (
                    <label key={p.id} style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 12, color: active ? '#8892a4' : '#64748b' }}>
                      <input type="checkbox" checked={active} onChange={() => setProject({ ...project, platforms: active ? project.platforms.filter((x) => x !== p.id) : [...project.platforms, p.id] })} style={{ accentColor: '#1cc88a', cursor: 'pointer' }} />
                      {p.label}
                    </label>
                  );
                })}
              </div>
            )}
          {/* Messaging */}
            <button onClick={() => toggleSection('messaging')} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', background: 'none', border: 'none', cursor: 'pointer', padding: '6px 0', marginTop: 8 }}>
              <span className="platform-group-label" style={{ color: '#8b5cf6', margin: 0 }}>Messaging / Event Bus</span>
              <span style={{ color: '#475569', fontSize: 10 }}>{expandedSections['messaging'] ? '▲' : '▼'}</span>
            </button>
            {expandedSections['messaging'] && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 4, paddingLeft: 4 }}>
                {(['Apache Kafka', 'IBM MQ', 'IBM Event Streams', 'AWS SQS', 'Azure Service Bus', 'Redpanda', 'None'] as const).map((item) => {
                  const active = ((project as any).messaging_list ?? []).includes(item);
                  return (
                    <label key={item} style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 12, color: active ? '#8892a4' : '#64748b' }}>
                      <input type="checkbox" checked={active} onChange={() => {
                        const list: string[] = (project as any).messaging_list ?? [];
                        setProject({ ...project, ...{ messaging_list: active ? list.filter((x) => x !== item) : [...list, item] } } as any);
                      }} style={{ accentColor: '#8b5cf6', cursor: 'pointer' }} />
                      {item}
                    </label>
                  );
                })}
              </div>
            )}

          {/* Database */}
            <button onClick={() => toggleSection('database')} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', background: 'none', border: 'none', cursor: 'pointer', padding: '6px 0', marginTop: 8 }}>
              <span className="platform-group-label" style={{ color: '#f59e0b', margin: 0 }}>Database</span>
              <span style={{ color: '#475569', fontSize: 10 }}>{expandedSections['database'] ? '▲' : '▼'}</span>
            </button>
            {expandedSections['database'] && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 4, paddingLeft: 4 }}>
                {(['PostgreSQL', 'SQLite', 'MongoDB', 'IBM Db2', 'Oracle', 'MS SQL Server', 'None'] as const).map((item) => {
                  const active = ((project as any).database_list ?? []).includes(item);
                  return (
                    <label key={item} style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 12, color: active ? '#8892a4' : '#64748b' }}>
                      <input type="checkbox" checked={active} onChange={() => {
                        const list: string[] = (project as any).database_list ?? [];
                        setProject({ ...project, ...{ database_list: active ? list.filter((x) => x !== item) : [...list, item] } } as any);
                      }} style={{ accentColor: '#f59e0b', cursor: 'pointer' }} />
                      {item}
                    </label>
                  );
                })}
              </div>
            )}

          {/* Deployment Target */}
            <button onClick={() => toggleSection('deployment')} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', background: 'none', border: 'none', cursor: 'pointer', padding: '6px 0', marginTop: 8 }}>
              <span className="platform-group-label" style={{ color: '#10b981', margin: 0 }}>Deployment Target</span>
              <span style={{ color: '#475569', fontSize: 10 }}>{expandedSections['deployment'] ? '▲' : '▼'}</span>
            </button>
            {expandedSections['deployment'] && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 4, paddingLeft: 4 }}>
                {(['On-Premises', 'IBM Cloud', 'AWS', 'Microsoft Azure', 'Google Cloud', 'Hybrid', 'Multi-Cloud'] as const).map((item) => {
                  const active = ((project as any).deployment_list ?? []).includes(item);
                  return (
                    <label key={item} style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 12, color: active ? '#8892a4' : '#64748b' }}>
                      <input type="checkbox" checked={active} onChange={() => {
                        const list: string[] = (project as any).deployment_list ?? [];
                        setProject({ ...project, ...{ deployment_list: active ? list.filter((x) => x !== item) : [...list, item] } } as any);
                      }} style={{ accentColor: '#10b981', cursor: 'pointer' }} />
                      {item}
                    </label>
                  );
                })}
              </div>
            )}
          </div>

        </>
      )}

    </aside>
  );
}
