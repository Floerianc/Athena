import os
from api_types import (
    QueryData, 
    OutputTypes
)
from openai import OpenAI
from typing import (
    List, 
    Any
)
from pprint import pprint
from config import Config

class GPTMemory:
    def __init__(
        self, 
        config: Config,
        openai_client: OpenAI
    ) -> None:
        self.config = config
        self.openai_client = openai_client
        
        self.history: List[QueryData] = []
        self.max_entries = 10
        self.tokens_per_memory = 200
    
    @property
    def stringize_history(self) -> str:
        input_string = ""
        for query_data in self.history:
            prompt = [query_data.query, query_data.rsp]
            input_string += "\n".join(prompt) + "\n"
        return input_string
    
    def shortened_history(self) -> str:
        base_params = self.config.base_params
        base_params["max_output_tokens"] = self.tokens_per_memory * (len(self.history) + 1)
        base_params["input"] = [
            {
                "role": "system", 
                "content": """
                RULES:
                    - Do not, under any circumstances, add more text than what there already is
                    - Do not comment anything. Just modify the text with the given instruction below.
                
                Your mission is to shorten every text you see. Leave the format the same.
                Meaning, you have one shortened text per line. Do not leave any blank lines under any circumstances.
                Additionally, if there's no input, just leave it entirely blank.
                Output must have the exact same amount of lines as the Input!
                """
            },
            {
                "role": "user",
                "content": self.stringize_history
            }
        ]
        rsp = self.openai_client.responses.create(
            **base_params
        )
        return rsp.output_text
    
    def convert_history_to_dict(self) -> List[dict]:
        history = self.shortened_history().splitlines()
        dicts = []
        
        for iteration, line in enumerate(history):
            if iteration % 2 == 0:
                role = "assistant"
            else:
                role = "user"
            rsp_obj = {"role": role, "content": line}
            dicts.append(rsp_obj)
        return dicts
    
    def response_input(self, system_prompt: str) -> List[dict[str, Any]]:
        rsp_input = [data for data in self.convert_history_to_dict()]
        rsp_input.insert(0, {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]})
        return rsp_input
    
    def add_context(self, data: QueryData) -> None:
        if len(self.history) >= 10:
            self.history.remove(self.history[-1])
        self.history.append(data)


if __name__ == "__main__":
    m = GPTMemory(Config(OutputTypes.PLAIN), OpenAI(api_key = os.getenv("CHROMA_OPENAI_API_KEY")))