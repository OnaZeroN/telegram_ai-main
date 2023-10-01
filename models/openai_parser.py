import openai
import dotenv
import os
import logging

import settings
from core import send_except, say_my_name

dotenv_path = os.path.join(os.path.dirname(__file__), '../.env')
dotenv.load_dotenv()

# Настройка логирования
logger = logging.getLogger(__name__)


class OpenAIParser:
    """Parsing response."""

    def __init__(self, key: str, model: str,):
        openai.api_key = key
        self.MAX_TOKENS = 7500 if model != 'gpt-3.5-turbo-16k' else 16000
        self.model = model
        self.messages_db = {}

    def _clear_msg_history(self, user_id):
        self.messages_db.pop(user_id)
        logger.error(f'lot of tokens, over {self.MAX_TOKENS}')

    def _message_db_handler(self, user_id, message: str, role="user") -> list:
        """Add new message to the message history."""
        user = str(user_id)
        if user not in self.messages_db:
            with open(settings.PROMPT_DIR, 'r') as f:
                self.messages_db[user] = []
                self.messages_db[user].append({"role": "system", "content": f.read()})
        self.messages_db[user].append({"role": role, "content": message})
        return self.messages_db[user]

    def _get_single_response(self, user_id: str, context_message="Привет!"):
        try:
            response = openai.ChatCompletion.create(model=self.model,
                                                    messages=self._message_db_handler(user_id, context_message))
            logger.info(
                f"_got_single_response: "
                f"{user_id}"
                f" received response"
                f" {response['usage']['total_tokens']}")
        except Exception as e:
            logger.critical(f"{user_id}, сломал бот: {e}")
            send_except(e, say_my_name())
            return "Произошли небольшие технические шоколадки, мы уже их еди... устраняем, Мы их устраняем )"
        return response["choices"][0]["message"]["content"]

    def get_response(self, user_id: int, context_message):
        user_id = str(user_id)
        temperature = settings.CHAT_TEMP
        try:
            messages = self._message_db_handler(user_id, context_message)
            response = openai.ChatCompletion.create(model=self.model,
                                                    messages=messages,
                                                    temperature=temperature,
                                                    )
            answer = response["choices"][0]["message"]['content']
            self._message_db_handler(user_id, answer, "assistant")

            tokens = response["usage"]["total_tokens"]

            logger.info(f"User {user_id}: tokens used '{tokens}' in {self.model} and {temperature} temp")
            if tokens > self.MAX_TOKENS:
                self._clear_msg_history(user_id)
            return answer
        except Exception as e:
            logger.error(f"Error occurred: {e}")
            send_except(e, say_my_name())
            self._clear_msg_history(user_id)
            return self._get_single_response(user_id, context_message)

    def set_fast_prompt(self, user_id, prompt):
        """Flash meta prompt"""
        user = str(user_id)
        if user not in self.messages_db:
            self.messages_db[user] = {"role": "system", "content": prompt}
            return
        self.messages_db.pop(user)
        self.set_fast_prompt(user_id, prompt)

    def convert_speech_to_text(self, audio_filepath):
        with open(audio_filepath, "rb") as audio:
            transcript = openai.Audio.transcribe("whisper-1", audio)
            return transcript["text"]

    def __str__(self,):
        return "OpenAI"

