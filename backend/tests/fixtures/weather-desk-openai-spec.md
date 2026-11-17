# Weather Desk

**Target Outcome:** A visitor asks one question about the weather and what to wear; three OpenAI agents answer it in a fixed sequence set by the squad, and K9-AIF governs every step, tool call and reply.
**Agent Framework:** OpenAI Agents SDK
**Agent Routing:** sequence
**Domain:** Weather and travel assistance

> Design specification for the development team. Open K9X Studio (studio.k9x.ai), go to Intake, and upload
> this file. Studio reads the agent register in section 3.1.8, sets the agent framework to OpenAI Agents SDK
> with sequence routing, and stages one squad. Click Generate, then Scaffold, to get a runnable K9-AIF project.

## 1. Context

The single-agent Weather Assist demo at openai.k9x.ai answers one kind of question: the weather for a
US zip code. Real assistants take mixed questions ("Will it rain in 10001 tomorrow, and do I need a coat?").
This design adds two agents around the weather agent, still governed end to end by K9-AIF.

## 2. Architecture in K9-AIF terms

| K9-AIF layer | In this project | What it does |
|---|---|---|
| Router | K9EventRouter | Admits the request and sends it to the orchestrator |
| Orchestrator | WeatherDeskIntelligenceOrchestrator | Zero Trust and k9x Shield at the entry; knows only its squad |
| Squad | WeatherDeskIntelligenceSquad | Runs its three agents in the order of its flow, with synthesis |
| Agents | FrontDeskAgent, WeatherAgent, AttireAdvisorAgent | One OpenAI agent each (K9OpenAIAgent), configured by agent YAML |

### 2.1 The flow: the squad decides, not the model

Every question goes through the same three steps, in this order:

| Step | Agent | Reads | Produces |
|---|---|---|---|
| 1 | FrontDeskAgent | The visitor's question | What the visitor needs: the zip code, and whether they asked about clothing |
| 2 | WeatherAgent | The question and step 1 | The current weather for the zip code, from the current_weather tool |
| 3 | AttireAdvisorAgent | The question and steps 1 and 2 | The final answer: the weather in one line, then what to wear |

- **The order is fixed by this design.** No model chooses the next step, and no agent is offered a handoff.
  The OpenAI Agents SDK runs one agent's turn at a time; the squad decides what runs next. The SDK's own
  guide calls this "orchestrating via code".
- **Synthesis: auto.** When the earlier steps' results grow beyond the squad's limit, the squad coordinator
  hands the next step a governed digest instead of the full outputs. Below that limit, each step reads the
  earlier outputs as they are.
- **The same question takes the same path every time**, so the flow can be tested, audited and explained.

Handoffs, where the model picks the specialist, are available for open-ended conversations: set
`**Agent Routing:** handoffs` above and generate again. This design doesn't use them.

### 2.2 Governance on every step

| Step | Check | Where |
|---|---|---|
| Request enters | Zero Trust role check, then Shield ingress | Orchestrator |
| Each step's input and output | Shield ingress and egress | Every agent, by construction (BaseAgent) |
| Each model call | K9 Model Router picks an eligible model (tool calling for WeatherAgent) | SDK model provider |
| Each tool call and result | Shield on the arguments and on the returned data | Tool guardrails |
| Final answer | Shield egress | Orchestrator |

### 2.3 Who may use the desk

| Role | Weather Desk |
|---|---|
| customer | yes |
| staff | yes |
| guest | no: refused by Zero Trust at the orchestrator, before any agent runs |

## 3. Design

### 3.1 Requirements

1. One question in, one answer out (the last step's output).
2. The three steps run in the order of section 2.1, every time.
3. Every agent is configured in agent YAML; its class is an empty subclass of K9OpenAIAgent.
4. The weather lookup is a tool with a fixed schema (zip_code), so its data is screened before any agent reads it.

### 3.1.8 Agent register

| Agent | Description | Inputs | Outputs | Tools | Zone |
|---|---|---|---|---|---|
| FrontDeskAgent | Step 1: reads the visitor's question and states what they need, the zip code and whether they asked about clothing | Visitor question | What the visitor needs | none | AMBER |
| WeatherAgent | Step 2: finds the current weather for the US zip code with the current_weather tool and reports it plainly | The question and step 1 | Conditions, temperature, wind | current_weather | AMBER |
| AttireAdvisorAgent | Step 3: writes the final answer, the weather in one line and then what to wear or pack | The question and steps 1 and 2 | The final answer | none | AMBER |

### 3.2 Tools

| Tool | Input | Output | Notes |
|---|---|---|---|
| current_weather | zip_code (5 digits) | Place, temperature, conditions, wind | Free public services (Zippopotam.us, Open-Meteo); no key needed |

### 3.3 Agent YAML sketch

```yaml
# agents/yaml/weather_agent.yaml
name: WeatherAgent
class: WeatherAgent
module: squad_agents.weather_agent    # an empty K9OpenAIAgent subclass
model: tools                          # K9 model catalog alias; the K9 Model Router picks the model
role: >
  You report the current weather for a US zip code.
instructions:
  - Call current_weather with the zip code from the request
  - Report only what the tool returned; never guess a temperature or a place
tools: [current_weather]              # names of ToolCapability entries in runtimes/tools.py
handoffs: []                          # always empty: the squad's flow decides what runs next
```

```yaml
# squads/yaml/weather_desk_intelligence_squad.yaml
squads:
  WeatherDeskIntelligenceSquad:
    agents: [FrontDeskAgent, WeatherAgent, AttireAdvisorAgent]
    synthesis: auto
    flow:
      - agent: FrontDeskAgent
      - agent: WeatherAgent
      - agent: AttireAdvisorAgent
```

Studio generates both. You edit the agents' instructions and tools.

## 4. Try it

1. Upload this file in K9X Studio, Intake.
2. Check the Agent Framework card shows OpenAI Agents SDK, with agent routing "sequence".
3. Generate the canvas, then Generate Scaffold. Each agent gets an empty class in `squad_agents/`, and the squad YAML gets the flow above.
4. In runtimes/tools.py, replace example_lookup with current_weather from the Weather Assist example (weather_zip/tools.py), and in WeatherAgent's YAML set `tools: [current_weather]` and `model: tools` (the tool-calling model).
5. Add current_weather to `approved_tools` (Shield's ToolAuthorizationCheck) in config/config.yaml. Without it, Shield refuses the tool call.
6. Set OLLAMA_BASE_URL in .env, pull a tool-calling model (K9_MODEL_TOOLS, default qwen2.5:7b), put your question in config/scenario.json, and run ./run.sh.

Needs k9-aif 1.28.0 or later (K9OpenAIAgent). Source of the single-agent example:
https://github.com/k9aif/examples/tree/main/k9x_openai_bedrock/openai
