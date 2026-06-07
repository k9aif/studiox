# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# tests/test_model_router.py

from pathlib import Path

import yaml

from k9_aif_abb.k9_factories.llm_factory import LLMFactory
from k9_aif_abb.k9_factories.model_router_factory import ModelRouterFactory
from k9_aif_abb.k9_inference.models.inference_request import InferenceRequest


def load_config():
    config_path = Path("k9_aif_abb/config/config.yaml")
    with config_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    config = load_config()

    print("\n--- Resetting and Bootstrapping LLMFactory ---")
    LLMFactory.reset()
    LLMFactory.bootstrap(config)

    ModelRouterFactory.reset()

    print("\n--- Creating Router ---")
    router = ModelRouterFactory.get_router(config)
    assert router is not None, "Router factory returned None"
    print(f"Router type: {router.__class__.__name__}")

    print("\n--- Router Persistence ---")
    print(
        "Configured provider:",
        config["inference"]["router"]["persistence"]["provider"]
    )

    if hasattr(router, "state_store") and hasattr(router.state_store, "db"):
        db = router.state_store.db
        print("Storage backend class:", db.__class__.__name__)

        if hasattr(db, "db_path"):
            print("SQLite DB path:", db.db_path)

        if hasattr(db, "database_url"):
            print("Database URL:", db.database_url)

    
    request = InferenceRequest(
        prompt="What is the capital of France?",
        task_type="chat",
    )

    print("\n--- Invoking Router ---")
    response = router.invoke(request)

    assert response is not None, "Router returned no response"
    assert hasattr(response, "model_alias"), "Response missing model_alias"
    assert hasattr(response, "output"), "Response missing output"
    assert response.model_alias, "Response model_alias is empty"
    assert response.output, "Response output is empty"

    print("\n--- Response ---")
    print("Model:", response.model_alias)
    print("Output:", response.output)

    print("\n[OK] Model router smoke test passed.")


if __name__ == "__main__":
    main()