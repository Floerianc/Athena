
<p align="center">
  <img src="./assets/icon_edit.png" alt="Athena Logo" width="128" />
</p>

<p style="font-size: 8pt" align="center">
    Icon was generated with AI.
    It's only a placeholder, will be replaced with real art
</p>

<h1 align="center">
    Athena
</h1>

<p align="center">
    <strong>
        Wisdom for your data.
    </strong><br>
    Ingest large JSON or text files, store them in a vector database, and let an AI answer your queries - quickly, efficiently, and flexibly.
</p>

---

## 🚀 Features

- **🔗 Vector‑based Storage**  
    • Split or normalize text (by blank lines, newlines, or fixed‐size chunks)  
    • Embed chunks into ChromaDB for ultra‑fast semantic lookup  
- **🔍 Smart Search & Retrieval**  
    • Highlight query terms in returned documents  
    • Filter results by metadata & distance thresholds  
    • Cap output by tokens for cost control  
- **🤖 AI Pipeline**  
    • Convert `QueryResults` + user query into a single, structured prompt  
    • Full support for JSON, plain‑text & Markdown outputs  
    • Configurable max_tokens for both input & output  
- **📊 Lightweight Benchmarks**  
    • Automatically log system specs, input sizes, timings & memory  
    • CLI‑friendly display and full JSON export of every run  
- **🎨 Colorful CLI** with Colorama  
- **⚙️ Rich Configuration** via `Config` (models, parsing modes, memory limits…)

---

## 📦 Installation

```bash
git clone https://github.com/floerianc/athena.git
cd athena
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
````

---

## ✅ What’s Done

- Vector DB integration & chunk formatting
- Query highlighting, result cleaning & token capping
- Prompt pipeline: structured JSON, plain‑text & Markdown modes
- ChromaDB collection lifecycle (delete old → load new)
- Extensive logging & Colorama‑powered CLI
- Config for every critical parameter
- JSON & Plaintext parsing
- Benchmarks with system & DB info + JSON export

---

## 🔮 Roadmap

| Priority      | Task                                                |
| ------------- | --------------------------------------------------- |
| **Very High** | • Plain‑text, Markdown & PDF input support          |
|               | • Improved summarization (faster models, per‑chunk) |
|               | • Search result re‑ranking by a secondary AI        |
|               | • Improved prompt shortener                         |
| **High**      | • Support max\_tokens for both input & output       |
|               | • Better error handling                             |
| **Mid**       | • Cool CLI polish & sub‑commands                    |
|               | • Major code cleanup & logging                      |
|               | • Unit tests                                        |
| **Low**       | • README enhancement & examples                     |
| **Future**    | • Webapp interface                                  |

---

## 📄 License

[GPLv3](LICENSE) © 2025 Floerianc
