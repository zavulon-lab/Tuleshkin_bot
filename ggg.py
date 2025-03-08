import discord
from discord import app_commands
from discord.ui import Select, View, Button
from discord.utils import get
import json
import os

# Функция для загрузки данных из JSON
def load_private_threads():
    if os.path.exists("private_threads.json"):
        with open("private_threads.json", "r") as file:
            return json.load(file)
    return {}  # Возвращаем пустой словарь, если файл не существует

# Функция для сохранения данных в JSON
def save_private_threads(data):
    with open("private_threads.json", "w") as file:
        json.dump(data, file, indent=4)

# Загружаем данные при запуске бота
private_threads = load_private_threads()

TOKEN = "MTMyMjMzODAxNzMyNjY2NTgzMw.G7n99D.bJD9MrAgqmbXLK768hGrcemItbfIA3TjI0NzKU"  # Замените на ваш токен
GUILD_ID = 1086923253362200586  # ID вашего сервера
CHANNEL_1_ID = 1346610156108251167  # ID первого канала
CHANNEL_2_ID = 1346610194825871390  # ID второго канала
PRIVATE_CHANNEL_ID = 1346910336548339792  # ID третьего канала для приватных веток
ALLOWED_ROLE_ID = 1086923253378986038  # ID роли, которая может создавать ветки
PRIVATE_THREAD_ROLE_ID = 1086923253378986038  # ID роли, которая может видеть приватные ветки
MAIN_CHANNEL_ID = 1346610946067529748  # ID основного канала, где будут кнопки
CATEGORY_ID = 1347908794595934240  # ID категории, где будут создаваться каналы
ROLE_ID = 1086923253378986038  # ID роли, которая будет видеть каналы
APPLICATION_CHANNEL_ID = 1347694649426575492  # ID канала для заявок

intents = discord.Intents.default()
intents.message_content = True

# Инициализация бота с командным деревом
class MyBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)  # Инициализация CommandTree

    async def on_ready(self):
        print(f"Бот {self.user} запущен!")
        await self.tree.sync(guild=discord.Object(id=GUILD_ID))  # Синхронизация команд

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

# Словарь для хранения созданных веток (ключ: ID ветки, значение: {"thread": объект ветки, "creator": создатель})
threads = {}

# Функция для проверки роли
def has_allowed_role(interaction: discord.Interaction) -> bool:
    """Проверяет, есть ли у пользователя роль, позволяющая создавать ветки."""
    return any(role.id == ALLOWED_ROLE_ID for role in interaction.user.roles)

class RollbackForm(discord.ui.Modal, title="Отправить откат"):
    def __init__(self, thread: discord.Thread):
        super().__init__()
        self.thread = thread  # Сохраняем объект выбранной ветки

    player_name = discord.ui.TextInput(label="Ваше имя", required=True)
    rollback_details = discord.ui.TextInput(
        label="Описание отката",
        style=discord.TextStyle.paragraph,
        required=True,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)  # Предотвращаем ошибку устаревшего взаимодействия

        try:
            # Форматируем сообщение с упоминанием отправителя отката
            formatted_message = (
                f"{self.rollback_details.value}\n\n"
                f"Отправитель: {interaction.user.mention}"
            )

            # Отправляем сообщение в выбранную ветку
            await self.thread.send(formatted_message)

            # Получаем или создаем приватную ветку для пользователя
            private_channel = interaction.guild.get_channel(PRIVATE_CHANNEL_ID)
            if not private_channel:
                await interaction.followup.send("❌ Канал для приватных веток не найден!", ephemeral=True)
                return

            # Проверяем, есть ли уже приватная ветка для пользователя
            if str(interaction.user.id) in private_threads:
                # Получаем существующую ветку
                thread_id = private_threads[str(interaction.user.id)]
                private_thread = interaction.guild.get_thread(thread_id)
                if not private_thread:
                    # Если ветка не найдена, создаем новую
                    private_thread = await private_channel.create_thread(
                        name=f"Личное дело {interaction.user.name}",
                        type=discord.ChannelType.private_thread,
                    )
                    # Обновляем данные в словаре и JSON
                    private_threads[str(interaction.user.id)] = private_thread.id
                    save_private_threads(private_threads)
            else:
                # Создаем новую приватную ветку
                private_thread = await private_channel.create_thread(
                    name=f"Личное дело {interaction.user.name}",
                    type=discord.ChannelType.private_thread,
                )
                # Добавляем доступ к ветке для отправителя и определённой роли
                await private_thread.add_user(interaction.user)  # Добавляем пользователя
                role = interaction.guild.get_role(PRIVATE_THREAD_ROLE_ID)
                if role:
                    await private_thread.send(f"{role.mention}")  # Упоминание роли для доступа
                # Сохраняем ветку в словаре и JSON
                private_threads[str(interaction.user.id)] = private_thread.id
                save_private_threads(private_threads)

            # Дублируем сообщение в приватную ветку
            await private_thread.send(formatted_message)

            # Отправляем подтверждение пользователю
            await interaction.followup.send("✅ Ваш откат успешно отправлен и сохранён в вашей личной ветке!", ephemeral=True)

        except discord.errors.NotFound:
            print("Ошибка: Ветка не найдена или удалена.")
            await interaction.followup.send(
                "❌ Не удалось отправить откат. Ветка не найдена или была удалена.", ephemeral=True
            )

        except Exception as e:
            print(f"Ошибка: {e}")
            await interaction.followup.send(
                "❌ Произошла ошибка при обработке вашего запроса.", ephemeral=True
            )

