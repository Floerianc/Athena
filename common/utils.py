import math
import os
import platform
from typing import Union


WORD_PER_TOKEN = 0.75
CHAR_PER_TOKEN = 4


def tokens_to_words(tokens: int) -> float:
    return tokens * WORD_PER_TOKEN


def tokens_to_chars(tokens: int) -> int:
    return tokens * CHAR_PER_TOKEN


def words_to_tokens(words: int) -> int:
    return math.floor(words / WORD_PER_TOKEN)


def chars_to_tokens(chars: int) -> int:
    return math.floor(chars / CHAR_PER_TOKEN)


def interpret_size(size: int | float) -> str:
    sizes = ["B", "KB", "MB", "GB", "TB"]
    index = 0

    while True:
        if size > 1024 and index <= len(sizes) - 1:
            size /= 1024
            index += 1
        else:
            break
    return " ".join([f"{size:.2f}", sizes[index]])


def clear_terminal() -> None:
    name = platform.system()
    if name == "Windows":
        command = "cls"
    else:
        command = "system"
    os.system(command)

def rangespace(start: Union[int, float], stop: Union[int, float], steps: int) -> list[int | float]:
    step_size = (stop - start) / steps
    return [start + (step_size * iteration) for iteration in range(steps + 1)]