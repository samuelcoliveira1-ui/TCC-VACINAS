import telebot
import time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
from textwrap import dedent

from bot import (
    bot, user_data, mensagem_localizacao,
    reiniciar_menu_natural, pdf_cooldown, COOLDOWN_PDF,
    esperando_cidade, esperando_localizacao, esperando_procurar, esperando_data, grupos,
    anti_spam, delete_if_exists, save_msg_id, safe_edit, em_fluxo,
    menu, menu_principal, menu_calendario, menu_regioes,
    menu_cobertura, gerar_estados_pagina, volta_para
)
from core.engine import pega_vacina, procura_vacina, consultar_cobertura, resposta_ia, dia
from utils.helpers import urls
from data_handler.handler_ubs import proximas_ubs

IA_SAUDACAO_TEXTO = dedent('''\
🤖 Olá! Seja bem-vindo(a)!

Sou um assistente virtual especializado em informações sobre vacinação. Posso ajudar você a encontrar informações de forma rápida e prática.

🔎 O que eu posso fazer:

💉 Consultar vacinas recomendadas com base na idade informada.

📊 Verificar a cobertura vacinal por região, estado ou cidade.

🏥 Encontrar Unidades Básicas de Saúde (UBS) próximas à sua localização.

📝 Basta me enviar sua dúvida.

Como posso ajudar você hoje?''')


def _markup_voltar_ia():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton('⬅️ Voltar', callback_data='voltar_ia'))
    return markup


def _markup_voltar_menu():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton('⬅️ Voltar', callback_data='voltar_menu'))
    return markup


@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    data = user_data.setdefault(user_id, {})

    for key in ['menu_msg_id', 'warning_msg_id', 'pdf_msg_id', 'search_msg_id']:
        delete_if_exists(chat_id, user_id, key)

    data['ultimo_menu'] = datetime.now()
    menu(chat_id, user_id)


def handle_cidade(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    estado = esperando_cidade.get(chat_id)
    if not estado or not isinstance(estado, dict):
        return

    uf = estado["uf"]
    cidade = message.text.strip()
    esperando_cidade.pop(chat_id, None)

    resposta = consultar_cobertura(cidade, uf=uf)

    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("⬅️ Voltar", callback_data="cob_estado"))

    data = user_data.setdefault(user_id, {})
    data['fluxo_cidade'] = True
    delete_if_exists(chat_id, user_id, 'menu_msg_id')

    msg = bot.send_message(chat_id, resposta, reply_markup=markup, parse_mode='HTML')
    data['menu_msg_id'] = msg.message_id


