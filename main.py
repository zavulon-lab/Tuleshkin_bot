from bot_token import TOKEN
from bot import bot
from datetime import datetime

import logging


logging.basicConfig(level=logging.WARNING, filename=f'{datetime.today().strftime(f'%Y - %m - %d')}.log',
										filemode='w', format="%(asctime)s - %(levelname)s - %(message)s")

# Запуск бота
bot.run(TOKEN)