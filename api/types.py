from enum import Enum
from dataclasses import (
    dataclass,
    field
)
from typing import (
    Union,
    List,
    TYPE_CHECKING
)
from chromadb.api.types import QueryResult

if TYPE_CHECKING:
    pass

class Models(Enum):
    BEST        = "gpt-4.1"         # Best allrounder. However, also most expensive     ($2   / 1M  tokens)
    BALANCED    = "gpt-4.1-mini"    # Good allrounder, quite cheap                      ($1.1 / 1M  tokens)
    FASTER      = "gpt-4.1-nano"    # Overall okay, very low latency and price          ($0.1 / 1M  tokens)
    FASTEST     = "gpt-3.5-turbo"   # Affordable and Fastest model, but worst quality   ($0.5 / 1M  tokens)
    REASONING   = "o4-mini"         # Affordable good reasoning model                   ($1.1 / 1M  tokens)


class TextParsings(Enum):
    AUTO        = "auto"            # Automatically detect the best parsing method
    BY_BLANK    = "by_blank"        # Split by blank spaces
    BY_NEWLINE  = "by_newline"      # Split by newlines
    BY_CHUNK    = "by_chunk"        # Split by chunks

@dataclass
class ResponseConfig:
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
    Respond with a markdown text where you answer the latest User-Querys questions in detail and respond to the latest User-Querys statements accordingly.
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


class InputTypes(Enum):
    AUTO    = "auto"
    PLAIN   = "txt"
    JSON    = "json"
    MD      = "md"
    PDF     = "pdf"


class QueryData:
    def __init__(self, query: str, data: Union[dict, QueryResult], rsp: Union[str, dict, None] = None) -> None:
        self.result = data
        self.query = query
        self.rsp = rsp


@dataclass
class Settings:
    timestamp: float
    input_file: str
    user_inputs: List[str]
    models: List[str]


@dataclass
class SystemInfo:
    CPU: str
    RAM: str
    OS: str
    PY: str


@dataclass
class DBInfo:
    input_size: str
    input_tokens: int
    documents: int


@dataclass
class BenchmarkResults:
    timestamps: List[tuple[float, float]] = field(default_factory=list)
    model_responses: List[QueryData] = field(default_factory=list)
    minTime: float = field(default_factory=float)
    avgTime: float = field(default_factory=float)
    maxTime: float = field(default_factory=float)