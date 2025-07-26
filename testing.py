import chromadb
from datetime import datetime
from ast import literal_eval

chroma_client = chromadb.Client()
chroma_collection = chroma_client.get_or_create_collection(
    name = "TestingDB",
    metadata = {
        'description': 'Testing with AI',
        'created': str(datetime.now())
    }
)

def convert_types(allowed_dict: dict) -> dict:
    for key, value in allowed_dict.items():
        if key == "string":
            continue
        else:
            converted = [str(v) for v in value[0]]
            value[0] = converted
    return allowed_dict

def test_types(convert: bool) -> dict:
    allowed = {
        'string': [["Hello"], True],
        'number': [[25, 0.25], True],
        'boolean': [[True, False], True],
        'null': [[None], True],
        'object': [[{"hello": "good bye"}], True],
        'array': [[["Hello", "Good bye"]], True]
    }
    
    if convert:
        allowed = convert_types(allowed)
    
    for key, value in allowed.items():
        try:
            chroma_collection.add(
                ids =       [f"{key}{i}" for i in range(len(value[0]))],
                documents = [v for v in value[0]]
            )
            allowed[key][1] = True
        except:
            allowed[key][1] = False
    return allowed

def get_documents() -> list[str]:
    return chroma_collection.get()['documents']

def convert_from_string(docs: list[str]) -> list:
    for i in range(len(docs)):
        try:
            docs[i] = literal_eval(docs[i])
        except:
            continue
    return docs

if __name__ == "__main__":
    test_types(True)
    
    docs = get_documents()
    print(docs)
    
    converted = convert_from_string(docs)
    print(converted)