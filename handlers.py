from constants import *
from bot import bot
from discord.ui import View
from constructor import ChannelSelect, ThreadSelectView, FormModal
from json_func import threads
from constructor import MainChannelButtons, ApplicationChannelButtons
from discord import Interaction, Object, app_commands, Thread


# Функция для проверки роли
def has_allowed_role(interaction: Interaction) -> bool:
		"""Проверяет, есть ли у пользователя роль, позволяющая создавать ветки."""
		return any(role.id == ALLOWED_ROLE_ID for role in interaction.user.roles)


# Отправка сообщения с кнопкой для подачи заявки
@bot.event
async def on_ready():
		print(f"Бот {bot.user} запущен!")
		await bot.tree.sync(guild=Object(id=GUILD_ID))  # Синхронизация команд

		# Отправляем сообщение с кнопками в основной канал
		main_channel = bot.get_channel(MAIN_CHANNEL_ID)
		if main_channel:
				await main_channel.send("Выберите действие:", view=MainChannelButtons())

		# Отправляем сообщение с кнопкой для подачи заявки в другой канал
		application_channel = bot.get_channel(APPLICATION_CHANNEL_ID)
		if application_channel:
				await application_channel.send("Нажмите кнопку, чтобы подать заявку:", view=ApplicationChannelButtons())

@bot.tree.command(name="создать_ветку", description="Создать ветку для откатов", guild=Object(id=GUILD_ID))
@app_commands.check(has_allowed_role)  # Проверка роли
async def create_thread(interaction: Interaction):
		"""Создает ветку в выбранном канале."""
		# Отправляем выпадающее меню для выбора канала
		view = View()
		view.add_item(ChannelSelect())
		await interaction.response.send_message(
				"Выберите канал для создания ветки:", view=view, ephemeral=True
		)
		
@create_thread.error
async def create_thread_error(interaction: Interaction, error: app_commands.AppCommandError):
		# Обработка ошибки, если у пользователя нет нужной роли
		if isinstance(error, app_commands.CheckFailure):
				await interaction.response.send_message(
						"❌ У вас нет прав на создание веток!", ephemeral=True
				)

@bot.tree.command(name="отправить_откат", description="Отправить откат в ветку", guild=Object(id=GUILD_ID))
async def send_rollback(interaction: Interaction):
    """Отправляет откат в выбранную ветку из двух каналов."""
    try:
        # Откладываем ответ, чтобы предотвратить истечение взаимодействия
        await interaction.response.defer(ephemeral=True)

        # Получаем оба канала
        channel_1 = interaction.guild.get_channel(CHANNEL_1_ID)
        channel_2 = interaction.guild.get_channel(CHANNEL_2_ID)

        if not channel_1 or not channel_2:
            await interaction.followup.send("❌ Один из каналов не найден!", ephemeral=True)
            return

        # Получаем активные ветки из канала 1 и сортируем их по дате создания
        threads_channel_1 = sorted(
            [thread for thread in channel_1.threads if not thread.archived],
            key=lambda x: x.created_at,  # Сортировка по дате создания
            reverse=True  # Сначала самые новые
        )

        # Получаем активные ветки из канала 2 и сортируем их по дате создания
        threads_channel_2 = sorted(
            [thread for thread in channel_2.threads if not thread.archived],
            key=lambda x: x.created_at,  # Сортировка по дате создания
            reverse=True  # Сначала самые новые
        )

        # Проверяем, есть ли активные ветки в каналах
        if not threads_channel_1 and not threads_channel_2:
            await interaction.followup.send("❌ Нет активных веток в указанных каналах!", ephemeral=True)
            return

        # Отправляем сообщение с выпадающими списками
        view = ThreadSelectView(threads_channel_1, threads_channel_2)
        await interaction.followup.send("Выберите ветку для отправки отката:", view=view, ephemeral=True)

    except Exception as e:
        print(f"Ошибка: {e}")
        await interaction.followup.send("❌ Произошла ошибка при обработке вашего запроса.", ephemeral=True)

@bot.event
async def on_thread_delete(thread: Thread):
		"""Удаляет ветку из списка при её удалении вручную."""
		if thread.id in threads:
				del threads[thread.id]

@bot.tree.command(name="заявка1", description="Заполнить заявку на вступление в семью", guild=Object(id=GUILD_ID))
async def application(interaction: Interaction):
		"""Отправляет модальное окно с формой заявки."""
		await interaction.response.send_modal(FormModal())

@bot.tree.command(name="sync", description="Синхронизировать команды", guild=Object(id=GUILD_ID))
async def sync(interaction: Interaction):
		await bot.tree.sync(guild=Object(id=GUILD_ID))
		await interaction.response.send_message("Команды синхронизированы!", ephemeral=True)
