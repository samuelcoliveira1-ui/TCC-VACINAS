from pathlib import Path
import json

BASE_DIR = Path(__file__).resolve().parents[1]

def carregar_json(nome_arquivo):
    caminho = BASE_DIR / "data" / "processed" / nome_arquivo
    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f)