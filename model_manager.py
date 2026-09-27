#!/usr/bin/env python3

import sys
import json
from pathlib import Path


BASE = Path.home() / "jiraiya"
MODELS_DIR = BASE / "models"
REGISTRY = MODELS_DIR / "models.json"


def load_models():

    if not REGISTRY.exists():
        raise RuntimeError("models.json not found")

    with open(
        REGISTRY,
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


def list_models():

    models = load_models()

    print()
    print("===== JIRAIYA MODELS =====")
    print()

    if not models:
        print("No models registered.")
        return

    for model_id, config in models.items():

        model_file = MODELS_DIR / config["file"]

        status = "READY" if model_file.exists() else "MISSING"

        print(
            f"{model_id}  |  "
            f"{config['name']}  |  "
            f"{status}"
        )

    print()


def get_model(model_id):

    models = load_models()

    if model_id not in models:
        raise ValueError(
            f"Model '{model_id}' not found."
        )

    config = models[model_id]

    model_file = MODELS_DIR / config["file"]

    if not model_file.exists():
        raise FileNotFoundError(
            f"Model file not found:\n{model_file}"
        )

    return {
        "id": model_id,
        "name": config["name"],
        "path": str(model_file),
        "context": config.get("context", 2048),
        "threads": config.get("threads", 4),
        "max_tokens": config.get("max_tokens", 300)
    }


def main():

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python model_manager.py list")
        print("  python model_manager.py get <model>")
        return

    command = sys.argv[1]

    if command == "list":

        list_models()

    elif command == "get" and len(sys.argv) >= 3:

        try:

            model = get_model(sys.argv[2])

            print()
            print("===== MODEL DETAILS =====")
            print()
            print(f"ID:          {model['id']}")
            print(f"Name:        {model['name']}")
            print(f"Path:        {model['path']}")
            print(f"Context:     {model['context']}")
            print(f"Threads:     {model['threads']}")
            print(f"Max tokens:  {model['max_tokens']}")
            print()

        except Exception as error:

            print(f"ERROR: {error}")

    else:

        print("Invalid command.")


if __name__ == "__main__":
    main()





