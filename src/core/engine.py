import re
import ollama
import json
import unicodedata
from datetime import date
from data_handler.loader import *

def pega_vacina(periodo):
    resultado = ''
    data = carregar_json('calendario_vacinas.json')
    data = [info for info in data if info['grupo'].split()[0] == periodo.split('_')[0]]

    if periodo.endswith('json'):
        return data

    for info in data:
        if info['idade_texto'] != '':
            resultado += f'🗓️ <b>{info['idade_texto'].replace('\n', ' ')}</b>:\n\n' if resultado == '' else f'───────────────────\n\n🗓️ <b>{info['idade_texto'].replace('\n', ' ')}</b>:\n\n'
        resultado += f'💉 {info['vacina'].replace('\n', ' ')}\n    • {info['dose'].replace('\n', ' ')}\n\n'
    return resultado

ALIASES_VACINA = {
    'vvsr': 'vírus sincicial respiratório',
    'vsrc': 'vírus sincicial respiratório',
    'virus sincicial': 'vírus sincicial respiratório',
    'vírus sincicial': 'vírus sincicial respiratório',
    'sincicial': 'vírus sincicial respiratório',
    'covid': 'covid-19',
    'covid 19': 'covid-19',
    'covid19': 'covid-19',
    'sars': 'covid-19',
    'coronavirus': 'covid-19',
    'coronavírus': 'covid-19',
    'tríplice viral': 'tríplice viral scr',
    'triplice viral': 'tríplice viral scr',
    'tríplice': 'tríplice viral scr',
    'triplice': 'tríplice viral scr',
    'scr': 'tríplice viral scr',
    'sarampo': 'tríplice viral scr',
    'poliomielite': 'poliomielite inativada vip',
    'polio': 'poliomielite inativada vip',
    'vip': 'poliomielite inativada vip',
    'poliomielite vip': 'poliomielite inativada vip',
    'poliomielite "vip"': 'poliomielite inativada vip',
    'meningocócica': 'meningocócica',
    'meningococica': 'meningocócica',
    'meningite': 'meningocócica',
    'meningococo': 'meningocócica',
    'febre amarela': 'febre amarela',
}

def _normalizar_busca(texto):
    texto = texto.lower().strip()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = texto.replace("-", "").replace(" ", "")
    return texto

def procura_vacina(nome):
    status = ''
    resultado = ''
    data = carregar_json('calendario_vacinas.json')
    nome_original = nome.lower().strip()

    nome_normalizado = _normalizar_busca(nome_original)
    alvo = None
    for alias, canonical in ALIASES_VACINA.items():
        if _normalizar_busca(alias) == nome_normalizado:
            alvo = canonical.lower()
            break

    if alvo is None:
        alvo = nome_original

    alvo_norm = _normalizar_busca(alvo)

    for info in data:
        if info['idade_texto'] != '':
            status = info['idade_texto']
        vacina_raw = info['vacina'].replace('\n', ' ')
        vacina_limpa = re.sub(r'\d+|[¹²³⁴⁵⁶⁷⁸⁹]', '', vacina_raw).lower().strip()
        vacina_norm = _normalizar_busca(vacina_limpa)

        match = False
        if vacina_norm == alvo_norm:
            match = True
        elif alvo_norm not in ('dt',) and alvo_norm.startswith(vacina_norm) and vacina_norm:
            match = True
        elif alvo_norm not in ('dt',) and vacina_norm.startswith(alvo_norm):
            match = True
        elif alvo_norm in vacina_norm:
            match = True

        if match:
            resultado += f'🗓️ <b>{status.replace(chr(10), " ")}</b>:\n\n' if resultado == '' else f'🗓️ <b>{status.replace(chr(10), " ")}</b>:\n\n'
            resultado += f'💉 {vacina_raw}\n    • {info["dose"].replace(chr(10), " ")}\n\n'

    if resultado == '':
        resultado = 'Termo não encontrado!'
    return resultado

def normalizar(texto):
    texto = texto.lower().strip()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = texto.replace(" ", "").replace("-", "")
    return texto

