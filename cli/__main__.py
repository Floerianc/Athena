import os.path
import time
from typing import Optional
from colorama import (
    Fore,
    Style
)
from Athena.cli.style import DEFAULT_STYLE
from Athena.cli.parser import get_setup_data
import Athena.common.logger as logger
from Athena.common.types import (
    InputTypes,
    OutputTypes,
    QueryData,
    SetupData
)
from Athena.common.utils import clear_terminal
from Athena.core.search import SearchEngine
from Athena.core import db
from Athena.core.config import Config
from Athena.core.gpt import GPTQuery
from Athena.cli.progress import (
    ProgressMessage,
    ProgressBar,
)
from Athena.processor.processor import Processor

DEBUG = True
EXITING_PHRASE = "exiting..."
CLEAR_STYLING = Style.RESET_ALL

def wait_for_user(msg: str = "> ") -> str:
    query = input(msg)
    if query.lower() in ["exit", "quit", "q", "e"]:
        return EXITING_PHRASE
    else:
        return query

def print_debug(
    data: QueryData,
    start_time: Optional[float],
    end_time: Optional[float]
) -> None:
    print(
        f"{Fore.CYAN}[DEBUG] {str(data.query)}",
        f"[DEBUG] {str(data.result)}",
        f"[DEBUG] {str(data.rsp)}{CLEAR_STYLING}",
        sep="\n"
    )
    if start_time and end_time:
        print(f"{DEFAULT_STYLE.accent_color}Query took {end_time - start_time:.2f} seconds.\nModel: {config.response.model}{CLEAR_STYLING}")

def get_data() -> SetupData:
    return SetupData(
        input_type=InputTypes.AUTO,
        output_type=OutputTypes.MD,
        input_file=input(f"{DEFAULT_STYLE.main_color}[Athena] (Enter full path to input data file)> {CLEAR_STYLING}"),
        schema_file=input(f"{DEFAULT_STYLE.main_color}[Athena] (Enter full path to JSON schema file)> {CLEAR_STYLING}")
    )

def main_loop(user_data: SetupData) -> None:
    while True:
        user_input = wait_for_user(f"{DEFAULT_STYLE.main_color}[Athena] >{CLEAR_STYLING} ")
        if user_input == EXITING_PHRASE:
            break
        
        s = time.time()
        clean_results = search_engine.search_collection(
            user_input
        )
        query_data = QueryData(user_input, clean_results)
        gpt_response = GPTQuery(dbm, query_data, config, user_data["schema_file"], instant_request=True)
        print(gpt_response.response)
        if DEBUG:
            # gpt_response.save_debug()
            print_debug(query_data, start_time=s, end_time=time.time())


if __name__ == "__main__":
    data = get_setup_data()
    
    # loading config
    ProgressMessage(
        message="Loading configuration",
        timeout=0.5
    )
    config = Config(data['input_type'], data['output_type'])

    # loading db
    p = ProgressBar(
        title="Loading DB",
        description="Loading ChromaDB, OpenAI client, OpenAI embedding and GPTMemory module.",
        steps=5
    )
    dbm = db.DBManager(config, progress_bar=p)
    p.thread.join()

    # loading processor
    ProgressMessage(
        message="Processing input data",
        timeout=0.5
    )
    p2 = ProgressBar(
        title="Normalizing",
        description="Normalizing document length of input data" if config.input_type != InputTypes.JSON else "Converting JSON to strings",
        steps=1
    )
    processor = Processor(dbm, config, filename=data["input_file"], insert_json=True, progress_bar=p2)
    p2.thread.join()

    # loading search engine
    ProgressMessage(
        message="Loading Search Engine",
        timeout=0.5
    )
    search_engine = SearchEngine(config, dbm)

    # loading logger
    ProgressMessage(
        message="Loading Logger",
        timeout=0.5
    )
    clear_terminal()

    log = logger.get_logger()
    print(f"Full log: {Fore.YELLOW}{os.path.realpath(logger._log_path)}{Fore.RESET}")
    main_loop(data)