import asyncio

from telebot import types

from typing import Union, Any
from dataclasses import dataclass


@dataclass
class DocumentPayload:
    """
    Dataclass hat contains information for calling the handle_docs function

    message: types.Message
    big_messages: list of messages
    """
    message: types.Message
    big_messages: list


class BigMessageHelper:
    """
    A class for processing a group of messages that are sent when a user tries to send a message longer than 4000 characters
    """
    def __init__(self, message: types.Message, big_messages: Union[Any, list]):
        """
        :param message: types.Message, message from the user
        :param big_messages: Union[Any, list], buffer of long messages
        """
        self.message: types.Message = message
        self.user_id = message.chat.id
        self.big_messages: list = big_messages

    def check_message_len(self) -> bool:
        """
        A class method that processes messages of more than 4000 characters, if the message is more than 4000 characters, it will add it to the buffer in the format {"text": message.text, "time": message.date} and return True, otherwise False

        If a message with a length of more than 4000 characters was sent and it is the only one in the buffer, the method will wait for a certain time, and if no new message has been added to the buffer during this time, it will return False
        """
        if len(self.message.text) > 3000:
            self.big_messages[self.user_id].append({"text": self.message.text, "time": self.message.date})
            if len(self.big_messages[self.user_id]) == 1:
                asyncio.run(asyncio.sleep(2))
            if len(self.big_messages[self.user_id]) == 1:
                self.big_messages[self.user_id] = []
            else:
                return True
            return False

    def check_message_group(self) -> bool:
        """
        The method of the class that checks the completion of a group of messages, if the message does not enter the time interval of the previous messages, it will mean that the group of messages is completed and will return True, otherwise False
        """
        if len(self.big_messages[self.user_id]) != 0 and self.message.date - 5 <= self.big_messages[self.user_id][0]["time"] <= self.message.date:
            self.big_messages[self.user_id].append({"text": self.message.text, "time": self.message.date})
            return True
        return False

    def get_message_group(self) -> DocumentPayload:
        """
        A method of the class that returns a payload to run the handle_docs function, as well as zeroing the message group buffer
        """
        payload = DocumentPayload(self.message, self.big_messages[self.user_id])
        self.big_messages[self.user_id] = []
        return payload
