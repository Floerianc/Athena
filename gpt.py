import os
import json
import db
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime
from typing import (
    Union, 
    Optional
)
from openai.types.responses.response import Response
from api_types import QueryData
from config import *

load_dotenv()

class GPTQuery:
    def __init__(
        self,
        db: db.DBManager,
        data: QueryData,
        config: Config,
        schema_path: Optional[str] = None, 
        instant_request: bool = True
    ) -> None:
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
        json_schema = ""
        
        if self.config.output_type == OutputTypes.JSON:
            json_schema = self._stringize_prompt_schema()
        
        query = self.data.query
        documents = self.data.result["documents"] or [[]]
        context = "\n\n".join(documents[0])
        
        return f"""
        JSON-Schema:
        {json_schema}
        
        User-Query: {query}
        
        Search results from database: 
        {context}
        """
    
    @property
    @db.log_event("Generating prompt...")
    def prompt(self) -> str:
        llm_head = self.config.output_header.header
        llm_content = self._prompt_content
        
        return "".join([llm_head, llm_content])
    
    @db.log_event("Turning JSON-Schema into string...")
    def _stringize_prompt_schema(self) -> str:
        cleaned_properties_list = []
        
        properties = self.schema["format"]["schema"]["properties"]
        for property_name, definition in properties.items():
            property_type = definition['type']
            property_description = definition['description']
            
            cleaned_properties_list.append(
                f"'{property_name}' [{property_type}]: {property_description}"
            )
        return "\n".join(cleaned_properties_list)
    
    @db.log_event("Converting JSON-Schema structured output into string...")
    def _validate_json_schema(self) -> dict:
        if not self.config.output_type == OutputTypes.JSON:
            return {}
        else:
            return self.schema
    
    def get_schema(self, path: str) -> dict:
        if os.path.exists(path):
            try:
                with open(path, "r") as j:
                    return json.load(j)
            except:
                raise Exception("Couldn't load JSON file. Check if path is correct.")
        else:
            raise ValueError(f"Couldn't find file at '{path}'.")
    
    @db.log_event("Waiting for OpenAI response...")
    def new_response(self, add_to_memory: bool = True) -> Union[dict, str]:
        base_params = self.config.base_params
        base_params["input"] = self.db.chat_history.response_input(self.config.output_header.header)
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
                db.log.error(
                    f"JSON decoding failed. Mayhaps not sufficient tokens\n"
                    f"(max_output_tokens={self.config.response.max_output_tokens}). Returning plain-text instead!"
                )
                return rsp.output_text
        else:
            return rsp.output_text
    
    def save_debug(self) -> None:
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


