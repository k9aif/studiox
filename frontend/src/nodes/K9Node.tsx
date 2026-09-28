import type { NodeProps } from '@xyflow/react';
import { Handle, Position } from '@xyflow/react';
import type { NodeData } from '../types';
import { useStore } from '../store';

const ICONS: Record<string, string> = {
  intent_squad: '⊕',
  router: '⇄',
  orchestrator: '◈',
  hil_orchestrator: '◇',
  squad: '◫',
  agent: '◉',
  validation_loop: '↻',
  critic_actor: '⇌',
  guard: '⊛',
};

// Drop the redundant "Agent" that sits between the stem and the role word
// in a node's DISPLAYED label only — e.g. "Agn4AnomalyDetectionAgentSquad"
// -> "Agn4AnomalyDetectionSquad". The role word itself (Squad/Orchestrator)
// stays — Ravi's call after seeing the first pass: keep the type visible in
// the label too, just drop the "Agent" filler word before it. Never touches
// the underlying name anywhere else — scaffold generation, the mapping
// document, YAML, everything keeps the full precise name; this is a
// render-only cosmetic trim.
function displayLabel(label: string): string {
  return label
    .replace(/Agent(Squad|Orchestrator)$/, '$1')
    .replace(/Orchestrator$/, 'Orch'); // Ravi: "Orchestrator can be abbreviated as Orch" — Squad stays full
}

// Process Studio's own GREEN/AMBER/RED zone coding (Carbon strong-accent
// triad — see plan.md's zone-color decision: read Process Studio's Tailwind
// hexes on import, render with Carbon's on our dark canvas).
const ZONE_COLORS: Record<string, string> = { GREEN: '#24a148', AMBER: '#f1c21b', RED: '#da1e28' };
const AGENT_LIKE_TYPES = new Set(['agent', 'validation_loop', 'critic_actor', 'guard']);
const SQUAD_LIKE_TYPES = new Set(['squad', 'intent_squad']);

const handleStyle = (color: string) => ({
  background: color,
  border: '2px solid #0a0a12',
  width: 10,
  height: 10,
  zIndex: 10,
});

