from enum import Enum

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
    
    def __init__(self, output: 'OutputTypes') -> None:
        self.header = ""
        match output:
            case OutputTypes.PLAIN:
                self.header = self.PLAINTEXT_HEADER
            case OutputTypes.JSON:
                self.header = self.JSON_HEADER

class OutputTypes(Enum):
    PLAIN   = "plaintext"
    JSON    = "json"
    MD      = "markdown"