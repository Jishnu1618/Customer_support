import json
from pathlib import Path
from typing import List, Dict, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class TFIDFRetriever:
    """
    TF-IDF Vectorizer Retriever fitted strictly on historical problem text (`customer_text`)
    from spotify_knowledge.jsonl.
    Retrieves top-K non-duplicate support exchanges across all intents.
    """
    
    def __init__(self, knowledge_path: Path):
        self.knowledge_path = knowledge_path
        self.documents: List[Dict[str, Any]] = []
        self.vectorizer: TfidfVectorizer = None
        self.tfidf_matrix = None
        self._load_and_fit()
        
    def _load_and_fit(self):
        print(f"Loading knowledge corpus from {self.knowledge_path}...")
        raw_docs = []
        seen_texts = set()
        
        with open(self.knowledge_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                cust_text = record.get("customer_text", "").strip()
                brand_reply = record.get("brand_reply_text", "").strip()
                ex_id = record.get("example_id", "")
                
                # Deduplicate exact customer texts
                if cust_text and cust_text not in seen_texts:
                    seen_texts.add(cust_text)
                    raw_docs.append({
                        "example_id": ex_id,
                        "customer_text": cust_text,
                        "brand_reply_text": brand_reply,
                        "group_id": record.get("group_id", "")
                    })
                    
        self.documents = raw_docs
        print(f"Loaded {len(self.documents)} unique historical support exchanges.")
        
        corpus_texts = [doc["customer_text"] for doc in self.documents]
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=25000,
            sublinear_tf=True
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(corpus_texts)
        print("TF-IDF vectorizer successfully fitted on historical corpus.")
        
    def retrieve(self, query_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve top-k most similar non-duplicate historical support exchanges.
        """
        if not query_text or not self.documents:
            return []
            
        query_vec = self.vectorizer.transform([query_text])
        scores = cosine_similarity(query_vec, self.tfidf_matrix)[0]
        
        # Get top indices
        top_indices = scores.argsort()[::-1][:top_k * 2]
        
        results = []
        seen_examples = set()
        
        for idx in top_indices:
            score = float(scores[idx])
            doc = self.documents[idx]
            ex_id = doc["example_id"]
            
            if ex_id not in seen_examples:
                seen_examples.add(ex_id)
                results.append({
                    "example_id": ex_id,
                    "customer_text": doc["customer_text"],
                    "brand_reply_text": doc["brand_reply_text"],
                    "similarity_score": round(score, 4)
                })
                if len(results) >= top_k:
                    break
                    
        return results