export function K9Node({ id, data, selected }: NodeProps) {
  const d = data as NodeData;
  const { edges, nodes, toggleSquadCollapse } = useStore();
  const icon = ICONS[d.componentType] ?? '◉';

  if (d.system) {
    return (
      <div style={{
        background: '#0d0d1a',
        border: '1.5px dashed #334155',
        borderRadius: 8,
        minWidth: 140,
        opacity: 0.82,
        pointerEvents: 'none',
      }}>
        <Handle type="target" position={Position.Top}    id="t-top"    style={{ opacity: 0, pointerEvents: 'none' }} />
        <Handle type="target" position={Position.Left}   id="t-left"   style={{ opacity: 0, pointerEvents: 'none' }} />
        <Handle type="target" position={Position.Right}  id="t-right"  style={{ opacity: 0, pointerEvents: 'none' }} />
        <Handle type="target" position={Position.Bottom} id="t-bottom" style={{ opacity: 0, pointerEvents: 'none' }} />
        <Handle type="source" position={Position.Bottom} id="s-bottom" style={{ opacity: 0, pointerEvents: 'none' }} />
        <Handle type="source" position={Position.Right}  id="s-right"  style={{ opacity: 0, pointerEvents: 'none' }} />
        <Handle type="source" position={Position.Left}   id="s-left"   style={{ opacity: 0, pointerEvents: 'none' }} />
        <Handle type="source" position={Position.Top}    id="s-top"    style={{ opacity: 0, pointerEvents: 'none' }} />
        <div style={{ padding: '8px 12px' }}>
          <div style={{ fontSize: 9, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', color: '#475569', marginBottom: 3 }}>
            ⊙ system
          </div>
          <div style={{ fontSize: 12, fontWeight: 500, color: '#64748b', lineHeight: 1.3 }}>
            {d.label}
          </div>
          <div style={{ fontSize: 10, color: '#334155', marginTop: 2, fontFamily: 'monospace' }}>
            {d.abbClass}
          </div>
        </div>
      </div>
    );
  }

  // Zone tint: agent nodes get a badge (precise, per-element); squad nodes
  // get a colored top edge (a squad = one BPMN lane, so this reads as the
  // lane's own zone, echoing Process Studio's per-lane coloring). Additive
  // to the existing role-based coloring (d.color) — never replaces it.
  const zoneColor = d.zone ? ZONE_COLORS[d.zone] : undefined;
  const isAgentLike = AGENT_LIKE_TYPES.has(d.componentType);
  const isSquadLike = SQUAD_LIKE_TYPES.has(d.componentType);

  return (
    <div
      style={{
        background: '#1e1e2e',
        border: `2px solid ${selected ? '#a78bfa' : d.color}`,
        borderRadius: 10,
        minWidth: 160,
        boxShadow: selected
          ? `0 0 0 3px #a78bfa33, 0 6px 24px ${d.color}55`
          : `0 2px 12px ${d.color}22`,
        transition: 'all 0.15s ease',
        ...(isSquadLike && zoneColor ? { borderTop: `4px solid ${zoneColor}` } : {}),
      }}
    >
      <Handle type="target" position={Position.Top}    id="t-top"    style={handleStyle(d.color)} />
      <Handle type="target" position={Position.Left}   id="t-left"   style={handleStyle(d.color)} />
      <Handle type="target" position={Position.Right}  id="t-right"  style={handleStyle(d.color)} />
      <Handle type="target" position={Position.Bottom} id="t-bottom" style={handleStyle(d.color)} />
      <Handle type="source" position={Position.Bottom} id="s-bottom" style={handleStyle(d.color)} />
      <Handle type="source" position={Position.Right}  id="s-right"  style={handleStyle(d.color)} />
      <Handle type="source" position={Position.Left}   id="s-left"   style={handleStyle(d.color)} />
      <Handle type="source" position={Position.Top}    id="s-top"    style={handleStyle(d.color)} />

      <div style={{ padding: '10px 14px' }}>
        <div style={{
          fontSize: 9, fontWeight: 700, letterSpacing: '0.08em',
          textTransform: 'uppercase', color: d.color, marginBottom: 4,
          display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 6,
        }}>
          <span>{icon} {d.componentType.replace('_', ' ')}</span>
          {isAgentLike && zoneColor && (
            <span
              title={`Autonomy zone: ${d.zone}`}
              style={{
                display: 'inline-flex', alignItems: 'center', gap: 3,
                color: zoneColor, border: `1px solid ${zoneColor}88`, borderRadius: 3,
                padding: '1px 5px', fontSize: 8, letterSpacing: '0.04em',
              }}
            >
              ● {d.zone}
            </span>
          )}
        </div>
        <div style={{
          fontSize: 13, fontWeight: 600, color: '#e2e2f0',
          lineHeight: 1.3, wordBreak: 'break-word',
        }}>
          {displayLabel(d.label)}
        </div>
        <div style={{
          fontSize: 10, color: '#6b6b8a', marginTop: 3, fontFamily: 'monospace',
        }}>
          {d.abbClass}
        </div>

        {(d.componentType === 'squad' || d.componentType === 'intent_squad') && (() => {
          const AGENT_TYPES = new Set(['agent', 'validation_loop', 'critic_actor', 'guard']);
          const agentCount = edges.filter((e) => {
            if (e.source !== id) return false;
            const tgt = nodes.find((n) => n.id === e.target);
            return tgt ? AGENT_TYPES.has((tgt.data as NodeData).componentType) : false;
          }).length;
          if (agentCount === 0) return null;
          const collapsed = !!d.collapsed;
          return (
            <button
              style={{
                marginTop: 8,
                display: 'flex',
                alignItems: 'center',
                gap: 4,
                background: collapsed ? `${d.color}22` : 'transparent',
                border: `1px solid ${d.color}55`,
                borderRadius: 4,
                color: d.color,
                fontSize: 10,
                fontWeight: 600,
                padding: '3px 7px',
                cursor: 'pointer',
                width: '100%',
                justifyContent: 'center',
                letterSpacing: '0.04em',
              }}
              onClick={(e) => {
                e.stopPropagation();
                toggleSquadCollapse(id);
              }}
              title={collapsed ? 'Expand agents' : 'Collapse agents'}
            >
              {collapsed ? '▶' : '▼'} {agentCount} agent{agentCount !== 1 ? 's' : ''}
            </button>
          );
        })()}
      </div>
    </div>
  );
}
