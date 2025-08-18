from Athena.core.db import DBManager
from Athena.core.config import (
    Config,
    InputTypes,
    OutputTypes
)
from Athena.processor.validator import Validator
from Athena.processor.serializer import Serializer
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Athena.cli.progress import ProgressBar


class Processor:
    def __init__(
        self, 
        db: DBManager,
        config: Config,
        filename: str,
        insert_json: bool = True,
        progress_bar: 'ProgressBar' = None
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
        self.progress_bar = progress_bar
        self.validator = Validator(self.config, self.db_manager, self.filename, progress_bar=self.progress_bar)
        self.serializer = Serializer()
        
        self.data = self.validator.validate_input()
        if insert_json:
            self.db_manager.insert_json(self.data)

if __name__ == "__main__":
    c = Config(InputTypes.MD, OutputTypes.PLAIN)
    c.parse_chunk_size = 640
    c.enforce_uniform_chunks = False
    p = Processor(
        db=DBManager(config=c),
        config=c,
        filename=r"C:\Users\stege.DESKTOP-VOI4DSV\Desktop\vir\Athena_Full\dumps\test.md",
        insert_json=False
    )
    for chunk in p.data:
        print(chunk)

    for chunk in p.data:
        print(len(chunk))