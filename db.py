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
from typing import TYPE_CHECKING
from memory import GPTMemory
from api.logger import log_event

if TYPE_CHECKING:
    from config import Config

load_dotenv()

class DBManager:
    @log_event("Loading client, embedding-function and chroma collection")
    def __init__(self, config: 'Config') -> None:
        self.client = chromadb.PersistentClient(
            path = './chromadb'
        )
        self.openai_ef = OpenAIEmbeddingFunction(
            api_key=os.getenv("CHROMA_OPENAI_API_KEY"),
            model_name="text-embedding-3-small"
        )
        self.openai_client = OpenAI(
            api_key = os.getenv("CHROMA_OPENAI_API_KEY")
        )
        self.collection = self.create_collection()
        self.chat_history = GPTMemory(self.client, self.openai_client, self.openai_ef, config)
    
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
    def _insert_json(self, json_obj: list[dict]) -> None:
        docs = [json.dumps(obj) for obj in json_obj]
        
        self.collection.upsert(
            ids = [f"doc{i+1}" for i in range(len(json_obj))],
            documents = docs,
            metadatas = json_obj if type(json_obj) is dict else None
        )
    
    def _load_json(self, filename: str) -> list:
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

@log_event("Deleting chroma database")
def annihilate_db() -> None:
    path = './chromadb/'
    if _verify_chromadb_path(path):
        try:
            shutil.rmtree(path)
        except:
            return