from keyboards import (
    DOC_MARKUP,
    GROUP_DOC_MARKUP,
    AUDIO_MARKUP,
    GROUP_AUDIO_MARKUP,
    CLEANER
)
from models.claude_parser import ClaudeParser
from models.openai_parser import OpenAIParser
from handlers import states

import os
import dotenv

import db_process

dotenv.load_dotenv()

# Chat base settings
PER_MODE = False
LIST_OF_ADMINS = (884263454, 14835038, 486707676, 1507436684, 63765009)
ALLOWED_USERS = (976870658, ) + LIST_OF_ADMINS

State = states.StateCustom()

STATES_BTN = {
    'main': CLEANER,
    'doc': DOC_MARKUP,
    'audio': AUDIO_MARKUP
}

GROUP_STATES_BTN = {
    'main': CLEANER,
    'doc': GROUP_DOC_MARKUP,
    'audio': GROUP_AUDIO_MARKUP
}


# Chat model
CHAT_TEMP = float(db_process.get_temperature())

CALLBACK_TO_MODES = {
    '3.5_tur': OpenAIParser(os.getenv("OPEN_API_KEY"), 'gpt-3.5-turbo'),
    #'4': OpenAIParser(os.getenv("OPEN_API_KEY"), 'gpt-4'),
    '3.5_tur16': OpenAIParser(os.getenv("OPEN_API_KEY"), 'gpt-3.5-turbo-16k'),
    '1.3_100k': ClaudeParser(os.getenv("ANTHROPIC_API_KEY"), 'claude-1.3-100k'),
    'i_1.2_100k': ClaudeParser(os.getenv("ANTHROPIC_API_KEY"), 'claude-instant-1.2'),
    '2': ClaudeParser(os.getenv("ANTHROPIC_API_KEY"), 'claude-2')
}

CURRENT_MODE = CALLBACK_TO_MODES[db_process.get_ai_model()]

# Voice settings
VOICES = {
    'наталья': 'Nec_24000',
    'борис': 'Bys_24000',
    'марфа': 'May_24000',
    'тарас': 'Tur_24000',
    'александра': 'Ost_24000',
    'сергей': 'Pon_24000',
    'kira (EN)': 'Kin_24000'
}
CURRENT_VOICE = VOICES[db_process.get_voice()]


# Dirs
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_prompt():
    path = os.path.join(BASE_DIR, 'telegram_ai', 'temp', 'prompt.txt')
    if os.path.exists(path):
        return path
    else:
        with open(os.path.join(path), "w") as f:
            f.write("Ты ассистент помошник!")
        return path


def get_prompt_doc():
    path = os.path.join(BASE_DIR, 'telegram_ai', 'temp', 'prompt_doc.txt')
    if os.path.exists(path):
        return path
    else:
        with open(os.path.join(path), "w") as f:
            f.write('Герменевтический анализ и  семантическая дестиляция'
                    ' этого документа в виде  маркированного списка с эмоджи.'
                    ' Язык русский')
        return path


def get_prompt_audio():
    path = os.path.join(BASE_DIR, 'telegram_ai', 'temp', 'prompt_audio.txt')
    if os.path.exists(path):
        return path
    else:
        with open(os.path.join(path), "w") as f:
            f.write('Герменевтический анализ и  семантическая дестиляция'
                    ' этого документа в виде  маркированного списка с эмоджи.'
                    ' Язык русский')
        return path


PROMPT_DIR = get_prompt()
PROMPT_DOC_DIR = get_prompt_doc()
PROMPT_AUDIO_DIR = get_prompt_audio()

PROMPT_MAX_OPENAI = 6000
MAX_TOKENS = 90000

EXCEPTION_ID = -947536198

SUPPORTED_FORMATS = ['.m4a', '.mp3', '.ogg', '.wav', '.aac', '.opus']

# response open ai settings
OPEN_AI_TEMPERATURE = 0    # default value = 0;   between 0 and 2

STREAM_RESPONSE=True
