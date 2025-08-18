import psutil
import sys
import os
import cpuinfo
import time
import json
import platform
from colorama import (
    Fore,
    Style
)
from datetime import datetime
import Athena.common.utils as utils
from Athena.core.config import Config
from Athena import _internal_dir
from Athena.core.db import DBManager
from Athena.core.gpt import GPTQuery
from Athena.core.search import SearchEngine
from Athena.processor import Processor
from Athena.common.types import (
    QueryData,
    Settings,
    BenchmarkResults,
    SystemInfo,
    DBInfo,
    InputTypes, OutputTypes
)
from Athena.cli.style import DEFAULT_STYLE

CLEAR_STYLE = Style.RESET_ALL
RESULT_HEADER = " BENCHMARK RESULTS ".center(80, "-")

class Benchmark:
    def __init__(self, processor: Processor, config: Config, settings: Settings, db: DBManager) -> None:
        self.settings = settings
        self.db = db
        self.config = config
        self.processor = processor
        self.search = SearchEngine(self.config, db)
        self.results = BenchmarkResults()
        
        self.system: SystemInfo
        self.db_info: DBInfo
        
        self.key_width = 20
        self.console_width = 80
    
    def set_system_info(self) -> None:
        os_name = platform.uname()
        cpu = cpuinfo.get_cpu_info()
        ram = psutil.virtual_memory().total
        python_ver = sys.version_info
        
        self.system = SystemInfo(
            CPU = f"{cpu['brand_raw']} ({psutil.cpu_count(logical=False)} Cores)",
            RAM = utils.interpret_size(ram),
            OS = " ".join([os_name.system, os_name.release]),
            PY = " ".join([str(python_ver[0]), str(python_ver[1])])
        )
    
    def set_database_info(self) -> None:
        db_input = self.db.collection.get()
        file_size = os.stat(self.settings.input_file).st_size
        formatted_file_size = utils.interpret_size(file_size)
        with open(self.settings.input_file, "r") as file:
            try:
                words = len(file.read().split())
            except:
                print("Too lazy to add functionality to read PDF file lol")
                words = -1
        
        self.db_info = DBInfo(
            input_size = formatted_file_size,
            input_tokens = utils.words_to_tokens(words),
            documents = len(db_input['documents']) if db_input["documents"] else 0
        )
    
    def setup(self) -> None:
        self.set_system_info()
        self.set_database_info()
    
    def show_info(self) -> None:
        key_width = self.key_width
        print(Fore.CYAN)
        print("Benchmark settings".center(self.console_width, "-"))
        print(f"{'Uniform chunks:'.ljust(key_width)}{self.config.enforce_uniform_chunks}")
        print(f"{'Input type:'.ljust(key_width)}{self.config.input_type.value}")
        print(f"{'Output type:'.ljust(key_width)}{self.config.output_type.value}")
        print(f"{'Max memory entries:'.ljust(key_width)}{self.config.max_entries}")
        print(f"{'Max memory results:'.ljust(key_width)}{self.config.max_search_results}")
        print(f"{'Parsing chunk size:'.ljust(key_width)}{self.config.parse_chunk_size}")
        print(f"{'Max distance:'.ljust(key_width)}{self.config.search_max_distance}")
        print(f"{'Max search results:'.ljust(key_width)}{self.config.search_max_results}")
        print(f"{'Max search tokens:'.ljust(key_width)}{self.config.search_max_tokens}")
        print(f"{'Tokens per memory:'.ljust(key_width)}{self.config.tokens_per_memory}")
        print(f"{'Text parsing mode:'.ljust(key_width)}{self.config.txt_parsing}")
        print(f"{'Timestamp:'.ljust(key_width)}{self.settings.timestamp}")
        print(f"{'Input file:'.ljust(key_width)}{self.settings.input_file}")
        print(f"{'Models:'.ljust(key_width)}{self.settings.models}")
        print(f"{'User inputs:'.ljust(key_width)}{self.settings.user_inputs}")
        print()
        print("System information".center(self.console_width, "-"))
        print(f"{'CPU:'.ljust(key_width)}{self.system.CPU}")
        print(f"{'Total RAM:'.ljust(key_width)}{self.system.RAM}")
        print(f"{'OS:'.ljust(key_width)}{self.system.OS}")
        print(f"{'Python version:'.ljust(key_width)}{self.system.PY}")
        print()
        print("Database information".center(self.console_width, "-"))
        print(f"{'Documents:'.ljust(key_width)}{self.db_info.documents}")
        print(f"{'Input file size:'.ljust(key_width)}{self.db_info.input_size}")
        print(f"{'Input file tokens:'.ljust(key_width)}{self.db_info.input_tokens}")
        print(CLEAR_STYLE)
    
    def start_benchmark(self) -> None:
        for model in self.settings.models:
            for user_input in self.settings.user_inputs:
                start = time.perf_counter()
                
                clean_results = self.search.search_collection(
                    user_input
                )
                query_data = QueryData(user_input, clean_results)
                gpt_response = GPTQuery(self.db, query_data, self.config, self.settings.schema_path, instant_request=True)
                
                end = time.perf_counter()
                
                print(f"Successfully got a response from {Fore.GREEN}{model}{CLEAR_STYLE} with input of {Fore.GREEN}{user_input}{CLEAR_STYLE}")
                self.results.timestamps.append((start, end))
                self.results.model_responses.append(query_data)
    
    def finalize_times(self) -> None:
        times = []
        for time_tuple in self.results.timestamps:
            start = time_tuple[0]
            end = time_tuple[1]
            times.append(end - start)
        
        self.results.minTime = min(times)
        self.results.maxTime = max(times)
        self.results.avgTime = sum(times) / len(times)
    
    def show_times(self) -> None:
        key_width = self.key_width
        
        print(Fore.CYAN)
        print("\n")
        print("BENCHMARK RESULTS".center(self.console_width, "-"))
        print("\n")
        print(f"{'All times:'.ljust(key_width)}{self.results.timestamps}")
        print(f"{'Min time:'.ljust(key_width)}{self.results.minTime:.2f} s")
        print(f"{'Max time:'.ljust(key_width)}{self.results.maxTime:.2f} s")
        print(f"{'Avg time:'.ljust(key_width)}{self.results.avgTime:.2f} s")
        print(CLEAR_STYLE)
    
    def finalize_benchmark(self) -> None:
        self.finalize_times()
        self.show_times()
        # self.export_benchmark()
    
    def export_benchmark(self) -> None:
        filename = datetime.now().strftime("%Y%m%d-%H%M%S")
        classes = [self.config, self.settings, self.system, self.db_info, self.results]
        json_objs = {}
        
        with open(os.path.join(_internal_dir, f"benchmarks/{filename}.json"), "a") as js:
            for class_instance in classes:
                json_objs[str(class_instance)] = self.processor.serializer.type_to_dict(class_instance)
            json.dump(json_objs, js, indent=4)
    
    def main(self) -> None:
        self.setup()
        self.show_info()
        time.sleep(3)
        
        print(f"{Fore.GREEN}STARTING BENCHMARK!{CLEAR_STYLE}")
        self.start_benchmark()
        self.finalize_benchmark()
    
    # def testing_dummy(self) -> None:
    #     c = Config(input_type=InputTypes.AUTO, output_type=OutputTypes.MD)
    #     i = ".\\dumps\\test.json"
    #     s = Settings(time.time(), i, ["Hallo, wie geht's dir?"], ["gpt-4.1-mini", "gpt-4.1-nano"])
    #     d = DBManager(c)
    #     p = Processor(d, c, i)
    #
    #     b = Benchmark(p, c, s, d)
    #
    #     b.setup()
    #     b.results = BenchmarkResults(
    #         timestamps=[(time.time() - 1, time.time())],
    #         model_responses=[
    #             QueryData(
    #                 "Hallo, wie geht es dir?",
    #                 {'documents': [["Hello"]]},
    #                 "Mir geht es super, danke!"
    #             )
    #         ],
    #         minTime=2,
    #         avgTime=2,
    #         maxTime=2
    #     )
    #     b.export_benchmark()


