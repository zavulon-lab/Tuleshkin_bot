from constants import *
from discord.ui import Select, View, Modal, TextInput, button, Button
from json_func import private_threads, save_private_threads
from discord import TextStyle, Interaction, CategoryChannel, SelectOption, TextChannel, ChannelType, Thread, ButtonStyle, SelectMenu
from discord.errors import NotFound
from datetime import datetime

# Словарь для хранения созданных веток (ключ: ID ветки, значение: {"thread": объект ветки, "creator": создатель})
threads = {}

# Модальное окно для заявки
class FormModal(Modal, title="Заявка на вступление в семью"):
		# Поля формы
		name = TextInput(label="Имя и возраст:", required=True)
		rp_experience = TextInput(
				label="Состоял в семьях/стаках:",
				required=True,
				style=TextStyle.paragraph,
		)
		shooting = TextInput(
				label="Опыт игры и достижения:",
				required=True,
				style=TextStyle.paragraph,
		)
		lvl_online = TextInput(
				label="Сервера с персонажами 2 уровня:",
				required=True,
		)
		family_experience = TextInput(
				label="Видеозаписи стрельбы:",
				required=True,
				style=TextStyle.paragraph,
		)

		async def on_submit(self, interaction: Interaction):
				"""Обработка отправки формы."""
				try:
						# Получаем гильдию (сервер)
						guild = interaction.guild
						if not guild:
								await interaction.response.send_message("❌ Ошибка! Сервер не найден.", ephemeral=True)
								return

						# Получаем категорию, где будут создаваться каналы
						category = guild.get_channel(CATEGORY_ID)
						if not category or not isinstance(category, CategoryChannel):
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
								f"🏠 **Видеозаписи стрельбы:** {self.family_experience.value}\n\n"
								f"{role.mention} {interaction.user.mention}"  # Упоминание роли и пользователя
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
								SelectOption(
										label="Капт-архив",
										value=str(CHANNEL_1_ID),  # ID первого канала
								),
								SelectOption(
										label="Мкл-архив",
										value=str(CHANNEL_2_ID),  # ID второго канала
								),
						],
				)

		async def callback(self, interaction: Interaction):
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

class CreateThreadModal(Modal, title="Создать ветку"):
		def __init__(self, channel: TextChannel):
				super().__init__()
				self.channel = channel  # Сохраняем выбранный канал

		thread_name = TextInput(label="Название ветки", required=True)

		async def on_submit(self, interaction: Interaction):
				# Создаем ветку в выбранном канале
				thread = await self.channel.create_thread(
						name=self.thread_name.value,
						type=ChannelType.public_thread,
				)

				# Сохраняем ветку и создателя в словарь
				threads[thread.id] = {"thread": thread, "creator": interaction.user}

				await interaction.response.send_message(
						f"✅ Ветка '{self.thread_name.value}' создана в канале {self.channel.mention}!",
						ephemeral=True,
				)

class ThreadSelect(Select):
		def __init__(self, threads: list[Thread]):
				options = [
						SelectOption(
								label=f"{thread.parent.name if thread.parent else 'Unknown'} - {thread.name}",  # Показываем название канала и ветки
								value=str(thread.id),  # Используем ID ветки как значение
						)
						for thread in threads
				]
				super().__init__(
						placeholder="Выберите ветку для отправки отката",
						options=options,
				)

		async def callback(self, interaction: Interaction):
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

		@button(label="📝Подать заявку", style=ButtonStyle.primary)
		async def submit_application_button(self, interaction: Interaction, button: Button):
				"""Обработчик кнопки для подачи заявки."""
				# Отправляем модальное окно
				await interaction.response.send_modal(FormModal())

