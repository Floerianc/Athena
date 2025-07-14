# TODO: Make first attempts with vector-based database              (X)
#       - Format lists into something chromadb can save             (HIGH PRIORITY)
# TODO: Query searches and other shit                               (X)
#       - Function to highlight query in documents                  (X)
#       - clean results                                             (X)
#       - Cap at max tokens                                         (X)
# TODO: Pipeline to AI to process query search and results          (X)
#       - Is able to convert QueryResults and user query into       (X)
#         a pure string prompt                                      (X) 
#       - Add full support for structured outputs                   (MID PRIORITY)
#       - Add support for max_tokens (doesn't work???)              (HIGH PRIORITY)
# TODO: Cool CLI and API for allat                                  (COMING SOON)
# TODO: Delete old collection before loading new one                (X)
# TODO: Major code clean-up                                         (HIGH PRIORITY)
# TODO: Fix venv

# externals
import sys

# locals
import processor
import search
import gpt

if __name__ == "__main__":
    proc = processor.Processor("./dumps/test.json")
    collection = proc.get_collection()
    
    search = search.SearchEngine(collection)
    query = 'Fasse die gesamte Geschichte kurz und knapp zusammen. Lasse aber nicht zu viele Informationen heraus.'
    results = search.search_collection(
        query,
    )
    cleaned = search.clean_results(results)
    
    data = gpt.InputData(
        query = query,
        data = results
    )
    query = gpt.GPTQuery(data, gpt.OutputTypes.PLAIN, "./dumps/schema.json")
    print(query.response)