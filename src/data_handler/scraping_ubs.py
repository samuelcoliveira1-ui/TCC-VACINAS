import requests
import zipfile
import io
from pathlib import Path
from datetime import datetime, timedelta

BASE_DIR = Path(__file__).resolve().parents[1]
OUT_DIR = BASE_DIR / "data" / "processed"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CSV_PATH = OUT_DIR / "ubs.csv"
URL_ZIP = "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/CNES/Unidades_Basicas_Saude-UBS_csv.zip"


def precisa_update():
    if not CSV_PATH.exists():
        return True
    data_modificacao = datetime.fromtimestamp(CSV_PATH.stat().st_mtime)
    return datetime.now() - data_modificacao > timedelta(days=7)


def baixar_ubs():
    response = requests.get(URL_ZIP, timeout=60)
    response.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        nome_csv = next(n for n in z.namelist() if n.endswith(".csv"))
        with z.open(nome_csv) as origem, open(CSV_PATH, "wb") as destino:
            destino.write(origem.read())


def garantir_ubs():
    if precisa_update():
        baixar_ubs()