def consultar_cobertura(local=None, uf=None):
    cobertura = carregar_json(
        'cobertura_vacinal.json'
    )["cobertura_vacinal_geral"]["Brasil"]

    if local is None:
        return list(cobertura.keys())
    
    if local:
        local = normalizar(local)

    for regiao, estados in cobertura.items():
        if normalizar(regiao) == local:
            soma, total = {}, {}
            for estado in estados.values():
                for macro in estado.values():
                    for vacina, vals in macro.get("Totais", {}).items():
                        if vacina == "Município Residência":
                            continue
                        try:
                            if isinstance(vals, dict):
                                soma[vacina] = soma.get(vacina, 0) + vals["num"]
                                total[vacina] = total.get(vacina, 0) + vals["den"]
                            else:
                                soma[vacina] = soma.get(vacina, 0) + float(vals)
                                total[vacina] = total.get(vacina, 0) + 1
                        except:
                            pass
            return formatar_cobertura(f"Região {regiao}", soma, total)

    for regiao, estados in cobertura.items():
        if local.upper() in estados:
            soma, total = {}, {}
            for macro in estados[local.upper()].values():
                for vacina, vals in macro.get("Totais", {}).items():
                    if vacina == "Município Residência":
                        continue
                    try:
                        if isinstance(vals, dict):
                            soma[vacina] = soma.get(vacina, 0) + vals["num"]
                            total[vacina] = total.get(vacina, 0) + vals["den"]
                        else:
                            soma[vacina] = soma.get(vacina, 0) + float(vals)
                            total[vacina] = total.get(vacina, 0) + 1
                    except:
                        pass
            return formatar_cobertura(local.upper(), soma, total)

    for regiao, estados in cobertura.items():
        for uf_estado, macros in estados.items():
            if uf and uf.upper() != uf_estado.upper():
                continue
            for macro in macros.values():
                for codigo, dados_municipio in macro.items():
                    if codigo == "Totais":
                        continue
                    municipio = dados_municipio.get("Município Residência", "")
                    nome_municipio = municipio.split(" - ")[-1]
                    if normalizar(nome_municipio) == local:
                        soma, total = {}, {}
                        for vacina, vals in dados_municipio.items():
                            if vacina == "Município Residência":
                                continue
                            try:
                                if isinstance(vals, dict):
                                    soma[vacina] = vals["num"] / vals["den"]
                                    total[vacina] = 1
                                else:
                                    soma[vacina] = float(vals)
                                    total[vacina] = 1
                            except:
                                pass
                        return formatar_cobertura(
                            f"{nome_municipio} ({uf_estado})",
                            soma,
                            total
                        )

    return "Local não encontrado."

nomes_estados = {
    "AC": "Acre",
    "AL": "Alagoas",
    "AP": "Amapá",
    "AM": "Amazonas",
    "BA": "Bahia",
    "CE": "Ceará",
    "DF": "Distrito Federal",
    "ES": "Espírito Santo",
    "GO": "Goiás",
    "MA": "Maranhão",
    "MT": "Mato Grosso",
    "MS": "Mato Grosso do Sul",
    "MG": "Minas Gerais",
    "PA": "Pará",
    "PB": "Paraíba",
    "PR": "Paraná",
    "PE": "Pernambuco",
    "PI": "Piauí",
    "RJ": "Rio de Janeiro",
    "RN": "Rio Grande do Norte",
    "RS": "Rio Grande do Sul",
    "RO": "Rondônia",
    "RR": "Roraima",
    "SC": "Santa Catarina",
    "SP": "São Paulo",
    "SE": "Sergipe",
    "TO": "Tocantins"
}

def formatar_cobertura(nome, soma, total):
    nome = nomes_estados.get(nome, nome)

    medias = {
        v: round((soma[v] / total[v]) * 100, 2)
        for v in soma
    }

    if not medias:
        return f"📊 <b>Cobertura vacinal</b>\n\n❌ Nenhum dado encontrado para esta região."

    geral = round(sum(soma[v] / total[v] * 100 for v in soma) / len(soma), 2)

    mensagem = (
        f"📊 <b>Cobertura vacinal - {nome}</b>\n\n"
        f"📈 <b>Média das vacinas:</b> {geral}%\n\n"
        f"💉 <b>Vacinas:</b>\n\n"
    )

    for vacina, media in sorted(medias.items()):
        vacina = vacina.replace("<", "&lt;").replace(">", "&gt;")
        mensagem += f"• {vacina}: {media}%\n"

    return mensagem[:3900]

def resto():
    return 'Olá, não entendi sua pergunta. Poderia fazê-lá novamente?'