# Модальное окно для заявки
class FormModal(discord.ui.Modal, title="Заявка на вступление в семью"):
    # Поля формы
    name = discord.ui.TextInput(label="Имя и возраст:", required=True)
    rp_experience = discord.ui.TextInput(
        label="Состоял в семьях/стаках:",
        required=True,
        style=discord.TextStyle.paragraph,
    )
    shooting = discord.ui.TextInput(
        label="Опыт игры и достижения:",
        required=True,
        style=discord.TextStyle.paragraph,
    )
    lvl_online = discord.ui.TextInput(
        label="Сервера с персонажами 2 уровня:",
        required=True,
    )
    family_experience = discord.ui.TextInput(
        label="Видеозаписи стрельбы:",
        required=True,
        style=discord.TextStyle.paragraph,
    )

    async def on_submit(self, interaction: discord.Interaction):
        """Обработка отправки формы."""
        try:
            # Получаем гильдию (сервер)
            guild = interaction.guild
            if not guild:
                await interaction.response.send_message("❌ Ошибка! Сервер не найден.", ephemeral=True)
                return

            # Получаем категорию, где будут создаваться каналы
            category = guild.get_channel(CATEGORY_ID)
            if not category or not isinstance(category, discord.CategoryChannel):
                await interaction.response.send_message("❌ Ошибка! Категория не найдена.", ephemeral=True)
                return

            # Создаем новый канал в категории
            channel_name = f"заявка-{self.name.value.lower().replace(' ', '-')}"
            new_channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                reason="Создание канала для новой заявки"
            )

            # Настраиваем права доступа для канала
            role = guild.get_role(ROLE_ID)
            if not role:
                await interaction.response.send_message("❌ Ошибка! Роль не найдена.", ephemeral=True)
                return

            # Запрещаем доступ всем, кроме роли и пользователя, который подал заявку
            await new_channel.set_permissions(guild.default_role, view_channel=False)
            await new_channel.set_permissions(role, view_channel=True)
            await new_channel.set_permissions(interaction.user, view_channel=True)  # Разрешаем доступ пользователю

            # Форматируем сообщение с заявкой
            formatted_message = (
                f"**Новая заявка на вступление!**\n\n"
                f"👤 **Имя и возраст:** {self.name.value}\n"
                f"🎮 **Состоял в семьях/стаках:** {self.rp_experience.value}\n"
                f"🔫 **Опыт игры и достижения:** {self.shooting.value}\n"
                f"⏳ **Сервера с персонажами 2 уровня:** {self.lvl_online.value}\n"
                f"🏠 **Видеозаписи стрельбы:** {self.family_experience.value}\n"
            )

            # Отправляем заявку в новый канал
            await new_channel.send(formatted_message)
            await interaction.response.send_message("✅ Ваша заявка отправлена!", ephemeral=True)

        except Exception as e:
            print(f"Ошибка при отправке заявки: {e}")
            await interaction.response.send_message("❌ Произошла ошибка при отправке заявки.", ephemeral=True)

