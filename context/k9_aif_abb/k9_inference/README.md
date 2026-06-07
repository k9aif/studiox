# K9 Inference Layer

The **K9 Inference Layer** provides a structured architectural framework for integrating large language models and AI inference providers into applications built with **K9-AIF (K9 Agentic Integration Framework)**.

The layer introduces architectural separation between:

• application logic  
• inference orchestration  
• model providers  

This allows AI systems to evolve independently of specific model vendors or deployment environments.

---

## Purpose

Modern AI systems often rely on multiple models and providers.  
Without an architectural abstraction layer, applications typically:

- couple directly to specific models
- embed provider-specific logic in application code
- lack governance over inference usage
- become difficult to evolve as model capabilities change

The **K9 Inference Layer** solves this by introducing a modular architecture for model interaction.

---

## Core Components

The inference layer consists of several architectural components:

``` bash

k9_inference
├── models
│   ├── inference_request.py
│   ├── inference_response.py
│   └── route_decision.py
│
├── routers
│   ├── base_model_router.py
│   └── k9_model_router.py
│
├── catalog
│   └── model_catalog.py

```

These components provide a modular system for defining inference requests, selecting models, and executing model interactions.

---

## Architectural Overview

The inference layer sits between agents/orchestrators and AI model providers.

``` code

Agent / Orchestrator
↓
InferenceRequest
↓
Model Router
↓
ModelCatalog
↓
LLMFactory
↓
Inference Provider
(Ollama / Watsonx / OpenAI / etc.)

```

This architecture ensures that application code remains independent from specific model implementations.

---

## Inference Request

`InferenceRequest` defines the structure of an inference call.

Example:

```python
InferenceRequest(
    prompt="Classify the user's request",
    task_type="chat",
    metadata={
        "agent": "claims_orchestrator",
        "stage": "intent_classification"
    }
)
```

Requests may include metadata used by the router to select the appropriate model.

---

## Model Router

``` code

BaseModelRouter (ABB)
K9ModelRouter (SBB)

```

## Architecture Diagram

---

## Architecture Diagram

<p align="center">
  <img src="k9_model_routing_architecture.png" width="550"/>
</p>

```



