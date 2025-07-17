import os
from configparser import ConfigParser
from api_types import (
    OutputTypes,
    ResponseConfig,
    OutputHeaders
)

class Config:
    def __init__(self, output_type: 'OutputTypes') -> None:
        self.response = ResponseConfig()
        self.output_type = output_type
        self.output_header = OutputHeaders(self.output_type)
        
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
        files = os.listdir("./")
        for file in files:
            if ".ini" in file or ".cfg" in file:
                return (file, True)
        return ("", False)
    
    def load_values(self) -> None:
        self.response.model              = self.parser.get("Response", "ModelName")
        self.response.temperature        = self.parser.getfloat("Response", "Temperature")
        self.response.max_output_tokens  = self.parser.getint("Response", "MaxOutputTokens")
        self.response.top_p              = self.parser.getfloat("Response", "TopP")
        self.response.store              = self.parser.getboolean("Response", "Store")