import db
import os
from dataclasses import fields
from chromadb.api.types import (
    Document,
    Documents
)
from typing import (
    List,
    Any,
)
from config import (
    Config,
    InputTypes,
    OutputTypes
)
from api.types import TextParsings
from api.logger import log_event

class Processor:
    def __init__(
        self, 
        db: db.DBManager, 
        config: Config, 
        filename: str, 
        insert_json: bool = True
    ) -> None:
        """__init__ Initialises Processor Class

        This class is used to process the input data
        so it can be stored in the ChromaDB database.

        Args:
            db (db.DBManager): DBManager for the ChromaDB classes
            config (Config): Configuration
            filename (str): Full path to the file
            insert_json (bool, optional): Instantly inserts data into Database upon initialisation. Defaults to True.
        """
        self.db_manager = db
        self.config = config
        self.filename = filename
        self.data: List[Any] = []
        self.validate_input()
        
        if insert_json:
            self.db_manager._insert_json(self.data)
    
    def _stringize_data(self) -> None:
        """_stringize_data Converts objects to strings

        Converts any non-string in the JSON to string
        """
        for i in range(len(self.data)):
            dictionary = self.data[i]
            for key, value in dictionary.items():
                if not isinstance(value, str):
                    self.data[i][key] = str(value)
    
    def _check_keys(self) -> None:
        """_check_keys Checks for key-consistancy

        Checks if all the keys in every object are consistant

        Raises:
            KeyError: If JSON schema is not consistant
        """
        previous_keys = []
        
        for obj in self.data:
            keys = list(obj.keys())
            if not previous_keys:
                previous_keys = keys
            else:
                if previous_keys != keys:
                    raise KeyError("JSON schema must be consistant for every object.")
    
    def _contains_blank_lines(
        self, 
        content: str
    ) -> bool:
        """_contains_blank_lines If content contains blank lines

        This checks every line in content string for a blank line.

        Args:
            content (str): Any string

        Returns:
            bool: True if there are blank lines
        """
        return any(not line.strip() for line in content.splitlines())
    
    def _contains_large_lines(
        self, 
        content: str
    ) -> bool:
        """_contains_large_lines If content has large lines

        Returns a boolean to tell if any string contains very long
        lines.
        
        This is partially to determine the parsing technique for
        plain-text inputs.
        
        It uses the parse_chunk_size config value as a reference
        to check if a line is extraordinary long.

        Args:
            content (str): Any string lol

        Returns:
            bool: True if contains very long lines.
        """
        return any(len(line) >= self.config.parse_chunk_size * 2 for line in content.splitlines())
    
    @log_event("Parsing text by blank lines...")
    def parse_by_blank(
        self, 
        content: str
    ) -> List[str]:
        """parse_by_blank Parses plain text

        Parses plain text content by blank lines

        Args:
            content (str): Any string

        Returns:
            List[str]: List of strings
        """
        return [line.strip() for line in content.splitlines() if line.strip()]
    
    @log_event("Parsing text by newlines...")
    def parse_by_newline(self, content: str) -> List[str]:
        """parse_by_newline Parses plain text

        Parses plain text content by newlines.

        Args:
            content (str): Any string :)

        Returns:
            List[str]: List of strings
        """
        return content.split("\n")
    
    @log_event("Parsing text by chunks...")
    def parse_by_chunk(
        self, 
        content: str
    ) -> List[str]:
        """parse_by_chunk Parses plain text

        If the file is for example just one very large line
        it doesn't make sense to parse by newlines or anything
        so this instead stores it as a list of chunks.
        
        The chunk size can be modified in the configuration file.

        Args:
            content (str): Any string

        Returns:
            List[str]: List of string chunks.
        """
        output_lines = []
        length = len(content)
        chunk_size = self.config.parse_chunk_size
        i0 = 0
        i1 = lambda: i0 + chunk_size
        
        while True:
            i = i1() if i1() <= length else length
            chunk = content[i0:i]
            output_lines.append(chunk)
            if i >= length:
                break
        return output_lines
    
    @log_event("Turning text file into documents...")
    def txt_to_documents(self) -> Documents:
        """txt_to_documents Converts text to Documents

        This method converts a plain text file into
        ChromaDB database ready Documents.

        Raises:
            ValueError: If the parsing method can't be found

        Returns:
            Documents: List of Strings for the database
        """
        filter_method = self.config.txt_parseing
        with open(os.path.realpath(self.filename), "r", encoding="UTF-8") as file:
            content = file.read()
        
        # holy shit this is ugly
        match filter_method:
            case TextParsings.AUTO:
                if self._contains_blank_lines(content):
                    return self.parse_by_blank(content)
                else:
                    if self._contains_large_lines(content):
                        return self.parse_by_chunk(content)
                    else:
                        return self.parse_by_newline(content)
            case TextParsings.BY_BLANK:
                return self.parse_by_blank(content)
            case TextParsings.BY_NEWLINE:
                return self.parse_by_newline(content)
            case TextParsings.BY_CHUNK:
                return self.parse_by_chunk(content)
            case _:
                raise ValueError(f"Unknown text parsing method: {filter_method}")
    
    def _lengthen_doc(
        self, 
        length: int, 
        chunk_size: int, 
        content: Documents, 
        index: int, 
        sep: str = " "
    ) -> Document:
        """_lengthen_doc Fallback function

        This is a fallback function for files that
        enforce being parsed by chunks.
        
        This is quite complex and seriously ugly but essentially
        it takes the content of a line and looks for the max chunk size
        to save the excess in the same line, essentially lenghtening each line
        to amount of `chunk_size`.
        
        For example:\n
        'Hello how are you'\n
        'doing my friend'\n
        gets turned into\n
        
        'Hello how are you doing my' <-- reached max chunk size\n
        'friend' <-- anything outside of chunk size remains untouched

        Args:
            length (int): Length of line
            chunk_size (int): Max chunk size
            content (Documents): Every line from the file
            index (int): Current index of the line in `content`
            sep (str, optional): Seperator between lines. Defaults to " ".

        Returns:
            Document: Lengthened line
        """
        start = index
        end = index + 1
        total_length = length
        last_index = len(content) - 1
        lengthened_doc = ""
        
        while True:
            is_last = end > last_index
            new_doc: Document = content[end] if not is_last else ""
            
            total_length += len(new_doc)
            if total_length >= chunk_size:
                excess = total_length - chunk_size
                lengthened_doc = sep.join(content[start:end])
                
                if excess > 0:
                    overflow = content[end][:excess]
                    cutoff = content[end][excess:]
                    content[end] = cutoff
                    lengthened_doc = f"{lengthened_doc}{sep}{overflow}".strip()
                
                del content[start:end-1]
                break
            elif is_last:
                lengthened_doc = sep.join(content[start:end])
                del content[start:end-1]
                break
            else:
                end += 1
        return lengthened_doc
    
    def _shorten_doc(
        self, 
        chunk_size: int, 
        index: int, 
        current_item: Document, 
        content: Documents
    ) -> Document:
        """_shorten_doc Fallback function

        This is the opposite of _lengthen_doc() as this
        shortens a line from the File and inserts the excess
        into the next line.

        Args:
            chunk_size (int): Max chunk size
            index (int): Current index in the list
            current_item (Document): Current line string
            content (Documents): Full list of every string

        Returns:
            Document: Shortened string
        """
        end = chunk_size
        current_item = current_item[0:end]
        content.insert(index+1, current_item[end:])
        return current_item
    
    @log_event("Chunking text file documents...")
    def normalize_document_lengths(
        self, 
        content: Documents
    ) -> Documents:
        """normalize_document_lengths I hate this

        This is the primary fallback function for files that enforce the
        normalizing of document lengths. This is to save tokens for each
        database input while remaining consistant with every input length.
        
        This took way too long to code and is ridiculously ugly but it works
        as a fallback.

        Args:
            content (Documents): List of every line in the file

        Returns:
            Documents: List of every normalized line
        """
        # I spent like 1.5 hours on trying to make this work 
        # just to realise that I am already chunking data
        # with another function so this is quite useless but
        # idgaf this is now just a smart utility tool :)
        chunk_size = self.config.parse_chunk_size
        
        for index, doc in enumerate(content):
            length = len(doc)
            
            if length < chunk_size:
                content[index] = self._lengthen_doc(length, chunk_size, content, index)
            elif length > chunk_size:
                content[index] = self._shorten_doc(chunk_size, index, content[index], content)
            else:
                continue
        return content
    
    def validate_json(self) -> None:
        """validate_json Validates JSON input data

        Validates the JSON input data and then upserts it into
        the ChromaDB database.
        """
        self.data = self.db_manager._load_json(self.filename)
        self._check_keys()
        self._stringize_data()
    
    def validate_txt(self) -> None:
        """validate_txt Validates Plain-text input data

        Validates the Plain-text input data and then upserts it into
        the ChromaDB database.
        """
        self.data = self.txt_to_documents()
        if self.config.enforce_uniform_chunks:
            self.data = self.normalize_document_lengths(self.data)
    
    def validate_md(self) -> None:
        pass
    
    @log_event("Validating input file...")
    def validate_input(self) -> None:
        """validate_input Validates the input file

        Pretty self-explanatory, check individual methods
        for more info.
        """
        match self.config.input_type:
            case InputTypes.AUTO:
                ext = os.path.splitext(self.filename)[1].lower()
                match ext:
                    case ".json":
                        self.validate_json()
                    case ".txt":
                        self.validate_txt()
                    case ".md":
                        self.validate_md()
            case InputTypes.JSON:
                self.validate_json()
            case InputTypes.PLAIN:
                self.validate_txt()
            case InputTypes.MD:
                self.validate_md()
    
    def _convert_nested_attr(
        self, 
        value: Any, 
        visited: set
    ) -> Any:
        """_convert_nested_attr Converts attributes of a class/dataclass

        This is a ridiculous method to convert every attribute of a class
        or dataclass into a JSON-serializable type, usually string or dictionary.
        
        This is primarily used by the benchmarking features as this requires
        the state of a class to be captured and saved in a file.

        Args:
            value (Any): Class / Dataclass instance
            visited (set): Set of visited values

        Returns:
            Any: Could be a string, list or dictionary
        """
        if id(value) in visited:
            return "<circular reference detected>"
        visited.add(id(value))
        
        if hasattr(value, "__dataclass_fields__"):
            return self.dataclass_to_dict(value, visited)
        elif hasattr(value, "__dict__"):
            return self.class_to_dict(value, visited)
        elif isinstance(value, list):
            return [self._convert_nested_attr(v, visited) for v in value]
        elif isinstance(value, dict):
            return {k: self._convert_nested_attr(v, visited) for k, v in value.items()}
        else:
            return str(value)
    
    def dataclass_to_dict(
        self, 
        instance: Any, 
        visited: set
    ) -> dict:
        """dataclass_to_dict Converts a dataclass

        This uses recursive methods to convert a dataclass
        into a dictionary which is able to be JSON-serialized

        Args:
            instance (Any): Dataclass instance
            visited (set): Set of visited values (classes, types etc.)

        Returns:
            dict: Dictionary containing variables and their values (variable_name: value)
        """
        obj = {}
        
        for field in fields(instance):
            attr = field.name
            value = getattr(instance, attr)
            obj[attr] = self._convert_nested_attr(value, visited)
        return obj
    
    def class_to_dict(
        self, 
        instance: Any, 
        visited: set
    ) -> dict:
        """class_to_dict Converts a class

        This uses recursive methods to convert a regular class
        into a dictionary which is able to be JSON-serialized

        Args:
            instance (Any): Class instance
            visited (set): Set of visited values (classes, types etc.)

        Returns:
            dict: Dictionary containing variables and their values (variable_name: value)
        """
        obj = {}
        
        for attr, value in instance.__dict__.items():
            obj[attr] = self._convert_nested_attr(value, visited)
        return obj
    
    def type_to_dict(
        self, 
        instance: Any
    ) -> Any:
        """type_to_dict Converts an instance

        This function converts a class/dataclass instance
        into a JSON-serializable object.
        
        For more info, check the individual methods.

        Args:
            instance (Any): (Data)class instance

        Returns:
            Any: JSON-serializable object (e.g. dictionary)
        """
        return self._convert_nested_attr(instance, visited=set())

if __name__ == "__main__":
    c = Config(InputTypes.PLAIN, OutputTypes.PLAIN)
    p = Processor(
        db=db.DBManager(config=c),
        config=c,
        filename='dumps/test.txt',
        insert_json=True
    )
    print(p.data)