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
    def __init__(self, db: db.DBManager, config: Config, filename: str, insert_json: bool = True) -> None:
        self.db_manager = db
        self.config = config
        self.filename = filename
        self.data: List[Any] = []
        self.validate_input()
        
        if insert_json:
            self.db_manager._insert_json(self.data)
    
    def _stringize_data(self) -> None:
        for i in range(len(self.data)):
            dictionary = self.data[i]
            for key, value in dictionary.items():
                if not isinstance(value, str):
                    self.data[i][key] = str(value)
    
    def _check_keys(self) -> None:
        previous_keys = []
        
        for obj in self.data:
            keys = list(obj.keys())
            if not previous_keys:
                previous_keys = keys
            else:
                if previous_keys != keys:
                    raise KeyError("JSON schema must be consistant for every object.")
    
    def _contains_blank_lines(self, content: str) -> bool:
        return any(not line.strip() for line in content.splitlines())
    
    def _contains_large_lines(self, content: str) -> bool:
        return any(len(line) >= self.config.parse_chunk_size * 2 for line in content.splitlines())
    
    @log_event("Parsing text by blank lines...")
    def parse_by_blank(self, content: str) -> List[str]:
        return [line.strip() for line in content.splitlines() if line.strip()]
    
    @log_event("Parsing text by newlines...")
    def parse_by_newline(self, content: str) -> List[str]:
        return content.split("\n")
    
    @log_event("Parsing text by chunks...")
    def parse_by_chunk(self, content: str) -> List[str]:
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
    
    def _lengthen_doc(self, length: int, chunk_size: int, content: Documents, index: int, sep: str = " ") -> Document:
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
    
    def _shorten_doc(self, chunk_size: int, index: int, current_item: Document, content: Documents) -> Document:
        end = chunk_size
        current_item = current_item[0:end]
        content.insert(index+1, current_item[end:])
        return current_item
    
    @log_event("Chunking text file documents...")
    def normalize_document_lengths(self, content: Documents) -> Documents:
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
        self.data = self.db_manager._load_json(self.filename)
        self._check_keys()
        self._stringize_data()
    
    def validate_txt(self) -> None:
        self.data = self.txt_to_documents()
        if self.config.enforce_uniform_chunks:
            self.data = self.normalize_document_lengths(self.data)
    
    def validate_md(self) -> None:
        pass
    
    @log_event("Validating input file...")
    def validate_input(self) -> None:
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
    
    def _convert_nested_attr(self, value: Any, visited: set) -> Any:
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
    
    def dataclass_to_dict(self, instance: Any, visited: set) -> dict:
        obj = {}
        
        for field in fields(instance):
            attr = field.name
            value = getattr(instance, attr)
            obj[attr] = self._convert_nested_attr(value, visited)
        return obj
    
    def class_to_dict(self, instance: Any, visited: set) -> dict:
        obj = {}
        
        for attr, value in instance.__dict__.items():
            obj[attr] = self._convert_nested_attr(value, visited)
        return obj
    
    def type_to_dict(self, instance: Any) -> Any:
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