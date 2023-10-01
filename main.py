import logging
import os
import re
import sys

from collections import defaultdict
from functools import wraps
from typing import Union, Any

from requests import ReadTimeout

import telebot
from telebot.formatting import escape_html


import utils
import settings
import db_process
from bot_utils import BigMessageHelper
from core import bot, bot_name, send_except, say_my_name
from handlers import docs, multi_messages
from keyboards import (
    AUDIO_MARKUP,
    CLEANER,
    commands,
    DOC_MARKUP,
    GROUP_AUDIO_MARKUP,
    GROUP_DOC_MARKUP,
    MENU_MARKUP,
    MODE_CHOOSE_MARKUP,
    VOICE_CHOOSE_MARKUP,
)
from models.speech_synthesis import synthesize_text
from models.voice_proccesing import convert_ogg_to_mp3, download_voice_as_ogg

# буфер длинных сообщений
big_messages = defaultdict(list)
# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

bot.set_my_commands(commands)

"""Decorators."""


def check_private_chat(func):
    @wraps(func)
    def wrapped(message):
        if message.chat.type == 'private':
            return func(message)
        return

    return wrapped


def admin_per(func):
    """Admin permission for function."""

    @wraps(func)
    def wrapped(message):
        user_id = message.chat.id
        if user_id not in settings.LIST_OF_ADMINS:
            bot.send_message(user_id, f'⛔ У вас нет администраторского доступа')
            logger.error(f'Попытка доступа к админ панели от {user_id}')
            return
        return func(message)

    return wrapped


def restricted(func):
    """Доступ к функции только у разрешенных юзеров, если settings.PER_MODE=True."""

    @wraps(func)
    def wrapped(message):
        user_id = message.chat.id
        if settings.PER_MODE and user_id not in settings.ALLOWED_USERS:
            bot.send_message(user_id, f'⛔ похоже, у вас нет доступа к этому ассистенту')
            logger.error(f'Попытка общения с ботом от {user_id}')
            return
        return func(message)

    return wrapped


def send_action(action='typing'):
    """Отправляет 'действие' во время обработки команды."""

    def decorator(func):
        @wraps(func)
        def command_func(message):
            chat_id = message.chat.id
            bot.send_chat_action(chat_id, action)
            return func(message)

        return command_func

    return decorator


"""Admin pipline."""


@bot.callback_query_handler(func=lambda call: call.data in settings.VOICES)
def save_voice(call):
    user_id = call.message.chat.id

    try:
        db_process.update_voice(call.data)
        bot.send_message(user_id, 'Успешный успех ✅')
    except Exception as e:
        bot.send_message(
            user_id,
            f'⛔ Попробуйте еще раз, что то пошло не по плану: {e}'
        )
        send_except(e, say_my_name())


@admin_per
def save_prompt(message):
    try:
        with open(settings.PROMPT_DIR, 'w') as f:
            f.write(message.text if message.text is not None else docs.doc_parser(message))
        settings.CURRENT_MODE.messages_db = {}
        msg = bot.send_message(message.chat.id, '✅ Вы успешно поменяли промпт')
        logger.info(f"Admin changed prompt, messages_db cleared")
    except Exception as e:
        msg = bot.send_message(message.chat.id, f'⛔ что то не то: {e}')
        logger.error(f"Admin could not change prompt. Reason: {e}")
        send_except(e, say_my_name())
    bot.register_next_step_handler(msg, start_message)


@admin_per
def save_prompt_doc(message):
    try:
        with open(settings.PROMPT_DOC_DIR, 'w') as f:
            f.write(message.text)
        msg = bot.send_message(message.chat.id, '✅ Вы успешно поменяли промпт для работы с документами.')
        logger.info(f"Admin changed prompt document mode, messages_db cleared")
    except Exception as e:
        msg = bot.send_message(message.chat.id, f'⛔ что то не то: {e}')
        logger.error(f"Admin could not change prompt. Reason: {e}")
        send_except(e, say_my_name())
    bot.register_next_step_handler(msg, start_message)


