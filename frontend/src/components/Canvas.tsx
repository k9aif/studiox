import { useCallback, useRef, useState } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  BackgroundVariant,
  useReactFlow,
} from '@xyflow/react';
import type { NodeMouseHandler, Connection, Edge } from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { useStore } from '../store';
import { K9Node } from '../nodes/K9Node';
import type { PaletteComponent, NodeData } from '../types';
import { VALID_TARGETS, RULE_HINT } from '../rules';

const NODE_TYPES = { k9node: K9Node };

let nodeCounter = 1;

interface CanvasProps {
  draggedComponent: PaletteComponent | null;
  generating: boolean;
}

interface ContextMenu {
  x: number;
  y: number;
  nodeId: string;
  nodeLabel: string;
}

export function Canvas({ generating }: CanvasProps) {
  const { nodes, edges, onNodesChange, onEdgesChange, onConnect, addNode, setSelectedNode } = useStore();
  const [rejected, setRejected] = useState<string | null>(null);
  const [contextMenu, setContextMenu] = useState<ContextMenu | null>(null);

  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const { screenToFlowPosition } = useReactFlow();

  // ── Connection validation ──────────────────────────────────
  const isValidConnection = useCallback(
    (connection: Edge | Connection): boolean => {
      const src = nodes.find((n) => n.id === connection.source);
      const tgt = nodes.find((n) => n.id === connection.target);
      if (!src || !tgt) return false;
      const srcType = (src.data as NodeData).componentType;
      const tgtType = (tgt.data as NodeData).componentType;
      return VALID_TARGETS[srcType]?.includes(tgtType) ?? false;
    },
    [nodes]
  );

  const onConnectStart = useCallback(() => setRejected(null), []);

  const onConnectEnd = useCallback(
    (_e: MouseEvent | TouchEvent, params: any) => {
      if (!params?.isValid && params?.fromNode) {
        const src = nodes.find((n) => n.id === params.fromNode.id);
        const srcType = (src?.data as NodeData | undefined)?.componentType;
        if (srcType) {
          setRejected(RULE_HINT[srcType]);
          setTimeout(() => setRejected(null), 3500);
        }
      }
    },
    [nodes]
  );

  // ── Drag-and-drop from palette ─────────────────────────────
  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const compJson = e.dataTransfer.getData('application/k9node');
      if (!compJson) return;
      const comp: PaletteComponent = JSON.parse(compJson);

      // Enforce singleton: only one router or intent_squad per architecture
      if ((comp as any).singleton) {
        const alreadyExists = nodes.some((n) => (n.data as NodeData).componentType === comp.type);
        if (alreadyExists) {
          setRejected(`Only one ${comp.label} allowed per architecture`);
          setTimeout(() => setRejected(null), 3500);
          return;
        }
      }

      const position = screenToFlowPosition({ x: e.clientX, y: e.clientY });
      const id = `${comp.type}-${nodeCounter++}`;
      addNode({
        id, type: 'k9node', position,
        data: {
          label: comp.label,
          componentType: comp.type,
          color: comp.color,
          abbClass: comp.abbClass,
          agentType: comp.type === 'validation_loop' ? 'K9ValidationLoopAgent'
            : comp.type === 'critic_actor' ? 'K9CriticActorAgent' : 'BaseAgent',
          model: 'general',
          pattern: 'reasoning',
          description: comp.description,
          temperature: '0.3',
          maxTokens: '2048',
          llmProvider: 'ollama',
        } as NodeData,
      } as any);

      if (comp.type === 'router') {
        const kafkaId = 'system-kafka';
        const kafkaExists = nodes.some((n) => n.id === kafkaId);
        if (!kafkaExists) {
          addNode({
            id: kafkaId, type: 'k9node',
            position: { x: position.x + 230, y: position.y },
            data: {
              label: 'Message Bus', componentType: 'system' as any,
              color: '#334155', abbClass: 'Apache Kafka',
              description: 'Event streaming backbone', system: true,
            } as NodeData,
          } as any);
        }
        onConnect({ source: id, target: kafkaId, sourceHandle: 's-right', targetHandle: 't-left' });
        // Auto-connect from IntentSquad if one exists
        const intentSquad = nodes.find((n) => (n.data as NodeData).componentType === 'intent_squad');
        if (intentSquad) {
          onConnect({ source: intentSquad.id, target: id, sourceHandle: 's-right', targetHandle: 't-left' });
        }
        // Auto-wire to any Orchestrators already on the canvas
        const orchestrators = nodes.filter((n) => (n.data as NodeData).componentType === 'orchestrator');
        for (const orch of orchestrators) {
          onConnect({ source: id, target: orch.id, sourceHandle: 's-right', targetHandle: 't-left' });
          onConnect({ source: kafkaId, target: orch.id, sourceHandle: 's-right', targetHandle: 't-left' });
        }
      }

      if (comp.type === 'intent_squad') {
        // Auto-create IntentSquad → K9IntentAgent
        const squadId = `squad-${nodeCounter++}`;
        addNode({
          id: squadId, type: 'k9node',
          position: { x: position.x, y: position.y + 160 },
          data: {
            label: 'IntentSquad', componentType: 'squad' as any,
            color: '#0ea5e9', abbClass: 'IntentSquad',
            description: 'Squad used by IntentOrchestrator to classify intent',
            model: 'general', pattern: 'reasoning',
            temperature: '0.3', maxTokens: '2048', llmProvider: 'ollama',
          } as NodeData,
        } as any);
        onConnect({ source: id, target: squadId, sourceHandle: 's-bottom', targetHandle: 't-top' });

        const agentId = `agent-${nodeCounter++}`;
        addNode({
          id: agentId, type: 'k9node',
          position: { x: position.x, y: position.y + 340 },
          data: {
            label: 'K9IntentAgent', componentType: 'agent' as any,
            color: '#10b981', abbClass: 'K9IntentAgent',
            agentType: 'BaseAgent', model: 'general', pattern: 'reasoning',
            description: 'LLM-driven intent classification — checks intent_map first, falls back to LLM',
            temperature: '0.3', maxTokens: '2048', llmProvider: 'ollama',
          } as NodeData,
        } as any);
        onConnect({ source: squadId, target: agentId, sourceHandle: 's-bottom', targetHandle: 't-top' });

        // Auto-wire from Router → Intent Orchestrator (via intent.in)
        const router = nodes.find((n) => (n.data as NodeData).componentType === 'router');
        if (router) {
          onConnect({ source: router.id, target: id, sourceHandle: 's-right', targetHandle: 't-left' });
        }
      }

      // ── Ensure the K9-AIF hierarchy is complete: Router → Orchestrator → Squad ──
      const ANCESTOR_GAP = 260;
      const ANCESTOR_DEFS: Record<'router' | 'orchestrator' | 'squad', { label: string; abbClass: string; color: string; description: string }> = {
        router:       { label: 'K9EventRouter', abbClass: 'K9EventRouter',    color: '#6366f1', description: 'Routes events by event_type' },
        orchestrator: { label: 'Orchestrator',   abbClass: 'BaseOrchestrator', color: '#8b5cf6', description: 'Coordinates squad execution' },
        squad:        { label: 'Squad',          abbClass: 'BaseSquad',        color: '#0ea5e9', description: 'Executes agent flow in sequence' },
      };
      const REQUIRED_PARENT: Record<'router' | 'orchestrator' | 'squad', 'router' | 'orchestrator' | undefined> = {
        router: undefined,
        orchestrator: 'router',
        squad: 'orchestrator',
      };

      const nearestNode = (candidates: typeof nodes, pos: { x: number; y: number }) =>
        candidates.reduce((best, n) => {
          const dist = (m: typeof n) => Math.hypot(m.position.x - pos.x, m.position.y - pos.y);
          return dist(n) < dist(best) ? n : best;
        });

      // Find the nearest existing node of `type`, or create it — recursively
      // creating its own required ancestor first — so a Squad never exists
      // without an Orchestrator, and an Orchestrator never exists without a Router.
      const ensureAncestor = (type: 'router' | 'orchestrator' | 'squad', near: { x: number; y: number }): string => {
        const existing = nodes.filter(
          (n) => (n.data as NodeData).componentType === type && !(n.data as NodeData).system
        );
        if (existing.length > 0) return nearestNode(existing, near).id;

        const newId = `${type}-${nodeCounter++}`;
        const pos = { x: near.x - ANCESTOR_GAP, y: near.y };
        addNode({
          id: newId, type: 'k9node', position: pos,
          data: { ...ANCESTOR_DEFS[type], componentType: type as any } as NodeData,
        } as any);

        if (type === 'router') {
          const kafkaId = 'system-kafka';
          if (!nodes.some((n) => n.id === kafkaId)) {
            addNode({
              id: kafkaId, type: 'k9node',
              position: { x: pos.x + 230, y: pos.y - 160 },
              data: {
                label: 'Message Bus', componentType: 'system' as any,
                color: '#334155', abbClass: 'Apache Kafka',
                description: 'Event streaming backbone', system: true,
              } as NodeData,
            } as any);
          }
          onConnect({ source: newId, target: kafkaId, sourceHandle: 's-right', targetHandle: 't-left' });
        }

        const parentType = REQUIRED_PARENT[type];
        if (parentType) {
          const parentId = ensureAncestor(parentType, pos);
          onConnect({ source: parentId, target: newId, sourceHandle: 's-right', targetHandle: 't-left' });
          if (type === 'orchestrator') {
            // Router (just ensured above) always comes with a Kafka node.
            onConnect({ source: 'system-kafka', target: newId, sourceHandle: 's-right', targetHandle: 't-left' });
          }
        }

        return newId;
      };

      // Auto-connect to nearest valid parent node — creating the Router →
      // Orchestrator → Squad ancestor chain if it doesn't exist yet, so a
      // dropped component never ends up orphaned on the canvas.
      const PARENT_TYPE: Partial<Record<string, string[]>> = {
        orchestrator:    ['router'],
        squad:           ['orchestrator'],
        agent:           ['squad', 'intent_squad'],
        validation_loop: ['squad', 'intent_squad'],
        critic_actor:    ['squad', 'intent_squad'],
        guard:           ['squad'],
      };
      const parentTypes = PARENT_TYPE[comp.type];
      if (parentTypes) {
        const candidates = nodes.filter(
          (n) => parentTypes.includes((n.data as NodeData).componentType) && !(n.data as NodeData).system
        );
        const parentId = candidates.length > 0
          ? nearestNode(candidates, position).id
          : ensureAncestor(parentTypes[0] as 'router' | 'orchestrator' | 'squad', position);

        onConnect({ source: parentId, target: id, sourceHandle: 's-right', targetHandle: 't-left' });
        if (comp.type === 'orchestrator') {
          // Either a pre-existing Router or ensureAncestor('router', ...) above
          // guarantees a Kafka node exists alongside it.
          onConnect({ source: 'system-kafka', target: id, sourceHandle: 's-right', targetHandle: 't-left' });
        }
      }

      setSelectedNode(id);
    },
    [screenToFlowPosition, addNode, onConnect, setSelectedNode, nodes]
  );

  const handleConnect = useCallback(
    (conn: any) => {
      onConnect(conn);
      const src = nodes.find((n) => n.id === conn.source);
      const tgt = nodes.find((n) => n.id === conn.target);
      if (
        (src?.data as NodeData)?.componentType === 'router' &&
        (tgt?.data as NodeData)?.componentType === 'orchestrator'
      ) {
        const kafka = nodes.find((n) => n.id === 'system-kafka');
        if (kafka) {
          onConnect({ source: 'system-kafka', target: conn.target, sourceHandle: 's-right', targetHandle: 't-left' });
        }
      }
    },
    [nodes, onConnect]
  );

  const onNodeClick: NodeMouseHandler = useCallback(
    (_e, node) => {
      if ((node.data as NodeData).system) return;
      setSelectedNode(node.id); setContextMenu(null);
    },
    [setSelectedNode]
  );

  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
    setContextMenu(null);
  }, [setSelectedNode]);

  // ── Right-click context menu ───────────────────────────────
  const onNodeContextMenu: NodeMouseHandler = useCallback(
    (e, node) => {
      e.preventDefault();
      if ((node.data as NodeData).system) return;
      setContextMenu({
        x: e.clientX,
        y: e.clientY,
        nodeId: node.id,
        nodeLabel: (node.data as NodeData).label,
      });
    },
    []
  );

  const handleDeleteNode = useCallback(() => {
    if (!contextMenu) return;
    onNodesChange([{ type: 'remove', id: contextMenu.nodeId }]);
    setContextMenu(null);
  }, [contextMenu, onNodesChange]);

  return (
    <div
      className="canvas-wrapper"
      ref={reactFlowWrapper}
      onDragOver={onDragOver}
      onDrop={onDrop}
      onClick={() => contextMenu && setContextMenu(null)}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={NODE_TYPES}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={handleConnect}
        onConnectStart={onConnectStart}
        onConnectEnd={onConnectEnd as any}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        onNodeContextMenu={onNodeContextMenu}
        isValidConnection={isValidConnection}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        defaultEdgeOptions={{
          animated: false,
          style: { stroke: '#6366f1', strokeWidth: 2 },
          markerEnd: { type: 'arrowclosed' as any, color: '#6366f1' },
        }}
        proOptions={{ hideAttribution: true }}
      >
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#2a2a3a" />
        <Controls style={{ background: '#1e1e2e', border: '1px solid #2a2a35', color: '#a0a0c0' }} />
      </ReactFlow>

      {/* Bottom-right watermark */}
      <div className="canvas-watermark">
        <span className="watermark-k9">K9-AIF</span>
        <span className="watermark-tag">Architecture-First Framework</span>
        <span className="watermark-url">k9x.ai</span>
      </div>

      {/* Rejected connection toast */}
      {rejected && (
        <div className="connection-toast">
          <span className="toast-icon">⊛</span>
          <span><strong>K9X Inspector:</strong> {rejected}</span>
        </div>
      )}

      {/* Empty state */}
      {nodes.length === 0 && !generating && (
        <div className="canvas-empty">
          <div className="canvas-empty-icon">⬡</div>
          <div className="canvas-empty-title">Design your K9-AIF system</div>
          <div className="canvas-empty-sub">Enter a description and click Generate — or drag components from the palette</div>
          <div className="canvas-empty-hint">
            Router → Orchestrator → Squad → Agent
          </div>
        </div>
      )}

      {/* Right-click context menu */}
      {contextMenu && (
        <div
          className="context-menu"
          style={{ left: contextMenu.x, top: contextMenu.y }}
        >
          <div className="context-menu-label">{contextMenu.nodeLabel}</div>
          <div className="context-menu-divider" />
          <button className="context-menu-item context-menu-danger" onClick={handleDeleteNode}>
            ✕ Delete Node
          </button>
        </div>
      )}
    </div>
  );
}
