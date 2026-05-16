"""
卡片刷新频率持久化配置管理
"""
import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "card_refresh.json")

# 刷新档位: label -> interval_ms
RATE_PRESETS = [
    ("2s/t",    2000),
    ("1s/t",    1000),   # 默认
    ("1s/2t",    500),
    ("1s/10t",   100),
    ("1s/30t",    33),
    ("1s/60t",    16),
]

DEFAULT_INDEX = 1  # "1s/t"

def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except:
        pass

def get_card_rate_index(card_key):
    cfg = load_config()
    return cfg.get(card_key, DEFAULT_INDEX)

def set_card_rate_index(card_key, index):
    cfg = load_config()
    cfg[card_key] = index
    save_config(cfg)
