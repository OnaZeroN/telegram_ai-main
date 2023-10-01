from typing import TypedDict


class ApiError(Exception):
    code: int
    description: str


def handle_error(error: ApiError):
    if error.code == 400:
        parse_400_error(error)
    else:
        ...


def parse_400_error(e: ApiError) -> None:
    if "can't parse entities" in e.description:
        ...
        #fix_parse_entities_error()

