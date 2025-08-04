from enum import Enum
from dataclasses import dataclass
from colorama import Fore

ANSIColor = str


@dataclass
class ColorProfile:
    main_color: ANSIColor
    accent_color: ANSIColor


class Style(Enum):
    BLACK = ColorProfile(Fore.BLACK, Fore.LIGHTBLACK_EX)
    RED = ColorProfile(Fore.RED, Fore.LIGHTRED_EX)
    GREEN = ColorProfile(Fore.GREEN, Fore.LIGHTGREEN_EX)
    YELLOW = ColorProfile(Fore.YELLOW, Fore.LIGHTYELLOW_EX)
    BLUE = ColorProfile(Fore.BLUE, Fore.LIGHTBLUE_EX)
    MAGENTA = ColorProfile(Fore.MAGENTA, Fore.LIGHTMAGENTA_EX)
    CYAN = ColorProfile(Fore.CYAN, Fore.LIGHTCYAN_EX)
    WHITE = ColorProfile(Fore.WHITE, Fore.LIGHTWHITE_EX)


def get_style(key: str) -> ColorProfile:
    style_map = {
        'BLACK': Style.BLACK,
        'RED': Style.RED,
        'GREEN': Style.GREEN,
        'YELLOW': Style.YELLOW,
        'BLUE': Style.BLUE,
        'MAGENTA': Style.MAGENTA,
        'CYAN': Style.CYAN,
        'WHITE': Style.WHITE,
    }
    style = style_map.get(key.upper())
    if style:
        return style.value
    else:
        return Style.MAGENTA.value


DEFAULT_STYLE = get_style("")