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

      // Auto-connect to nearest valid parent node
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
        if (candidates.length > 0) {
          const nearest = candidates.reduce((best, n) => {
            const dx = n.position.x - position.x;
            const dy = n.position.y - position.y;
            const dist = Math.sqrt(dx * dx + dy * dy);
            const bdx = best.position.x - position.x;
            const bdy = best.position.y - position.y;
            return dist < Math.sqrt(bdx * bdx + bdy * bdy) ? n : best;
          });
          onConnect({ source: nearest.id, target: id, sourceHandle: 's-right', targetHandle: 't-left' });
          if (comp.type === 'orchestrator') {
            const kafka = nodes.find((n) => n.id === 'system-kafka');
            if (kafka) onConnect({ source: 'system-kafka', target: id, sourceHandle: 's-right', targetHandle: 't-left' });
          }
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
