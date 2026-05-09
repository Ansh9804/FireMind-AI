import os
import json
import pickle
from backend.app_config import DATA_PATH

CACHE_PATH = os.path.join(DATA_PATH, "texts_cache.pkl")

class MockIndex:
    def add(self, embeddings):
        pass

def semantic_chunk_text(text, max_chunk_size=800):
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""
    
    for p in paragraphs:
        if len(current_chunk) + len(p) < max_chunk_size:
            current_chunk += p + "\n\n"
        else:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            current_chunk = p + "\n\n"
            
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
        
    return chunks

def load_documents():
    docs = []
    json_path = os.path.join(DATA_PATH, "source_documents.json")
    if os.path.exists(json_path):
        try:
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)
                if "documents" in data:
                    docs.extend([d["content"] for d in data["documents"]])
        except Exception as e:
            print(f"Error loading main JSON: {e}")

    extra_path = os.path.join(DATA_PATH, "extra")
    if os.path.exists(extra_path):
        for file in os.listdir(extra_path):
            file_path = os.path.join(extra_path, file)
            try:
                if file.endswith((".txt", ".md")):
                    with open(file_path, encoding="utf-8") as f:
                        docs.append(f.read())
                elif file.endswith(".json"):
                    with open(file_path, encoding="utf-8") as f:
                        data = json.load(f)
                        docs.append(json.dumps(data))
            except Exception as e:
                print(f"Error loading extra file {file}: {e}")

    final_docs = []
    for doc in docs:
        final_docs.extend(semantic_chunk_text(doc))
    return final_docs

def build_index():
    if os.path.exists(CACHE_PATH):
        print("Loading cached documents...")
        try:
            with open(CACHE_PATH, "rb") as f:
                texts = pickle.load(f)
            return MockIndex(), texts
        except Exception as e:
            print(f"Failed to load cache: {e}")

    print("Loading documents...")
    texts = load_documents()
    print("Documents ready!")
    return MockIndex(), texts

def create_embeddings(texts):
    return None

def save_index(index, texts):
    try:
        os.makedirs(DATA_PATH, exist_ok=True)
        with open(CACHE_PATH, "wb") as f:
            pickle.dump(texts, f)
        print(f"Successfully saved {len(texts)} chunks to cache.")
    except Exception as e:
        print(f"Failed to save cache: {e}")