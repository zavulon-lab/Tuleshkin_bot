from constants import *
from constructor import MainChannelButtons, ApplicationChannelButtons
from discord import Intents, Client, app_commands, Object


intents = Intents.default()
intents.message_content = True

# Инициализация бота с командным деревом
class MyBot(Client):
		def __init__(self):
				super().__init__(intents=intents)
				self.tree = app_commands.CommandTree(self)  # Инициализация CommandTree

		async def on_ready(self):
				print(f"Бот {self.user} запущен!")
				await self.tree.sync(guild=Object(id=GUILD_ID))  # Синхронизация команд

				# Отправляем сообщение с кнопками в основной канал
				main_channel = self.get_channel(MAIN_CHANNEL_ID)
				if main_channel:
						await main_channel.send("Выберите действие:", view=MainChannelButtons())

				# Отправляем сообщение с кнопкой для подачи заявки в другой канал
				application_channel = self.get_channel(APPLICATION_CHANNEL_ID)
				if application_channel:
						await application_channel.send("Нажмите кнопку, чтобы подать заявку:", view=ApplicationChannelButtons())

# Создаем экземпляр бота
bot = MyBot()