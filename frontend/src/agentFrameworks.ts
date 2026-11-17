// The agent framework a project's squads run on (one per project). Shared by Intake, the Palette, the YAML preview
// and the canvas, so they always describe the same choice. The scaffold generator (backend/services/scaffold_service.py,
// AGENT_FRAMEWORKS) generates the matching runtime module per squad, wrapped by K9-AIF's own adapter.
//
// One per project because some agent frameworks can't share an environment: openai-agents needs openai>=3 and
// crewai (through instructor) needs openai<3.

import type { ProjectMeta } from './types';

export type AgentFramework = 'native' | 'openai_agents' | 'crewai' | 'langgraph' | 'claude_agent_sdk';

export interface AgentFrameworkInfo {
  id: AgentFramework;
  label: string;
  adapter: string;      // the K9-AIF facade the generated runtime returns ('' for native)
  squadAs: string;      // what a squad becomes on this framework
  agentAs: string;      // what an agent becomes on this framework ('' for native)
  note: string;         // one line for Intake
  color: string;
}

export const AGENT_FRAMEWORKS: AgentFrameworkInfo[] = [
  { id: 'native', label: 'K9-AIF native', adapter: '', squadAs: 'Squad', agentAs: '',
    note: 'Squads of K9-AIF agents (BaseAgent). No other agent framework needed.', color: '#0ea5e9' },
  { id: 'openai_agents', label: 'OpenAI Agents SDK', adapter: 'K9OpenAIAgent', squadAs: 'Squad of OpenAI agents', agentAs: 'OpenAI agent',
    note: 'Each agent is an OpenAI agent, and the squad runs them in flow order with synthesis: the squad decides, '
        + 'not the model. Handoffs (the model picks the agent) only when the design spec sets Agent Routing: handoffs. '
        + 'Needs k9-aif 1.28.0 or later.',
    color: '#34d399' },
  { id: 'crewai', label: 'CrewAI', adapter: 'K9CrewAIAdapter', squadAs: 'Crew', agentAs: 'CrewAI agent',
    note: 'Each squad runs as a sequential Crew; every agent uses the governed K9 model bridge.', color: '#f59e0b' },
  { id: 'langgraph', label: 'LangGraph', adapter: 'K9LangGraphAdapter', squadAs: 'Graph', agentAs: 'Graph node',
    note: 'Each squad runs as a StateGraph, one node per agent, each node calling llm_invoke.', color: '#a78bfa' },
  { id: 'claude_agent_sdk', label: 'Claude Agent SDK', adapter: 'K9ClaudeAgentSDKAdapter', squadAs: 'Session + subagents', agentAs: 'Claude subagent',
    note: 'Each squad runs as one Claude session with its squad-mates as confined subagents.', color: '#fb923c' },
];

/** For the OpenAI Agents SDK: who picks the next agent. 'sequence' unless the design spec asked for handoffs. */
export function routingOf(project: Partial<ProjectMeta>): 'sequence' | 'handoffs' {
  return project.agent_routing === 'handoffs' ? 'handoffs' : 'sequence';
}

export function frameworkInfo(id: AgentFramework): AgentFrameworkInfo {
  return AGENT_FRAMEWORKS.find((f) => f.id === id) ?? AGENT_FRAMEWORKS[0];
}

/** The project's agent framework. Older projects saved before this field existed may carry the old 'crewai'
 *  palette tag in `platforms`; those still open as CrewAI. */
export function frameworkOf(project: Partial<ProjectMeta>): AgentFramework {
  if (project.agent_framework) return project.agent_framework;
  return (project.platforms ?? []).includes('crewai') ? 'crewai' : 'native';
}

/** The project with its agent framework set, and the old palette tags ('crewai', 'langchain') removed. */
export function withFramework<T extends ProjectMeta>(project: T, id: AgentFramework): T {
  return { ...project, agent_framework: id,
           platforms: (project.platforms ?? []).filter((p) => p !== 'crewai' && p !== 'langchain') };
}
