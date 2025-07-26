import os
import chromadb
import json
from chromadb.api import ClientAPI
from chromadb.api.types import Document, QueryResult
from datetime import datetime
from openai import OpenAI
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from typing import (
    List, 
    Any,
    Union,
    TYPE_CHECKING
)
from ast import literal_eval
from config import (
    InputTypes,
    OutputTypes
)
from api.types import (
    QueryData, 
    OutputTypes
)
from api.logger import log_event

if TYPE_CHECKING:
    from config import Config

class GPTMemory:
    def __init__(
        self, 
        chroma_client: ClientAPI,
        openai_client: OpenAI,
        openai_embedding: OpenAIEmbeddingFunction,
        config: 'Config',
    ) -> None:
        self.config = config
        self.openai_client = openai_client
        self.chroma_client = chroma_client
        self.openai_ef = openai_embedding
        
        self.chroma_collection = self.chroma_client.get_or_create_collection(
            name="MemoryDB",
            embedding_function=self.openai_ef, # type: ignore
            metadata = {
                'description': 'Testing with AI',
                'created': str(datetime.now())
            }
        )
        self.most_recent_memories: List[QueryData] = []
        
        self.max_entries = self.config.max_entries
        self.max_search_results = self.config.max_search_results
        self.tokens_per_memory = self.config.tokens_per_memory
    
    @property
    def responses(self) -> List[Document]:
        all_data = self.chroma_collection.get()
        if all_data["documents"]:
            return all_data["documents"]
        else:
            return []
    
    @property
    @log_event("Turning recent memories into strings...")
    def stringize_recent_memories(self) -> str:
        memory_strings = []
        for memory in self.most_recent_memories:
            responses = self.create_response_dicts(memory, shorten=False)
            memory_strings.append("\n".join(str(rsp) for rsp in responses))
        return "".join(memory_strings)
    
    def _convert_from_string(self, docs: list[str]) -> list[Any]:
        for i in range(len(docs)):
            try:
                docs[i] = literal_eval(docs[i])
            except:
                continue
        return docs
    
    def filter_responses_by_query(self, user_query: str) -> List[dict[str, Any]]:
        rsp = self.chroma_collection.query(
            query_texts=[user_query],
            n_results=3
        )
        if rsp and rsp["documents"]:
            return self._convert_from_string(rsp["documents"][0])
        else:
            return []
    
    def recent_responses(self, amount: int = 5) -> List[dict[str, Any]]:
        rsps = self.get_all_responses()
        return rsps[-amount:] # get n latest responses
    
    def get_all_responses(self) -> List[dict[str, Any]]:
        return self._convert_from_string(self.responses)
    
    @log_event("Building response input...")
    def response_input(self, system_prompt: str, user_query: str) -> List[dict[str, Any]]:
        recent_inputs = self.recent_responses()
        filtered_inputs = self.filter_responses_by_query(user_query)
        
        rsp_input = recent_inputs + filtered_inputs
        rsp_input.insert(0, {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]})
        return rsp_input
    
    @log_event("Shortening user input and model output...")
    def shorten_data(self, data: List[str]) -> List[str]:
        if len(data) != 2:
            raise ValueError(f"Input must be exactly 2 lines. Not {len(data)}")
        
        base_params = self.config.base_params.copy()
        base_params["max_output_tokens"] = len(data) * self.tokens_per_memory
        base_params["input"] = [
            {
                "role": "system", 
                "content": """
                You are a plain-text shortening AI. Your task is to shorten the following two messages while preserving their meaning.
                The output MUST be EXACTLY two lines. USE ONE NEWLINE TO START THE SECOND LINE
                You HAVE to follow this format UNDER ANY CIRCUMSTANCES:
                <shortened user INPUT (one line)><newline><shortened model OUTPUT (one line)>
                """
            },
            {
                "role": "user",
                "content": "\n".join(data)
            }
        ]
        rsp = self.openai_client.responses.create(
            **base_params
        )
        output = rsp.output_text.strip()
        output_lines = output.splitlines()
        
        if len(output_lines) != len(data):
            raise ValueError(f"Output and input don't have same amount of lines.\nOutput lines: {len(output_lines)}, expected: {len(data)}")
        for line in output_lines:
            try:
                json.loads(line)
            except:
                pass # treat as plain-text
        return output_lines
    
    @log_event("Converting user input and model output to dictionaries...")
    def create_response_dicts(self, data: QueryData, shorten: bool = True) -> list[dict]:
        if shorten:
            if data.rsp:
                rsp = self.shorten_data([data.query, data.rsp])
                data.query = rsp[0]
                data.rsp = rsp[1]
            else:
                raise AttributeError(f"QueryData object doesn't have a .rsp attribute yet!\nQueryData: {str(data)}")
        
        user = {"role": "user", "content": data.query}
        assistant = {"role": "assistant", "content": data.rsp}
        return [user, assistant]
    
    def to_document(self, data: Union[list, dict]) -> Document:
        if isinstance(data, list):
            for i in range(len(data)):
                obj = data[i]
                if isinstance(obj, str):
                    continue
                else:
                    data[i] = str(obj)
        
        elif isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str):
                    continue
                else:
                    data[key] = str(value)
        else:
            raise TypeError(f"Data is either list or dict, not {type(data)}")
        return str(data)
    
    def add_newest_memory(self, data: QueryData) -> None:
        if len(self.most_recent_memories) >= self.max_entries:
            self.most_recent_memories.pop(0)
        self.most_recent_memories.append(data)
    
    @log_event("Adding context to memories...")
    def add_context(self, data: QueryData) -> None:
        responses = self.create_response_dicts(data)
        length = self.chroma_collection.count()
        
        self.chroma_collection.upsert(
            ids =       [f"memory{length+i}" for i in range(len(responses))],
            documents = [str(self.to_document(response)) for response in responses]
        )
        self.add_newest_memory(data)

if __name__ == "__main__":
    a = GPTMemory(
        chroma_client=chromadb.Client(),
        openai_client=OpenAI(api_key=os.getenv("CHROMA_OPENAI_API_KEY")),
        openai_embedding=OpenAIEmbeddingFunction(
            api_key=os.getenv("CHROMA_OPENAI_API_KEY"),
            model_name="text-embedding-3-small"
        ),
        config=Config(InputTypes.PLAIN, OutputTypes.MD)
    )
    a.add_context(
        QueryData(
            data={},
            query="What is the capital of France?",
            rsp="The capital of France is Paris."
        )
    )
    
    print(a.stringize_recent_memories)