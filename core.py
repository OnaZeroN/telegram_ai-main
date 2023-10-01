import telebot
import dotenv
import os
import traceback
import requests

import settings

os.environ['OPEN_API_KEY'] = "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"
os.environ['ANTHROPIC_API_KEY'] = "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"
os.environ['BOT_TOKEN'] = "6005260165:AAFVdet3tDjCb0JHJISGfPOAb1BJSWzaf4w"


# Загрузка токена бота и ключа OpenAI из .env файла
dotenv.load_dotenv()
BOT_TOKEN = "6005260165:AAFVdet3tDjCb0JHJISGfPOAb1BJSWzaf4w"

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
