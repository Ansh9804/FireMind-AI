import os
import json
import faiss
import pickle
import numpy as np
import socket
socket.setdefaulttimeout(120) # Increase timeout for model downloads
from sentence_transformers import SentenceTransformer
from backend.app_config import DATA_PATH

model = SentenceTransformer('all-MiniLM-L6-v2')
CACHE_PATH = os.path.join(DATA_PATH, "faiss_index.pkl")

# 🔥 UPGRADE: Semantic Chunker (Respects paragraphs and sentences)
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

def create_embeddings(texts):
    return np.array(model.encode(texts)).astype("float32")

def build_index():
    if os.path.exists(CACHE_PATH):
        print("Loading cached index...")
        with open(CACHE_PATH, "rb") as f:
            index, texts = pickle.load(f)
        return index, texts

    print("Building new FAISS index...")
    texts = load_documents()
    
    if not texts:
        print("No documents found. Returning empty index.")
        dim = model.get_sentence_embedding_dimension()
        return faiss.IndexFlatL2(dim), []

    embeddings = create_embeddings(texts)
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    save_index(index, texts)
    print("Index ready!")
    return index, texts

def save_index(index, texts):
    try:
        os.makedirs(DATA_PATH, exist_ok=True)
        with open(CACHE_PATH, "wb") as f:
            pickle.dump((index, texts), f)
        print(f"Index successfully saved to {CACHE_PATH} with {len(texts)} chunks.")
    except Exception as e:
        print(f"Failed to save index: {e}")