@admin_per
def save_prompt_audio(message):
    try:
        with open(settings.PROMPT_AUDIO_DIR, 'w') as f:
            f.write(message.text)
        msg = bot.send_message(message.chat.id, '✅ Вы успешно поменяли промпт для работы с аудиофайлами.')
        logger.info(f"Admin changed prompt audio mode, messages_db cleared")
    except Exception as e:
        msg = bot.send_message(message.chat.id, f'⛔ что то не то: {e}')
        logger.error(f"Admin could not change prompt. Reason: {e}")
        send_except(e, say_my_name())
    bot.register_next_step_handler(msg, start_message)


@bot.message_handler(commands=['admin'])
@admin_per
def admin_mode(message):
    response = "Меню редактирования бота"
    bot.send_message(message.chat.id, response, reply_markup=MENU_MARKUP)


@bot.callback_query_handler(func=lambda call: call.data == 'admin')
def admin_mode_call(call):
    response = "Меню редактирования бота"
    bot.edit_message_text(chat_id=call.message.chat.id,
                          message_id=call.message.id,
                          text=response,
                          reply_markup=MENU_MARKUP)


@bot.callback_query_handler(func=lambda call: call.data == 'mode')
def select_model(call):
    response = (f"Сейчас активен {settings.CURRENT_MODE.model}"
                "\nКакую модель выберем? ")
    bot.edit_message_text(chat_id=call.message.chat.id,
                          text=response,
                          reply_markup=MODE_CHOOSE_MARKUP,
                          message_id=call.message.id)


@bot.callback_query_handler(func=lambda call: str(call.data).startswith('cl') or str(call.data).startswith('gpt'))
def select_temp_claude(call):
    ai, cllbck = map(str, call.data.split("-"))
    temp_range = '(-1 ; 1)' if ai == 'cl' else '(0 ; 2)'
    db_process.update_ai_model(cllbck)
    model = settings.CURRENT_MODE = settings.CALLBACK_TO_MODES[db_process.get_ai_model()]
    bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.id)
    msg = bot.send_message(call.message.chat.id, f"Какую температуру выставим для {model.model}? {temp_range}\n"
                                                 f"Сейчас {settings.CHAT_TEMP}")
    bot.register_next_step_handler(msg, set_temp_cl if ai == 'cl' else set_temp_gpt)


def set_temp_cl(message):
    try:
        number = float(message.text)
        if -1 <= number <= 1:
            db_process.update_temperature(str(number))
            bot.reply_to(message, f'Все норм, вы ввели: {number}')
            settings.CHAT_TEMP = float(number)
        else:
            bot.reply_to(message, 'Минимум -1, максимум 1, default 0.7')
    except ValueError:
        bot.reply_to(message, 'Это не похоже на число. Пожалуйста, попробуйте еще раз.')
        return


def set_temp_gpt(message):
    try:
        number = float(message.text)
        if 0 <= number <= 2:
            db_process.update_temperature(str(number))
            bot.reply_to(message, 'Все норм, вы ввели: {}'.format(number))
            settings.CHAT_TEMP = float(number)
        else:
            bot.reply_to(message, 'Минимум 0, максимум 2, default 1')
    except ValueError:
        bot.reply_to(message, 'Это не похоже на число. Пожалуйста, попробуйте еще раз.')
        return


@bot.callback_query_handler(func=lambda call: call.data == 'prompt')
def new_promt(call):
    response = "Введите новый МЕТАпромпт или отправьте документ: "
    msg = bot.send_message(text=response, chat_id=call.message.chat.id)
    settings.State.set_state(str(call.message.chat.id), 'set_prompt')
    bot.register_next_step_handler(msg, save_prompt)


@bot.callback_query_handler(func=lambda call: call.data == 'prompt_doc')
def new_promt_doc(call):
    response = "Введите новый промпт(Режим Документа): "
    msg = bot.send_message(text=response, chat_id=call.message.chat.id)
    bot.register_next_step_handler(msg, save_prompt_doc)


@bot.callback_query_handler(func=lambda call: call.data == 'prompt_audio')
def new_promt_audio(call):
    response = "Введите новый промпт(Режим Диктофона): "
    msg = bot.send_message(text=response, chat_id=call.message.chat.id)
    bot.register_next_step_handler(msg, save_prompt_audio)


