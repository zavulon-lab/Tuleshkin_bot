from json import load, dump
from os import path


# Функция для загрузки данных из JSON
def load_private_threads():
		if path.exists("private_threads.json"):
				with open("private_threads.json", "r") as file:
						return load(file)
		return {}  # Возвращаем пустой словарь, если файл не существует

# Функция для сохранения данных в JSON
def save_private_threads(data):
		with open("private_threads.json", "w") as file:
				dump(data, file, indent=4)

# Загружаем данные при запуске бота
private_threads = load_private_threads()