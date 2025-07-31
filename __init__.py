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
# TODO: Cool CLI                                                    (WORKING ON...)
# TODO:     - Cool initialisation with progress bars and shiii      (WORKING ON...)
# TODO: Delete old collection before loading new one                (X)
# TODO: More logging                                                (X)
# TODO: Major code clean-up                                         (WORKING ON...)
# TODO: Colorama color                                              (X)
# TODO: Code comments and docs                                      (X) (For now!)
# TODO: README File                                                 (X) (For now!)
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
#           Try with long single lines (shorten_doc())              (X)
#           Markdown: Per chapter
# TODO:     PDF: Per Page                                           (WORKING ON..)
# TODO:         - For some reason not same output as plain .txt

# TODO: Support max_tokens for input AND output                     (HIGH PRIORITY)
# TODO: Improve summarization (shorten_data)                        (HIGH PRIORITY)
#           Idea: Do it for each individually with a fast model
# TODO: Sort search results by relevance from another AI            (HIGH PRIORITY)
# TODO: Prompt shortener                                            (HIGH PRIORITY)
# TODO: Webapp                                                      (NOT IMPORTANT YET)
# TODO: Unit-Tests                                                  (MID PRIORITY)
# TODO: Benchmarks                                                  (X) (For now)
#       - Allows for settings (timestamp, input_file, user_inputs, models to test)
#       - Gathers system info (CPU, RAM, OS, Python version)
#       - DB Info (input_size, input_tokens, documents)
#       - Results (timestamps, model_responses, minTime, maxTime, avgTime)
#       - Shows every step nicely in console (CLI)
#       - Full JSON export (every class, dataclass and result)
#       - Dummy Data to test
#       - BUT: can be heavy on OpenAI tokens!

# externals
import os
import sys

os.chdir(
    os.path.dirname(
        os.path.realpath(sys.argv[0])
    )
)

# Benchmark results:
#   1. Attempt:
#       min time: 3.12 s
#       avg time: 4.71 s
#       max time: 6.65 s
#
#   2. Attempt:
#       min time: 2.68 s
#       avg time: 5.07 s
#       max time: 8.56 s

# Token calculation:
#   Coming soon