def dia(nascimento):
    try:
        dia, mes, ano = map(int, nascimento.split('/'))
        nasc = date(ano, mes, dia)
        atual = date.today()
        ano = 0

        if atual.year == nasc.year:
            mes = atual.month - nasc.month
            return idade(f'{mes} months')
        else:
            ano = atual.year - nasc.year

        if not (nasc.month, nasc.day) < (atual.month, atual.day) and ano != 0:
            ano -= 1

        return idade(f'{ano} years')
    except Exception as e:
        return "Poderia repetir sua pergunta?"
   
def idade(id):
    ano = mes = semana = -1
    resultado = ''
    mini = 0
    ystat = False
    try:

        if 'year' in id or 'ano' in id:
            ano = int(id.split()[0])
            if ano == 1:
                ano = -1
                mes = 12
        elif 'month' in id or 'mes' in id:
            mes = int(id.split()[0])
        elif 'semana' in id or 'week' in id:
            if id == 'semana':
                semana = '1 semana'
            semana = int(id.split()[0])
        
        if semana != -1:
            periodo = 'Gestante_json'
        elif 0 <= ano <= 9 or 0 <= mes <= 15:
            periodo = 'Criança_json'
        elif 10 <= ano <= 24:
            periodo = 'Adolescente_json'
        elif 25 <= ano <= 59:
            return (pega_vacina('Adulto'), 'grupo_adulto')
        elif ano >= 60:
            return (pega_vacina('Idoso'), 'grupo_idoso')

        mapa_grupo_idade = {
            'Gestante_json': 'grupo_gestante',
            'Criança_json': 'grupo_crianca',
            'Adolescente_json': 'grupo_jovens',
        }
        grupo_periodo = mapa_grupo_idade.get(periodo)
        data = pega_vacina(periodo)
    except Exception as e:
            return "Poderia repetir sua pergunta?"
    
    for info in data:
        if info['idade_min'] is not None:
            mini = info["idade_min"]
            
        if info['idade_min'] is None:
            info['idade_min'] = mini

        if info['idade_max'] is None or info['idade_max'] == 0:
            info["idade_max"] = -1

        if semana != -1 and ano == mes == -1:
            match = re.search(r'(\d+)ª', info['dose'])
            if match and semana < int(match.group(1)):
                return (resultado, grupo_periodo)
            if info['idade_texto'] != '':
                resultado += f'🗓️ <b>{info['idade_texto'].replace('\n', ' ')}</b>:\n\n' if resultado == '' else f'───────────────────\n\n🗓️ <b>{info['idade_texto'].replace('\n', ' ')}</b>:\n\n'
            resultado += f'💉 {info['vacina'].replace('\n', ' ')}\n    • {info['dose'].replace('\n', ' ')}\n\n'
        elif mes > 0 and ano == -1:
            if info['idade_texto'].endswith('anos'):
                return (resultado, grupo_periodo)

            if info['idade_max'] == -1:
                if mes >= info['idade_min']:
                    if info['idade_texto'] != '':
                        resultado += f'🗓️ <b>{info['idade_texto'].replace('\n', ' ')}</b>:\n\n' if resultado == '' else f'───────────────────\n\n🗓️ <b>{info['idade_texto'].replace('\n', ' ')}</b>:\n\n'
                    resultado += f'💉 {info['vacina'].replace('\n', ' ')}\n    • {info['dose'].replace('\n', ' ')}\n\n'
            else:
                if info['idade_min'] <= mes <= info['idade_max']:
                    if info['idade_texto'] != '':
                        resultado += f'🗓️ <b>{info['idade_texto'].replace('\n', ' ')}</b>:\n\n' if resultado == '' else f'───────────────────\n\n🗓️ <b>{info['idade_texto'].replace('\n', ' ')}</b>:\n\n'
                    resultado += f'💉 {info['vacina'].replace('\n', ' ')}\n    • {info['dose'].replace('\n', ' ')}\n\n'
        else:
            mes = ano * 12
            if info['idade_texto'].endswith('meses'):
                ystat = False

            if info['idade_texto'].endswith('anos'):
                ystat = True

            if not ystat:
                if info['idade_max'] == -1:
                    if mes >= info['idade_min']:
                        if info['idade_texto'] != '':
                            resultado += f'🗓️ <b>{info['idade_texto'].replace('\n', ' ')}</b>:\n\n' if resultado == '' else f'───────────────────\n\n🗓️ <b>{info['idade_texto'].replace('\n', ' ')}</b>:\n\n'
                        resultado += f'💉 {info['vacina'].replace('\n', ' ')}\n    • {info['dose'].replace('\n', ' ')}\n\n'
                else:
                    if info['idade_min'] <= mes <= info['idade_max']:
                        if info['idade_texto'] != '':
                            resultado += f'🗓️ <b>{info['idade_texto'].replace('\n', ' ')}</b>:\n\n' if resultado == '' else f'───────────────────\n\n🗓️ <b>{info['idade_texto'].replace('\n', ' ')}</b>:\n\n'
                        resultado += f'💉 {info['vacina'].replace('\n', ' ')}\n    • {info['dose'].replace('\n', ' ')}\n\n'
            else:
                if info['idade_max'] == -1:
                    if ano >= info['idade_min']:
                        if info['idade_texto'] != '':
                            resultado += f'🗓️ <b>{info['idade_texto'].replace('\n', ' ')}</b>:\n\n' if resultado == '' else f'───────────────────\n\n🗓️ <b>{info['idade_texto'].replace('\n', ' ')}</b>:\n\n'
                        resultado += f'💉 {info['vacina'].replace('\n', ' ')}\n    • {info['dose'].replace('\n', ' ')}\n\n'
                else:
                    if info['idade_min'] <= ano <= info['idade_max']:
                        if info['idade_texto'] != '':
                            resultado += f'🗓️ <b>{info['idade_texto'].replace('\n', ' ')}</b>:\n\n' if resultado == '' else f'───────────────────\n\n🗓️ <b>{info['idade_texto'].replace('\n', ' ')}</b>:\n\n'
                        resultado += f'💉 {info['vacina'].replace('\n', ' ')}\n    • {info['dose'].replace('\n', ' ')}\n\n'
    return (resultado, grupo_periodo)

