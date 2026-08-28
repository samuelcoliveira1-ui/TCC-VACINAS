import pandas as pd
from math import radians, sin, cos, sqrt, atan2
from pathlib import Path
import urllib.parse
import requests

BASE_DIR = Path(__file__).resolve().parents[1]
CSV_PATH = BASE_DIR / "data" / "processed" / "ubs.csv"


def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


def carregar_ibge():
    try:
        r = requests.get(
            "https://servicodados.ibge.gov.br/api/v1/localidades/municipios",
            timeout=10
        ).json()
        return {str(m["id"])[:6]: m["nome"] for m in r}
    except:
        return {}

IBGE_MUNICIPIOS = carregar_ibge()

BRASIL_LAT_MIN, BRASIL_LAT_MAX = -33.75, 5.27
BRASIL_LON_MIN, BRASIL_LON_MAX = -73.99, -28.65

def coordenadas_no_brasil(lat: float, lon: float) -> bool:
    return (BRASIL_LAT_MIN <= lat <= BRASIL_LAT_MAX and
            BRASIL_LON_MIN <= lon <= BRASIL_LON_MAX)


def proximas_ubs(user_lat: float, user_lon: float) -> str:
    if not coordenadas_no_brasil(user_lat, user_lon):
        return None
    if not CSV_PATH.exists():
        return "❌ Base de dados de UBS não encontrada. Tente novamente mais tarde."

    df = pd.read_csv(CSV_PATH, sep=";", encoding="utf-8", dtype=str)

    df["LATITUDE"] = pd.to_numeric(df["LATITUDE"], errors="coerce")
    df["LONGITUDE"] = pd.to_numeric(
        df["LONGITUDE"].str.replace(",", ".", regex=False), errors="coerce"
    )
    df = df.dropna(subset=["LATITUDE", "LONGITUDE"])

    df["distancia"] = df.apply(
        lambda r: haversine(user_lat, user_lon, r["LATITUDE"], r["LONGITUDE"]),
        axis=1
    )

    top3 = df.nsmallest(3, "distancia")

    medalhas = ["🥇", "🥈", "🥉"]
    texto = "🏥 <b>UBSs mais próximas:</b>\n\n"

    for i, (_, row) in enumerate(top3.iterrows(), 1):
        nome = row["NOME"]
        endereco = str(row.get("LOGRADOURO", "")).strip().title()
        bairro = str(row.get("BAIRRO", "")).strip().title()
        ibge = str(row.get("IBGE", "")).strip()
        cidade = IBGE_MUNICIPIOS.get(ibge, "").title()
        medalha = medalhas[i - 1]
        label = " — mais próxima" if i == 1 else ""

        query = nome
        if endereco and endereco != "nan":
            query += f" {endereco}"
            if bairro and bairro != "nan":
                query += f" {bairro}"
        query_encoded = urllib.parse.quote(query)

        texto += f"{medalha}<b>{nome}</b>{label}\n"
        if endereco and endereco != "nan":
            texto += f"    {endereco}"
            if bairro and bairro != "nan":
                texto += f", {bairro}"
            if cidade:
                texto += f", {cidade}"
            texto += "\n"
        texto += f'    <a href="https://www.google.com/maps/search/?api=1&query={query_encoded}">📍 Ver no Google Maps</a>\n'
        texto += "\n"

    return texto.strip()


def cep_para_coords(cep: str):
    """Converte CEP em (lat, lon) via ViaCEP + Nominatim. Retorna None se falhar."""
    cep = cep.replace("-", "").strip()

    try:
        via = requests.get(f"https://viacep.com.br/ws/{cep}/json/", timeout=5).json()
        if via.get("erro"):
            return None

        logradouro = via.get("logradouro", "")
        bairro = via.get("bairro", "")
        localidade = via.get("localidade", "")
        uf = via.get("uf", "")

        queries = []

        queries.append(f"{cep}, Brasil")

        partes = [p for p in [logradouro, bairro, localidade, uf] if p.strip()]
        if len(partes) >= 2:
            queries.append(", ".join(partes) + ", Brasil")

        queries.append(f"{localidade}, {uf}, Brasil")

        for q in queries:
            nominatim = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": q, "format": "json", "limit": 1},
                headers={"User-Agent": "VacinaBrasilBot/1.0"},
                timeout=5
            ).json()
            if nominatim:
                return float(nominatim[0]["lat"]), float(nominatim[0]["lon"])

        return None

    except Exception:
        return None