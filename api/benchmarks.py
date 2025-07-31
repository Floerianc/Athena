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
import api.utils as utils
from config import Config
from db import DBManager
from gpt import GPTQuery
from search import SearchEngine
from processor import Processor
from api.types import (
    QueryData,
    InputTypes,
    OutputTypes,
    Settings,
    BenchmarkResults,
    SystemInfo,
    DBInfo
)

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
        os = platform.uname()
        cpu = cpuinfo.get_cpu_info()
        ram = psutil.virtual_memory().total
        python_ver = sys.version_info
        
        self.system = SystemInfo(
            CPU = f"{cpu['brand_raw']} ({psutil.cpu_count(logical=False)} Cores)",
            RAM = utils.interpret_size(ram),
            OS = " ".join([os.system, os.release]),
            PY = " ".join([str(python_ver[0]), str(python_ver[1])])
        )
    
    def set_database_info(self) -> None:
        db_input = self.db.collection.get()
        file_size = os.stat(self.settings.input_file).st_size
        formatted_file_size = utils.interpret_size(file_size)
        with open(self.settings.input_file, "r") as file:
            words = len(file.read().split())
        
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
        print(f"{'Text parsing mode:'.ljust(key_width)}{self.config.txt_parseing}")
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
                gpt_response = GPTQuery(self.db, query_data, self.config, "dumps/schema.json", instant_request=True)
                
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
        self.export_benchmark()
    
    def export_benchmark(self) -> None:
        filename = datetime.now().strftime("%Y%m%d-%H%M%S")
        classes = [self.config, self.settings, self.system, self.db_info, self.results]
        json_objs = {}
        
        with open(f"logs/benchmark_{filename}.json", "a") as js:
            for class_instance in classes:
                json_objs[str(class_instance)] = self.processor.type_to_dict(class_instance)
            json.dump(json_objs, js, indent=4)
    
    def main(self) -> None:
        self.setup()
        self.show_info()
        time.sleep(3)
        
        print(f"{Fore.GREEN}STARTING BENCHMARK!{CLEAR_STYLE}")
        self.start_benchmark()
        self.finalize_benchmark()
    
    def testing_dummy(self) -> None:
        c = Config(input_type=InputTypes.AUTO, output_type=OutputTypes.MD)
        i = "C:\\Users\\stege.DESKTOP-VOI4DSV\\Desktop\\vir\\Athena_Full\\Athena\\dumps\\test.json"
        s = Settings(time.time(), i, ["Hallo, wie geht's dir?"], ["gpt-4.1-mini", "gpt-4.1-nano"])
        d = DBManager(c)
        p = Processor(d, c, i)
        
        b = Benchmark(p, c, s, d)
        
        b.setup()
        b.results = BenchmarkResults(
            timestamps=[(time.time() - 1, time.time())],
            model_responses=[
                QueryData(
                    "Hallo, wie geht es dir?",
                    {'documents': [["Hello"]]},
                    "Mir geht es super, danke!"
                )
            ],
            minTime=2,
            avgTime=2,
            maxTime=2
        )
        b.export_benchmark()