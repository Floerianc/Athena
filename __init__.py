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
    db = db.DBManager()
    config = config.Config(config.OutputTypes.JSON)
    processor = processor.Processor(db, "dumps/test.json", insert_json=True)
    search_engine = search.SearchEngine(db)
    
    query = "Was müsste Leon tun, um ein eigenständiges, erfolgreiches Silicon Valley Unternehmen zu gründen? Beziehe dich auf explizite Stellen aus der Geschichte und nenne detaillierte Vorschläge."
    raw_results = search_engine.search_collection(
        query
    )
    
    query_data = gpt.QueryData(query, raw_results)
    gpt_response = gpt.GPTQuery(query_data, config, "dumps/schema.json", instant_request=True)
    print(gpt_response.response)
    
    gpt_response.save_debug()