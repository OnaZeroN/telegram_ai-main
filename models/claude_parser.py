# -*- coding: utf-8 -*-
import logging
import dotenv

import settings
from core import send_except, say_my_name
from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT
from typing import Union, Any

dotenv.load_dotenv()

logger = logging.getLogger(__name__)


class ClaudeParser:

    def __init__(self, key, model):
        self.client = Anthropic(
            api_key=key,
        )
        self.model = model
        self.messages_db = {}
        if model == "claude-1.3-100k" or model == "claude-2":
            settings.MAX_TOKENS = 90000
        else:
            settings.MAX_TOKENS = 6000

    def _message_db_handler(self, user_id, message: str) -> list:
        """Add new message to the message history."""
        user = str(user_id)
        if user not in self.messages_db:
            with open(settings.PROMPT_DIR, 'r', encoding="utf-8") as f:
                self.messages_db[user] = f"{HUMAN_PROMPT} {f.read()} {AI_PROMPT}"
        self.messages_db[user] += f"{HUMAN_PROMPT} {message} {AI_PROMPT}"
        return self.messages_db[user]

    def set_fast_prompt(self, user_id, prompt):
        """Flash meta prompt"""
        user = str(user_id)
        if user not in self.messages_db:
            self.messages_db[user] = str(f"{HUMAN_PROMPT} {prompt} {AI_PROMPT}")
            return
        self.messages_db.pop(user)
        self.set_fast_prompt(user_id, prompt)

    def get_tokens(self, user_key) -> int:
        try:
            tokens = self.client.count_tokens(self.messages_db[user_key])
        except:
            tokens = 0
        return tokens

    def get_response(self, user_id, message):
        temperature = settings.CHAT_TEMP
        user_key = str(user_id)
        try:
            response = self.get_request(self._message_db_handler(user_key, message), temperature)

            text = self.messages_db[user_key]
            tokens = self.client.count_tokens(text)
            if tokens > settings.MAX_TOKENS:
                self.messages_db.pop(user_key)
                logging.error(f"User: {user_key}: lot of tokens, over {settings.MAX_TOKENS}")
            logging.info(f"User {user_id}: tokens used '{tokens}' in {self.model} and {temperature} temp")
            return response
        except Exception as e:
            logging.error(f"Error occurred for User: {user_key}, Message: {message}. Exception: {e}")
            send_except(e, say_my_name())
            self.messages_db.pop(user_key)
            return self.get_response(user_id, message)

    def get_stream_response(self, user_id: Union[int, str], message: str) -> Any:
        temperature = settings.CHAT_TEMP
        user_key = str(user_id)
        try:
            return self.get_request(self._message_db_handler(user_key, message), temperature, True)
        except Exception as e:
            logging.error(f"Error occurred for User: {user_key}, Message: {message}. Exception: {e}")
            send_except(e, say_my_name())
            self.messages_db.pop(user_key)
            return self.get_stream_response(user_id, message)

    def get_request(self, prompt: str, temperature: float, stream: bool = False) -> Any:
        completion = self.client.completions.create(
            model=self.model,
            max_tokens_to_sample=2000,
            prompt=prompt,
            temperature=temperature,
            timeout=1000.0,
            stream=stream
        )
        return completion if stream else completion.completion

    def __str__(self,):
        return "Claude"
