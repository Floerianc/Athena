import os
from configparser import ConfigParser
from Athena.common.types import (
    InputTypes,
    OutputTypes,
    ResponseConfig,
    OutputHeaders,
    TextParsings
)

class Config:
    def __init__(
        self, 
        input_type: 'InputTypes' = InputTypes.AUTO, 
        output_type: 'OutputTypes' = OutputTypes.MD
    ) -> None:
        # gpt communication
        self.output_type = output_type
        self.input_type = input_type
        self.response = ResponseConfig()
        self.output_header = OutputHeaders(self.output_type)
        
        # .txt parsing
        self.txt_parsing = TextParsings.AUTO
        self.enforce_uniform_chunks: bool = True
        self.parse_chunk_size = 512     # chars --> tokens
        
        # memory management
        self.max_entries = 5
        self.max_search_results = 3
        self.tokens_per_memory = 200    # tokens
        
        # searching chromadb
        self.search_max_tokens = 2048   # tokens
        self.search_max_distance = 1.2
        self.search_max_results = 96
        
        cfg = self.check_for_cfg()
        if cfg[1]:
            self.parser = ConfigParser()
            self.parser.read(cfg[0])
            self.load_values()
    
    @property
    def base_params(self) -> dict:
        return {
            'model': self.response.model,
            'input': [],
            "reasoning": {},
            "tools": [],
            "temperature": self.response.temperature,
            "max_output_tokens": self.response.max_output_tokens,
            "top_p": self.response.top_p,
            "store": self.response.store
        }
    
    def check_for_cfg(self) -> tuple[str, bool]:
        """check_for_cfg Checks if the root folder has a config file
        
        Checks for any .ini or .cfg files in the root folder
        and returns a boolean and its path
        
        Returns:
            tuple[str, bool]: Path to the config file and boolean
        """
        files = os.listdir("./")
        for file in files:
            if ".ini" in file or ".cfg" in file:
                return (file, True)
        return ("", False)
    
    def load_values(self) -> None:
        self.response.model             = self.parser.get("Response", "ModelName")
        self.response.temperature       = self.parser.getfloat("Response", "Temperature")
        self.response.max_output_tokens = self.parser.getint("Response", "MaxOutputTokens")
        self.response.top_p             = self.parser.getfloat("Response", "TopP")
        self.response.store             = self.parser.getboolean("Response", "Store")
        
        self.parse_chunk_size           = self.parser.getint("Parsing", "TextParsingChunkSize")
        self.enforce_uniform_chunks     = self.parser.getboolean("Parsing", "EnforceUniformChunks")
        
        self.max_entries                = self.parser.getint("Memory", "Entries")
        self.tokens_per_memory          = self.parser.getint("Memory", "TokensPerMemory")
        self.max_search_results         = self.parser.getint("Memory", "SearchResults")
        
        self.search_max_tokens          = self.parser.getint("Search", "MaxTokens")
        self.search_max_distance        = self.parser.getfloat("Search", "MaxDistance")
        self.search_max_results         = self.parser.getint("Search", "MaxResults")