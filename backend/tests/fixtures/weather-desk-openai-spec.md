# Weather Desk

**Target Outcome:** A visitor asks one question about the weather and what to wear; a front desk agent hands it to the right specialist, and K9-AIF governs every agent, tool call and reply.
**Agent Framework:** OpenAI Agents SDK
**Domain:** Weather and travel assistance

> How to use this file: open K9X Studio (studio.k9x.ai), go to Intake, and upload this file.
> Studio reads the agent register in section 3.1.8, sets the agent framework to OpenAI Agents SDK,
> and stages one squad. Click Generate, then Scaffold, to get a runnable K9-AIF project.

## 1. Context

The single-agent Weather Assist demo at openai.k9x.ai answers one kind of question: the weather for a
US zip code. Real assistants take mixed questions ("Will it rain in 10001 tomorrow, and do I need a coat?").
This spec models the next step: a small group of OpenAI agents that hand work to each other, still
governed end to end by K9-AIF.

## 2. Architecture in K9-AIF terms

| K9-AIF layer | In this project | What it does |
|---|---|---|
| Router | K9EventRouter | Admits the request and sends it to the orchestrator |
| Orchestrator | WeatherDeskIntelligenceOrchestrator | Zero Trust and k9x Shield at the entry; knows only its squad |
| Squad | WeatherDeskIntelligenceSquad | Runs on the OpenAI Agents SDK through K9OpenAIAgentsAdapter |
| Agents | FrontDeskAgent, WeatherAgent, AttireAdvisorAgent | One OpenAI agent each, built from agent YAML |

On the OpenAI Agents SDK the squad becomes one Runner run. The first agent in the squad is the entry agent,
and its squad-mates are its handoffs. The adapter caps handoffs per run, so a handoff group stays small.

### 2.1 Governance on every step

| Step | Check | Where |
|---|---|---|
| Request enters | Zero Trust role check, then Shield ingress | Orchestrator |
| Each agent's turn | Zero Trust for openai_agent:&lt;name&gt; | Adapter run hooks |
| Each model call | K9 Model Router picks an eligible model (tool calling required) | SDK model provider |
| Each tool call and result | Shield on the arguments and on the returned data | Tool guardrails |
| Each agent's reply | Shield egress | Adapter run hooks |
| Final answer | Shield egress once more | Orchestrator |

### 2.2 Who may run which agent

| Role | FrontDeskAgent | WeatherAgent | AttireAdvisorAgent |
|---|---|---|---|
| customer | yes | yes | yes |
| staff | yes | yes | yes |
| guest | yes | no | no |

A guest reaches the front desk, but the handoff to WeatherAgent is refused by Zero Trust at that agent's turn.

## 3. Design

### 3.1 Requirements

1. One question in, one answer out, whatever the number of agents involved.
2. Every agent is defined in agent YAML; no agent is built in code outside the adapter.
3. The weather lookup is a tool with a fixed schema (zip_code), so its data is screened before any agent reads it.
4. At most three handoffs per run.

### 3.1.8 Agent register

| Agent | Description | Inputs | Outputs | Tools | Zone |
|---|---|---|---|---|---|
| FrontDeskAgent | Entry agent: reads the question and hands off to WeatherAgent or AttireAdvisorAgent; answers greetings itself | Visitor question | Handoff or short answer | none | AMBER |
| WeatherAgent | Finds the current weather for a US zip code with the current_weather tool and reports it plainly | Zip code | Conditions, temperature, wind | current_weather | AMBER |
| AttireAdvisorAgent | Suggests what to wear or pack from the weather WeatherAgent reported | Weather summary | Clothing advice | none | AMBER |

### 3.2 Tools

| Tool | Input | Output | Notes |
|---|---|---|---|
| current_weather | zip_code (5 digits) | Place, temperature, conditions, wind | Free public services (Zippopotam.us, Open-Meteo); no key needed |

### 3.3 Agent YAML sketch

```yaml
# agents/yaml/weather_agent.yaml (same format as the Weather Assist example)
name: WeatherAgent
model: weather                 # K9 model catalog task; the K9 Model Router picks the model
role: >
  You are a weather assistant for US zip codes.
instructions:
  - Call current_weather with the zip code
  - Report only what the tool returned; never guess a temperature or a place
tools:                         # names of ToolCapability entries in runtimes/tools.py
  - current_weather
```

Studio generates one YAML per agent. You don't write handoffs: the squad runtime
(runtimes/weather_desk_intelligence_squad.py) makes the first agent the entry agent and gives it the
other two as handoffs, from the squad order. You edit instructions and tools.

## 4. When to use handoffs, and when a native squad

| Use handoffs (this spec) | Use a native K9-AIF squad |
|---|---|
| The model decides which specialist answers | The steps and their order are known in advance |
| Two to four agents | A long, fixed process |
| Conversation-style requests | Records, rules and approvals (deterministic steps are adapters, not agents) |

## 5. Try it

1. Upload this file in K9X Studio, Intake.
2. Check the Agent Framework card shows OpenAI Agents SDK.
3. Generate the canvas, then Generate Scaffold. The squad gets runtimes/weather_desk_intelligence_squad.py, which returns K9OpenAIAgentsAdapter.
4. In runtimes/tools.py, replace example_lookup with current_weather from the Weather Assist example (weather_zip/tools.py), and add `tools: [current_weather]` to WeatherAgent's YAML.
5. Add current_weather to `approved_tools` (Shield's ToolAuthorizationCheck) in config/config.yaml. Without it, Shield refuses the tool call.
6. Set OLLAMA_BASE_URL in .env, pull a tool-calling model (K9_MODEL_TOOLS, default qwen2.5:7b), put your question in config/scenario.json, and run ./run.sh.

Source of the single-agent example: https://github.com/k9aif/examples/tree/main/k9x_openai_bedrock/openai
