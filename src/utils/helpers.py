import re

# obtendo números da faixa etária
def extrair_idade(idade_texto):
    if not idade_texto:
        return None, None

    idade_texto = str(idade_texto).lower()

    if 'ao nascer' in idade_texto:
        return 0, 0

    numeros = re.findall(r'\d+', idade_texto)

    if len(numeros) >= 2:
        return int(numeros[0]), int(numeros[1])
    elif len(numeros) == 1:
        return int(numeros[0]), None
    else:
        return None, None

def remove_repetido(palavra):
    result = [palavra[0]]
    for l in palavra[1:]:
        if l != result[-1]:
            result.append(l)
    return ''.join(result)

# calendários relevantes disponíveis em https://www.gov.br/saude/pt-br/vacinacao/arquivos/
urls = {
    'grupo_gestante': 'https://www.gov.br/saude/pt-br/vacinacao/arquivos/calendario-nacional-de-vacinacao-gestante/',
    'grupo_crianca': 'https://www.gov.br/saude/pt-br/vacinacao/arquivos/calendario-nacional-de-vacinacao-crianca/',
    'grupo_jovens': 'https://www.gov.br/saude/pt-br/vacinacao/arquivos/calendario-nacional-de-vacinacao-adolescentes-jovens/',
    'grupo_adulto': 'https://www.gov.br/saude/pt-br/vacinacao/arquivos/calendario-nacional-de-vacinacao-adulto/',
    'grupo_idoso': 'https://www.gov.br/saude/pt-br/vacinacao/arquivos/calendario-nacional-de-vacinacao-idoso/',
}

