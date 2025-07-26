import json
from colorama import Fore
from chromadb import QueryResult
from chromadb.api.types import Document
from typing import (
    Any,
    List,
    Optional
)
import db
from config import Config
from api.logger import log_event

class SearchEngine:
    def __init__(self, config: Config, db_manager: db.DBManager) -> None:
        self.config = config
        self.db_manager = db_manager
        self.collection = self.db_manager.get_collection()
    
    def jsonify_results(self, result: QueryResult, key: str) -> List:
        data = result.get(key, None)
        if data:
            json_strs = data[0]
            
            if len(json_strs) > 1:
                return [json.loads(string) for string in json_strs]
            else:
                return []
        else:
            return []
    
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
    
    def filter_by_tokens(self, results: QueryResult, max_tokens: int) -> QueryResult:
        documents = results["documents"] or [[]]
        distances = results["distances"] or [[]]
        metadatas = results["metadatas"] or [[]]
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
                metadatas[0].pop(cutoff_iteration)
                ids[0].pop(cutoff_iteration)
        else:
            pass
        return results
    
    def filter_by_distance(self, results: QueryResult, max_distance: float) -> QueryResult:
        # I genuinely don't know how to do this. This is ugly as fuck
        distances = results.get("distances") or [[]]
        documents = results.get("documents") or [[]]
        ids = results.get("ids") or [[]]
        metadatas = results.get("metadatas") or [[]]

        for i in reversed(range(len(distances[0]))):
            if distances[0][i] > max_distance:
                distances[0].pop(i)
                documents[0].pop(i)
                ids[0].pop(i)
                metadatas[0].pop(i)
            else:
                continue
        return results
    
    @log_event("Searching in collection")
    def search_collection(
        self,
        *query: str,
        strict_search: Optional[str] = None,
        filter_key: Optional[dict] = None
    ) -> QueryResult:
        query_args = {
            "query_texts": list(query),
            "n_results": self.config.search_max_results
        }
        
        if strict_search:
            query_args["where_document"] = {"$contains": strict_search}
        if filter_key:
            query_args["where"] = filter_key
        
        results = self.collection.query(
            query_texts=query_args["query_texts"],
            n_results=query_args["n_results"]
        )
        
        filtered_results = self.filter_by_distance(results=results, max_distance=self.config.search_max_distance)
        return self.filter_by_tokens(results=filtered_results, max_tokens=self.config.search_max_tokens)