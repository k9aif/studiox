import type { ComponentType } from './types';

const ADAPTER_TYPES: ComponentType[] = [
  'messaging_adapter', 'workflow_adapter', 'process_adapter', 'api_adapter',
  'bpm_adapter', 'rules_adapter', 'data_adapter',
];

// K9-AIF hierarchy: the ONLY valid source→target connections
export const VALID_TARGETS: Record<ComponentType, ComponentType[]> = {
  intent_squad:      ['agent', 'validation_loop', 'critic_actor', 'router'],
  // Router can go agentic (→ Orchestrator) OR straight to a deterministic adapter
  router:            ['orchestrator', ...ADAPTER_TYPES],
  // Orchestrator can mix agentic squads with deterministic adapter steps
  orchestrator:      ['squad', ...ADAPTER_TYPES],
  hil_orchestrator:  ['squad', ...ADAPTER_TYPES],
  squad:             ['agent', 'validation_loop', 'critic_actor', 'guard'],
  agent:             [],
  validation_loop:   [],
  critic_actor:      [],
  guard:             [],
  system:            [],
  // Messaging Adapter is NOT a leaf — an event on Kafka/SQS can trigger a workflow or integration flow
  messaging_adapter: ['workflow_adapter', 'process_adapter'],
  // All other adapters are leaf nodes
  workflow_adapter:  [],
  process_adapter:   [],
  api_adapter:       [],
  bpm_adapter:       [],
  rules_adapter:     [],
  data_adapter:      [],
};

export const RULE_HINT: Record<ComponentType, string> = {
  intent_squad:      'IntentSquad → IntentAgent, then → Router',
  router:            'Router → Orchestrator (agentic) or directly to an Adapter (deterministic)',
  orchestrator:      'Orchestrator → Squads (agentic) and/or Adapters (deterministic)',
  hil_orchestrator:  'HIL Orchestrator → 1 or more Squads (event-driven, no Router)',
  squad:             'Squad → Agent / ValidationLoop / CriticActor / Guard',
  agent:             'Agents have no outgoing connections',
  validation_loop:   'ValidationLoop has no outgoing connections',
  critic_actor:      'CriticActor has no outgoing connections',
  guard:             'Guard has no outgoing connections',
  system:            'System infrastructure nodes are read-only',
  messaging_adapter: 'Event bus (Kafka, RabbitMQ, SQS/SNS) — can trigger Workflow or Process Flow adapters',
  workflow_adapter:  'Delegates to a workflow engine — deterministic, no LLM',
  process_adapter:   'Delegates to an integration platform — deterministic, no LLM',
  api_adapter:       'Calls an external REST/GraphQL API — deterministic, no LLM',
  bpm_adapter:       'Delegates to a BPM engine — deterministic, no LLM',
  rules_adapter:     'Invokes a business rules engine — deterministic, no LLM',
  data_adapter:      'Reads/writes a database or data warehouse directly',
};

// What a given source type is ALLOWED to connect to (human-readable)
export const VALID_NEXT_LABEL: Record<ComponentType, string> = {
  intent_squad:      'IntentAgent, Router',
  router:            'Orchestrator or any Adapter',
  orchestrator:      '1+ Squads and/or Adapters',
  hil_orchestrator:  '1+ Squads',
  squad:             'Agent, Validation Loop, Critic-Actor, Guard',
  agent:             '—',
  validation_loop:   '—',
  critic_actor:      '—',
  guard:             '—',
  system:            '—',
  messaging_adapter: 'Workflow Adapter, Process Flow Adapter',
  workflow_adapter:  '—',
  process_adapter:   '—',
  api_adapter:       '—',
  bpm_adapter:       '—',
  rules_adapter:     '—',
  data_adapter:      '—',
};
