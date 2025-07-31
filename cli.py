import time
from typing import Optional
from colorama import (
    Fore,
    Style
)
from config import Config
from api.types import (
    InputTypes,
    OutputTypes,
    QueryData,
)
from db import DBManager
from processor import Processor
from search import SearchEngine
from gpt import GPTQuery
from api.benchmarks import (
    Benchmark,
    Settings
)

config = Config(InputTypes.PLAIN, OutputTypes.MD)
db = DBManager(config)
processor = Processor(db, config, filename="dumps/test.txt", insert_json=True)
search_engine = SearchEngine(config, db)

DEBUG = True
EXITING_PHRASE = "exiting..."
CLEAR_STYLING = Style.RESET_ALL

def wait_for_user(msg: str = "> ") -> str:
    query = input(msg)
    if query.lower() in ["exit", "quit", "q", "e"]:
        return EXITING_PHRASE
    else:
        return query

def print_debug(data: QueryData, start_time: Optional[float], end_time: Optional[float]) -> None:
    print(
        f"{Fore.CYAN}[DEBUG] {str(data.query)}",
        f"[DEBUG] {str(data.result)}",
        f"[DEBUG] {str(data.rsp)}{CLEAR_STYLING}",
        sep="\n"
    )
    if start_time and end_time:
        print(f"{Fore.GREEN}Query took {end_time - start_time:.2f} seconds.\nModel: {config.response.model}{CLEAR_STYLING}")

def main_loop() -> None:
    while True:
        user_input = wait_for_user(f"{Fore.MAGENTA}[Athena] >{CLEAR_STYLING} ")
        if user_input == EXITING_PHRASE:
            break
        
        s = time.time()
        clean_results = search_engine.search_collection(
            user_input
        )
        query_data = QueryData(user_input, clean_results)
        gpt_response = GPTQuery(db, query_data, config, "dumps/schema.json", instant_request=True)
        print(gpt_response.response)
        if DEBUG:
            # gpt_response.save_debug()
            print_debug(query_data, start_time=s, end_time=time.time())


if __name__ == "__main__":
    main_loop()