@bot.callback_query_handler(func=lambda call: call.data == 'voice')
def choose_voice(call):
    response = (f"Сейчас активен {settings.CURRENT_VOICE}"
                f"\nКакой голос выберем? ")
    bot.edit_message_text(response,
                          call.message.chat.id,
                          call.message.id,
                          reply_markup=VOICE_CHOOSE_MARKUP)


@bot.callback_query_handler(func=lambda call: call.data == 'exit_doc')
def exit_doc(call):
    clean_history(call.message)


"""Handlers."""


@bot.message_handler(commands=['start'])
@restricted
def start_message(message):
    """Обработчик команды /start"""

    settings.State.set_state(str(message.chat.id), 'main')

    bot.delete_message(message.chat.id, message.message_id)

    bot.send_chat_action(message.chat.id, "typing")
    response = 'Здравствуйте! Чем я могу вам помочь?'
    bot.send_message(message.chat.id, response)
    logger.info(f"User {message.chat.id}: sent /start command")


@bot.message_handler(commands=['reset'])
def clean_history(message):
    user_id = message.chat.id
    user_key = str(user_id)

    thread_id = ''
    if message.reply_to_message is not None:
        thread_id = message.reply_to_message.message_thread_id
        user_key = f'{thread_id}{user_id}'

    try:
        settings.State.set_state(user_key, 'main')
        settings.CURRENT_MODE.messages_db.pop(user_key)
        bot.send_message(
            chat_id=message.chat.id,
            text='Успешно',
            reply_markup=CLEANER,
            message_thread_id=thread_id,
        )
    except:
        bot.send_message(
            chat_id=message.chat.id,
            text='Уже очищено',
            reply_markup=CLEANER,
            message_thread_id=thread_id
        )
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except:
        err = f'{user_key} не получется удалять сообщения юзера'
        logger.error(err)
        bot.send_message(settings.EXCEPTION_ID, err)
    return


@bot.message_handler(func=lambda message: 'Выйти из режима' in message.text)
@check_private_chat
def exit_document(message):
    clean_history(message)
    return


@send_action
@bot.message_handler(func=lambda message: True if bot_name in message.text or len(big_messages[message.chat.id]) > 0 else False)
@restricted
def text_group_message(message):
    """Обработчик групповых текстовых сообщений."""
    print(True if bot_name in message.text or len(big_messages[message.chat.id]) > 0 else False)
    print(big_messages[message.chat.id])
    user_id = message.chat.id
    user_key = str(user_id)
    thread_id = ''
    if message.reply_to_message is not None:
        thread_id = message.reply_to_message.message_thread_id
        user_key = f'{thread_id}{user_id}'

    user_message = re.sub(bot_name, '', message.text)

    state, prefix = settings.State.get_state_and_prefix(user_key)

    if 'выйти из режима' in user_message.lower():
        return

    big_messages_helper = BigMessageHelper(message=message, big_messages=big_messages)

    if big_messages_helper.check_message_len():
        return

    if big_messages_helper.check_message_group():
        payload = big_messages_helper.get_message_group()
        handle_docs(payload.message, payload.big_messages)
        return

    bot.send_chat_action(
        chat_id=user_id,
        action="typing",
        message_thread_id=thread_id
    )

    try:
        response = utils.send_response(bot=bot, user_id=user_id,
                                       user_message=user_message,
                                       prefix=prefix,
                                       parse_mode="HTML",
                                       reply_markup=settings.GROUP_STATES_BTN[state],
                                       thread_id=thread_id)

    except telebot.apihelper.ApiTelegramException as e:
        if "Bad Request: can't parse entities" in e.description:
            logger.error(f"HTML parsing")
            return bot.send_message(
                chat_id=user_id,
                text=escape_html(f'{prefix}{response}'),
                reply_markup=settings.GROUP_STATES_BTN[state],
                message_thread_id=thread_id
            )
        settings.State.set_state(user_key, 'main')
        logger.error(f"Error occurred: {e}")
        send_except(e, say_my_name())


