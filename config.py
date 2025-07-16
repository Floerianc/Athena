import os
from configparser import ConfigParser
from enum import Enum
from dataclasses import dataclass

class Models(Enum):
    BEST        = "gpt-4.1"         # Best allrounder. However, also most expensive     ($2   / 1M  tokens)
    BALANCED    = "gpt-4.1-mini"    # Good allrounder, quite cheap                      ($1.1 / 1M  tokens)
    LATENCY     = "gpt-4.1-nano"    # Overall okay, very low latency and price          ($0.1 / 1M  tokens)
    REASONING   = "o4-mini"         # Affordable good reasoning model                   ($1.1 / 1M  tokens)

@dataclass
class Response:
    model: str              = Models.BALANCED.value
    temperature: float      = 1.0
    max_output_tokens: int  = 1024
    top_p: float            = 1
    store: bool             = True


class OutputHeaders:
    PLAINTEXT_HEADER = """
    You are a strict plain-text generator for a general purpose AI with deep understanding of given data and questions.
    Output a single valid plain-text object and try to connect the given data with the given user query to answer their
    questions, statements and more. Remain formal and factually correct whenever useful.
    """
    
    JSON_HEADER = """
    You are a strict JSON-object generator for a general purpose AI with deep understanding of given data and questions.
    Output a single valid JSON object and try to connect the given data with the given user query to answer their
    questions, statements and more. Remain formal and factually correct whenever useful.
    
    Additionally, follow the following JSON-schema:
    """
    
    MARKDOWN_HEADER = """
    You are a strict markdown generator for a general purpose AI with deep understanding of given data and questions.
    Output a single valid markdown object and try to connect the given data with the given user query to answer their
    questions, statements and more. Remain formal and factually correct whenever useful.
    """
    
    def __init__(self, output: 'OutputTypes') -> None:
        self.header = ""
        match output:
            case OutputTypes.PLAIN:
                self.header = self.PLAINTEXT_HEADER
            case OutputTypes.JSON:
                self.header = self.JSON_HEADER
            case OutputTypes.MD:
                self.header = self.MARKDOWN_HEADER

class OutputTypes(Enum):
    PLAIN   = "plaintext"
    JSON    = "json"
    MD      = "markdown"


class Config:
    def __init__(self, output_type: 'OutputTypes') -> None:
        self.response = Response()
        self.output_type = output_type
        self.output_header = OutputHeaders(self.output_type)
        
        cfg = self.check_for_cfg()
        if cfg[1]:
            self.parser = ConfigParser()
            self.parser.read(cfg[0])
            self.load_values()
    
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