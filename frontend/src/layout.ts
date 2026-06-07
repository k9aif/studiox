import type { Node, Edge } from '@xyflow/react';
import type { NodeData } from './types';

// Left-to-right hierarchical layout.
// Squads are leaf nodes for layout purposes — agents start collapsed.
// Agent positions are computed separately so they render correctly on expand.

const NODE_H  = 80;
const V_GAP   = 50;

// Fixed X columns per tier — wider spacing to accommodate long node names
const LEVEL_X: Record<string, number> = {
  intent_squad:    -80,
  router:          150,
  orchestrator:    480,
  squad:           820,
  agent:           1160,
  validation_loop: 1160,
  critic_actor:    1160,
  guard:           1160,
  system:          150,
};

const AGENT_TYPES = new Set(['agent', 'validation_loop', 'critic_actor', 'guard']);

export function applyHierarchyLayout(
  nodes: Node<NodeData>[],
  edges: Edge[]
): Node<NodeData>[] {
  if (nodes.length === 0) return nodes;

  // Build children map — skip system edges and agent-level targets (squads are leaves)
  const children: Record<string, string[]> = {};
  const hasParent = new Set<string>();

  nodes.forEach((n) => { children[n.id] = []; });

  edges.forEach((e) => {
    const src = nodes.find((n) => n.id === e.source);
    const tgt = nodes.find((n) => n.id === e.target);
    if (!src || !tgt) return;
    if ((src.data as NodeData).system || (tgt.data as NodeData).system) return;
    if (AGENT_TYPES.has((tgt.data as NodeData).componentType)) return;
    children[e.source] = children[e.source] ?? [];
    if (!children[e.source].includes(e.target)) {
      children[e.source].push(e.target);
    }
    hasParent.add(e.target);
  });

  // Roots = non-system, non-agent nodes without a parent
  const roots = nodes
    .filter((n) => {
      const d = n.data as NodeData;
      return !hasParent.has(n.id) && !d.system && !AGENT_TYPES.has(d.componentType);
    })
    .map((n) => n.id);

  // Vertical space a subtree occupies
  const heightCache: Record<string, number> = {};
  function subtreeHeight(id: string): number {
    if (heightCache[id] !== undefined) return heightCache[id];
    const kids = children[id] ?? [];
    if (kids.length === 0) {
      heightCache[id] = NODE_H;
      return NODE_H;
    }
    const total = kids.reduce((sum, k) => sum + subtreeHeight(k), 0)
      + (kids.length - 1) * V_GAP;
    heightCache[id] = Math.max(NODE_H, total);
    return heightCache[id];
  }

  const pos: Record<string, { x: number; y: number }> = {};

  function assign(id: string, topEdge: number) {
    const h    = subtreeHeight(id);
    const cy   = topEdge + h / 2;
    const node = nodes.find((n) => n.id === id)!;
    const x    = LEVEL_X[(node.data as NodeData).componentType] ?? 980;
    pos[id] = { x, y: cy - NODE_H / 2 };

    const kids = children[id] ?? [];
    let cursor = topEdge;
    kids.forEach((kid) => {
      assign(kid, cursor);
      cursor += subtreeHeight(kid) + V_GAP;
    });
  }

  let cursor = 60;  // top margin
  roots.forEach((rootId) => {
    assign(rootId, cursor);
    cursor += subtreeHeight(rootId) + V_GAP * 3;
  });

  // Position agent nodes fanned vertically to the right of their squad or intent_squad
  const squadAgentMap: Record<string, string[]> = {};
  edges.forEach((e) => {
    const src = nodes.find((n) => n.id === e.source);
    const tgt = nodes.find((n) => n.id === e.target);
    if (!src || !tgt) return;
    const srcType = (src.data as NodeData).componentType;
    if (srcType !== 'squad' && srcType !== 'intent_squad') return;
    if (!AGENT_TYPES.has((tgt.data as NodeData).componentType)) return;
    squadAgentMap[e.source] = squadAgentMap[e.source] ?? [];
    if (!squadAgentMap[e.source].includes(e.target)) {
      squadAgentMap[e.source].push(e.target);
    }
  });

  Object.entries(squadAgentMap).forEach(([squadId, agentIds]) => {
    if (!pos[squadId]) return;
    const squadCY = pos[squadId].y + NODE_H / 2;
    const totalH  = agentIds.length * NODE_H + (agentIds.length - 1) * V_GAP;
    const startY  = squadCY - totalH / 2;
    agentIds.forEach((agId, i) => {
      pos[agId] = {
        x: LEVEL_X.agent,
        y: startY + i * (NODE_H + V_GAP),
      };
    });
  });

  // Kafka: same column as router, below it
  const routerNode = nodes.find((n) => (n.data as NodeData).componentType === 'router');
  const kafkaNode  = nodes.find((n) => (n.data as NodeData).system);
  if (routerNode && kafkaNode && pos[routerNode.id]) {
    pos[kafkaNode.id] = {
      x: LEVEL_X.router,
      y: pos[routerNode.id].y + NODE_H + 60,
    };
  }

  return nodes.map((n) =>
    pos[n.id] ? { ...n, position: pos[n.id] } : n
  );
}
