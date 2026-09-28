import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import {
  addEdge,
  applyNodeChanges,
  applyEdgeChanges,
} from '@xyflow/react';
import type {
  Node,
  Edge,
  NodeChange,
  EdgeChange,
  Connection,
} from '@xyflow/react';
import type { AppScreen, ProjectMeta, NodeData, CanvasLayer } from './types';
import { applyHierarchyLayout } from './layout';

interface Snapshot {
  nodes: Node<NodeData>[];
  edges: Edge[];
}

export interface LlmSessionConfig {
  provider: string;
  endpoint: string;
  model: string;
  api_key: string;
  // Guardian is a mandatory safety screen on every Intake upload, but uses
  // its own model on the same endpoint (a Granite Guardian model) — separate
  // from `model`, which narrates docs / suggests canvases.
  guardianModel?: string;
}

export interface LogEntry {
  id: number;
  ts: string;
  msg: string;
  level: 'info' | 'warn' | 'error';
}

interface StudioStore {
  screen: AppScreen;
  project: ProjectMeta;
  nodes: Node<NodeData>[];
  edges: Edge[];
  selectedNodeId: string | null;
  generating: boolean;
  genResult: { winner: string; winnerScore: number; winnerAgents: number; winnerSquads: number } | null;
  setGenResult: (r: any) => void;
  genSource: string;
  setGenSource: (s: string) => void;
  scaffoldFiles: { path: string; content: string; binary?: boolean }[];
  setScaffoldFiles: (f: { path: string; content: string }[]) => void;
  genScoring: any;
  setGenScoring: (s: any) => void;
  theme: 'dark' | 'light';
  history: Snapshot[];
  future: Snapshot[];
  llmConfig: LlmSessionConfig | null;
  setLlmConfig: (cfg: LlmSessionConfig | null) => void;
  availableModels: string[];
  setAvailableModels: (m: string[]) => void;
  llmActive: boolean;
  setLlmActive: (v: boolean) => void;
  logs: LogEntry[];
  addLog: (msg: string, level?: 'info' | 'warn' | 'error') => void;
  lastTemplateSuggestion: any;
  setLastTemplateSuggestion: (s: any) => void;
  lastTemplateId: string | null;
  setLastTemplateId: (id: string | null) => void;
  reapplyTemplate: boolean;
  triggerReapply: () => void;
  pendingCanvasSuggestion: any;
  setPendingCanvasSuggestion: (s: any) => void;
  // Mapping-document-first gate (plan.md step 5): a deterministic import
  // (spec/BPMN) lands here first, not directly in pendingCanvasSuggestion —
  // the human reviews/edits the matrix and explicitly confirms before the
  // canvas (and later, scaffold) gets built from it.
  pendingMappingDocument: { suggestion: any; mapping_document: any } | null;
  setPendingMappingDocument: (d: { suggestion: any; mapping_document: any } | null) => void;
  // Whether the current mapping document has been confirmed (canvas built
  // from it). NOT cleared alongside pendingMappingDocument on confirm — the
  // matrix stays visible in the Traceability tab as a record of what's on
  // canvas, it doesn't disappear once used. A fresh import resets this.
  mappingDocumentConfirmed: boolean;
  setMappingDocumentConfirmed: (v: boolean) => void;
  specImported: boolean;
  setSpecImported: (v: boolean) => void;
  lastSpecFile: File | null;
  setLastSpecFile: (f: File | null) => void;
  // Set only by a BPMN import, mutually exclusive with lastSpecFile — lets
  // Regenerate (Studio.tsx) tell "this canvas came from a rule-based BPMN
  // parse" apart from "this canvas came from an LLM-processed spec doc".
  // Ravi: Regenerate after a BPMN import was silently falling through to
  // the generic /api/suggest LLM path (lastSpecFile was never set for a
  // BPMN import) and producing unrelated, generic output — the mapping-
  // document-first architecture says BPMN input must stay rule-based, so
  // Regenerate simply doesn't offer itself for a BPMN-derived canvas.
  // NOT itself persisted (a File object can't survive JSON storage) — see
  // canvasIsRuleBased below for the flag that actually survives a refresh.
  lastBpmnFile: File | null;
  setLastBpmnFile: (f: File | null) => void;
  // Persisted twin of "lastBpmnFile is set" — a plain boolean, unlike the
  // File object, so it survives a page refresh. Ravi found the gap: after
  // refreshing a BPMN-derived canvas, Regenerate reappeared because
  // lastBpmnFile (excluded from persistence) reset to null while the
  // canvas/mapping-document data itself correctly persisted. Set together
  // with lastBpmnFile everywhere that sets it; Studio.tsx's Regenerate gate
  // reads this instead of the File object.
  canvasIsRuleBased: boolean;
  setCanvasIsRuleBased: (v: boolean) => void;
  // Staged intake inputs — decouples "upload a file" from "generate" (Ravi:
  // uploading BPMN or a blueprint spec used to fire generation immediately,
  // making the two mutually exclusive in practice since the first upload
  // built the canvas before the second file could be added). A file is
  // staged, not acted on, until the user clicks Generate on the Intake
  // tab. Staging a second BPMN/blueprint replaces the first — never two of
  // the same role at once. Not persisted (mirrors lastBpmnFile/
  // lastSpecFile — these hold full /api/*/import responses, not just File
  // objects, so re-fetching after a refresh isn't meaningful either; a
  // refresh mid-staging just starts staging over).
  stagedBpmn: { fileName: string; result: any } | null;
  setStagedBpmn: (v: { fileName: string; result: any } | null) => void;
  stagedBlueprint: { fileName: string; result: any } | null;
  setStagedBlueprint: (v: { fileName: string; result: any } | null) => void;
  // Process Studio's companion eval plan (-evals.md) — staged alongside
  // BPMN/blueprint but not itself an architecture input; never drives
  // canvas generation. `result` is /api/evals/import's response (rows/
  // counts/total), consumed at scaffold-generation time by
  // scaffold_service.py's _gen_eval_test_files(). Same not-persisted
  // rationale as stagedBpmn/stagedBlueprint above.
  stagedEvals: { fileName: string; result: any } | null;
  setStagedEvals: (v: { fileName: string; result: any } | null) => void;
  generatedDocs: { name: string; content: string; ts: string }[];
  addGeneratedDoc: (name: string, content: string) => void;
  removeGeneratedDoc: (name: string) => void;
  // Ravi: "after a Scaffold is generated, if I view it, and go back to
  // Canvas, I should not be able to Generate Scaffold again... The button
  // should be Regenerate" then, softened: "Regenerate is ok (if someone
  // deleted it from the Generated Docs folder and wanted to regenerate it
  // or want to play around to check the behaviour" — not a hard block,
  // just clear signaling that this is a repeat action, not a first-time
  // one. Reset whenever the canvas is actually cleared/rebuilt (below),
  // not on every node edit — regenerating after a tweak is exactly the
  // "click again" case this is meant to allow, not block.
  hasGeneratedScaffold: boolean;
  setHasGeneratedScaffold: (v: boolean) => void;
  clearSession: () => void;

