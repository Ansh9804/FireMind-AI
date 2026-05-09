import numpy as np
import socket
socket.setdefaulttimeout(120) # Increase timeout for model downloads
from sentence_transformers import SentenceTransformer, CrossEncoder

# Load our primary retriever and our new secondary re-ranker
model = SentenceTransformer('all-MiniLM-L6-v2')
cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

def retrieve_context(query, index, texts, fetch_k=15, final_k=4):
    if not texts or index is None or index.ntotal == 0:
        return ""

    # Phase 1: Fast FAISS Retrieval (Cast a wide net)
    query_vec = model.encode([query]).astype("float32")
    D, I = index.search(query_vec, fetch_k)

    initial_results = []
    for i in I[0]:
        if 0 <= i < len(texts):
            initial_results.append(texts[i])

    if not initial_results:
        return ""

    # Phase 2: Cross-Encoder Re-ranking (High accuracy sorting)
    cross_inp = [[query, doc] for doc in initial_results]
    scores = cross_encoder.predict(cross_inp)

    # Sort the documents based on the Cross-Encoder's scoring
    ranked_results = [doc for _, doc in sorted(zip(scores, initial_results), reverse=True)]

    # Return only the absolute best matches
    return "\n\n".join(ranked_results[:final_k])