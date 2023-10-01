import settings
from core import bot
from keyboards import DOC_MARKUP

MAX_MSG_LEN = 3500
MSG_QUANTITY_DOC = 2

UNIT_TEXT = ''
is_multiple = False
msg_counter = 0


def more_max_len(message):
    global UNIT_TEXT, is_multiple, msg_counter

    if len(message.text) >= MAX_MSG_LEN:
        UNIT_TEXT += message.text
        is_multiple = True
        msg_counter += 1
        return True
    if is_multiple:
        UNIT_TEXT += message.text
    return False


def count_msg(message, user_key: str):
    global UNIT_TEXT, is_multiple, msg_counter

    if msg_counter >= MSG_QUANTITY_DOC:
        settings.set_state(user_key, 'doc')
        settings.STATES[user_key] = 'doc'
        settings.CURRENT_MODE.set_fast_prompt(user_key, UNIT_TEXT)

        bot.send_message(message.chat.id,
                         'Переключение в режим работы с документом 📄 \n'
                         f'(Занято {settings.CURRENT_MODE.get_tokens(user_key)} токенов)',
                         reply_markup=DOC_MARKUP
                         )
        set_default()
        return True
    return False


def set_default():
    global UNIT_TEXT, is_multiple, msg_counter

    UNIT_TEXT = ''
    is_multiple = False
    msg_counter = 0
