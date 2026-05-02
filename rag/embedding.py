# rag/embedding.py
import math
from collections import Counter
from typing import List, Dict, Iterable

class TfidfVectorizer:
    """
    A from-scratch implementation of TF-IDF vectorization.
    It does not rely on any external libraries like scikit-learn.
    """
    def __init__(self):
        self._idf: Dict[str, float] = {}
        self._vocabulary: set = set()
        self._doc_count: int = 0

    def _tokenize(self, text: str) -> List[str]:
        """A very simple tokenizer that splits by space and lowercases."""
        return text.lower().split()

    def fit(self, corpus: Iterable[str]):
        """
        Learns the vocabulary and IDF scores from a corpus of documents.
        :param corpus: An iterable of documents (strings).
        """
        self._doc_count = 0
        doc_freqs = Counter()
        
        # First pass: count document frequencies and build vocabulary
        for doc in corpus:
            self._doc_count += 1
            tokens = self._tokenize(doc)
            self._vocabulary.update(tokens)
            # Use a set to count each term only once per document
            doc_freqs.update(set(tokens))

        # Calculate IDF for each term in the vocabulary
        for term in self._vocabulary:
            # Classic IDF formula: log(N / (df + 1)) to avoid division by zero
            self._idf[term] = math.log(self._doc_count / (doc_freqs[term] + 1))

    def transform(self, documents: Iterable[str]) -> List[Dict[str, float]]:
        """
        Transforms documents into their TF-IDF vector representation.
        :param documents: An iterable of documents (strings).
        :return: A list of TF-IDF vectors (dictionaries).
        """
        tfidf_vectors = []
        for doc in documents:
            tokens = self._tokenize(doc)
            term_counts = Counter(tokens)
            total_terms = len(tokens)
            
            tfidf_vector = {}
            if total_terms > 0:
                for term, count in term_counts.items():
                    if term in self._vocabulary:
                        # TF = (term frequency in doc) / (total terms in doc)
                        tf = count / total_terms
                        # TF-IDF = TF * IDF
                        tfidf_vector[term] = tf * self._idf[term]
            
            tfidf_vectors.append(tfidf_vector)
            
        return tfidf_vectors

    def fit_transform(self, corpus: Iterable[str]) -> List[Dict[str, float]]:
        """
        A convenience method to both fit the model and transform the corpus.
        :param corpus: An iterable of documents (strings).
        :return: A list of TF-IDF vectors for the corpus.
        """
        self.fit(corpus)
        return self.transform(corpus)

if __name__ == '__main__':
    print("--- Testing embedding.py ---")
    
    # Sample corpus
    corpus = [
        "this is the first document",
        "this document is the second document",
        "and this is the third one",
        "is this the first document"
    ]

    vectorizer = TfidfVectorizer()
    
    # Test fit_transform
    tfidf_matrix = vectorizer.fit_transform(corpus)
    
    print("Vocabulary:", sorted(list(vectorizer._vocabulary)))
    print("\nTF-IDF Matrix:")
    for i, vec in enumerate(tfidf_matrix):
        # Print sorted by term for consistent output
        sorted_vec = {k: f"{v:.4f}" for k, v in sorted(vec.items())}
        print(f"  Doc {i+1}: {sorted_vec}")

    # Test transform on a new document
    new_doc = ["this is a new document"]
    new_vec = vectorizer.transform(new_doc)
    print("\nTF-IDF for new doc:")
    sorted_new_vec = {k: f"{v:.4f}" for k, v in sorted(new_vec[0].items())}
    print(f"  New Doc: {sorted_new_vec}")
