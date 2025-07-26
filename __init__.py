# TODO: Make first attempts with vector-based database              (X)
#       - Format lists into something chromadb can save             (X) (Easier than I thought lol)
# TODO: Query searches and other shit                               (X)
#       - Function to highlight query in documents                  (X)
#       - clean results                                             (X)
#       - Cap at max tokens                                         (X)
# TODO: Pipeline to AI to process query search and results          (X)
#       - Is able to convert QueryResults and user query into       (X)
#         a pure string prompt                                      (X)
#       - Add full support for structured outputs                   (X)
#       - Add support for max_tokens                                (X)
# TODO: Cool CLI                                                    (MID PRIORITY)
# TODO: Delete old collection before loading new one                (X)
# TODO: More logging                                                (X)
# TODO: Major code clean-up                                         (MID PRIORITY)
# TODO: Colorama color                                              (LOW PRIORITY)
# TODO: Code comments and docs                                      (VERY HIGH PRIORITY)
# TODO: README File                                                 (LOW PRIORITY)
# TODO: More Configs                                                (X)
# TODO: Better Error handling                                       (MID PRIORITY)
# TODO: Improve typings                                             (X)
# TODO: Fix logging bug                                             (X)
# TODO: Put logging decorator into seperated file
# TODO: Fix venv                                                    (X)
# TODO: Add memory / history to chat                                (X)
#           Idee: Memory nach queue filtern mit ChromaDB
#               # TODO: include recent responses for better context (X)
# TODO: Support plain-text, markdown and PDF inputs                 (VERY HIGH PRIORITY)
#           Plain-text: After each newline/blank line/by chunk_size (X)
#               - Allows parsing in these ways:
#                   - By blank lines
#                   - By newlines
#                   - By chunking to specific length
#               - Allows chunking text:
#                   - Lengthens text to specific length
#                   - Shortens text to specific length
#           TODO: Try with long single lines (shorten_doc())
#           Markdown: Per chapter
#           PDF: Per Page
# TODO: Support max_tokens for input AND output                     (HIGH PRIORITY)
# TODO: Improve summarization (shorten_data)                        (HIGH PRIORITY)
#           Idea: Do it for each individually with a fast model
# TODO: Sort search results by relevance from another AI            (HIGH PRIORITY)
# TODO: Prompt shortener                                            (HIGH PRIORITY)
# TODO: Webapp                                                      (NOT IMPORTANT YET)
# TODO: Unit-Tests                                                  (MID PRIORITY)
# TODO: Benchmarks                                                  (MID PRIORITY)

# externals
import os
import sys
import time

os.chdir(
    os.path.dirname(
        os.path.realpath(sys.argv[0])
    )
)

# locals
import config
import db
import processor
import search
import gpt

if __name__ == "__main__":
    config = config.Config(config.InputTypes.PLAIN, config.OutputTypes.MD)
    db = db.DBManager(config)
    processor = processor.Processor(db, config, "dumps/test.txt", insert_json=True)
    search_engine = search.SearchEngine(config, db)
    
    while True:
        query = input("To AI > ")
        if query.lower() in ["exit", "quit", "q"]:
            print("Exiting...")
            break
        
        s = time.time()
        clean_results = search_engine.search_collection(
            query
        )
        
        query_data = gpt.QueryData(query, clean_results)
        gpt_response = gpt.GPTQuery(db, query_data, config, "dumps/schema.json", instant_request=True)
        print(gpt_response.response)
        # print(db.chat_history.chroma_collection.get())
        # print(str(gpt_response.data))
        gpt_response.save_debug()
        
        e = time.time()
        print(f"Query took {e - s:.2f} seconds.\nModel: {config.response.model}")


# Token calculation:

# Input:
#   length of query                             (???    Tokens              )   [Testing: 40 Tokens]
#   max_tokens from search result in chromadb   (2048   Tokens by default   )   [Testing: 2048 Tokens]
#   Chat history / Memory                       (n * max_tokens             )   [Testing: n * 200 Tokens * 2, max: 2000 Tokens]
#   JSON-Schema                                 (???    Tokens              )   [Testing: 238 Tokens]
#   Total:
#       40 + 2048 + 238 = 2326 Tokens           (According to OpenAI: 2.41k) <-- The rest is probably from the formatting of the Input

# Output:
#   max_tokens for the output

# Benchmark results:
#   - gpt-4.1-mini:     13.22 seconds for 1 query
#   - gpt-4.1-nano:     5.56 seconds for 1 query
#   - gpt-3.5-turbo:    6.32 seconds for 1 query (???)