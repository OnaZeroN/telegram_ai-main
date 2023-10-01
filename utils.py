import settings

import telebot
from typing import Optional, Union

MAX_RESPONSE_LENGTH = 4096
STREAM_CHAR_LENGTH = 100


def send_response(bot: telebot.TeleBot,
                  user_id: int,
                  user_message: str,
                  prefix: str = "",
                  parse_mode: Union[str, None] = "HTML",
                  reply_markup: Optional[telebot.types.ReplyKeyboardMarkup] = None,
                  thread_id: Optional[int] = None,
                  msg: Optional[telebot.types.Message] = None) -> str:
    if settings.STREAM_RESPONSE and "claude" in settings.CURRENT_MODE.model:
        stream_response = settings.CURRENT_MODE.get_stream_response(user_id, user_message)
        prev_response = response = ""
        for content in stream_response:
            response += content.completion
            response = response[:MAX_RESPONSE_LENGTH]

            if abs(len(response) - len(prev_response)) < STREAM_CHAR_LENGTH and content.stop_reason is None:
                continue

            if msg is None:
                msg = bot.send_message(chat_id=user_id, 
                                        text=f'{prefix}{response}',
                                        parse_mode=parse_mode,
                                        message_thread_id=thread_id)
                
            else:
                bot.edit_message_text(chat_id=user_id, 
                                    message_id=msg.message_id, 
                                    text=f'{prefix}{response}',
                                    parse_mode=parse_mode)
            prev_response = response
        return response

    response = settings.CURRENT_MODE.get_response(user_id, user_message)
    if msg is not None:
        bot.delete_message(user_id, msg.message_id)
    bot.send_message(chat_id=user_id, 
                        text=f'{prefix}{response}',
                        reply_markup=reply_markup,
                        parse_mode=parse_mode,
                        message_thread_id=thread_id)
    return response
