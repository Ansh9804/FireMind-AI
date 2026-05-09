import re
import math

class BM25:
    def __init__(self, corpus):
        self.corpus = corpus
        self.doc_len = [len(self.tokenize(doc)) for doc in corpus]
        self.avg_doc_len = sum(self.doc_len) / len(corpus) if corpus else 1
        self.doc_freqs = []
        self.idf = {}
        self.k1 = 1.5
        self.b = 0.75
        self.initialize()

    def tokenize(self, text):
        return re.findall(r'\w+', text.lower())

    def initialize(self):
        df = {}
        for doc in self.corpus:
            frequencies = {}
            tokens = self.tokenize(doc)
            for token in tokens:
                frequencies[token] = frequencies.get(token, 0) + 1
            self.doc_freqs.append(frequencies)
            for token in set(tokens):
                df[token] = df.get(token, 0) + 1
        
        for token, freq in df.items():
            self.idf[token] = math.log((len(self.corpus) - freq + 0.5) / (freq + 0.5) + 1)

    def score(self, query, index):
        query_tokens = self.tokenize(query)
        score = 0.0
        doc_freq = self.doc_freqs[index]
        d_len = self.doc_len[index]
        for token in query_tokens:
            if token in doc_freq:
                freq = doc_freq[token]
                tf = (freq * (self.k1 + 1)) / (freq + self.k1 * (1 - self.b + self.b * d_len / self.avg_doc_len))
                score += self.idf.get(token, 0) * tf
        return score

    def retrieve(self, query, top_k=4):
        if not self.corpus:
            return []
        scores = [self.score(query, i) for i in range(len(self.corpus))]
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        # Return chunks with non-zero score
        return [self.corpus[i] for i, score in ranked[:top_k] if score > 0]

def retrieve_context(query, index, texts, fetch_k=15, final_k=4):
    if not texts:
        return ""
    bm25 = BM25(texts)
    results = bm25.retrieve(query, top_k=final_k)
    return "\n\n".join(results)