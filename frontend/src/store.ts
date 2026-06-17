import { create } from 'zustand';
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
import type { AppScreen, ProjectMeta, NodeData } from './types';
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
  specImported: boolean;
  setSpecImported: (v: boolean) => void;
  lastSpecFile: File | null;
  setLastSpecFile: (f: File | null) => void;
  generatedDocs: { name: string; content: string; ts: string }[];
  addGeneratedDoc: (name: string, content: string) => void;
  removeGeneratedDoc: (name: string) => void;
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
  setGenerating: (v: boolean) => void;
  toggleTheme: () => void;
  undo: () => void;
  redo: () => void;
  layoutCanvas: () => void;
  toggleSquadCollapse: (squadId: string) => void;
  collapseAllSquads: () => void;
}

const MAX_HISTORY = 50;

export const useStore = create<StudioStore>((set) => ({
  screen: 'splash',
  project: { project_name: '', app_name: '', author: '', domain: '', description: '', project_folder: '', framework_path: '', platforms: [], messaging_list: [], database_list: [], deployment_list: [] },
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
  specImported: false,
  setSpecImported: (v: boolean) => set({ specImported: v }),
  lastSpecFile: null as File | null,
  setLastSpecFile: (f: File | null) => set({ lastSpecFile: f }),
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

  clearSession: () => set({
    nodes: [], edges: [], selectedNodeId: null,
    history: [], future: [],
    generatedDocs: [], logs: [],
    specImported: false, pendingCanvasSuggestion: null,
    lastTemplateSuggestion: null, lastTemplateId: null,
    project: { project_name: '', app_name: '', author: '', domain: '', description: '', project_folder: '', framework_path: '', platforms: [], messaging_list: [], database_list: [], deployment_list: [] },
  }),

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

  clearCanvas: () =>
    set((s) => ({
      history: [...s.history, { nodes: s.nodes, edges: s.edges }].slice(-MAX_HISTORY),
      future: [],
      nodes: [],
      edges: [],
      selectedNodeId: null,
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
}));
