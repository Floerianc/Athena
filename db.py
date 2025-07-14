import chromadb
import os
import json
import logging
import shutil
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from datetime import datetime
from dotenv import load_dotenv
from typing import Callable

load_dotenv()

logging.basicConfig(
    filename="./log.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
log = logging.getLogger(__name__)

# idk how decorators work i just copied this from somewhere lol
def log_event(msg: str):
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            log.info(f"{func.__name__}: {msg}")
            result = func(*args, **kwargs) # type: ignore
            return result
        return wrapper
    return decorator

class DBManager:
    @log_event("Loading client, embedding-function and chroma collection")
    def __init__(self) -> None:
        self.client = chromadb.PersistentClient(
            path = './chromadb'
        )
        self.openai_ef = OpenAIEmbeddingFunction(
            api_key=os.getenv("CHROMA_OPENAI_API_KEY"),
            model_name="text-embedding-3-small"
        )
        self.collection = self.create_collection()
    
    def get_client(self) -> ClientAPI:
        return self.client
    
    def get_collection(self) -> Collection:
        return self.collection
    
    def create_collection(self) -> Collection:
        return self.client.get_or_create_collection(
            name = "VData",
            embedding_function=self.openai_ef, # type: ignore
            metadata = {
                'description': 'Testing with AI',
                'created': str(datetime.now())
            }
        )
    
    @log_event("Upserting JSON-data into collection")
    def _insert_json(self, json_obj: dict) -> None:
        docs = [json.dumps(obj) for obj in json_obj]
        
        self.collection.upsert(
            ids = [f"doc{i+1}" for i in range(len(json_obj))],
            documents = docs,
            metadatas = json_obj
        )
    
    def _load_data(self, filename: str) -> dict:
        if filename:
            with open(f"{os.path.realpath(filename)}") as file:
                log.info("Loading JSON to RAM...")
                return json.load(file)
        return {}

def _verify_chromadb_path(path: str) -> bool:
    content = os.listdir(path)
    files = [
        file for file in content if 
        os.path.isfile(os.path.realpath(f"{path}{file}"))
    ]
    folders = [
        folder for folder in content if 
        os.path.isdir(os.path.realpath(f"{path}{folder}"))]
    
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

@log_event("Deleting chroma database")
def annihilate_db() -> None:
    path = './chromadb/'
    if _verify_chromadb_path(path):
        try:
            shutil.rmtree(path)
        except:
            os.remove(os.path.realpath(f"{path}chroma.sqlite3"))

def get_logger():
    return log