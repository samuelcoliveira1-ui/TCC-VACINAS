import bot as _bot
import handlers

from data_handler.scraping_ubs import garantir_ubs
from data_handler.scraping_calendario import precisa_update as cal_update
from data_handler.scraping_cobertura import precisa_update as cob_update

if __name__ == '__main__':
    garantir_ubs()
    cal_update()
    cob_update()

    _bot.bot.polling()