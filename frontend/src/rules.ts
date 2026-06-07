import type { ComponentType } from './types';

// K9-AIF hierarchy: the ONLY valid source→target connections
export const VALID_TARGETS: Record<ComponentType, ComponentType[]> = {
  intent_squad:    ['agent', 'validation_loop', 'critic_actor', 'router'],
  router:          ['orchestrator'],
  orchestrator:    ['squad'],
  squad:           ['agent', 'validation_loop', 'critic_actor', 'guard'],
  agent:           [],
  validation_loop: [],
  critic_actor:    [],
  guard:           [],
  system:          [],
};

export const RULE_HINT: Record<ComponentType, string> = {
  intent_squad:    'IntentSquad → IntentAgent, then → Router',
  router:          'Router → Orchestrator only',
  orchestrator:    'Orchestrator → Squad only',
  squad:           'Squad → Agent / ValidationLoop / CriticActor / Guard',
  agent:           'Agents have no outgoing connections',
  validation_loop: 'ValidationLoop has no outgoing connections',
  critic_actor:    'CriticActor has no outgoing connections',
  guard:           'Guard has no outgoing connections',
  system:          'System infrastructure nodes are read-only',
};

// What a given source type is ALLOWED to connect to (human-readable)
export const VALID_NEXT_LABEL: Record<ComponentType, string> = {
  intent_squad:    'IntentAgent, Router',
  router:          'Orchestrator',
  orchestrator:    'Squad',
  squad:           'Agent, Validation Loop, Critic-Actor, Guard',
  agent:           '—',
  validation_loop: '—',
  critic_actor:    '—',
  guard:           '—',
  system:          '—',
};
