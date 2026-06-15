export type ComponentType =
  | 'intent_squad'
  | 'router'
  | 'orchestrator'
  | 'squad'
  | 'agent'
  | 'validation_loop'
  | 'critic_actor'
  | 'guard'
  | 'system';

export type AgentClassType = 'BaseAgent' | 'K9ValidationLoopAgent' | 'K9CriticActorAgent';

export interface PaletteComponent {
  type: ComponentType;
  label: string;
  abbClass: string;
  color: string;
  description: string;
  singleton?: boolean;
}

export interface NodeData extends Record<string, unknown> {
  label: string;
  componentType: ComponentType;
  color: string;
  abbClass: string;
  agentType?: AgentClassType;
  model?: string;
  pattern?: string;
  description?: string;
  squadName?: string;
  orchestratorName?: string;
  temperature?: string;
  maxTokens?: string;
  llmProvider?: string;
  routingStrategy?: string;
  retryPolicy?: string;
  system?: boolean;
  collapsed?: boolean;
}

export interface ProjectMeta {
  project_name: string;
  app_name: string;
  author: string;
  domain: string;
  description: string;
  project_folder: string;
  framework_path: string;
  platforms: string[];
  messaging_list?: string[];
  database_list?: string[];
  deployment_list?: string[];
  // Business context
  vision?: string;
  current_state?: string;
  pain_points?: string;
  target_goals?: string;
  notes?: string;
  // Enrichment fields
  key_processes?: string;
  systems_of_record?: string;
  integration_patterns?: string;
  compliance_requirements?: string;
  hitl_decisions?: string;
  volume_sla?: string;
  // Demo scenario — shown by run.sh and sent as the squad's input payload
  scenario?: ProjectScenario;
}

export interface ProjectScenario {
  title: string;
  narrative: string;
  payload: Record<string, unknown>;
}

export type AppScreen = 'splash' | 'setup' | 'studio';
