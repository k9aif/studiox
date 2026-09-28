import type { Node, Edge } from '@xyflow/react';
import type { NodeData, CanvasLayer } from './types';
import { LEVEL_X } from './layout';

// Canvas sub-tabs (Orchestrators / Squads / Adapters / HIL): a pure filter
// over the existing nodes/edges, computed fresh each render — not a second
// layout, not a mutation of node.hidden (that field belongs to the existing
// squad-collapse feature; see store.ts's comment on canvasLayer). This is
// the one lesson this whole session kept relearning: one graph, computed
// once, viewed different ways — not re-derived per view.

const ADAPTER_TYPES = new Set([
  'messaging_adapter', 'workflow_adapter', 'process_adapter',
  'api_adapter', 'bpm_adapter', 'rules_adapter', 'data_adapter',
]);
const SQUAD_AGENT_TYPES = new Set([
  'squad', 'intent_squad', 'agent', 'validation_loop', 'critic_actor', 'guard',
]);

function bfsForward(startId: string, edges: Edge[]): Set<string> {
  const visited = new Set<string>();
  const queue = [startId];
  while (queue.length) {
    const cur = queue.shift()!;
    for (const e of edges) {
      if (e.source === cur && !visited.has(e.target)) {
        visited.add(e.target);
        queue.push(e.target);
      }
    }
  }
  return visited;
}

function bfsConnected(startId: string, edges: Edge[]): Set<string> {
  const visited = new Set([startId]);
  let grew = true;
  while (grew) {
    grew = false;
    for (const e of edges) {
      if (visited.has(e.source) && !visited.has(e.target)) { visited.add(e.target); grew = true; }
      if (visited.has(e.target) && !visited.has(e.source)) { visited.add(e.source); grew = true; }
    }
  }
  return visited;
}

/** Which node ids should be visible for the given canvas layer. */
export function computeLayerVisibleIds(layer: CanvasLayer, nodes: Node<NodeData>[], edges: Edge[]): Set<string> {
  if (layer === 'all') return new Set(nodes.map((n) => n.id));

  if (layer === 'hil') {
    const hil = nodes.find((n) => n.data.componentType === 'hil_orchestrator');
    return hil ? bfsConnected(hil.id, edges) : new Set();
  }

  const visible = new Set<string>();
  nodes.filter((n) => n.data.componentType === 'router').forEach((n) => visible.add(n.id));

  if (layer === 'orchestrators') {
    nodes.filter((n) => n.data.componentType === 'orchestrator' || n.data.componentType === 'hil_orchestrator')
      .forEach((n) => visible.add(n.id));
    return visible;
  }

  const allowedLeaf = layer === 'squads' ? SQUAD_AGENT_TYPES : ADAPTER_TYPES;
  for (const n of nodes) {
    if (n.data.componentType !== 'orchestrator') continue;
    const descendants = bfsForward(n.id, edges);
    const matching = [...descendants].filter((id) => {
      const t = nodes.find((m) => m.id === id)?.data.componentType;
      return t ? allowedLeaf.has(t) : false;
    });
    if (matching.length === 0) continue; // hide childless orchestrators for this layer — see plan.md
    visible.add(n.id);
    matching.forEach((id) => visible.add(id));
  }
  return visible;
}

// Column backgrounds — x-bands read directly from layout.ts's LEVEL_X (not
// a separate copy — an earlier draft of this file duplicated the numbers
// here, which is exactly the "two sources that can drift" mistake this
// whole session has been about avoiding; importing LEVEL_X makes that
// impossible instead of just unlikely). Each column spans from the
// midpoint before it to the midpoint after it.
const COLUMN_CENTERS: { label: string; x: number; color: string }[] = [
  { label: 'Router',       x: LEVEL_X.router,             color: '#6366f1' },
  { label: 'Orchestrator', x: LEVEL_X.orchestrator,        color: '#8b5cf6' },
  { label: 'Squad',        x: LEVEL_X.squad,               color: '#0ea5e9' },
  { label: 'Adapter',      x: LEVEL_X.messaging_adapter,   color: '#f59e0b' }, // same amber as ArchGuidePanel's "Adapter" gate
  { label: 'Agent',        x: LEVEL_X.agent,               color: '#10b981' },
];
const NODE_W_ESTIMATE = 220; // K9Node minWidth (160) plus margin, for band width only

export interface ColumnBand { label: string; color: string; left: number; width: number }

export function computeColumnBands(): ColumnBand[] {
  return COLUMN_CENTERS.map((col, i) => {
    const prev = COLUMN_CENTERS[i - 1];
    const next = COLUMN_CENTERS[i + 1];
    const left = prev ? (prev.x + col.x) / 2 + NODE_W_ESTIMATE / 2 : col.x - NODE_W_ESTIMATE;
    const right = next ? (col.x + next.x) / 2 + NODE_W_ESTIMATE / 2 : col.x + NODE_W_ESTIMATE * 1.5;
    return { label: col.label, color: col.color, left, width: right - left };
  });
}
