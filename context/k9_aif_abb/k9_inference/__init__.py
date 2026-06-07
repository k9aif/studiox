# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
K9-AIF Inference Package

The `k9_inference` package provides inference-related components within
the K9-AIF framework.

It is responsible for abstracting interactions with language models and
other inference engines, enabling flexible and provider-independent model usage.

This package builds on the base inference contracts defined in `k9_core`
and supports pluggable integration with multiple model providers.


## Key Responsibilities

- Providing abstraction over language model and inference providers
- Supporting multiple backend integrations (local and external)
- Enabling model execution through routing layers
- Standardizing request/response handling for inference operations
- Allowing extensibility for new model providers and capabilities


## Architectural Pattern

In K9-AIF, inference is not invoked directly.

Instead:

    Application / Agent → ModelRouter → Inference (LLM providers)

- Agents and SBBs do NOT directly select models
- Model selection is delegated to a router
- Router uses configuration, policy, or context to choose the model
- Inference components execute the request


## Usage Example

Note: usually config.yaml exists in its own folder.  below is just an example. 

from k9_aif_abb.k9_factories.model_router_factory import ModelRouterFactory

config = {
    "model_router": {
        "type": "default"
    },
    "models": {
        "general": {
            "provider": "ollama",
            "model": "llama3.2:1b"
        }
    }
}

router = ModelRouterFactory.create(config)

response = router.route({
    "task": "general",
    "prompt": "Explain K9-AIF in one sentence"
})

print(response)


"""