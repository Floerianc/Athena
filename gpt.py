import os
import json
import db
from chromadb import QueryResult
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime
from consts import *

load_dotenv()

client = OpenAI(
    api_key = os.getenv("CHROMA_OPENAI_API_KEY")
)

class QueryData:
    def __init__(self, query: str, data: QueryResult) -> None:
        self.result = data
        self.query = query

class GPTQuery:
    def __init__(self, data: QueryData, outputType: 'OutputTypes', schema_path: str, instant_request: bool = True, max_tokens: int = 1024) -> None:
        self.data = data
        self.outputType = outputType
        
        self.max_tokens = max_tokens
        self.schema = self.get_schema(schema_path)
        self.promptHeader = OutputHeaders(outputType)
        
        if instant_request:
            self.response = self.new_response()
    
    @property
    def _prompt_content(self) -> str:
        json_schema = ""
        
        if self.outputType == OutputTypes.JSON:
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
        llm_head = self.promptHeader.header
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
        if not self.outputType == OutputTypes.JSON:
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
    def new_response(self) -> str:
        # TODO: More elegant solution!!
        
        if self.outputType == OutputTypes.PLAIN:
            rsp = client.responses.create(
                model="gpt-4.1-mini",
                input=[
                    {
                        "role": "system",
                        "content": [
                            {
                                "type": "input_text",
                                "text": self.prompt
                            }
                        ]
                    }
                ],
                reasoning={},
                tools=[],
                temperature=1.0,
                max_output_tokens=self.max_tokens,
                top_p=1,
                store=True
            )
            return rsp.output_text
        
        elif self.outputType == OutputTypes.JSON:
            rsp = client.responses.create(
                model="gpt-4.1-mini",
                input=[
                    {
                        "role": "system",
                        "content": [
                            {
                                "type": "input_text",
                                "text": self.prompt
                            }
                        ]
                    }
                ],
                text=self._validate_json_schema(),
                reasoning={},
                tools=[],
                temperature=1.0,
                max_output_tokens=self.max_tokens,
                top_p=1,
                store=True
            )
            return json.loads(rsp.output_text)
        else:
            return ""
    
    def save_debug(self) -> None:
        query_input = [
            f"Query: {self.data.query}",
            f"Search results: {json.dumps(self.data.result)}"
        ]
        
        output_header = [
            f"Output-Type: {self.outputType.name} ({self.outputType.value})"
            f"Prompt header: {self.promptHeader}"
        ]
        
        prompt = [
            f"Prompt content: {self._prompt_content}"
        ]
        
        rsp = [
            f"Schema: {json.dumps(self.schema)}"
            f"Response: {self.response}"
        ]
        
        with open(f"debug.dat", "a") as debug: # FIXME: Bad code + datetime based string!!!
            for l in [query_input, output_header, prompt, rsp]:
                string = "\n".join(l)
                debug.write(string)

if __name__ == "__main__":
    pass