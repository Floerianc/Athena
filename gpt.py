import os
import json
import db
from chromadb import QueryResult
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime
from typing import (
    Union, 
    Optional
)
from config import *

load_dotenv()

client = OpenAI(
    api_key = os.getenv("CHROMA_OPENAI_API_KEY")
)

class QueryData:
    def __init__(self, query: str, data: QueryResult) -> None:
        self.result = data
        self.query = query

class GPTQuery:
    def __init__(
        self,
        data: QueryData,
        config: Config,
        schema_path: Optional[str] = None, 
        instant_request: bool = True, 
        max_tokens: int = 1024
    ) -> None:
        self.data = data
        self.config = config
        
        self.max_tokens = max_tokens
        
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
    def new_response(self) -> Union[dict, str]:
        base_params = {
            'model': "gpt-4.1-mini",
            'input': [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": self.prompt,
                        }
                    ]
                }
            ],
            "reasoning": {},
            "tools": [],
            "temperature": 1.0,
            "max_output_tokens": self.max_tokens,
            "top_p": 1,
            "store": True
        }
        
        if self.config.output_type == OutputTypes.JSON:
            base_params["text"] = self._validate_json_schema()
        
        rsp = client.responses.create(
            **base_params
        )
        
        if self.config.output_type == OutputTypes.JSON:
            try:
                return json.loads(rsp.output_text)
            except json.JSONDecodeError:
                db.log.error(
                    f"JSON decoding failed. Mayhaps not sufficient tokens\n"
                    f"(max_output_tokens={self.max_tokens}). Returning plain-text instead!"
                )
        return rsp.output_text
    
    def save_debug(self) -> None:
        debug_info = {
            'query': self.data.query,
            'search_results': json.dumps(self.data.result),
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


