import logging
from typing import Callable

logging.basicConfig(
    filename="./logs/log.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
log = logging.getLogger(__name__)

# idk how decorators work i just copied this from somewhere lol
def log_event(msg: str):
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            log.info(f"{func.__name__}: {msg}")
            result = func(*args, **kwargs) # type: ignore
            return result
        return wrapper
    return decorator

def get_logger() -> logging.Logger:
    return log