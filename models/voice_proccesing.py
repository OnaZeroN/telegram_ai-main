import os
import pydub
import uuid

from settings import BASE_DIR

AUDIOS_DIR = os.path.join(BASE_DIR, 'telegram_ai', 'temp', 'voice')


def create_dir_if_not_exists(dir):
    if not os.path.exists(dir):
        os.mkdir(dir)


def generate_unique_name():
    uuid_value = uuid.uuid4()
    return f"{str(uuid_value)}"


def download_voice_as_ogg(downloaded_file):
    create_dir_if_not_exists(AUDIOS_DIR)
    ogg_filepath = os.path.join(AUDIOS_DIR, f"{generate_unique_name()}.ogg")
    with open(ogg_filepath, 'wb') as new_file:
        new_file.write(downloaded_file)

    return ogg_filepath


def convert_ogg_to_mp3(ogg_filepath, format="ogg"):
    mp3_filepath = os.path.join(AUDIOS_DIR, f"{generate_unique_name()}.mp3")
    audio = pydub.AudioSegment.from_file(ogg_filepath, format=format)
    audio.export(mp3_filepath, format="mp3")
    return mp3_filepath