@send_action
@bot.message_handler(func=lambda message: True)
@restricted
@check_private_chat
def text_message(message):
    print(message)
    """Обработчик личных текстовых сообщений."""

    user_id = message.chat.id
    user_message = message.text
    user_key = str(user_id)

    state, prefix = settings.State.get_state_and_prefix(user_key)

    big_messages_helper = BigMessageHelper(message=message, big_messages=big_messages)

    if big_messages_helper.check_message_len():
        return

    if big_messages_helper.check_message_group():
        payload = big_messages_helper.get_message_group()
        handle_docs(payload.message, payload.big_messages)
        return

    bot.send_chat_action(user_id, "typing")

    try:
        response = utils.send_response(bot=bot, user_id=user_id,
                                       user_message=user_message,
                                       prefix=prefix,
                                       parse_mode="HTML",
                                       reply_markup=settings.STATES_BTN[state])

    except telebot.apihelper.ApiTelegramException as e:
        if "Bad Request: can't parse entities" in e.description:
            logger.error(f"HTML parsing")
            return bot.send_message(chat_id=user_id, text=escape_html(f'{prefix}{response}'))
        settings.State.set_state(user_key, 'main')
        logger.error(f"Error occurred: {e}")
        send_except(e, say_my_name())


@bot.message_handler(content_types=["voice"])
@check_private_chat
def voice_message_handler(message):
    user_id = message.chat.id

    msg = bot.send_message(message.chat.id, 'Слушаю вопрос 🎶')

    file_info = bot.get_file(message.voice.file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    ogg_path = download_voice_as_ogg(downloaded_file)
    converted_file_path = convert_ogg_to_mp3(ogg_path)

    # задаём максимальный размер голосового сообщения в байтах
    max_size = 3000000

    if file_info.file_size > max_size:
        bot.send_message(message.chat.id,
                         f"Объем аудиофайла превышает {max_size / 1000000} мегабайт. Пожалуйста, отправьте файл меньшего объёма.")
        return
    try:
        text = settings.CALLBACK_TO_MODES['3.5_tur'].convert_speech_to_text(converted_file_path)
        if 'пиши' not in text and 'текст' not in text:
            bot.edit_message_text(chat_id=user_id, text='Записываю ответ', message_id=msg.message_id)
            bot.send_chat_action(user_id, 'record_audio')

            response = escape_html(settings.CURRENT_MODE.get_response(user_id, text))

            voice = synthesize_text(response)

            if voice:
                bot.delete_message(user_id, msg.id)
                bot.send_voice(user_id, voice)
            else:
                bot.edit_message_text(chat_id=user_id, text=response, message_id=msg.message_id)

        else:
            bot.send_chat_action(user_id, 'typing')
            response = utils.send_response(bot=bot, user_id=user_id,
                                           user_message=text,
                                           prefix="",
                                           parse_mode="HTML",
                                           reply_markup=None,
                                           thread_id=None,
                                           msg=msg)

    except Exception as e:
        text_message(message)
        logger.error(f"Error occurred: {e}")
        send_except(e, say_my_name())

    finally:
        os.remove(converted_file_path)
        os.remove(ogg_path)


@bot.message_handler(content_types=['document'])
def handle_docs(message, big_message: Union[Any, list] = None):
    user_id = message.chat.id
    user_key = str(user_id)

    thread_id = ''

    if message.reply_to_message is not None:
        thread_id = message.reply_to_message.message_thread_id
        user_key = f'{thread_id}{user_id}'

    is_group = message.chat.type in ("group", "supergroup")

    if settings.CURRENT_MODE.__str__() != "Claude":
        bot.send_message(
            chat_id=user_id,
            text='Режим документа пока доступен только в Claude',
            message_thread_id=thread_id
        )
        return
    if not big_message:
        text = docs.doc_parser(message)
    else:
        text = ''.join(item["text"] for item in big_message)
    if text is None:
        return
    msg = bot.send_message(
        chat_id=message.chat.id,
        text='Начинаю сканировать файл...',
        message_thread_id=thread_id
    )

    try:
        if settings.State.get_state_and_prefix(user_key)[1] == "set_prompt":
            with open(settings.PROMPT_DIR, 'w') as f:
                f.write(text)
            settings.CURRENT_MODE.messages_db = {}
            bot.send_message(message.chat.id, '✅ Вы успешно поменяли промпт')
            logger.info(f"Admin changed prompt, messages_db cleared")
            settings.State.set_state(user_key, 'main')
            return
        if settings.CURRENT_MODE.get_tokens(user_key) > settings.MAX_TOKENS:
            bot.send_message(user_id, '⚠️ Слишком большой документ! ⚠️')
            settings.CURRENT_MODE.messages_db.pop(user_key)
            return

        settings.CURRENT_MODE.set_fast_prompt(user_key, text)
        settings.State.set_state(user_key, 'doc')

        with open(settings.get_prompt_audio(), 'r') as f:
            start_text = f.read()

        utils.send_response(bot=bot, user_id=user_id,
                            user_message=start_text,
                            prefix="",
                            parse_mode="HTML",
                            reply_markup=None,
                            thread_id=thread_id,
                            msg=msg)

        keyboard = GROUP_DOC_MARKUP if is_group else DOC_MARKUP
        bot.send_message(
            chat_id=message.chat.id,
            text='✅ Сканирование завершено \n'
                 'Режим работы: документ \n'
                 f'(Занято {settings.CURRENT_MODE.get_tokens(user_key)} токенов) \n\n'
                 'Какие у вас будут вопросы по текущему документу? ',
            reply_markup=keyboard,
            message_thread_id=thread_id
        )
        logger.info(f"Doc mode, messages_db cleared")

        if os.path.exists('document.doc'):
            os.remove('document.doc')
        else:
            logger.info("The file does not exist")

    except Exception as e:
        bot.reply_to(message, e)


"""Режим диктофона"""


@bot.message_handler(content_types=['audio'])
def handle_audio(message):
    user_id = message.chat.id
    user_key = str(user_id)

    is_doc = message.chat.type == "group"

    if settings.CURRENT_MODE.__str__() != "Claude":
        bot.send_message(user_id, 'Режим документа пока доступен только в Claude')
        return
    msg = bot.send_message(message.chat.id, 'Начинаю сканировать аудиофайл...')

    try:
        settings.State.set_state(user_key, 'audio')

        file_info = bot.get_file(message.audio.file_id)
        file_path = file_info.file_path
        file_extension = os.path.splitext(file_path)[1]

        if file_extension.lower() in settings.SUPPORTED_FORMATS:
            file = bot.download_file(file_path)
            save_path = os.path.join(settings.BASE_DIR, 'telegram_ai', 'temp', 'voice',
                                     f"{message.audio.file_id}{file_extension}")

            with open(save_path, 'wb') as audio:
                audio.write(file)

            mp3_filepath = convert_ogg_to_mp3(save_path, format=file_extension[1:])
            text = settings.CALLBACK_TO_MODES['3.5_tur'].convert_speech_to_text(mp3_filepath)

            settings.CURRENT_MODE.set_fast_prompt(user_id, text)

            if settings.CURRENT_MODE.get_tokens(user_key) > settings.MAX_TOKENS:
                bot.send_message(user_id, '⚠️ Слишком большой документ! ⚠️')
                settings.CURRENT_MODE.messages_db.pop(user_key)
                return

            with open(settings.get_prompt_audio(), 'r') as f:
                start_text = f.read()

            response = utils.send_response(bot=bot, user_id=user_id,
                                           user_message=start_text,
                                           prefix="",
                                           parse_mode="HTML",
                                           reply_markup=None,
                                           thread_id=None,
                                           msg=msg)

            keyboard = GROUP_AUDIO_MARKUP if is_doc else AUDIO_MARKUP
            bot.send_message(message.chat.id,
                             '✅ Сканирование завершено \n'
                             'Режим работы: диктофон \n'
                             f'(Занято {settings.CURRENT_MODE.get_tokens(user_key)} токенов) \n\n'
                             'Какие у вас будут вопросы по текущему аудиофайлу? ',
                             reply_markup=keyboard,
                             )
            logger.info(f"Admin changed prompt, messages_db cleared")

            if os.path.exists(save_path):
                os.remove(save_path)
            else:
                logger.info("The file does not exist")


        else:
            bot.reply_to(message, 'Неподдерживаемый формат файла.')

    except Exception as e:
        bot.reply_to(message, f'Произошла ошибка при загрузке файла. \n {e}')


if __name__ == '__main__':
    try:
        bot.infinity_polling(timeout=1000)
    except (ConnectionError, ReadTimeout) as e:
        sys.stdout.flush()
        os.execv(sys.argv[0], sys.argv)
    else:
        bot.infinity_polling(timeout=1000)