class ChannelSelect(Select):
    def __init__(self):
        super().__init__(
            placeholder="Выберите канал для создания ветки",
            options=[
                discord.SelectOption(
                    label="Капт-архив",
                    value=str(CHANNEL_1_ID),  # ID первого канала
                ),
                discord.SelectOption(
                    label="Мкл-архив",
                    value=str(CHANNEL_2_ID),  # ID второго канала
                ),
            ],
        )

    async def callback(self, interaction: discord.Interaction):
        # Получаем выбранный канал
        selected_channel_id = int(self.values[0])
        selected_channel = interaction.guild.get_channel(selected_channel_id)

        if not selected_channel:
            await interaction.response.send_message(
                "❌ Канал не найден!", ephemeral=True
            )
            return

        # Отправляем модальное окно для ввода названия ветки
        await interaction.response.send_modal(CreateThreadModal(selected_channel))

class CreateThreadModal(discord.ui.Modal, title="Создать ветку"):
    def __init__(self, channel: discord.TextChannel):
        super().__init__()
        self.channel = channel  # Сохраняем выбранный канал

    thread_name = discord.ui.TextInput(label="Название ветки", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        # Создаем ветку в выбранном канале
        thread = await self.channel.create_thread(
            name=self.thread_name.value,
            type=discord.ChannelType.public_thread,
        )

        # Сохраняем ветку и создателя в словарь
        threads[thread.id] = {"thread": thread, "creator": interaction.user}

        await interaction.response.send_message(
            f"✅ Ветка '{self.thread_name.value}' создана в канале {self.channel.mention}!",
            ephemeral=True,
        )

class ThreadSelect(Select):
    def __init__(self, threads: list[discord.Thread]):
        options = [
            discord.SelectOption(
                label=f"{thread.parent.name if thread.parent else 'Unknown'} - {thread.name}",  # Показываем название канала и ветки
                value=str(thread.id),  # Используем ID ветки как значение
            )
            for thread in threads
        ]
        super().__init__(
            placeholder="Выберите ветку для отправки отката",
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        # Получаем выбранную ветку
        selected_thread_id = int(self.values[0])
        selected_thread = interaction.guild.get_thread(selected_thread_id)

        if not selected_thread:
            await interaction.response.send_message(
                "❌ Ветка не найдена!", ephemeral=True
            )
            return

        # Открываем модальное окно для ввода отката
        await interaction.response.send_modal(RollbackForm(selected_thread))

class ApplicationChannelButtons(View):
    def __init__(self):
        super().__init__(timeout=None)  # timeout=None делает кнопки активными всегда

    @discord.ui.button(label="📝Подать заявку", style=discord.ButtonStyle.primary)
    async def submit_application_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Обработчик кнопки для подачи заявки."""
        # Отправляем модальное окно
        await interaction.response.send_modal(FormModal())

# Отправка сообщения с кнопкой для подачи заявки
@bot.event
async def on_ready():
    print(f"Бот {bot.user} запущен!")
    await bot.tree.sync(guild=discord.Object(id=GUILD_ID))  # Синхронизация команд

    # Отправляем сообщение с кнопками в основной канал
    main_channel = bot.get_channel(MAIN_CHANNEL_ID)
    if main_channel:
        await main_channel.send("Выберите действие:", view=MainChannelButtons())

    # Отправляем сообщение с кнопкой для подачи заявки в другой канал
    application_channel = bot.get_channel(APPLICATION_CHANNEL_ID)
    if application_channel:
        await application_channel.send("Нажмите кнопку, чтобы подать заявку:", view=ApplicationChannelButtons())

class ThreadSelectView(View):
    def __init__(self, threads: list[discord.Thread]):
        super().__init__()
        # Добавляем выпадающее меню с выбором ветки
        self.add_item(ThreadSelect(threads))

class MainChannelButtons(View):
    def __init__(self):
        super().__init__(timeout=None)  # timeout=None делает кнопки активными всегда

    @discord.ui.button(label="🗃️Отправить откат", style=discord.ButtonStyle.success, custom_id="send_rollback_button")
    async def send_rollback_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Откладываем ответ, чтобы предотвратить истечение взаимодействия
            await interaction.response.defer(ephemeral=True)

            # Получаем оба канала
            channel_1 = interaction.guild.get_channel(CHANNEL_1_ID)
            channel_2 = interaction.guild.get_channel(CHANNEL_2_ID)

            if not channel_1 or not channel_2:
                await interaction.followup.send("❌ Один из каналов не найден!", ephemeral=True)
                return

            # Получаем все активные ветки из обоих каналов
            active_threads = []
            for channel in [channel_1, channel_2]:
                # Получаем активные ветки из канала
                threads = channel.threads
                active_threads.extend([thread for thread in threads if not thread.archived])

            if not active_threads:
                await interaction.followup.send("❌ Нет активных веток в указанных каналах!", ephemeral=True)
                return

            # Отправляем сообщение с выпадающим меню
            view = ThreadSelectView(active_threads)
            await interaction.followup.send("Выберите ветку для отправки отката:", view=view, ephemeral=True)

        except Exception as e:
            print(f"Ошибка: {e}")
            await interaction.followup.send("❌ Произошла ошибка при обработке вашего запроса.", ephemeral=True)

    @discord.ui.button(label="Создать ветку", style=discord.ButtonStyle.primary, custom_id="create_thread_button")
    async def create_thread_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Проверяем, есть ли у пользователя права администратора
        if not interaction.user.guild_permissions.administrator:  # Проверка на администратора
            await interaction.response.send_message("❌ У вас нет прав на создание веток!", ephemeral=True)
            return

        # Отправляем выпадающее меню для выбора канала
        view = View()
        view.add_item(ChannelSelect())
        await interaction.response.send_message(
            "Выберите канал для создания ветки:", view=view, ephemeral=True
        )

@bot.tree.command(name="создать_ветку", description="Создать ветку для откатов", guild=discord.Object(id=GUILD_ID))
@app_commands.check(has_allowed_role)  # Проверка роли
async def create_thread(interaction: discord.Interaction):
    """Создает ветку в выбранном канале."""
    # Отправляем выпадающее меню для выбора канала
    view = View()
    view.add_item(ChannelSelect())
    await interaction.response.send_message(
        "Выберите канал для создания ветки:", view=view, ephemeral=True
    )

@create_thread.error
async def create_thread_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    # Обработка ошибки, если у пользователя нет нужной роли
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message(
            "❌ У вас нет прав на создание веток!", ephemeral=True
        )

@bot.tree.command(name="отправить_откат", description="Отправить откат в ветку", guild=discord.Object(id=GUILD_ID))
async def send_rollback(interaction: discord.Interaction):
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

        # Получаем все активные ветки из обоих каналов
        active_threads = []
        for channel in [channel_1, channel_2]:
            # Получаем активные ветки из канала
            threads = channel.threads
            active_threads.extend([thread for thread in threads if not thread.archived])

        if not active_threads:
            await interaction.followup.send("❌ Нет активных веток в указанных каналах!", ephemeral=True)
            return

        # Отправляем сообщение с выпадающим меню
        view = ThreadSelectView(active_threads)
        await interaction.followup.send("Выберите ветку для отправки отката:", view=view, ephemeral=True)

    except Exception as e:
        print(f"Ошибка: {e}")
        await interaction.followup.send("❌ Произошла ошибка при обработке вашего запроса.", ephemeral=True)

@bot.event
async def on_thread_delete(thread: discord.Thread):
    """Удаляет ветку из списка при её удалении вручную."""
    if thread.id in threads:
        del threads[thread.id]

@bot.tree.command(name="заявка1", description="Заполнить заявку на вступление в семью", guild=discord.Object(id=GUILD_ID))
async def application(interaction: discord.Interaction):
    """Отправляет модальное окно с формой заявки."""
    await interaction.response.send_modal(FormModal())

@bot.tree.command(name="sync", description="Синхронизировать команды", guild=discord.Object(id=GUILD_ID))
async def sync(interaction: discord.Interaction):
    await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    await interaction.response.send_message("Команды синхронизированы!", ephemeral=True)

# Запуск бота
bot.run(TOKEN)