  setScreen: (s: AppScreen) => void;
  setProject: (p: ProjectMeta) => void;
  addNode: (node: Node<NodeData>) => void;
  updateNodeData: (id: string, data: Partial<NodeData>) => void;
  onNodesChange: (changes: NodeChange[]) => void;
  onEdgesChange: (changes: EdgeChange[]) => void;
  onConnect: (conn: Connection) => void;
  setSelectedNode: (id: string | null) => void;
  clearCanvas: () => void;
  // Full reset for a brand-new project — everything clearCanvas() resets,
  // PLUS project fields and the intake/import flags. Ravi: "clear means
  // clear all, reset" — the header's own Clear button used to call
  // clearCanvas() alone, leaving project_name behind; since BPMN import
  // only sets project_name when it was empty, a stale name then silently
  // blocked the next uploaded BPMN's name from ever applying. Both the
  // header Clear button and IntakePanel's own "✕ Clear" call this one
  // action now, so they can't drift into two different "Clear" behaviors
  // again.
  clearProject: () => void;
  // Same node/edge reset as clearCanvas, but leaves pendingMappingDocument/
  // mappingDocumentConfirmed alone — for Palette.tsx's buildCanvas() to call
  // at the start of a rebuild. clearCanvas() itself resets those two too
  // (correct for the user-facing Clear button), but buildCanvas() calling
  // clearCanvas() as its own "start fresh" step was silently wiping the
  // Traceability matrix data on every canvas build, including the one
  // triggered by confirming that same matrix — MappingDocumentPanel's
  // handleConfirm() explicitly does NOT clear it ("the matrix stays visible
  // ... it doesn't disappear once used"), but three calls downstream,
  // buildCanvas -> clearCanvas undid that. Ravi: "if I click on
  // traceability, nothing there, it seems to have disappeared."
  resetCanvasNodesForRebuild: () => void;
  setGenerating: (v: boolean) => void;
  toggleTheme: () => void;
  undo: () => void;
  redo: () => void;
  layoutCanvas: () => void;
  toggleSquadCollapse: (squadId: string) => void;
  collapseAllSquads: () => void;
  // Canvas sub-tabs (Orchestrators/Squads/Adapters/HIL): a pure view filter,
  // computed at render time in Canvas.tsx from `nodes`/`edges` — this is
  // just which one is selected. Deliberately NOT mutating node/edge `hidden`
  // here the way toggleSquadCollapse does; two independent writers of the
  // same boolean field would clobber each other on every layer switch.
  canvasLayer: CanvasLayer;
  setCanvasLayer: (l: CanvasLayer) => void;
  // Which top-level Studio tab is active. Lives here (not local useState in
  // Studio.tsx) specifically so it's covered by the same persistence as
  // everything else — otherwise a refresh restores the canvas data but
  // still dumps the user back on "About", which reads as "still broken"
  // even though the actual data survived. Typed loosely (matches the
  // existing `as any` casts at call sites) to avoid Studio.tsx's local
  // CenterTab type creating an import cycle.
  centerTab: string;
  setCenterTab: (t: string) => void;
  // Landing page's onboarding wizard (images 1-3: numbered stepper modal) —
  // Ravi: "with an option at the left bottom (do not display this next
  // time checkbox), typical behaviour." Persisted so the choice survives a
  // refresh/revisit; the wizard itself is still reachable afterward via the
  // landing page's own "How K9X Studio works" link, it just stops
  // auto-opening.
  hideOnboarding: boolean;
  setHideOnboarding: (v: boolean) => void;
  // Ravi: with the login screen auto-authenticating everyone as the same
  // "demo" identity (IBM's own SSO handles real identity upstream — see
  // LandingPage.tsx), this is what actually distinguishes concurrent
  // reviewers. Generated once per browser and persisted (see below) rather
  // than regenerated per tab/reload, so it stays stable for one person
  // across a session. NOT a server-side session key — the backend is
  // stateless (every request carries its full project payload; nothing is
  // stored between requests to collide on), so this is for traceability
  // in generated docs only, not concurrency control.
  clientId: string;
}

