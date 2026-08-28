from playwright.sync_api import sync_playwright
from pathlib import Path
import pandas as pd
import json
import os
from datetime import datetime, timedelta

BASE_DIR = Path(__file__).resolve().parents[1]
OUT_DIR = BASE_DIR / "data" / "processed"
OUT_DIR.mkdir(parents=True, exist_ok=True)

URL_COBERTURA = "https://infoms.saude.gov.br/extensions/SEIDIGI_DEMAS_VACINACAO_CALENDARIO_NACIONAL_COBERTURA_RESIDENCIA/SEIDIGI_DEMAS_VACINACAO_CALENDARIO_NACIONAL_COBERTURA_RESIDENCIA.html#"

URL_COVID = "https://infoms.saude.gov.br/extensions/SEIDIGI_DEMAS_COBERTURA_COVID_RESIDENCIA/SEIDIGI_DEMAS_COBERTURA_COVID_RESIDENCIA.html#"

JSON_PATH = OUT_DIR / "cobertura_vacinal.json"


def precisa_update():
    if not JSON_PATH.exists():
        return True
    data_modificacao = datetime.fromtimestamp(JSON_PATH.stat().st_mtime)
    return datetime.now() - data_modificacao > timedelta(days=7)


def esperar(page, t=4000):
    page.wait_for_timeout(t)


def clicar(page, sel):
    el = page.locator(sel)
    el.scroll_into_view_if_needed()
    el.click()


def baixar(page, click_fn, output_path):
    with page.expect_download(timeout=30000) as d:
        click_fn()

    download = d.value
    final_path = output_path.with_suffix(".xlsx")
    download.save_as(str(final_path))
    return final_path


def baixar_cobertura(page):

    page.goto(URL_COBERTURA, wait_until="domcontentloaded")
    esperar(page, 8000)

    page.locator("#aba2-tab").click(force=True)
    esperar(page, 8000)

    page.locator('[title="Numerador"]').click(force=True)
    esperar(page, 1000)

    page.locator('[title="Denominador"]').click(force=True)
    esperar(page, 1000)

    page.locator('[data-testid="actions-toolbar-confirm"]').click(force=True)
    esperar(page, 6000)

    return baixar(
        page,
        lambda: clicar(page, "#exportar-dados-QV1-10"),
        OUT_DIR / "cobertura_vacinal_geral.xlsx"
    )

def baixar_covid_mono(page):

    page.goto(URL_COVID, wait_until="domcontentloaded")
    esperar(page, 5000)

    page.locator("#mono-tab").click(force=True)
    esperar(page, 5000)

    return baixar(
        page,
        lambda: clicar(page, "#exportar-dados-QV1-05"),
        OUT_DIR / "covid_monovalente_municipio.xlsx"
    )


def baixar_covid_mono_uf(page):

    page.goto(URL_COVID, wait_until="domcontentloaded")
    esperar(page, 5000)

    page.locator("#mono-tab").click(force=True)
    esperar(page, 5000)

    return baixar(
        page,
        lambda: clicar(page, "#exportar-dados-QV1-04"),
        OUT_DIR / "covid_monovalente_uf.xlsx"
    )


def baixar_covid_biva(page):

    page.locator("#home-tab").click(force=True)
    esperar(page, 8000)

    return baixar(
        page,
        lambda: clicar(page, "#exportar-dados-QV1-10"),
        OUT_DIR / "covid_bivalente_municipio.xlsx"
    )


def baixar_covid_biva_uf(page):

    page.locator("#home-tab").click(force=True)
    esperar(page, 8000)

    return baixar(
        page,
        lambda: clicar(page, "#exportar-dados-QV1-09"),
        OUT_DIR / "covid_bivalente_uf.xlsx"
    )


def clean(v):
    if pd.isna(v):
        return None
    v = str(v).strip()
    return None if v.lower() == "nan" else v

def parse_xlsx(path, name):

    df = pd.read_excel(path)

    if "Unnamed: 1" in df.columns and df.iloc[0]['Unnamed: 1'] == 'Região Ocorrência':

        df_data = df.iloc[1:].reset_index(drop=True)

        num_cols = [c for c in df.columns if c.endswith('.1')]
        den_cols = [c for c in df.columns if c.endswith('.2')]
        vacinas  = [c.replace('.1', '') for c in num_cols]

        C1, C2, C3, C4, C5 = 'Unnamed: 1', 'Unnamed: 2', 'Unnamed: 3', 'Unnamed: 4', 'Imunobiológico'

        def cell(row, col):
            v = row[col]
            return str(v).strip() if pd.notna(v) else None

        def to_float(v):
            try: return float(v)
            except: return None

        brasil = {}

        for _, row in df_data.iterrows():
            n1 = cell(row, C1)
            n2 = cell(row, C2)
            n3 = cell(row, C3)
            n4 = cell(row, C4)
            n5 = cell(row, C5)

            if n2 in (None, 'Totais') or n3 in (None, 'Totais'):
                continue

            vacinas_row = {}
            for vacina, nc, dc in zip(vacinas, num_cols, den_cols):
                num = to_float(row[nc])
                den = to_float(row[dc])
                if num is not None and den and den > 0:
                    vacinas_row[vacina] = {
                        "num": num,
                        "den": den
                    }

            if not vacinas_row:
                continue

            brasil.setdefault(n1, {}).setdefault(n2, {}).setdefault(n3, {})

            if n4 == 'Totais':
                brasil[n1][n2][n3]['Totais'] = vacinas_row
            elif n5 and n5 != 'Totais':
                brasil[n1][n2][n3].setdefault(n5, {})
                brasil[n1][n2][n3][n5]['Município Residência'] = n5
                brasil[n1][n2][n3][n5].update(vacinas_row)

        return {name: {"Brasil": brasil}}

    else:
        records = {}
        for _, row in df.iterrows():
            key = None
            entry = {}
            for col in df.columns:
                v = row[col]
                if pd.isna(v):
                    continue
                try:
                    entry[col] = round(float(v), 6)
                except (ValueError, TypeError):
                    entry[col] = str(v).strip()

            if "Cód. Município" in df.columns:
                key = str(int(row["Cód. Município"])) if pd.notna(row["Cód. Município"]) else None
            elif "Cód. UF" in df.columns:
                key = str(int(row["Cód. UF"])) if pd.notna(row["Cód. UF"]) else None

            if key:
                records[key] = entry

        return {name: records}
def run():

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        cob = baixar_cobertura(page)

        mono = baixar_covid_mono(page)
        mono_uf = baixar_covid_mono_uf(page)

        biva = baixar_covid_biva(page)
        biva_uf = baixar_covid_biva_uf(page)

        browser.close()

    data = {}
    cob_data = parse_xlsx(cob, "cobertura_vacinal_geral")
    print("Regiões encontradas:", list(cob_data.get("cobertura_vacinal_geral", {}).get("Brasil", {}).keys()))
    data.update(cob_data)     
    data.update(parse_xlsx(mono, "covid_monovalente_municipio"))
    data.update(parse_xlsx(mono_uf, "covid_monovalente_uf"))
    data.update(parse_xlsx(biva, "covid_bivalente_municipio"))
    data.update(parse_xlsx(biva_uf, "covid_bivalente_uf"))

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    for p in [cob, mono, mono_uf, biva, biva_uf]:
        if os.path.exists(p):
            os.remove(p)

    return JSON_PATH


if __name__ == "__main__":
    if precisa_update():
        run()