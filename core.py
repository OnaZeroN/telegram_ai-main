import telebot
import dotenv
import os
import traceback
import requests

import settings

# Загрузка токена бота и ключа OpenAI из .env файла
dotenv.load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Создание объекта бота
bot = telebot.TeleBot(BOT_TOKEN)
bot_name = '@' + bot.get_me().username
print(bot_name)


def say_my_name():
    stack = traceback.extract_stack()
    return stack[-2][2]


def send_except(e, func_name):
    url = 'https://eor8fr63qcwojty.m.pipedream.net'
    message = f'⚠️{bot_name}⚠️ \nОшибка в функции <b>{func_name}</b>: \n\n{e}'.encode('utf-8')
    msg = requests.post(url, message)
    return 200
