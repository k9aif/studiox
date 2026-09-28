export type ComponentType =
  | 'intent_squad'
  | 'router'
  | 'orchestrator'
  | 'hil_orchestrator'
  | 'squad'
  | 'agent'
  | 'validation_loop'
  | 'critic_actor'
  | 'guard'
  | 'system'
  // ── Integration Adapters (design-time, deterministic / non-agentic)
  | 'messaging_adapter'
  | 'workflow_adapter'
  | 'process_adapter'
  | 'api_adapter'
  | 'bpm_adapter'
  | 'rules_adapter'
  | 'data_adapter';

export type AgentClassType = 'BaseAgent' | 'K9ValidationLoopAgent' | 'K9CriticActorAgent';

// Process Studio's own GREEN/AMBER/RED autonomy-zone coding, carried through
// from BPMN import (see backend/services/bpmn_service.py). Explicit and
// separate from AgentClassType — BaseAgent alone is ambiguous (it means both
// "GREEN zone" and "no zone data found"), so don't infer one from the other.
export type Zone = 'GREEN' | 'AMBER' | 'RED';

// Canvas sub-tabs — a view filter over the same graph, not a separate one.
// See canvasLayers.ts.
export type CanvasLayer = 'all' | 'orchestrators' | 'squads' | 'adapters' | 'hil';

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
  zone?: Zone;
  // The BPMN process/task id a node was derived from (bpmn_service.py's
  // process_id) — carried through so Generate Scaffold's payload can
  // include it on agents/adapters, same as zone below. See buildCanvas()
  // (Palette.tsx) and buildProjectPayload() (Studio.tsx).
  processId?: string;
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
  parallelSquads?: boolean;
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
  object_storage_list?: string[];
  docling_enabled?: boolean;
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
  // Which Process Studio input files fed this generation — set by
  // IntakePanel.tsx's stage*File functions when staging succeeds, read by
  // scaffold_service.py's _gen_manifest_md() to build MANIFEST.md's
  // input-artifact -> output-artifact table. Empty/absent means that input
  // type wasn't provided for this project.
  source_bpmn_filename?: string;
  source_spec_filename?: string;
  source_evals_filename?: string;
  source_evals_case_count?: number | null;
  // Parsed eval-case rows from /api/evals/import — one object per test
  // case (id/category/agent/step/scenario/expected/pass_criteria/
  // severity). Read by scaffold_service.py's _gen_eval_test_files().
  source_evals_rows?: Record<string, string>[];
  // Parsed §1.7/§3.4 MCP tool rows from the blueprint (tool_id/name/
  // description/io_schema/authentication/source/build_approach/status) —
  // read by scaffold_service.py's _gen_mcp_tool_files() to generate one
  // stub per "New Build"/"API Wrap"/"MCP Gateway" tool.
  mcp_tools?: Record<string, string>[];
  // Blueprint's own title/subtitle/Target Outcome/Process Reference and
  // atomic-step stats (blueprint_service._parse_header_meta) — read by
  // scaffold_service.py's _gen_main_html() for docs/main.html's hero
  // section. Set by IntakePanel.tsx from combine()'s response whenever a
  // blueprint doc was staged.
  header_meta?: Record<string, string | number>;
}

export interface ProjectScenario {
  title: string;
  narrative: string;
  payload: Record<string, unknown>;
}

export type AppScreen = 'landing' | 'splash' | 'setup' | 'studio';