def localizar():
    return "__LOCALIZAR__"

def greet():
    return 'Olá, no que posso ajudar?'

def resposta_ia(perg):
    functions = {
        "pega": pega_vacina,
        "procura": procura_vacina,
        "cobertura": consultar_cobertura,
        "dia": dia,
        "idade": idade,
        "greet": lambda _: greet(),
        "localizar": lambda _: localizar(),
        "resto": lambda _: resto()
    }

    prompt = f"""
    You are a function selector for a Brazilian vaccination bot.

    Available functions:
    - greet: use when greeting. pass empty string as args
    - pega: searches vaccines for age groups. Arguments must be exactly one of: Gestante, Criança, Adolescente, Jovem, Adulto, Idoso
    - procura: searches by vaccine name (e.g. dengue, hepatite, covid)
    - cobertura: searches vaccination coverage by location. Accepts Brazilian regions (Norte, Nordeste, Centro-Oeste, Sul, Sudeste), state abbreviations (SP, RJ, MG...), or city names (e.g. Sobral, Campinas). Pass exactly what the user said as the location.
    - dia: converts a date in dd/mm/yyyy format to an age group
    - idade: classifies an age into years/months/weeks. Format: "x years", "y months", "z weeks". Do not convert values.
    - localizar: use when the user wants to find nearby UBS (health posts), clinics or vaccination points near them. No arguments needed.
    - resto: use for anything unrelated to the above.

    User request:
    "{perg}"

    Reply with a JSON in this format:
    {{
        "funcao": "function_name",
        "args": "arguments"
    }}

    For localizar, use empty string as args.
    Return only valid JSON. Do not use ```
    """
    response = ollama.chat(
        model='qwen2.5',
        messages=[
            {'role': 'user', 'content': prompt}
        ]
    )
    selected = response['message']['content'].strip()
    selected = json.loads(selected)

    if selected['funcao'] in functions:
        if selected['funcao'] == 'pega':
            periodo = selected['args']
            normalizacao = {
                'Jovem': 'Adolescente',
                'Jovens': 'Adolescente',
                'Adolescente': 'Adolescente',
                'Adolescentes': 'Adolescente',
            }
            periodo = normalizacao.get(periodo, periodo)
            resultado = pega_vacina(periodo)
            mapa_grupo = {
                'Gestante': 'grupo_gestante',
                'Criança': 'grupo_crianca',
                'Adolescente': 'grupo_jovens',
                'Adulto': 'grupo_adulto',
                'Idoso': 'grupo_idoso',
            }
            grupo = mapa_grupo.get(periodo)
            return (resultado, grupo)
        resultado = functions[selected['funcao']](selected['args'])
        if selected['funcao'] in ('dia', 'idade') and isinstance(resultado, tuple):
            return resultado
        return resultado
