import os
import json
import db
from chromadb import QueryResult
from openai import OpenAI
from dotenv import load_dotenv
from consts import *

load_dotenv()

client = OpenAI(
    api_key = os.getenv("CHROMA_OPENAI_API_KEY")
)

class InputData:
    def __init__(self, query: str, data: QueryResult) -> None:
        self.result = data
        self.query = query

class GPTQuery:
    def __init__(self, data: InputData, outputType: 'OutputTypes', schema_path: str, instant_request: bool = True, max_tokens: int = 1024) -> None:
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
            json_schema = self.stringize_schema()
        
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
    def stringize_schema(self) -> str:
        cleaned_properties_list = []
        
        properties = self.schema["schema"]["properties"]
        for property_name, definition in properties.items():
            property_type = definition['type']
            property_description = definition['description']
            
            cleaned_properties_list.append(
                f"'{property_name}' [{property_type}]: {property_description}"
            )
        return "\n".join(cleaned_properties_list)
    
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
            temperature=1.55,
            max_output_tokens=self.max_tokens,
            top_p=1,
            store=True
        )
        return rsp.output_text 

if __name__ == "__main__":
    pass