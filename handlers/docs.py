from pathlib import Path
from docx import Document
from PyPDF2 import PdfReader

import requests

from core import bot, BOT_TOKEN


ALLOWED_TYPES = ('.doc', '.docx', '.pdf')


def doc_parser(message) -> str:
    file_info = bot.get_file(message.document.file_id)
    file_type = Path(file_info.file_path).suffix
    if file_type not in ALLOWED_TYPES:
        return

    download_url = f'https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}'

    r = requests.get(download_url, allow_redirects=True)

    if file_type == '.pdf':
        open('document.pdf', 'wb').write(r.content)

        pdf = PdfReader('document.pdf')
        pages = len(pdf.pages)
        text = "\n".join(page.extract_text() for page in pdf.pages)
    else:
        open('document.doc', 'wb').write(r.content)
        doc = Document('document.doc')

        text = "\n".join(p.text for p in doc.paragraphs)
    return text
