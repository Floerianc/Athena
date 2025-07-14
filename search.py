import json
import db
import processor
from colorama import Fore
from chromadb import (
    Collection,
    QueryResult,
)
from chromadb.api.types import Document
from typing import (
    Union,
    Any,
    List,
    Optional
)

class SearchEngine:
    def __init__(self, collection: Collection) -> None:
        self.collection = collection
    
    def jsonify_results(self, result: QueryResult, key: str) -> Union[dict, list[dict]]:
        data = result.get(key, None)
        if data:
            json_strs = data[0]
            
            if len(json_strs) > 1:
                return [json.loads(string) for string in json_strs]
            else:
                return json.loads(json_strs[0])
        else:
            return {}
    
    def clean_results(self, result: QueryResult) -> dict[str, Any]:
        return {
            'distances': result.get("distances"),
            'documents': self.jsonify_results(result, "documents"),
            'ids': result.get("ids"),
            'metadatas': result.get("metadatas")
        }
    
    def _highlight_documents(self, documents: List[List[Document]], query: str) -> List[Document]:
        highlighted_docs = documents[0]
        
        for word in query.split():
            for i, doc in enumerate(highlighted_docs):
                highlighted_docs[i] = doc.replace(word, f"{Fore.RED}{word}{Fore.RESET}")
        return highlighted_docs
    
    def pprint_documents(self, result: QueryResult, query: str) -> None:
        documents = result["documents"]
        distances = result["distances"]
        
        if documents and distances:
            highlighted_docs = self._highlight_documents(documents, query)
            for i, doc in enumerate(highlighted_docs):
                print(
                    f"\t\t{i+1}. dst: {distances[0][i]}\n\n{doc}\n"
                )
        else:
            return
    
    def calculate_token_amount(self, text: str) -> float:
        # rule of thumb: 3/4 words = 1 token
        token_per_word = 1 / (3/4)
        return len(text.split()) * token_per_word
    
    def limit_by_tokens(self, results: QueryResult, max_tokens: int) -> QueryResult:
        documents = results["documents"] or [[]]
        distances = results["distances"] or [[]]
        ids = results.get("ids", [[]])
        
        tokens_used = 0
        cutoff_iteration = len(documents[0])
        
        for iteration, doc in enumerate(documents[0]):
            tokens_used += self.calculate_token_amount(doc)
            if tokens_used > max_tokens:
                cutoff_iteration = iteration
                break
            else:
                continue
        
        if cutoff_iteration:
            loop_count = len(documents[0]) - cutoff_iteration
            for _ in range(loop_count):
                documents[0].pop(cutoff_iteration)
                distances[0].pop(cutoff_iteration)
                ids[0].pop(cutoff_iteration)
        else:
            pass
        return results
    
    @db.log_event("Searching in collection")
    def search_collection(
        self,
        *query: str,
        max_tokens: int = 2048,
        strict_search: Optional[str] = None,
        filter_key: Optional[dict] = None
    ) -> QueryResult:
        query_args = {
            "query_texts": list(query),
            "n_results": 64
        }
        
        if strict_search:
            query_args["where_document"] = {"$contains": strict_search}
        if filter_key:
            query_args["where"] = filter_key
        
        results = self.collection.query(
            query_texts=list(query),
            n_results=64
        )
        return self.limit_by_tokens(results, max_tokens)

if __name__ == "__main__":
    pass