def get_inputs() -> list[str]:
    inputs = []
    while True:
        user_input = input("Input to the model ('exit' to finish): ")
        if user_input.lower() == "exit":
            break
        else:
            inputs.append(user_input)
    return inputs


if __name__ == "__main__":
    from Athena.cli.progress import ProgressBar
    models = [
        "gpt-4.1",
        "gpt-4.1-mini",
        "gpt-4.1-nano",
    ]

    print(f"{DEFAULT_STYLE.main_color}Check the source code of this benchmark script to change models{CLEAR_STYLE}\nCurrently testing these models: {Fore.CYAN}{models}{CLEAR_STYLE}")
    input_file = input("Please enter the full path of the input file: ")
    utils.clear_terminal()

    cfg = Config(InputTypes.AUTO, OutputTypes.MD)

    p1 = ProgressBar(title="Loading DB", description="", steps=5)
    dbm = DBManager(config=cfg, progress_bar=p1)
    p1.thread.join()

    prc = Processor(db=dbm, config=cfg, filename=input_file, insert_json=True)
    settings = Settings(
        timestamp=time.time(),
        input_file=input_file,
        user_inputs=get_inputs(),
        schema_path=input("Enter the full path to the JSON Schema: "),
        models=models
    )
    b = Benchmark(processor=prc, config=cfg, db=dbm, settings=settings)
    b.main()

    option = input("Export full benchmark results? (y/n)\n> ")
    if option.lower() == "y":
        b.export_benchmark()