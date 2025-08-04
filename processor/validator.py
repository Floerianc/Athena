import os
from typing import (
    List,
    Any,
    TYPE_CHECKING
)
from Athena.config import Config
from Athena.db import DBManager
from Athena.processor.normalizer import DocumentNormalizer
from Athena.processor.parser import DocumentParser
from Athena.common.types import InputTypes
from Athena.common.logger import log_event

if TYPE_CHECKING:
    from Athena.cli.progress import ProgressBar

class Validator:
    def __init__(
        self, 
        config: Config, 
        db: DBManager, 
        filename: str,
        progress_bar: 'ProgressBar' = None
    ) -> None:
        self.config = config
        self.db_manager = db
        self.filename = filename
        self.progress_bar = progress_bar
        self.data: List[Any] = []
        
        self.normalizer = DocumentNormalizer(self.config)
        self.parser = DocumentParser(self.config, self.filename)
    
    def _stringize_data(
        self,
        progress_bar: 'ProgressBar' = None
    ) -> None:
        """_stringize_data Converts objects to strings

        Converts any non-string in the JSON to string
        """
        if progress_bar:
            progress_bar.steps = len(self.data)

        for i in range(len(self.data)):
            if progress_bar: progress_bar.advance_step()

            dictionary: dict = self.data[i]
            for key, value in dictionary.items():
                if not isinstance(value, str):
                    self.data[i][key] = str(value)
    
    def _check_keys(self) -> None:
        """_check_keys Checks for key-consistency

        Checks if all the keys in every object are consistent

        Raises:
            KeyError: If JSON schema is not consistent
        """
        previous_keys = []
        
        for obj in self.data:
            keys = list(obj.keys())
            if not previous_keys:
                previous_keys = keys
            else:
                if previous_keys != keys:
                    raise KeyError("JSON schema must be consistent for every object.")
    
    def validate_json(self) -> None:
        """validate_json Validates JSON input data

        Validates the JSON input data and then upserts it into
        the ChromaDB database.
        """
        self.data = self.db_manager.load_json(self.filename)
        self._check_keys()
        self._stringize_data(self.progress_bar)
    
    def validate_txt(self) -> None:
        """validate_txt Validates Plain-text input data

        Validates the Plain-text input data and then upserts it into
        the ChromaDB database.
        """
        filter_method = self.config.txt_parsing
        with open(os.path.realpath(self.filename), "r", encoding="UTF-8") as file:
            content = file.read()
        
        self.data = self.parser.txt_to_documents(
            filter_method=filter_method, 
            text=content
        )
        if self.config.enforce_uniform_chunks:
            self.data = self.normalizer.normalize_document_lengths(self.data, self.progress_bar)
    
    def validate_md(self) -> None:
        with open(os.path.realpath(self.filename), "r", encoding="UTF-8") as file:
            content = file.read()
        self.data = self.parser.md_to_documents(text=content)
        if self.config.enforce_uniform_chunks:
            self.data = self.normalizer.normalize_document_lengths(self.data, self.progress_bar)
    
    def validate_pdf(self) -> None:
        self.data = self.parser.pdf_to_documents()
        if self.config.enforce_uniform_chunks:
            self.data = self.normalizer.normalize_document_lengths(self.data, self.progress_bar)
    
    @log_event("Validating input file...")
    def validate_input(self) -> List[Any]:
        """validate_input Validates the input file

        Pretty self-explanatory, check individual methods
        for more info.
        """
        match self.config.input_type.value:
            case InputTypes.AUTO.value:
                ext = os.path.splitext(self.filename)[1].lower()
                match ext:
                    case ".json":
                        self.validate_json()
                    case ".txt":
                        self.validate_txt()
                    case ".md":
                        self.validate_md()
                    case ".pdf":
                        self.validate_pdf()
                    case _:
                        raise ValueError(f"Invalid file extension \"{ext}\" in \"{self.filename}\"")
            case InputTypes.JSON.value:
                self.validate_json()
            case InputTypes.PLAIN.value:
                self.validate_txt()
            case InputTypes.MD.value:
                self.validate_md()
            case InputTypes.PDF.value:
                self.validate_pdf()
            case _:
                raise ValueError(f"Invalid InputType {self.config.input_type}. Perhaps try again. Sometimes the parser does some funny stuff lol\nFor me, changing debugger or updating Python worked.")
        return self.data