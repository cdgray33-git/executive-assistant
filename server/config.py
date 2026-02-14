"""
User configuration management for Executive Assistant
Stores personalization settings in ~/.jarvis/config.json
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("config")

# Config stored in user's home directory (works on Mac)
CONFIG_DIR = Path.home() / ".jarvis"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "ea_name": "JARVIS",
    "user_name": "User",
    "banner_text": "JARVIS, Your Executive Assistant",
    "model": "qwen2.5:7b-instruct",
    "auto_cleanup": {
        "enabled": False,
        "interval_minutes": 180,  # 3 hours default
        "max_emails_per_run": 50
    },
    "ui_preferences": {
        "show_capabilities_list": False,
        "theme": "light"
    }
}


def get_config() -> Dict[str, Any]:
    """
    Load user configuration from disk
    Creates default config if none exists
    """
    try:
        if CONFIG_FILE.exists():
            config = json.loads(CONFIG_FILE.read_text())
            logger.info(f"Loaded config: {config.get('ea_name')} for {config.get('user_name')}")
            return config
        else:
            logger.info("No config found, using defaults")
            save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG.copy()
    except Exception as e:
        logger.error(f"Config load error: {e}, using defaults")
        return DEFAULT_CONFIG.copy()


def save_config(config: Dict[str, Any]) -> bool:
    """
    Save user configuration to disk
    """
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(config, indent=2))
        logger.info(f"Config saved: {config.get('ea_name')}")
        return True
    except Exception as e:
        logger.error(f"Config save error: {e}")
        return False


def update_config(updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update specific config values (merge with existing)
    """
    config = get_config()
    
    # Deep merge for nested dicts
    for key, value in updates.items():
        if isinstance(value, dict) and key in config and isinstance(config[key], dict):
            config[key].update(value)
        else:
            config[key] = value
    
    save_config(config)
    return config


def reset_config() -> Dict[str, Any]:
    """
    Reset configuration to defaults
    """
    save_config(DEFAULT_CONFIG)
    logger.info("Config reset to defaults")
    return DEFAULT_CONFIG.copy()
