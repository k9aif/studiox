# K9-AIF Framework Context

You are designing a multi-agent system using K9-AIF.

## Hierarchy
Event → Router → Orchestrator → Squad → Agents → LLM

One Orchestrator coordinates one Squad. A Squad executes 2-5 agents in sequence.
Each agent enriches a shared context passed to the next agent.

## Agent types — pick one per agent

- BaseAgent: one-shot tasks. Use for: triage, classify, route, audit, guard, notify.
- K9ValidationLoopAgent: iterative tasks. Use for: validate, verify, fraud detection, compliance checks, confidence scoring.
- K9CriticActorAgent: generate-then-refine tasks. Use for: draft reports, write narratives, recommend actions.

## Decision rule
"Needs to retry until confident?" → K9ValidationLoopAgent
"Drafts output and improves it?" → K9CriticActorAgent
"One-pass answer?" → BaseAgent

## Model values
- "general" → BaseAgent (triage, classify, route)
- "reasoning" → K9ValidationLoopAgent or K9CriticActorAgent
- "extraction" → document parsing agents
- "chat" → conversational agents

## Naming
- Agents: PascalCase + "Agent" suffix (TriageAgent, FraudDetectionAgent)
- Squads: PascalCase + "Squad" suffix (ClaimsProcessingSquad)
- Orchestrators: PascalCase + "Orchestrator" suffix (ClaimsOrchestrator)

## Squad rules
- 2-5 agents per squad
- First agent: triage or classify
- Last agent: audit or guard
- One orchestrator per squad, named to match
