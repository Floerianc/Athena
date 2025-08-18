import json
from dotenv import load_dotenv
from datetime import datetime
from typing import (
    Union,
    Optional,
    List
)
from chromadb.api.types import (
    Document,
    Documents
)
from Athena.core.db import DBManager
from Athena.core.config import *
from Athena.common.logger import log_event
from Athena.common.types import QueryData

load_dotenv()

class GPTQuery:
    def __init__(
        self,
        db: DBManager,
        data: QueryData,
        config: Config,
        schema_path: Optional[str] = None, 
        instant_request: bool = True
    ) -> None:
        """__init__ Initialises GPTQuery

        This is a class all about the direct communication
        with an OpenAI model. Therefore, this needs a lot of
        data.
        
        It uses the DBManager to access past memories, QueryData
        to create user input, the config to apply your settings to the
        model response (like max tokens, model & more), schema path for
        the response JSON schema and instant request boolean to immediately
        send a request when initialised.

        Args:
            db (db.DBManager): DBManager for past memories
            data (QueryData): User input and database results
            config (Config): Configuration
            schema_path (Optional[str], optional): Path to JSON schema. Defaults to None.
            instant_request (bool, optional): Automatically send request to OpenAI. Defaults to True.
        """
        self.db = db
        self.data = data
        self.config = config
        
        if schema_path:
            self.schema = self.get_schema(schema_path)
        else:
            self.schema = {}
        if instant_request:
            self.response = self.new_response()
    
    @property
    def _prompt_content(self) -> str:
        """_prompt_content Returns the content of the prompt

        Returns the JSON schema, search results from
        ChromaDB, recent memories and latest user query
        as a partially formatted large string.

        Returns:
            str: Prompt body content
        """
        json_schema = ""
        
        if self.config.output_type == OutputTypes.JSON:
            json_schema = self._stringize_prompt_schema()
        
        query = self.data.query
        documents: List[Documents] = self.data.result["documents"] or [[]]
        context: Document = "\n".join(documents[0])
        
        return f"""
        JSON-Schema:
        {json_schema}
        
        Search results from database: 
        {context}
        Most recent memories:
        {self.db.chat_history.stringize_recent_memories}
        Latest User-Query: {query}
        """
    
    @property
    def prompt(self) -> str:
        """prompt Returns the full prompt to OpenAI

        Joins the header and body content of the prompt
        and returns it

        Returns:
            str: Entire OpenAI prompt
        """
        llm_head = self.config.output_header.header
        llm_content = self._prompt_content
        
        return "".join([llm_head, llm_content])
    
    @log_event("Turning JSON-Schema into string...")
    def _stringize_prompt_schema(self) -> str:
        """_stringize_prompt_schema Turns the JSON schema into a string

        Turns the JSON schema into a string. Each key contains
        a name, data type and description so the AI won't mess up the schema.

        Returns:
            str: JSON schema as string
        """
        cleaned_properties_list = []
        
        properties = self.schema["format"]["schema"]["properties"]
        for property_name, definition in properties.items():
            property_type = definition['type']
            property_description = definition['description']
            
            cleaned_properties_list.append(
                f"'{property_name}' [{property_type}]: {property_description}"
            )
        return "\n".join(cleaned_properties_list)
    
    @log_event("Converting JSON-Schema structured output into string...")
    def _validate_json_schema(self) -> dict:
        """_validate_json_schema Returns schema if necessary

        This method returns the full JSON schema as a dictionary
        if using the JSON output_type. Else it returns an empty dictionary

        Returns:
            dict: JSON Schema or empty dictionary
        """
        if not self.config.output_type == OutputTypes.JSON:
            return {}
        else:
            return self.schema
    
    def get_schema(
        self, 
        path: str
    ) -> dict:
        """get_schema Loads the JSON schema

        Loads the file of a given path and interprets
        it as a JSON file, loading it as a dictionary.

        Args:
            path (str): Full path to the JSON schema

        Raises:
            Exception: If there are any problems with reading from the file (e.g. typo)
            ValueError: If there is no file on that path

        Returns:
            dict: _description_
        """
        path = os.path.realpath(path)
        if os.path.exists(path):
            try:
                with open(path, "r") as j:
                    return json.load(j)
            except:
                raise Exception("Couldn't load JSON file. Check if path is correct.")
        else:
            if self.config.output_type == OutputTypes.JSON.name:
                raise ValueError(f"Couldn't find file at '{path}'.")
            else:
                return {}
    
    @log_event("Waiting for OpenAI response...")
    def new_response(
        self, 
        add_to_memory: bool = True
    ) -> Union[dict, str]:
        """new_response Sends a request to OpenAI

        Sends a request to the in the config file defined OpenAI model.
        It loads the necessary OpenAI client params from config and
        imports relevant memories from past interactions.
        
        Additionally, the add_to_memory parameter determines if the method
        automatically adds the user input and model output to the memories of
        the model.
        
        For more info, you should read the doc-strings of the other methods
        this method calls.

        Args:
            add_to_memory (bool, optional): If user input and model output 
            should be added to memories. Defaults to True.

        Returns:
            Union[dict, str]: Either a dictionary (JSON) or string (Plain-text/Markdown)
        """
        base_params = self.config.base_params
        base_params["input"] = self.db.chat_history.response_input(self.config.output_header.header, self.data.query)
        base_params["input"].append(
            {
                "role": "user",
                "content": self._prompt_content
            }
        )
        
        if self.config.output_type == OutputTypes.JSON:
            base_params["text"] = self._validate_json_schema()
        
        rsp = self.db.openai_client.responses.create(
            **base_params
        )
        
        if add_to_memory:
            self.data.rsp = rsp.output_text
            self.db.chat_history.add_context(self.data)
        if self.config.output_type == OutputTypes.JSON:
            try:
                return json.loads(rsp.output_text)
            except json.JSONDecodeError:
                log_event(
                    f"JSON decoding failed. Mayhaps not sufficient tokens\n"
                    f"(max_output_tokens={self.config.response.max_output_tokens}). Returning plain-text instead!"
                )
                return rsp.output_text
        else:
            return rsp.output_text
    
    @log_event("Saving debug message...")
    def save_debug(self) -> None:
        """save_debug Saves debug info

        Saves a rather simple debug file containing:
        * user query
        * search results from the database
        * output type
        * prompt header
        * prompt body content
        * json schema
        * model response
        """
        debug_info = {
            'query': self.data.query,
            'search_results': json.dumps(self.data.result["documents"]),
            'output_type': f"{self.config.output_type.name} --> {self.config.output_type.value}",
            'prompt_header': self.config.output_header.header,
            'prompt_content': self._prompt_content,
            'json_schema': json.dumps(self.schema),
            'response': self.response
        }
        date_string = datetime.now().strftime("%d-%m-%Y_%H%M%S")
        
        with open(f"{date_string}.dat", "a") as debug:
            for name, value in debug_info.items():
                debug.write(f"{name}: {value}\n")


if __name__ == "__main__":
    pass