@bot.message_handler(content_types=['location'])
def handle_localizacao(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if chat_id not in esperando_localizacao:
        return

    esperando_localizacao.discard(chat_id)
    
    try:
        msg_rm = bot.send_message(chat_id, "Buscando...", reply_markup=telebot.types.ReplyKeyboardRemove())
        bot.delete_message(chat_id, msg_rm.message_id)
    except:
        pass

    try:
        bot.delete_message(chat_id, message.message_id)
    except:
        pass

    resposta = proximas_ubs(message.location.latitude, message.location.longitude)

    try:
        bot.delete_message(chat_id, message.message_id)
    except:
        pass

    if resposta is None:
        esperando_localizacao.add(chat_id)
        markup = InlineKeyboardMarkup()
        err_msg = bot.send_message(chat_id, "📍 Localização inválida. Envie uma localização dentro do Brasil.", reply_markup=markup)
        data = user_data.setdefault(user_id, {})
        data['localizacao_erro_msg_id'] = err_msg.message_id
        return

    data = user_data.setdefault(user_id, {})
    delete_if_exists(chat_id, user_id, 'localizacao_erro_msg_id')

    try:
        msg_rm = bot.send_message(chat_id, "Buscando...", reply_markup=telebot.types.ReplyKeyboardRemove())
        bot.delete_message(chat_id, msg_rm.message_id)
    except:
        pass

    try:
        bot.delete_message(chat_id, mensagem_localizacao.get(chat_id))
    except:
        pass

    delete_if_exists(chat_id, user_id, 'ubs_msg_id')

    veio_da_ia = data.get('mode', False) and data.get('ia_origem_ubs', False)
    voltar_callback = 'voltar_ia_ubs' if veio_da_ia else 'voltar_menu'

    inline_markup = InlineKeyboardMarkup()
    inline_markup.row(InlineKeyboardButton("⬅️ Voltar", callback_data=voltar_callback))
    inline_markup.row(InlineKeyboardButton("🔄 Buscar novamente", callback_data="localizar"))

    menu_msg_id = data.get('menu_msg_id')
    if menu_msg_id:
        try:
            bot.delete_message(chat_id, menu_msg_id)
        except:
            pass

    msg = bot.send_message(chat_id, resposta, reply_markup=inline_markup, parse_mode="HTML")
    data['ubs_msg_id'] = msg.message_id
    data['menu_msg_id'] = None


def handle_cep(chat_id, cep, user_id=None):
    from data_handler.handler_ubs import cep_para_coords

    esperando_localizacao.discard(chat_id)

    try:
        msg_rm = bot.send_message(chat_id, "Buscando...", reply_markup=telebot.types.ReplyKeyboardRemove())
        bot.delete_message(chat_id, msg_rm.message_id)
    except:
        pass

    try:
        bot.delete_message(chat_id, mensagem_localizacao.get(chat_id))
    except:
        pass

    coords = cep_para_coords(cep)

    markup_invalido = None

    if not coords:
        err_msg = bot.send_message(chat_id, "📍 Localização inválida. Envie novamente.", reply_markup=markup_invalido)
        if user_id is not None:
            user_data.setdefault(user_id, {})['localizacao_erro_msg_id'] = err_msg.message_id
        esperando_localizacao.add(chat_id)
        return

    resposta = proximas_ubs(coords[0], coords[1])

    if resposta is None:
        err_msg = bot.send_message(chat_id, "📍 Localização inválida. Envie novamente.", reply_markup=markup_invalido)
        if user_id is not None:
            user_data.setdefault(user_id, {})['localizacao_erro_msg_id'] = err_msg.message_id
        esperando_localizacao.add(chat_id)
        return

    if user_id is not None:
        data = user_data.setdefault(user_id, {})
        veio_da_ia = data.get('mode', False) and data.get('ia_origem_ubs', False)
        voltar_callback = 'voltar_ia_ubs' if veio_da_ia else 'voltar_menu'
    else:
        voltar_callback = 'voltar_menu'

    inline_markup = InlineKeyboardMarkup()
    inline_markup.row(InlineKeyboardButton("⬅️ Voltar", callback_data=voltar_callback))
    inline_markup.row(InlineKeyboardButton("🔄 Buscar novamente", callback_data="localizar"))

    if user_id is not None:
        data = user_data.setdefault(user_id, {})
        delete_if_exists(chat_id, user_id, 'localizacao_erro_msg_id')
        delete_if_exists(chat_id, user_id, 'ubs_msg_id')
        menu_msg_id = data.get('menu_msg_id')
        if menu_msg_id:
            try:
                bot.delete_message(chat_id, menu_msg_id)
            except:
                pass
        msg = bot.send_message(chat_id, resposta, reply_markup=inline_markup, parse_mode="HTML")
        data['ubs_msg_id'] = msg.message_id
        data['menu_msg_id'] = None
    else:
        bot.send_message(chat_id, resposta, reply_markup=inline_markup, parse_mode="HTML")


def handle_procurar_input(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    data = user_data.setdefault(user_id, {})

    esperando_procurar.discard(chat_id)

    termo = message.text.strip().lower()
    resposta = procura_vacina(termo)

    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton('⬅️ Voltar', callback_data='voltar_procurar'))

    delete_if_exists(chat_id, user_id, 'menu_msg_id')

    msg = bot.send_message(chat_id, resposta, reply_markup=markup, parse_mode='HTML')
    data['procurar_resultado_msg_id'] = msg.message_id


def handle_data_nasc_input(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    data = user_data.setdefault(user_id, {})

    esperando_data.discard(chat_id)

    prompt_msg_id = data.pop('data_nasc_prompt_msg_id', None)
    if prompt_msg_id:
        try:
            bot.delete_message(chat_id, prompt_msg_id)
        except:
            pass

    resultado_raw = dia(message.text.strip())
    resultado = resultado_raw[0] if isinstance(resultado_raw, tuple) else resultado_raw

    if isinstance(resultado, Exception) or not resultado:
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton('⬅️ Voltar', callback_data='calendario_vacinal'))
        msg = bot.send_message(chat_id, '❌ Data inválida. Use o formato DD/MM/AAAA.', reply_markup=markup)
        data['data_nasc_prompt_msg_id'] = msg.message_id
        esperando_data.add(chat_id)
        return

    mapa_grupo = {
        'Gestante': 'grupo_gestante',
        'Criança': 'grupo_crianca',
        'Adolescente': 'grupo_jovens',
        'Adulto': 'grupo_adulto',
        'Idoso': 'grupo_idoso',
    }

    grupo_pdf = None
    texto = message.text.strip()
    try:
        dia_n, mes_n, ano_n = map(int, texto.split('/'))
        from datetime import date
        nasc = date(ano_n, mes_n, dia_n)
        atual = date.today()
        if atual.year == nasc.year:
            anos = 0
        else:
            anos = atual.year - nasc.year
            if not (nasc.month, nasc.day) <= (atual.month, atual.day):
                anos -= 1

        if anos >= 60:
            grupo_pdf = 'grupo_idoso'
        elif 25 <= anos <= 29:
            grupo_pdf = 'grupo_adulto'
        elif 10 <= anos <= 24:
            grupo_pdf = 'grupo_jovens'
        else:
            grupo_pdf = 'grupo_crianca'
    except:
        grupo_pdf = None

    markup = InlineKeyboardMarkup()
    if grupo_pdf:
        markup.row(InlineKeyboardButton('📄 Ver ou Baixar PDF', callback_data=f'baixar_pdf_{grupo_pdf}'))
    markup.row(InlineKeyboardButton('⬅️ Voltar', callback_data='voltar_calendario'))

    delete_if_exists(chat_id, user_id, 'pdf_msg_id')
    msg = bot.send_message(chat_id, resultado, reply_markup=markup, parse_mode='HTML')
    data['menu_msg_id'] = msg.message_id
    data['data_nasc_resultado'] = message.text.strip()


@bot.message_handler(func=lambda m: m.text and not m.text.startswith('/'))
def start_natural(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    agora = datetime.now()

    if chat_id in esperando_localizacao and message.text.strip().isdigit():
        handle_cep(chat_id, message.text.strip(), user_id=user_id)
        return

    if esperando_cidade.get(chat_id):
        handle_cidade(message)
        return

    if chat_id in esperando_procurar:
        handle_procurar_input(message)
        return

    if chat_id in esperando_data:
        handle_data_nasc_input(message)
        return

    data = user_data.setdefault(user_id, {})
    ultimo_menu = data.get('ultimo_menu')

    if data.get('mode', False):
        resposta = resposta_ia(message.text)

        for key in ('ia_saudacao_msg_id', 'ia_resposta_msg_id'):
            delete_if_exists(chat_id, user_id, key)

        if resposta == '__LOCALIZAR__':
            data['ia_origem_ubs'] = True
            esperando_localizacao.add(chat_id)
            reply_markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, input_field_placeholder="Ou digite seu CEP...")
            reply_markup.add(telebot.types.KeyboardButton("📍 Enviar minha localização", request_location=True))
            inline_markup = InlineKeyboardMarkup()
            inline_markup.row(InlineKeyboardButton("⬅️ Voltar", callback_data="voltar_ia"))
            texto_localizar = "Clique no botão para enviar sua localização (ative o GPS e permita acesso à localização) ou informe um CEP (somente números)"
            msg_loc = bot.send_message(chat_id, texto_localizar, reply_markup=inline_markup, parse_mode='HTML')
            data['menu_msg_id'] = msg_loc.message_id
            msg = bot.send_message(chat_id, "Aguardando resposta...", reply_markup=reply_markup)
            mensagem_localizacao[chat_id] = msg.message_id
            return

        if isinstance(resposta, tuple):
            texto_vacina, grupo_pdf = resposta
            if not texto_vacina or not texto_vacina.strip():
                texto_vacina = 'Não encontrei informações para esse grupo.'
            markup = InlineKeyboardMarkup()
            if grupo_pdf:
                markup.row(InlineKeyboardButton('📄 Ver ou Baixar PDF', callback_data=f'baixar_pdf_{grupo_pdf}'))
            markup.row(InlineKeyboardButton('⬅️ Voltar', callback_data='voltar_ia'))
            delete_if_exists(chat_id, user_id, 'pdf_msg_id')
            msg = bot.send_message(chat_id, texto_vacina, reply_markup=markup, parse_mode='html')
            data['ia_resposta_msg_id'] = msg.message_id
            data['ia_grupo_pdf'] = grupo_pdf
            return

        markup = _markup_voltar_ia()
        resposta_texto = resposta[0] if isinstance(resposta, tuple) else resposta
        if not resposta_texto or not str(resposta_texto).strip():
            resposta_texto = 'Não encontrei informações para essa pergunta.'
        msg = bot.send_message(chat_id, resposta_texto, reply_markup=markup, parse_mode='html')
        data['ia_resposta_msg_id'] = msg.message_id
        data['ia_grupo_pdf'] = None
        return

    if ultimo_menu is None:
        data['ultimo_menu'] = agora
        menu(chat_id, user_id)
        return

    if (agora - ultimo_menu >= reiniciar_menu_natural) and not em_fluxo(chat_id):
        data['ultimo_menu'] = agora
        delete_if_exists(chat_id, user_id, 'pdf_msg_id')
        delete_if_exists(chat_id, user_id, 'search_msg_id')
        menu(chat_id, user_id)
    else:
        msg = bot.reply_to(message, 'Use: /start para exibir o menu novamente ou aguarde um minuto.')
        save_msg_id(user_id, 'search_msg_id', msg)


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    data = user_data.setdefault(user_id, {})

    if not anti_spam(user_id, call.data):
        return

    valid_ids = [
        data.get('menu_msg_id'), data.get('pdf_msg_id'), data.get('ubs_msg_id'),
        data.get('ia_resposta_msg_id'), data.get('ia_saudacao_msg_id'),
        data.get('search_msg_id'), data.get('procurar_resultado_msg_id'),
        data.get('data_nasc_prompt_msg_id')
    ]

    if call.message.message_id not in valid_ids:
        try:
            bot.answer_callback_query(call.id)
        except:
            pass
        return

    try:
        bot.answer_callback_query(call.id)
    except:
        pass

    def edita_mensagem(mensagem, grupo):
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton('📄 Ver ou Baixar PDF', callback_data=f'baixar_pdf_{grupo}'))
        markup.row(InlineKeyboardButton('⬅️ Voltar', callback_data='voltar_calendario'))
        safe_edit(pega_vacina(mensagem), chat_id, call.message.message_id, markup)

    # IA
    if call.data == 'assistente':
        data['mode'] = True
        data['ia_origem_ubs'] = False
        markup = _markup_voltar_menu()
        safe_edit(IA_SAUDACAO_TEXTO, chat_id, call.message.message_id, markup)
        data['ia_saudacao_msg_id'] = call.message.message_id
        data['menu_msg_id'] = call.message.message_id
        data['ia_resposta_msg_id'] = None
        return

    if call.data == 'voltar_ia':
        data['ia_resposta_msg_id'] = None
        data['ia_grupo_pdf'] = None
        delete_if_exists(chat_id, user_id, 'pdf_msg_id')
        markup = _markup_voltar_menu()
        safe_edit(IA_SAUDACAO_TEXTO, chat_id, call.message.message_id, markup)
        data['ia_saudacao_msg_id'] = call.message.message_id
        data['menu_msg_id'] = call.message.message_id
        esperando_localizacao.discard(chat_id)
        try:
            bot.delete_message(chat_id, mensagem_localizacao.get(chat_id))
            mensagem_localizacao.pop(chat_id, None)
        except:
            pass
        try:
            msg_rm = bot.send_message(chat_id, "\u200b", reply_markup=telebot.types.ReplyKeyboardRemove())
            bot.delete_message(chat_id, msg_rm.message_id)
        except:
            pass
        return

    if call.data == 'voltar_ia_ubs':
        data['ubs_msg_id'] = None
        data['ia_origem_ubs'] = False
        markup = _markup_voltar_menu()
        safe_edit(IA_SAUDACAO_TEXTO, chat_id, call.message.message_id, markup)
        data['ia_saudacao_msg_id'] = call.message.message_id
        data['menu_msg_id'] = call.message.message_id
        return

    # procura
    if call.data == 'procurar_vacina':
        esperando_procurar.add(chat_id)
        data['procurar_resultado'] = False
        markup = _markup_voltar_menu()
        safe_edit('Informe o nome da vacina:', chat_id, call.message.message_id, markup)
        data['menu_msg_id'] = call.message.message_id
        return

    if call.data == 'voltar_procurar':
        esperando_procurar.add(chat_id)
        data['procurar_resultado'] = False
        markup = _markup_voltar_menu()
        safe_edit('Informe o nome da vacina:', chat_id, call.message.message_id, markup)
        data['menu_msg_id'] = call.message.message_id
        data['procurar_resultado_msg_id'] = None
        return

    if call.data == 'data_nasc':
        esperando_data.add(chat_id)
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton('⬅️ Voltar', callback_data='calendario_vacinal'))
        safe_edit('Informe uma data de nascimento:', chat_id, call.message.message_id, markup)
        data['data_nasc_prompt_msg_id'] = call.message.message_id
        data['menu_msg_id'] = call.message.message_id
        return

    # calendário
    if call.data == 'calendario_vacinal':
        safe_edit('Escolha o grupo/faixa etária ou informe uma data de nascimento:', chat_id, call.message.message_id, menu_calendario())

    elif call.data.startswith('baixar_pdf_'):
        now = time.time()

        if data.get('pdf_msg_id'):
            bot.answer_callback_query(call.id, "📄 O PDF já está aberto")
            return

        if user_id in pdf_cooldown and now - pdf_cooldown[user_id] < COOLDOWN_PDF:
            bot.answer_callback_query(call.id, '⏳ Aguarde um pouco antes de baixar novamente')
            return

        pdf_cooldown[user_id] = now
        grupo = call.data.replace('baixar_pdf_', '')
        url = urls.get(grupo)

        if not url:
            bot.answer_callback_query(call.id, 'PDF não encontrado')
            return

        delete_if_exists(chat_id, user_id, 'pdf_msg_id')
        msg_pdf = bot.send_message(
            chat_id,
            f'📄 Calendário de vacinação - {grupo.replace("grupo_", "").capitalize()}\n\n'
            f'🔗 <a href="{url}">Abrir documento oficial (PDF)</a>\n\n',
            parse_mode='HTML'
        )
        data['pdf_msg_id'] = msg_pdf.message_id

    # cobertura
    elif call.data == 'cobertura':
        data['fluxo_cidade'] = False
        esperando_cidade.pop(chat_id, None)
        safe_edit("Como você deseja ver a cobertura?", chat_id, call.message.message_id, menu_cobertura())

    elif call.data == 'cob_regiao':
        safe_edit("Escolha a região:", chat_id, call.message.message_id, menu_regioes())

    elif call.data.startswith('regiao_'):
        regiao = call.data.replace('regiao_', '')
        texto = consultar_cobertura(regiao)
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton('⬅️ Voltar', callback_data='cob_regiao'))
        try:
            bot.edit_message_text(texto, chat_id, call.message.message_id, reply_markup=markup, parse_mode='HTML')
        except:
            bot.send_message(chat_id, texto, reply_markup=markup, parse_mode='HTML')

    elif call.data == 'cob_estado':
        if data.get('fluxo_cidade'):
            esperando_cidade[chat_id] = True
        else:
            esperando_cidade.pop(chat_id, None)
        safe_edit("Escolha o estado:", chat_id, call.message.message_id, gerar_estados_pagina(0))

    elif call.data.startswith("estado_page_"):
        pagina = int(call.data.replace("estado_page_", ""))
        safe_edit("Escolha o estado:", chat_id, call.message.message_id, gerar_estados_pagina(pagina))

    elif call.data == 'cob_cidade':
        esperando_cidade[chat_id] = True
        safe_edit("Escolha o estado:", chat_id, call.message.message_id, gerar_estados_pagina(0))

    elif call.data.startswith("estado_"):
        uf = call.data.replace("estado_", "")

        if esperando_cidade.get(chat_id):
            origem = esperando_cidade[chat_id].get("origem", "cobertura") if isinstance(esperando_cidade[chat_id], dict) else "cobertura"
            esperando_cidade[chat_id] = {"uf": uf, "origem": origem}
            markup = InlineKeyboardMarkup()
            markup.row(InlineKeyboardButton("⬅️ Voltar", callback_data="cob_estado"))
            safe_edit(f"Informe o nome da cidade ({uf}):", chat_id, call.message.message_id, markup)
            return

        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("⬅️ Voltar", callback_data="cob_estado"))
        safe_edit(consultar_cobertura(uf), chat_id, call.message.message_id, markup)

    # ubs
    elif call.data == 'localizar':
        esperando_localizacao.add(chat_id)
        delete_if_exists(chat_id, user_id, 'ubs_msg_id')

        if not data.get('mode', False):
            data['ia_origem_ubs'] = False

        reply_markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, input_field_placeholder="Ou digite seu CEP...")
        reply_markup.add(telebot.types.KeyboardButton("📍 Enviar minha localização", request_location=True))

        inline_markup = InlineKeyboardMarkup()
        inline_markup.row(InlineKeyboardButton("⬅️ Voltar", callback_data="voltar_menu"))

        texto_localizar = "Clique no botão para enviar sua localização (ative o GPS e permita acesso à localização) ou informe um CEP (somente números)"

        try:
            bot.edit_message_text(texto_localizar, chat_id, call.message.message_id, reply_markup=inline_markup, parse_mode='HTML')
            data['menu_msg_id'] = call.message.message_id
        except:
            msg_localizar = bot.send_message(chat_id, texto_localizar, reply_markup=inline_markup, parse_mode='HTML')
            data['menu_msg_id'] = msg_localizar.message_id

        msg = bot.send_message(chat_id, "Aguardando resposta...", reply_markup=reply_markup)
        mensagem_localizacao[chat_id] = msg.message_id

    # saiba mais
    elif call.data == 'fontes':
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton('⬅️ Voltar', callback_data='voltar_menu'))
        safe_edit(
            'ℹ️ <b>Fontes oficiais do sistema</b>\n\n'
            '📄 <b>Calendários de Vacinação (PDFs)</b>\n\u200B \n'
            'https://www.gov.br/saude/pt-br/vacinacao/arquivos/\n\n'
            '📊 <b>Dados da Cobertura Vacinal</b>\n\u200B \n'
            '<b>Cobertura Geral</b>\n\u200B \n'
            'https://infoms.saude.gov.br/extensions/SEIDIGI_DEMAS_VACINACAO_CALENDARIO_NACIONAL_COBERTURA_RESIDENCIA/SEIDIGI_DEMAS_VACINACAO_CALENDARIO_NACIONAL_COBERTURA_RESIDENCIA.html\n\n'
            '<b>Cobertura COVID-19</b>\n\u200B \n'
            'https://infoms.saude.gov.br/extensions/SEIDIGI_DEMAS_COBERTURA_COVID_RESIDENCIA/SEIDIGI_DEMAS_COBERTURA_COVID_RESIDENCIA.html#\n\n'
            '📍 <b>Base de Dados das UBSs</b>\n\u200B \n'
            '<b>Cobertura Geral</b>\n\u200B \n'
            'https://dadosabertos.saude.gov.br/dataset/unidades-basicas-de-saude-ubs/resource/264326aa-6aa2-4bc9-8dad-21f9aebe5e66\n\n'
            '👨\u200d💻 <b>Sobre o Bot</b>\n\u200B \n'
            '<b>Assistente virtual para Telegram que informa vacinas recomendadas com base na faixa etária.</b>\n\n'
            'Projeto desenvolvido durante o 1º semestre de 2026 por estudantes do curso de Análise e Desenvolvimento de Sistemas da FATEC São José dos Campos.\n\n'
            '👥 <b>Equipe</b>\n\u200B \n'
            '• Nicolas Fonseca Meira — Scrum Master\n'
            '• Miguel Silva Gomes — Product Owner\n'
            '• Gabriel Yudi Fujimoto — Scrum Team\n',
            chat_id,
            call.message.message_id,
            markup
        )

    elif call.data == 'voltar_menu':
        if data.get('ubs_msg_id') == call.message.message_id:
            data['ubs_msg_id'] = None
            data['menu_msg_id'] = call.message.message_id
        data['fluxo_cidade'] = False
        data['ia_saudacao_msg_id'] = None
        data['ia_resposta_msg_id'] = None
        data['ia_origem_ubs'] = False
        data['procurar_resultado'] = False
        esperando_cidade.pop(chat_id, None)
        esperando_localizacao.discard(chat_id)
        esperando_procurar.discard(chat_id)
        esperando_data.discard(chat_id)

        try:
            msg_rm = bot.send_message(chat_id, "\u200b", reply_markup=telebot.types.ReplyKeyboardRemove())
            bot.delete_message(chat_id, msg_rm.message_id)
        except:
            pass

        try:
            bot.delete_message(chat_id, mensagem_localizacao.get(chat_id))
            mensagem_localizacao.pop(chat_id, None)
        except:
            pass

        volta_para(call, 'menu_principal')
        data['mode'] = False

    elif call.data == 'voltar_calendario':
        esperando_data.discard(chat_id)
        volta_para(call, 'calendario_vacinal')
        delete_if_exists(chat_id, user_id, 'pdf_msg_id')

    elif call.data == 'voltar_cobertura':
        volta_para(call, 'cobertura')

    elif call.data in grupos:
        edita_mensagem(grupos[call.data], call.data)


    bot.answer_callback_query(call.id)
