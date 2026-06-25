import { useStore } from '../store';
import type { AgentClassType } from '../types';
import { toPascal } from '../classDiagram';

const PATTERN_OPTIONS = ['reasoning', 'extraction', 'chat', 'guardrails'];
const AGENT_TYPE_OPTIONS: AgentClassType[] = ['BaseAgent', 'K9ValidationLoopAgent', 'K9CriticActorAgent'];
const ROUTING_STRATEGIES = ['event_type', 'intent'];
const RETRY_POLICIES = ['none', 'fixed_delay', 'exponential_backoff'];


export function Inspector() {
  const { nodes, selectedNodeId, updateNodeData } = useStore();
  const node = nodes.find((n) => n.id === selectedNodeId);

  const footer = (
    <div className="inspector-footer">
      <div className="inspector-footer-title">Continue in your IDE</div>
      <div className="inspector-footer-body">
        Once the scaffold is generated, take the project to
        <span className="inspector-footer-tool"> VS Code + Claude Code</span> to implement agent logic.
      </div>
      <div className="inspector-footer-links">
        <a href="https://k9x.ai" target="_blank" rel="noopener noreferrer">k9x.ai</a>
        <span className="inspector-footer-dot">·</span>
        <a href="https://k9x.ai/examples" target="_blank" rel="noopener noreferrer">Examples</a>
        <span className="inspector-footer-dot">·</span>
        <a href="https://k9x.ai/blog" target="_blank" rel="noopener noreferrer">Blog</a>
      </div>
    </div>
  );

  if (!node) {
    return null;
  }

  if (false) {
    return (
      <aside className="inspector empty">
        <div className="inspector-header">
          <span className="inspector-icon">⊛</span> K9X Inspector
        <span className="inspector-cop-lights">
          <span className="cop-light cop-red" />
          <span className="cop-light cop-amber" />
          <span className="cop-light cop-green" />
        </span>
</div>
        <div className="inspector-empty-msg">
          <div className="inspector-empty-icon">◎</div>
          <p>Select a node to configure it</p>
        </div>
        {footer}
        <div style={{ padding: '8px 12px', margin: '4px 0', background: 'rgba(99,102,241,0.06)', border: '1px solid #2a2d3e', borderRadius: 6, fontSize: 11, color: '#6366f1' }}>
          ⬡ LLM config → <strong>Setup tab</strong>
        </div>
      </aside>
    );
  }

  const { data } = node;
  const isAgent = ['agent', 'validation_loop', 'critic_actor'].includes(data.componentType);
  const isRouter = data.componentType === 'router';
  const isOrchestrator = data.componentType === 'orchestrator';
  const isHilOrchestrator = data.componentType === 'hil_orchestrator';
  const isIntentSquad = data.componentType === 'intent_squad';

  const set = (key: string, val: string) => updateNodeData(node.id, { [key]: val });

  return (
    <aside className="inspector">
      <div className="inspector-body">
        {/* Component type badge */}
        <div
          className="inspector-type-badge"
          style={{ background: data.color + '22', color: data.color, borderColor: data.color + '44' }}
        >
          {data.componentType.replace(/_/g, ' ')} · {data.abbClass}
        </div>

        {/* Name */}
        <div className="inspector-field">
          <label className="inspector-label">Name</label>
          <input
            className="inspector-input"
            value={data.label}
            onChange={(e) => set('label', e.target.value)}
            onBlur={(e) => {
              const pascal = toPascal(e.target.value);
              if (pascal && pascal !== e.target.value) set('label', pascal);
            }}
            title="Used as the generated Python class name and PlantUML identifier — normalized to PascalCase (no spaces/punctuation) when you click away."
          />
        </div>

        {/* Agent-specific fields */}
        {isAgent && (
          <>
            <div className="inspector-field">
              <label className="inspector-label">Agent Type</label>
              <select
                className="inspector-input"
                value={data.agentType ?? 'BaseAgent'}
                onChange={(e) => set('agentType', e.target.value)}
              >
                {AGENT_TYPE_OPTIONS.map((o) => (
                  <option key={o} value={o}>{o}</option>
                ))}
              </select>
            </div>

            <div className="inspector-field">
              <label className="inspector-label">Pattern</label>
              <select
                className="inspector-input"
                value={data.pattern ?? 'reasoning'}
                onChange={(e) => set('pattern', e.target.value)}
              >
                {PATTERN_OPTIONS.map((o) => (
                  <option key={o} value={o}>{o}</option>
                ))}
              </select>
            </div>

            <div style={{ fontSize: 10, color: '#4a4a6a', padding: '4px 0 8px 0', lineHeight: 1.5 }}>
              LLM provider, model, temperature, and token limits are resolved at runtime
              by the ModelRouter via config.yaml — not set per agent.
            </div>
          </>
        )}

        {/* Intent Squad fields */}
        {isIntentSquad && (
          <>
            <div className="inspector-section-label">Intent Classification</div>
            <div className="inspector-field">
              <label className="inspector-label">Routing Strategy</label>
              <select
                className="inspector-input"
                value={data.routingStrategy ?? 'intent'}
                onChange={(e) => set('routingStrategy', e.target.value)}
              >
                <option value="intent">intent (non-deterministic)</option>
                <option value="confidence">confidence threshold</option>
              </select>
            </div>
            <div style={{ fontSize: 10, color: '#4a4a6a', padding: '4px 0 8px 0', lineHeight: 1.5 }}>
              IntentSquad classifies incoming events before the Router. The IntentAgent
              enriches the context with a classified intent that the Router uses to route deterministically.
            </div>
          </>
        )}

        {/* Router-specific fields */}
        {isRouter && (
          <>
            <div className="inspector-section-label">Router Configuration</div>
            <div className="inspector-field">
              <label className="inspector-label">Routing Strategy</label>
              <select
                className="inspector-input"
                value={data.routingStrategy ?? 'event_type'}
                onChange={(e) => set('routingStrategy', e.target.value)}
              >
                {ROUTING_STRATEGIES.map((o) => (
                  <option key={o} value={o}>{o.replace(/_/g, ' ')}</option>
                ))}
              </select>
            </div>
          </>
        )}

        {/* Orchestrator-specific fields */}
        {isOrchestrator && (
          <>
            <div className="inspector-section-label">Orchestrator Configuration</div>
            <div className="inspector-field">
              <label className="inspector-label">Retry Policy</label>
              <select
                className="inspector-input"
                value={data.retryPolicy ?? 'none'}
                onChange={(e) => set('retryPolicy', e.target.value)}
              >
                {RETRY_POLICIES.map((o) => (
                  <option key={o} value={o}>{o.replace(/_/g, ' ')}</option>
                ))}
              </select>
            </div>
            <div className="inspector-field">
              <label className="inspector-label" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <input
                  type="checkbox"
                  checked={data.parallelSquads ?? false}
                  onChange={(e) => updateNodeData(node.id, { parallelSquads: e.target.checked })}
                  style={{ accentColor: '#3b82f6' }}
                />
                Parallel Squad Execution
              </label>
              <div style={{ fontSize: 10, color: '#4a4a6a', lineHeight: 1.5, marginTop: 4 }}>
                When enabled, connected squads run concurrently via execute_squads(parallel=True).
                Use for independent or cross-cutting squads. Disable for squads that feed into each other.
              </div>
            </div>
          </>
        )}

        {/* HIL Orchestrator-specific fields */}
        {isHilOrchestrator && (
          <>
            <div className="inspector-section-label">HIL Configuration</div>
            <div style={{ fontSize: 10, color: '#14b8a6', lineHeight: 1.5, background: '#14b8a611', borderRadius: 4, padding: '8px' }}>
              ◇ Event-driven orchestrator — subscribes to Kafka HIL topics.
              No Router needed. Triggered when a human completes a task
              in the HIL case management platform.
            </div>

            <div className="inspector-field">
              <label className="inspector-label">Subscribe Topics</label>
              <input
                className="inspector-input"
                value={(data as any).hilTopics ?? 'workflow.hil.*'}
                onChange={(e) => set('hilTopics', e.target.value)}
                placeholder="workflow.hil.eoc.claims.*"
                title="Kafka topic pattern this HIL Orchestrator subscribes to"
              />
            </div>

            <div className="inspector-field">
              <label className="inspector-label">Reply Topic</label>
              <input
                className="inspector-input"
                value={(data as any).hilReplyTopic ?? ''}
                onChange={(e) => set('hilReplyTopic', e.target.value)}
                placeholder="workflow.hil.response"
                title="Topic where human decisions are published back"
              />
            </div>

            <div className="inspector-field">
              <label className="inspector-label">Retry Policy</label>
              <select
                className="inspector-input"
                value={data.retryPolicy ?? 'none'}
                onChange={(e) => set('retryPolicy', e.target.value)}
              >
                {RETRY_POLICIES.map((o) => (
                  <option key={o} value={o}>{o.replace(/_/g, ' ')}</option>
                ))}
              </select>
            </div>
          </>
        )}

        {/* Description */}
        <div className="inspector-field">
          <label className="inspector-label">Description</label>
          <textarea
            className="inspector-input inspector-textarea"
            rows={3}
            value={data.description ?? ''}
            onChange={(e) => set('description', e.target.value)}
          />
        </div>

        {/* ABB reference */}
        <div className="inspector-abb">
          <div className="inspector-label">ABB Contract</div>
          <code className="inspector-abb-code">{data.abbClass}</code>
        </div>
      </div>
      {footer}
    </aside>
  );
}
