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
import api.utils as utils

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
        """__init__ Initialises GPTMemory

        This class maintains everything related to memory.
        
        It uses the ChromaDB ClientAPI to make DB queries
        to filter out irrelevant information for the OpenAI model
        to save tokens and time.
        
        Additionally, we use another OpenAI client and embedding
        function to shorten input data to save even more tokens
        while maintaining good understanding.

        Args:
            chroma_client (ClientAPI): ChromaDB ClientAPI
            openai_client (OpenAI): OpenAI Client
            openai_embedding (OpenAIEmbeddingFunction): OpenAI EF
            config (Config): Configuration (model, max tokens etc.)
        """
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
        """responses Returns all responses

        Returns every user input and 
        response from the OpenAI model that is loaded
        in the database.

        Returns:
            List[Document]: List of strings (user input, then model response)
        """
        all_data = self.chroma_collection.get()
        if all_data["documents"]:
            return all_data["documents"]
        else:
            return []
    
    @property
    @log_event("Turning recent memories into strings...")
    def stringize_recent_memories(self) -> str:
        """stringize_recent_memories Transforms memories into strings

        Turns all the most recent memories into strings that can be
        passed to the OpenAI model.

        Returns:
            str: string of every recent user input and model output
        """
        memory_strings = []
        for memory in self.most_recent_memories:
            responses = self.create_response_dicts(memory, shorten=False)
            memory_strings.append("\n".join(str(rsp) for rsp in responses))
        return "".join(memory_strings)
    
    def _convert_from_string(
        self, 
        docs: list[str]
    ) -> list[Any]:
        """_convert_from_string Converts string to Any

        Converts any string to another data type if possible.
        
        This is especially useful because the ChromaDB only stores
        data as strings so if there's a string representing a dictionary
        you can transform the string into a fully functional dictionary.

        Args:
            docs (list[str]): List of strings

        Returns:
            list[Any]: Any output
        """
        for i in range(len(docs)):
            try:
                docs[i] = literal_eval(docs[i])
            except:
                continue
        return docs
    
    def filter_responses_by_query(
        self, 
        user_query: str
    ) -> List[dict[str, Any]]:
        """filter_responses_by_query Filters database data

        This method uses the user query to filter relevant
        information from the database to save input tokens
        while at the same time not neglecting the quality of the model 

        Args:
            user_query (str): User's query.

        Returns:
            List[dict[str, Any]]: List of model inputs/outputs ({role: "user", content: ""})
        """
        rsp = self.chroma_collection.query(
            query_texts=[user_query],
            n_results=3
        )
        if rsp and rsp["documents"]:
            return self._convert_from_string(rsp["documents"][0])
        else:
            return []
    
    def recent_responses(
        self, 
        amount: int = 5
    ) -> List[dict[str, Any]]:
        """recent_responses Returns recent responses

        Returns the n most recent user input and model output.

        Args:
            amount (int, optional): The <amount> latest responses. Defaults to 5.

        Returns:
            List[dict[str, Any]]: List of user input and model output dictionaries.
        """
        rsps = self.get_all_responses()
        return rsps[-amount:] # get n latest responses
    
    def get_all_responses(self) -> List[dict[str, Any]]:
        """get_all_responses Returns every response

        Returns every user input and model output as a
        list of dictionaries

        Returns:
            List[dict[str, Any]]: List of user input and model output
        """
        return self._convert_from_string(self.responses)
    
    @log_event("Building response input...")
    def response_input(
        self, 
        system_prompt: str, 
        user_query: str
    ) -> List[dict[str, Any]]:
        """response_input Returns user prompt input

        Constructs the user prompt's model input 
        (basically the chat context) with a given system prompt
        and user query.
        
        It gets the most recent responses, then searches for the
        most relevant database inputs and joins them together
        for the OpenAI model to use as context.

        Args:
            system_prompt (str): Straightening thread for the model lol
            user_query (str): User query ???

        Returns:
            List[dict[str, Any]]: List of responses (chat context)
        """
        recent_inputs = self.recent_responses()
        filtered_inputs = self.filter_responses_by_query(user_query)
        
        rsp_input = recent_inputs + filtered_inputs
        rsp_input.insert(0, {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]})
        return rsp_input
    
    @log_event("Using fallback function to shorten in- and output...")
    def _shorten_data_fallback(
        self, 
        data: List[str]
    ) -> List[str]:
        """_shorten_data_fallback Fallback for shorten data

        This is a method returning a list containing the last 
        `n` tokens of a string. This is primarily used to
        shorten user input and model output while still trying
        to preserve the actual meaning by saving the **last** `n` tokens
        instead of the **first** `n` tokens as usually models give a
        summarization at the end of their response.
        
        For actual use-case check _shorten_data() 

        Args:
            data (List[str]): List of strings (data)

        Returns:
            List[str]: List of shortened strings
        """
        shortened = []
        max_chars = utils.tokens_to_chars(self.config.tokens_per_memory)
        for item in data:
            start = 0 if len(item) <= max_chars else len(item) - max_chars
            shortened.append(item[start:])
        return shortened
    
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
            log_event(f"Output and input don't have same amount of lines.\nOutput lines: {len(output_lines)}, expected: {len(data)}")
            return self._shorten_data_fallback(data)
        return output_lines
    
    @log_event("Converting user input and model output to dictionaries...")
    def create_response_dicts(
        self, 
        data: QueryData, 
        shorten: bool = True
    ) -> list[dict]:
        """create_response_dicts Creates response dictionaries

        Creates dictionaries containing the user input and model output (response)
        which is how OpenAI stores chat and user context.
        
        Check the return statement so you clearly understand what I mean.
        
        Additionally, this method can also call another method to shorten
        the user input and model output to save tokens when further talking to 
        OpenAI models.

        Args:
            data (QueryData): User input, model output and database results
            shorten (bool, optional): Shortens the data. Defaults to True.

        Raises:
            AttributeError: If there's no model response yet, it will fail.

        Returns:
            list[dict]: List of dictionaries containing chat context.
        """
        if shorten:
            if data.rsp:
                if isinstance(data.rsp, dict):
                    data.rsp = json.dumps(data.rsp)
                elif not isinstance(data.rsp, str):
                    data.rsp = str(data.rsp)
                
                rsp = self.shorten_data([data.query, str(data.rsp)])
                data.query = rsp[0]
                data.rsp = rsp[1]
            else:
                raise AttributeError(f"QueryData object doesn't have a .rsp attribute yet!\nQueryData: {str(data)}")
        
        user = {"role": "user", "content": data.query}
        assistant = {"role": "assistant", "content": data.rsp}
        return [user, assistant]
    
    def to_document(
        self, 
        data: Union[list, dict]
    ) -> Document:
        """to_document Converts data to Document

        Converts lists and dictionaries to strings for the
        ChromaDB to insert.

        Args:
            data (Union[list, dict]): List/Dictionary to turn into string

        Raises:
            TypeError: This method can only convert lists and dictionaries

        Returns:
            Document: Document is another name for strings.
        """
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
    
    def add_newest_memory(
        self, 
        data: QueryData
    ) -> None:
        """add_newest_memory Adds new memory

        This adds the current user input, model output
        and database results to the most recent memories
        so the model can remember past messages so there are
        less awkward conversations.

        Args:
            data (QueryData): Data to be appended to the list of memories.
        """
        if len(self.most_recent_memories) >= self.max_entries:
            self.most_recent_memories.pop(0)
        self.most_recent_memories.append(data)
    
    @log_event("Adding context to memories...")
    def add_context(self, data: QueryData) -> None:
        """add_context Adds context to the OpenAI model and ChromaDB database

        Uses the QueryData object to store user input and model output/response
        to construct chat context to add into the Database.

        Args:
            data (QueryData): User input, model output and database results.
        """
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