import requests
import warnings
from urllib3.exceptions import InsecureRequestWarning

from db_process import get_voice
from settings import VOICES

# Отключение предупреждений о небезопасных запросах
warnings.simplefilter('ignore', InsecureRequestWarning)


def get_token():
    url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    headers = {
        "Authorization": "Basic MWM2OThhMDUtZjc1Mi00YzYxLWE5MWEtZjEyYjNlYWQ0NjcxOjRlNDc3ZmE5LWUwZTAtNDcwMS04Zjk5LTYyMjEzZDFmNzVkMg==",
        "RqUID": "3f7c0a1a-5b41-4a5d-981a-cb37d0e7c8a5",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {"scope": "SALUTE_SPEECH_PERS"}
    response = requests.post(url, headers=headers, data=data, verify=False)

    if response.status_code == 200:
        token_info = response.json()
        return token_info['access_token']
    else:
        raise Exception(f"Error getting token: {response.text}")


def synthesize_text(text):
    token = get_token()
    url = f"https://smartspeech.sber.ru/rest/v1/text:synthesize?format=opus&voice={VOICES[get_voice()]}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/text",
    }
    data = text.encode("utf-8")

    response = requests.post(url, headers=headers, data=data, verify=False)
    return response.content
