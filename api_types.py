from enum import Enum
from dataclasses import dataclass
from typing import (
    Union,
    Optional,
    TYPE_CHECKING
)
from chromadb.api.types import QueryResult

if TYPE_CHECKING:
    pass

class Models(Enum):
    BEST        = "gpt-4.1"         # Best allrounder. However, also most expensive     ($2   / 1M  tokens)
    BALANCED    = "gpt-4.1-mini"    # Good allrounder, quite cheap                      ($1.1 / 1M  tokens)
    LATENCY     = "gpt-4.1-nano"    # Overall okay, very low latency and price          ($0.1 / 1M  tokens)
    REASONING   = "o4-mini"         # Affordable good reasoning model                   ($1.1 / 1M  tokens)


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


class QueryData:
    def __init__(self, query: str, data: QueryResult, rsp: Optional[str] = None) -> None:
        self.result = data
        self.query = query
        self.rsp = rsp