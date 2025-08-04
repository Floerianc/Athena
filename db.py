import chromadb
import os
import json
import shutil
from openai import OpenAI
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from datetime import datetime
from dotenv import load_dotenv
from typing import (
    Optional,
    TYPE_CHECKING
)
from Athena.memory import GPTMemory
from Athena.common.logger import log_event
from Athena.cli.progress import ProgressBar
from Athena import _internal_dir

if TYPE_CHECKING:
    from config import Config

load_dotenv()

class DBManager:
    @log_event("Loading client, embedding-function and chroma collection")
    def __init__(
        self, 
        config: 'Config',
        progress_bar: Optional[ProgressBar] = None,
    ) -> None:
        if progress_bar: progress_bar.advance_step()
        self.client = chromadb.PersistentClient(path=os.path.join(_internal_dir, "chromadb/"))

        if progress_bar: progress_bar.advance_step()
        self.openai_ef = OpenAIEmbeddingFunction(
            api_key=os.getenv("CHROMA_OPENAI_API_KEY"),
            model_name="text-embedding-3-small"
        )

        if progress_bar: progress_bar.advance_step()
        self.openai_client = OpenAI(api_key=os.getenv("CHROMA_OPENAI_API_KEY"))

        if progress_bar: progress_bar.advance_step()
        self.collection = self.create_collection()

        if progress_bar: progress_bar.advance_step()
        self.chat_history = GPTMemory(self.client, self.openai_client, self.openai_ef, config)
    
    def get_client(self) -> ClientAPI:
        """get_client Returns the Client

        Returns the current in use ChromaDB ClientAPI

        Returns:
            ClientAPI: ChromaDB client
        """
        return self.client
    
    def get_collection(self) -> Collection:
        """get_collection Returns the collection

        Returns the current in-use ChromaDB Collection

        Returns:
            Collection: ChromaDB Collection
        """
        return self.collection
    
    def create_collection(self) -> Collection:
        """create_collection Get or creates a collection named 'VData'

        Creates or gets a ChromaDB named 'VData' which is used to store
        the data from the input file. 
        
        Returns:
            Collection: ChromaDB Collection
        """
        return self.client.get_or_create_collection(
            name = "VData",
            embedding_function=self.openai_ef, # type: ignore
            metadata = {
                'description': 'Database for data input',
                'created': str(datetime.now())
            }
        )
    
    @log_event("Upserting JSON-data into collection")
    def insert_json(
        self, 
        json_obj: list[dict]
    ) -> None:
        """_insert_json Inserts JSON into DB

        Inserts all the data from the JSON file into the DB

        Args:
            json_obj (list[dict]): List of dictionaries (Pythonic JSON objects)
        """
        docs = [json.dumps(obj) for obj in json_obj]
        
        self.collection.upsert(
            ids = [f"doc{i+1}" for i in range(len(json_obj))],
            documents = docs,
            metadatas = json_obj if type(json_obj) is dict else None
        )

    def load_json(
        self,
        filename: str
    ) -> list:
        """_load_json Loads the content of a JSON

        Loads the content of a JSON file and returns it.
        Note that the filename should be the full file path.

        Args:
            filename (str): Full path to the file

        Returns:
            list: List of Dictionaries (Pythonic JSON objects)
        """
        if filename:
            with open(filename) as file:
                log_event("Loading JSON to RAM...")
                json_file = json.load(file)
                if not isinstance(json_file, list):
                    return [json_file]
                else:
                    return json_file
        else:
            return []

def _verify_chromadb_path(path: str) -> bool:
    """_verify_chromadb_path Confirms the path of the chroma database

    This method uses a lot of checks to determine whether or not
    the given path is the path to the ChromaDB files.

    Args:
        path (str): Path to a folder

    Returns:
        bool: True if the folder is the ChromaDB folder
    """
    content = os.listdir(path)
    files = [
        file for file in content if os.path.isfile(os.path.realpath(f"{path}{file}"))
    ]
    folders = [
        folder for folder in content if os.path.isdir(os.path.realpath(f"{path}{folder}"))]
    
    if len(files) == 1:
        pass
    else:
        return False
    
    for folder in folders:
        for file in os.listdir(os.path.join(path, folder)):
            if file.endswith('.bin'):
                continue
            else:
                return False
    return True

@log_event("Deleting every database")
def annihilate_db() -> None:
    """annihilate_db Deletes the entire database

    This method uses a lot of checks to determine the 
    location of the database so it doesn't accidentally delete
    any other important folders.
    
    NOTE: The default folder path is ./_internal/chromadb/
    """
    path = _internal_dir
    if _verify_chromadb_path(path):
        try:
            shutil.rmtree(path)
        except:
            raise FileNotFoundError("ChromaDB folder does not exist")