class ThreadSelectView(View):
    def __init__(self, threads_channel_1=None, threads_channel_2=None):
        super().__init__()
        
        # Устанавливаем пустые списки по умолчанию
        if threads_channel_1 is None:
            threads_channel_1 = []
        if threads_channel_2 is None:
            threads_channel_2 = []

        # Создаем выпадающие списки для веток из канала 1
        if threads_channel_1:
            # Разделяем ветки на группы по 25
            for i in range(0, len(threads_channel_1), 25):
                group = threads_channel_1[i:i + 25]  # Берем срез из 25 элементов
                options_channel_1 = [SelectOption(label=thread.name, value=str(thread.id)) for thread in group]
                select_channel_1 = Select(
                    custom_id=f"channel_1_select_{i}",
                    placeholder=f"КАПТ(часть {i // 25 + 1})",
                    options=options_channel_1
                )
                select_channel_1.callback = self.on_select_channel_1
                self.add_item(select_channel_1)

        # Создаем выпадающие списки для веток из канала 2
        if threads_channel_2:
            # Разделяем ветки на группы по 25
            for i in range(0, len(threads_channel_2), 25):
                group = threads_channel_2[i:i + 25]  # Берем срез из 25 элементов
                options_channel_2 = [SelectOption(label=thread.name, value=str(thread.id)) for thread in group]
                select_channel_2 = Select(
                    custom_id=f"channel_2_select_{i}",
                    placeholder=f"МКЛ(часть {i // 25 + 1})",
                    options=options_channel_2
                )
                select_channel_2.callback = self.on_select_channel_2
                self.add_item(select_channel_2)

    async def on_select_channel_1(self, interaction: Interaction):
        # Обработка выбора ветки из канала 1
        selected_thread_id = int(interaction.data["values"][0])  # Получаем выбранный ID ветки
        selected_thread = interaction.guild.get_thread(selected_thread_id)
        if selected_thread:
            await interaction.response.send_modal(RollbackForm(selected_thread))
        else:
            await interaction.response.send_message("❌ Ветка не найдена.", ephemeral=True)

    async def on_select_channel_2(self, interaction: Interaction):
        # Обработка выбора ветки из канала 2
        selected_thread_id = int(interaction.data["values"][0])  # Получаем выбранный ID ветки
        selected_thread = interaction.guild.get_thread(selected_thread_id)
        if selected_thread:
            await interaction.response.send_modal(RollbackForm(selected_thread))
        else:
            await interaction.response.send_message("❌ Ветка не найдена.", ephemeral=True)

class MainChannelButtons(View):
    def __init__(self):
        super().__init__(timeout=None)  # timeout=None делает кнопки активными всегда

    @button(label="🗃️Отправить откат", style=ButtonStyle.success, custom_id="send_rollback_button")
    async def send_rollback_button(self, interaction: Interaction, button: Button):
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
            await interaction.followup.send("❌ Произошла ошибка при обработке вашего запроса. 4444", ephemeral=True)

    @button(label="Создать ветку", style=ButtonStyle.primary, custom_id="create_thread_button")
    async def create_thread_button(self, interaction: Interaction, button: Button):
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
				
class RollbackForm(Modal, title="Отправить откат"):
		def __init__(self, thread: Thread):
				super().__init__()
				self.thread = thread  # Сохраняем объект выбранной ветки

		player_name = TextInput(label="Ваше имя", required=True)
		rollback_details = TextInput(
				label="Описание отката",
				style=TextStyle.paragraph,
				required=True,
		)

		async def on_submit(self, interaction: Interaction):
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
												type=ChannelType.private_thread,
										)
										# Обновляем данные в словаре и JSON
										private_threads[str(interaction.user.id)] = private_thread.id
										save_private_threads(private_threads)
						else:
								# Создаем новую приватную ветку
								private_thread = await private_channel.create_thread(
										name=f"Личное дело {interaction.user.name}",
										type=ChannelType.private_thread,
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

				except NotFound:
						print("Ошибка: Ветка не найдена или удалена.")
						await interaction.followup.send(
								"❌ Не удалось отправить откат. Ветка не найдена или была удалена.", ephemeral=True
						)

				except Exception as e:
						print(f"Ошибка: {e}")
						await interaction.followup.send(
								"отправилось", ephemeral=True
						)
