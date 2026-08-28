import json
import sys
from io import BytesIO
from pathlib import Path
from datetime import datetime, timedelta

import requests
import pdfplumber

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))
ARQUIVO_JSON = BASE_DIR / "data" / "processed" / "calendario_vacinas.json"

GRUPOS = {
    'grupo_idoso': 'Idoso',
    'grupo_adulto': 'Adulto',
    'grupo_jovens': 'Adolescente e Jovem',
    'grupo_crianca': 'Criança',
    'grupo_gestante': 'Gestante'
}

from utils.helpers import extrair_idade, remove_repetido, urls


def gerar_calendario_vacinas():
    arquivo_json = []

    for grupo, url in urls.items():
        grupo_nome = GRUPOS.get(grupo, 'Nenhum')

        resp = requests.get(url)
        resp.raise_for_status()

        with pdfplumber.open(BytesIO(resp.content)) as pdf:
            for pagina in pdf.pages:
                tabelas = pagina.extract_tables()
                if not tabelas:
                    continue

                for tabela in tabelas:
                    for linha in tabela[1:]:
                        if not linha or len(linha) < 4:
                            continue

                        idade_texto = linha[0] or ''
                        idade_min, idade_max = extrair_idade(idade_texto)

                        vacina = linha[1] or ''
                        vacina_str = str(vacina)

                        if len(vacina_str) >= 4:
                            if vacina_str[0] == vacina_str[1] and vacina_str[2] == vacina_str[3]:
                                vacina = remove_repetido(vacina_str)
                            else:
                                vacina = vacina_str

                        arquivo_json.append({
                            'grupo': grupo_nome,
                            'idade_min': idade_min,
                            'idade_max': idade_max,
                            'idade_texto': idade_texto,
                            'vacina': vacina or '',
                            'dose': linha[2] or '',
                            'descricao': linha[3] or '',
                            'observacoes': None
                        })

    ARQUIVO_JSON.parent.mkdir(parents=True, exist_ok=True)

    with open(ARQUIVO_JSON, "w", encoding="utf-8") as f:
        json.dump(arquivo_json, f, ensure_ascii=False, indent=2)


def precisa_update():
    if not ARQUIVO_JSON.exists():
        return True

    data_modificacao = datetime.fromtimestamp(ARQUIVO_JSON.stat().st_mtime)
    return datetime.now() - data_modificacao > timedelta(days=7)


def atualizar_se_precisar():
    if precisa_update():
        gerar_calendario_vacinas()
        return True
    return False


if __name__ == "__main__":
    atualizar_se_precisar()