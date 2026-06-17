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
        }}>
          {icon} {d.componentType.replace('_', ' ')}
        </div>
        <div style={{
          fontSize: 13, fontWeight: 600, color: '#e2e2f0',
          lineHeight: 1.3, wordBreak: 'break-word',
        }}>
          {d.label}
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
