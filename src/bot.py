import telebot
import time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import timedelta

TOKEN = "SEU_TOKEN_AQUI"
bot = telebot.TeleBot(TOKEN)

user_data = {}
ultimo_clique = {}
mensagem_localizacao = {}
reiniciar_menu_natural = timedelta(minutes=1)
pdf_cooldown = {}
COOLDOWN_PDF = 5

esperando_cidade = {}
esperando_localizacao = set()
esperando_procurar = set()
esperando_data = set()

grupos = {
    'grupo_gestante': 'Gestante',
    'grupo_crianca': 'Criança',
    'grupo_jovens': 'Adolescente',
    'grupo_adulto': 'Adulto',
    'grupo_idoso': 'Idoso'
}

estados = [
    "SP","MG","RJ","BA","PR","RS","PE","CE","PA","SC","GO","MA","AM","PB",
    "ES","MT","RN","PI","AL","DF","MS","SE","RO","TO","AC","AP","RR"
]

estados_por_pagina = 9


# utils

def anti_spam(user_id, action, cooldown=0.8):
    key = f'{user_id}:{action}'
    now = time.time()
    if key in ultimo_clique and now - ultimo_clique[key] < cooldown:
        return False
    ultimo_clique[key] = now
    return True


def delete_if_exists(chat_id, user_id, key):
    data = user_data.get(user_id, {})
    if not data:
        return
    msg_id = data.get(key)
    if not msg_id:
        return
    try:
        bot.delete_message(chat_id, msg_id)
    except telebot.apihelper.ApiTelegramException:
        pass
    data[key] = None


def save_msg_id(user_id, key, msg):
    user_data.setdefault(user_id, {})[key] = msg.message_id


def safe_edit(text, chat_id, message_id, markup=None):
    try:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode='HTML')
    except telebot.apihelper.ApiTelegramException:
        pass


def em_fluxo(chat_id):
    return chat_id in esperando_localizacao or esperando_cidade.get(chat_id) or chat_id in esperando_procurar or chat_id in esperando_data


# menu principal

def menu_principal():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton('Calendário Vacinal 📅', callback_data='calendario_vacinal'),
        InlineKeyboardButton('Cobertura 📊', callback_data='cobertura')
    )
    markup.row(
        InlineKeyboardButton('IA (experimental) 🤖', callback_data='assistente'),
        InlineKeyboardButton('Localizar 📍', callback_data='localizar')
    )
    markup.row(
        InlineKeyboardButton('Procurar 🔎', callback_data='procurar_vacina'),
        InlineKeyboardButton('Saiba Mais ℹ️', callback_data='fontes')
    )
    return markup


def menu_regioes():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton('Sudeste', callback_data='regiao_Sudeste'),
        InlineKeyboardButton('Nordeste', callback_data='regiao_Nordeste')
    )
    markup.row(
        InlineKeyboardButton('Sul', callback_data='regiao_Sul'),
        InlineKeyboardButton('Norte', callback_data='regiao_Norte')
    )
    markup.row(InlineKeyboardButton('Centro-Oeste', callback_data='regiao_Centro-Oeste'))
    markup.row(InlineKeyboardButton('⬅️ Voltar', callback_data='cobertura'))
    return markup


def menu_calendario():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton('Gestante 🤰', callback_data='grupo_gestante'),
        InlineKeyboardButton('Criança 👶', callback_data='grupo_crianca'),
        InlineKeyboardButton('Jovens 🧑', callback_data='grupo_jovens')
    )
    markup.row(
        InlineKeyboardButton('Adulto 🧑‍💼', callback_data='grupo_adulto'),
        InlineKeyboardButton('Idoso 👴', callback_data='grupo_idoso')
    )
    markup.row(InlineKeyboardButton('📅 Informar data', callback_data='data_nasc'))
    markup.row(InlineKeyboardButton('⬅️ Voltar', callback_data='voltar_menu'))
    return markup


def menu_cobertura():
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("Região 🌎", callback_data="cob_regiao"),
        InlineKeyboardButton("Estado 🗺️", callback_data="cob_estado")
    )
    markup.row(InlineKeyboardButton("Cidade 🏙️", callback_data="cob_cidade"))
    markup.row(InlineKeyboardButton("⬅️ Voltar", callback_data="voltar_menu"))
    return markup


def gerar_estados_pagina(pagina):
    start = pagina * estados_por_pagina
    end = start + estados_por_pagina

    markup = InlineKeyboardMarkup(row_width=3)
    markup.add(*[InlineKeyboardButton(uf, callback_data=f"estado_{uf}") for uf in estados[start:end]])

    if pagina == 0:
        if end < len(estados):
            markup.row(InlineKeyboardButton("➡️ Próximo", callback_data=f"estado_page_{pagina+1}"))
        markup.row(InlineKeyboardButton("⬅️ Voltar", callback_data="cobertura"))
    else:
        nav = [InlineKeyboardButton("⬅️ Anterior", callback_data=f"estado_page_{pagina-1}")]
        if end < len(estados):
            nav.append(InlineKeyboardButton("➡️ Próximo", callback_data=f"estado_page_{pagina+1}"))
        markup.row(*nav)

    return markup


def menu(chat_id, user_id):
    data = user_data.setdefault(user_id, {})
    old_msg_id = data.get('menu_msg_id')
    if old_msg_id:
        try:
            bot.delete_message(chat_id, old_msg_id)
        except telebot.apihelper.ApiTelegramException:
            pass
    old_warning = data.get('warning_msg_id')
    if old_warning:
        try:
            bot.delete_message(chat_id, old_warning)
        except telebot.apihelper.ApiTelegramException:
            pass
    msg = bot.send_message(chat_id, '<b>Bem-vindo(a) ao Vacina Brasil Bot 💉🇧🇷</b>\n<b>O que deseja consultar hoje?</b>\n\n<b>⚠️ ATENÇÃO:</b> este bot oferece apenas informações gerais e NÃO substitui a consulta a um profissional de saúde.', parse_mode='HTML', reply_markup=menu_principal())
    data['menu_msg_id'] = msg.message_id


def volta_para(call, destino):
    if destino == 'cobertura':
        safe_edit('Como você deseja ver a cobertura?', call.message.chat.id, call.message.message_id, menu_cobertura())
        return

    menus = {
        'menu_principal': ('<b>Bem-vindo(a) ao Vacina Brasil Bot 💉🇧🇷</b>\n<b>O que deseja consultar hoje?</b>\n\n<b>⚠️ ATENÇÃO:</b> este bot oferece apenas informações gerais e NÃO substitui a consulta a um profissional de saúde.', menu_principal),
        'calendario_vacinal': ('Escolha a faixa etária:', menu_calendario),
    }

    if destino in menus:
        texto, menu_func = menus[destino]
        safe_edit(texto, call.message.chat.id, call.message.message_id, menu_func())