const MAX_HISTORY = 50;

// Separate, non-persist-middleware localStorage key (not the zustand
// `k9x-studiox-session` blob below) — deliberately independent of the
// rest of the app's state so it survives clearSession()/clearProject()
// resets untouched; it identifies the browser, not the project.
// crypto.randomUUID() only exists in "secure contexts" (HTTPS, or
// http://localhost) — a studio reached over plain HTTP on a
// LAN IP is NOT a secure context.
// Calling it there throws "crypto.randomUUID is not a function", and
// since this runs at store-creation time (module load), that exception
// crashed the entire app before anything could render — a blank black
// page, matching Ravi's report exactly. This fallback never touches
// crypto.randomUUID, so it works identically on HTTP/LAN and HTTPS.
function makeClientId(): string {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

function getOrCreateClientId(): string {
  const KEY = 'k9x_client_id';
  try {
    const existing = localStorage.getItem(KEY);
    if (existing) return existing;
    const id = makeClientId();
    localStorage.setItem(KEY, id);
    return id;
  } catch {
    return makeClientId();
  }
}

// Shared by the initial state, clearSession, and clearProject — was
// duplicated three ways before, which is exactly how the header Clear
// button and clearSession's own reset drifted apart in the first place.
const EMPTY_PROJECT: ProjectMeta = {
  project_name: '', app_name: '', author: '', domain: '', description: '',
  project_folder: '', framework_path: '', platforms: [],
  messaging_list: [], database_list: [], deployment_list: [],
};

export const useStore = create<StudioStore>()(
  persist(
    (set) => ({
  screen: 'landing',
  project: EMPTY_PROJECT,
  nodes: [],
  edges: [],
  selectedNodeId: null,
  generating: false,
  genResult: null,
  setGenResult: (genResult) => set({ genResult }),
  genSource: '',
  setGenSource: (genSource) => set({ genSource }),
  scaffoldFiles: [],
  setScaffoldFiles: (scaffoldFiles) => set({ scaffoldFiles }),
  genScoring: null,
  setGenScoring: (genScoring) => set({ genScoring }),
  theme: 'dark',
  history: [],
  future: [],
  // Ravi: "we want LLM only for guardian. period." — reversing an earlier
  // decision to show a pre-wired qwen3.8:27b as if already connected
  // (green checkmark and all) even on a fresh visitor's browser where
  // nothing was ever actually tested/reachable. No default narration LLM
  // now — the header shows "No LLM" honestly until someone deliberately
  // configures + tests one in Setup. Guardian is unaffected either way:
  // it resolves entirely server-side via GOVERNANCE_LLM_ENDPOINT/MODEL
  // (see routes.py's _guardian_config), never depending on this.
  llmConfig: null,
  setLlmConfig: (cfg) => set({ llmConfig: cfg }),
  availableModels: [],
  setAvailableModels: (availableModels) => set({ availableModels }),
  llmActive: false,
  setLlmActive: (v) => set({ llmActive: v }),
  logs: [],
  addLog: (msg, level = 'info') =>
    set((s) => ({
      logs: [
        ...s.logs.slice(-49),
        { id: Date.now(), ts: new Date().toLocaleTimeString(), msg, level },
      ],
    })),

  lastTemplateSuggestion: null as any,
  setLastTemplateSuggestion: (s: any) => set({ lastTemplateSuggestion: s }),
  lastTemplateId: null as string | null,
  setLastTemplateId: (id: string | null) => set({ lastTemplateId: id }),
  reapplyTemplate: false,
  triggerReapply: () => set((s) => ({ reapplyTemplate: !s.reapplyTemplate })),
  pendingCanvasSuggestion: null as any,
  setPendingCanvasSuggestion: (s: any) => set({ pendingCanvasSuggestion: s }),
  pendingMappingDocument: null,
  setPendingMappingDocument: (d) => set({ pendingMappingDocument: d }),
  mappingDocumentConfirmed: false,
  setMappingDocumentConfirmed: (v) => set({ mappingDocumentConfirmed: v }),
  specImported: false,
  setSpecImported: (v: boolean) => set({ specImported: v }),
  lastSpecFile: null as File | null,
  setLastSpecFile: (f: File | null) => set({ lastSpecFile: f }),
  lastBpmnFile: null as File | null,
  setLastBpmnFile: (f: File | null) => set({ lastBpmnFile: f }),
  canvasIsRuleBased: false,
  setCanvasIsRuleBased: (v: boolean) => set({ canvasIsRuleBased: v }),
  stagedBpmn: null,
  setStagedBpmn: (v) => set({ stagedBpmn: v }),
  stagedBlueprint: null,
  setStagedBlueprint: (v) => set({ stagedBlueprint: v }),
  stagedEvals: null,
  setStagedEvals: (v) => set({ stagedEvals: v }),
  generatedDocs: [],
  removeGeneratedDoc: (name) =>
    set((s) => ({ generatedDocs: s.generatedDocs.filter((d) => d.name !== name) })),
  addGeneratedDoc: (name, content) =>
    set((s) => ({
      generatedDocs: [
        { name, content, ts: new Date().toLocaleTimeString() },
        ...s.generatedDocs.filter((d) => d.name !== name),
      ],
    })),
  hasGeneratedScaffold: false,
  setHasGeneratedScaffold: (v) => set({ hasGeneratedScaffold: v }),

  clearSession: () => set({
    nodes: [], edges: [], selectedNodeId: null,
    history: [], future: [],
    generatedDocs: [], logs: [],
    specImported: false, pendingCanvasSuggestion: null,
    lastTemplateSuggestion: null, lastTemplateId: null,
    lastSpecFile: null, lastBpmnFile: null, canvasIsRuleBased: false,
    stagedBpmn: null, stagedBlueprint: null, stagedEvals: null,
    pendingMappingDocument: null, mappingDocumentConfirmed: false, canvasLayer: 'all',
    project: EMPTY_PROJECT, hasGeneratedScaffold: false,
  }),

  // See the interface's clearProject comment — same full reset as
  // clearSession's project-clearing fields, minus logs (Clear starts a new
  // project, it doesn't wipe your activity history the way signing out
  // does). Ravi: "the top right, Clear button does not remove the
  // generated docs list, scaffold display. it all remains... View
  // Scaffold still shows old generated code." — generatedDocs/scaffoldFiles
  // used to be left alone on the theory they're session-level "downloads,"
  // but showing a previous project's scaffold/docs after starting a fresh
  // one reads as stale/broken, not a feature — reset them too now.
  clearProject: () =>
    set((s) => ({
      history: [...s.history, { nodes: s.nodes, edges: s.edges }].slice(-MAX_HISTORY),
      future: [],
      nodes: [], edges: [], selectedNodeId: null,
      pendingMappingDocument: null, mappingDocumentConfirmed: false,
      pendingCanvasSuggestion: null, canvasLayer: 'all',
      stagedBpmn: null, stagedBlueprint: null, stagedEvals: null,
      specImported: false, lastTemplateId: null, lastTemplateSuggestion: null,
      lastSpecFile: null, lastBpmnFile: null, canvasIsRuleBased: false,
      project: EMPTY_PROJECT,
      generatedDocs: [], scaffoldFiles: [], hasGeneratedScaffold: false,
    })),

  setScreen: (screen) => set({ screen }),
  setProject: (project) => set({ project }),

  addNode: (node) =>
    set((s) => ({
      history: [...s.history, { nodes: s.nodes, edges: s.edges }].slice(-MAX_HISTORY),
      future: [],
      nodes: [...s.nodes, node],
    })),

  updateNodeData: (id, data) =>
    set((s) => ({
      history: [...s.history, { nodes: s.nodes, edges: s.edges }].slice(-MAX_HISTORY),
      future: [],
      nodes: s.nodes.map((n) =>
        n.id === id ? { ...n, data: { ...n.data, ...data } } : n
      ),
    })),

  onNodesChange: (changes) =>
    set((s) => {
      const removedIds = new Set(
        changes.filter((c) => c.type === 'remove').map((c) => (c as any).id)
      );
      const shouldSnapshot = removedIds.size > 0;
      return {
        history: shouldSnapshot
          ? [...s.history, { nodes: s.nodes, edges: s.edges }].slice(-MAX_HISTORY)
          : s.history,
        future: shouldSnapshot ? [] : s.future,
        nodes: applyNodeChanges(changes, s.nodes as Node[]) as Node<NodeData>[],
        edges: removedIds.size > 0
          ? s.edges.filter((e) => !removedIds.has(e.source) && !removedIds.has(e.target))
          : s.edges,
      };
    }),

  onEdgesChange: (changes) =>
    set((s) => {
      const hasRemove = changes.some((c) => c.type === 'remove');
      return {
        history: hasRemove
          ? [...s.history, { nodes: s.nodes, edges: s.edges }].slice(-MAX_HISTORY)
          : s.history,
        future: hasRemove ? [] : s.future,
        edges: applyEdgeChanges(changes, s.edges),
      };
    }),

  onConnect: (conn) =>
    set((s) => {
      const duplicate = s.edges.some(
        (e) => e.source === conn.source && e.target === conn.target
      );
      if (duplicate) return s;
      const isSystem = conn.source === 'system-kafka' || conn.target === 'system-kafka';
      const isHil = isSystem && s.nodes.some(
        (n) => (n.id === conn.source || n.id === conn.target) &&
               (n.data as NodeData).componentType === 'hil_orchestrator'
      );
      const edgeColor = isHil ? '#14b8a6' : isSystem ? '#475569' : '#6366f1';
      const edgeStyle = isSystem || isHil
        ? { stroke: edgeColor, strokeWidth: 1.5, strokeDasharray: '6 4' }
        : { stroke: edgeColor, strokeWidth: 2 };
      return {
        history: [...s.history, { nodes: s.nodes, edges: s.edges }].slice(-MAX_HISTORY),
        future: [],
        edges: addEdge(
          {
            ...conn,
            animated: false,
            style: edgeStyle,
            markerEnd: { type: 'arrowclosed' as any, color: edgeColor },
          },
          s.edges
        ),
      };
    }),

  setSelectedNode: (id) => set({ selectedNodeId: id }),

  // Ravi: "when I click on clear, nothing happens ... what if I as a user
  // want to clear and upload document again?" — Clear only ever reset
  // nodes/edges. The Traceability tab's mapping-document state (added
  // later, for the persistence fix) was never wired into it, so the matrix
  // stayed stale after clicking Clear — same gap existed in clearSession
  // (logout), fixed there too, below.
  clearCanvas: () =>
    set((s) => ({
      history: [...s.history, { nodes: s.nodes, edges: s.edges }].slice(-MAX_HISTORY),
      future: [],
      nodes: [],
      edges: [],
      selectedNodeId: null,
      pendingMappingDocument: null,
      mappingDocumentConfirmed: false,
      pendingCanvasSuggestion: null,
      canvasLayer: 'all',
      stagedBpmn: null,
      stagedBlueprint: null,
      stagedEvals: null,
      hasGeneratedScaffold: false,
    })),

  resetCanvasNodesForRebuild: () =>
    set((s) => ({
      history: [...s.history, { nodes: s.nodes, edges: s.edges }].slice(-MAX_HISTORY),
      future: [],
      nodes: [],
      edges: [],
      selectedNodeId: null,
      canvasLayer: 'all',
      hasGeneratedScaffold: false,
    })),

  setGenerating: (v) => set({ generating: v }),

  toggleTheme: () =>
    set((s) => {
      const next = s.theme === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      return { theme: next };
    }),

  undo: () =>
    set((s) => {
      if (s.history.length === 0) return s;
      const prev = s.history[s.history.length - 1];
      return {
        history: s.history.slice(0, -1),
        future: [...s.future, { nodes: s.nodes, edges: s.edges }].slice(-MAX_HISTORY),
        nodes: prev.nodes,
        edges: prev.edges,
        selectedNodeId: null,
      };
    }),

  redo: () =>
    set((s) => {
      if (s.future.length === 0) return s;
      const next = s.future[s.future.length - 1];
      return {
        future: s.future.slice(0, -1),
        history: [...s.history, { nodes: s.nodes, edges: s.edges }].slice(-MAX_HISTORY),
        nodes: next.nodes,
        edges: next.edges,
        selectedNodeId: null,
      };
    }),

  layoutCanvas: () =>
    set((s) => ({
      history: [...s.history, { nodes: s.nodes, edges: s.edges }].slice(-MAX_HISTORY),
      future: [],
      nodes: applyHierarchyLayout(s.nodes as Node<NodeData>[], s.edges),
    })),

  toggleSquadCollapse: (squadId: string) =>
    set((s) => {
      const squad = s.nodes.find((n) => n.id === squadId);
      if (!squad) return s;
      const nowCollapsed = !(squad.data as NodeData).collapsed;
      const AGENT_TYPES = new Set(['agent', 'validation_loop', 'critic_actor', 'guard']);
      const agentIds = new Set(
        s.edges
          .filter((e) => e.source === squadId)
          .map((e) => e.target)
          .filter((tid) => {
            const t = s.nodes.find((n) => n.id === tid);
            return t ? AGENT_TYPES.has((t.data as NodeData).componentType) : false;
          })
      );
      const newNodes = s.nodes.map((n) => {
        if (n.id === squadId) return { ...n, data: { ...n.data, collapsed: nowCollapsed } };
        if (agentIds.has(n.id)) return { ...n, hidden: nowCollapsed };
        return n;
      });
      const newEdges = s.edges.map((e) => {
        if (e.source === squadId && agentIds.has(e.target)) return { ...e, hidden: nowCollapsed };
        return e;
      });
      return { nodes: newNodes, edges: newEdges };
    }),

  collapseAllSquads: () =>
    set((s) => {
      const squadIds = s.nodes
        .filter((n) => ['squad', 'intent_squad'].includes((n.data as NodeData).componentType))
        .map((n) => n.id);
      if (squadIds.length === 0) return s;
      const AGENT_TYPES = new Set(['agent', 'validation_loop', 'critic_actor', 'guard']);
      let nodes = s.nodes;
      let edges = s.edges;
      squadIds.forEach((squadId) => {
        const agentIds = new Set(
          edges
            .filter((e) => e.source === squadId)
            .map((e) => e.target)
            .filter((tid) => {
              const t = nodes.find((n) => n.id === tid);
              return t ? AGENT_TYPES.has((t.data as NodeData).componentType) : false;
            })
        );
        nodes = nodes.map((n) => {
          if (n.id === squadId) return { ...n, data: { ...n.data, collapsed: true } };
          if (agentIds.has(n.id)) return { ...n, hidden: true };
          return n;
        });
        edges = edges.map((e) => {
          if (e.source === squadId && agentIds.has(e.target)) return { ...e, hidden: true };
          return e;
        });
      });
      return { nodes, edges };
    }),

  canvasLayer: 'all',
  setCanvasLayer: (l) => set({ canvasLayer: l }),
  centerTab: 'about',
  setCenterTab: (t) => set({ centerTab: t }),
  hideOnboarding: false,
  setHideOnboarding: (v) => set({ hideOnboarding: v }),
  clientId: getOrCreateClientId(),
    }),
    {
      name: 'k9x-studiox-session',
      storage: createJSONStorage(() => localStorage),
      // Persist canvas/project/import state so a refresh doesn't lose work
      // (reported bug: "if I refresh the page, everything disappears").
      // Excluded deliberately:
      //   - lastSpecFile: a browser File object, not JSON-serializable
      //   - logs, generating, llmActive: transient UI state, not worth
      //     resurrecting stale on reload
      //   - history/future (undo/redo stacks): restoring a mid-edit undo
      //     history across a full page reload is more confusing than useful
      partialize: (state) => ({
        screen: state.screen,
        project: state.project,
        nodes: state.nodes,
        edges: state.edges,
        theme: state.theme,
        llmConfig: state.llmConfig,
        pendingCanvasSuggestion: state.pendingCanvasSuggestion,
        pendingMappingDocument: state.pendingMappingDocument,
        mappingDocumentConfirmed: state.mappingDocumentConfirmed,
        specImported: state.specImported,
        lastTemplateSuggestion: state.lastTemplateSuggestion,
        lastTemplateId: state.lastTemplateId,
        generatedDocs: state.generatedDocs,
        scaffoldFiles: state.scaffoldFiles,
        genResult: state.genResult,
        genSource: state.genSource,
        genScoring: state.genScoring,
        canvasLayer: state.canvasLayer,
        centerTab: state.centerTab,
        canvasIsRuleBased: state.canvasIsRuleBased,
        hideOnboarding: state.hideOnboarding,
      }),
    }
  )
);
