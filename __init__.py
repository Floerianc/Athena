# TODO: Make first attempts with vector-based database              (X)
#       - Format lists into something chromadb can save             (HIGH PRIORITY)
# TODO: Query searches and other shit                               (X)
#       - Function to highlight query in documents                  (X)
#       - clean results                                             (X)
#       - Cap at max tokens                                         (X)
# TODO: Pipeline to AI to process query search and results          (X)
#       - Is able to convert QueryResults and user query into       (X)
#         a pure string prompt                                      (X)
#       - Add full support for structured outputs                   (X)
#       - Add support for max_tokens                                (X)
# TODO: Cool CLI and API for allat                                  (COMING SOON)
# TODO: Delete old collection before loading new one                (X)
# TODO: Major code clean-up                                         (MID PRIORITY)
# TODO: More Configs                                                (MID PRIORITY)
# TODO: Fix venv                                                    (X)
# TODO: Add memory / history to chat                                (HIGH PRIORITY)
# TODO: Support plain-text, markdown and PDF inputs                 (VERY HIGH PRIORITY)
# TODO: Tools for summarization (z.B. chapters)                     (HIGH PRIORITY)
# TODO: Sort search results by relevance from another AI            (HIGH PRIORITY)
# TODO: Prompt shortener                                            (HIGH PRIORITY)
# TODO: Webapp                                                      (NOT IMPORTANT YET)
# TODO: Unit-Tests                                                  (MID PRIORITY)

# externals
import os
import sys

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
    config = config.Config(config.OutputTypes.JSON)
    db = db.DBManager(config)
    processor = processor.Processor(db, "dumps/test.json", insert_json=True)
    search_engine = search.SearchEngine(db)
    
    query = "Was müsste Leon tun, um ein eigenständiges, erfolgreiches Silicon Valley Unternehmen zu gründen? Beziehe dich auf explizite Stellen aus der Geschichte und nenne detaillierte Vorschläge."
    raw_results = search_engine.search_collection(
        query
    )
    
    query_data = gpt.QueryData(query, raw_results)
    gpt_response = gpt.GPTQuery(db, query_data, config, "dumps/schema.json", instant_request=True)
    print(gpt_response.response)
    
    gpt_response.save_debug()


# Token calculation:

# Input:
#   length of query                             (???    Tokens              )   [Testing: 40 Tokens]
#   max_tokens from search result in chromadb   (2048   Tokens by default   )   [Testing: 2048 Tokens]
#   Chat history / Memory                       (n * max_tokens             )   [Testing: n * 200 Tokens, max: 2000 Tokens]
#   JSON-Schema                                 (???    Tokens              )   [Testing: 238 Tokens]
#   Total:
#       40 + 2048 + 238 = 2326 Tokens           (According to OpenAI: 2.41k) <-- The rest is probably from the formatting of the Input

# Output:
#   max_tokens for the output