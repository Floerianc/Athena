import json
from colorama import Fore
from chromadb import QueryResult
from chromadb.api.types import Document
from typing import (
    Any,
    List,
    Dict,
    Optional
)
import Athena.db as db
from Athena.config import Config
from Athena.common.logger import log_event

class SearchEngine:
    def __init__(
        self, 
        config: Config, 
        db_manager: db.DBManager
    ) -> None:
        """__init__ Initialises SearchEngine

        This class is used to post search queries into the 
        ChromaDB database.

        Args:
            config (Config): Configuration file
            db_manager (db.DBManager): DBManager for ChromaDB collection
        """
        self.config = config
        self.db_manager = db_manager
        self.collection = self.db_manager.get_collection()
    
    def jsonify_results(
        self, 
        result: QueryResult, 
        key: str
    ) -> List:
        """jsonify_results Converts ChromaDB's QueryResult

        Converts a ChromaDB QueryResult into a JSON-serializable format
        
        Dude im tired of writing docs already.......

        Args:
            result (QueryResult): Result of the search query
            key (str): Key in QueryResult to be converted

        Returns:
            List: Converted list
        """
        data = result.get(key, None)
        if data and isinstance(data, list):
            json_strs = data[0]
            
            if len(json_strs) >= 1:
                return [json.loads(string) for string in json_strs]
            else:
                return []
        else:
            return []
    
    def clean_results(
        self, 
        result: QueryResult
    ) -> dict[str, Any]:
        """clean_results Returns cleaned QueryResults

        Returns a rather clean QueryResult dictionary.
        This is mainly for convenience and doesn't really have
        another meaning, it's just more clean imo.

        Args:
            result (QueryResult): Search results from ChromaDB

        Returns:
            dict[str, Any]: Cleaned dictionary
        """
        return {
            'distances': result.get("distances"),
            'documents': self.jsonify_results(result, "documents"),
            'ids': result.get("ids"),
            'metadatas': result.get("metadatas")
        }
    
    def _highlight_documents(
        self, 
        documents: List[List[Document]], 
        query: str
    ) -> List[Document]:
        """_highlight_documents Highlights user query

        This method highlights parts of the user query in
        the data input.

        Args:
            documents (List[List[Document]]): Inserted Documents in ChromaDB
            query (str): User query

        Returns:
            List[Document]: List of highlighted documents
        """
        highlighted_docs = documents[0]
        
        for word in query.split():
            for i, doc in enumerate(highlighted_docs):
                highlighted_docs[i] = doc.replace(word, f"{Fore.RED}{word}{Fore.RESET}")
        return highlighted_docs
    
    def pprint_documents(
        self, 
        result: QueryResult, 
        query: str
    ) -> None:
        """pprint_documents Pretty-Prints documents

        Another convenience function for debugging.
        Prints the documents and their distance to the original
        user input in a rather pretty way.
        
        Args:
            result (QueryResult): Search results dadada you know the drill
            query (str): User queryyyyy
        """
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
    
    def calculate_token_amount(
        self, 
        text: str
    ) -> float:
        """calculate_token_amount Calculates token amount

        Args:
            text (str): Any string

        Returns:
            float: Amount of tokens for string.
        """
        # rule of thumb: 3/4 words = 1 token
        token_per_word = 1 / (3/4)
        return len(text.split()) * token_per_word
    
    def filter_by_tokens(
        self, 
        results: QueryResult, 
        max_tokens: int
    ) -> QueryResult:
        """filter_by_tokens Filters results

        Filters the results by a set amount of max_tokens
        to save tokens later when using the OpenAI models

        Args:
            results (QueryResult): Search results from database
            max_tokens (int): Max token amount

        Returns:
            QueryResult: Filtered results
        """
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
    
    def filter_by_distance(
        self, 
        results: QueryResult, 
        max_distance: float
    ) -> QueryResult:
        """filter_by_distance Filters results

        Same as the filter_by_tokens() function but
        with the distances rather than token length

        Args:
            results (QueryResult): Search results
            max_distance (float): max distance

        Returns:
            QueryResult: Filtered results
        """
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
        """search_collection Searches collection

        This function sends a query to the database which returns
        the most relevant data for the corresponding user input.
        This then gets filtered but a few functions to save tokens
        and only use the most relevant information.

        Args:
            strict_search (Optional[str], optional): Searches for a strict key word. Defaults to None.
            filter_key (Optional[dict], optional): Filters by a specific metadata key. Defaults to None.

        Returns:
            QueryResult: Search results
        """
        query_args: Dict[str, Any] = {
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