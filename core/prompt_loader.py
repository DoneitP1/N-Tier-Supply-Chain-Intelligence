import os
import yaml
from typing import Dict
from functools import lru_cache

PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")

@lru_cache()
def load_prompt(prompt_name: str) -> Dict[str, str]:
    """
    Loads a prompt from a YAML file in the prompts directory.
    Usage: prompts = load_prompt("contract_extraction")
    """
    file_path = os.path.join(PROMPTS_DIR, f"{prompt_name}.yaml")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Prompt file not found: {file_path}")
    
    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
