# utils/hybrid_retriever.py

import streamlit as st
from typing import List, Dict, Any
from langchain.docstore.document import Document
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
import numpy as np
import re

class HybridRetriever:
    """
    A simplified hybrid retriever that combines semantic search (vector) with keyword search (BM25)
    for improved retrieval performance.
    """
    
    def __init__(self, vectordb: Chroma, documents: List[Document], 
                 semantic_weight: float = 0.7, keyword_weight: float = 0.3):
        """
        Initialize the hybrid retriever.
        
        Args:
            vectordb: Chroma vector database
            documents: List of documents for BM25 indexing
            semantic_weight: Weight for semantic search results (0-1)
            keyword_weight: Weight for keyword search results (0-1)
        """
        self.vectordb = vectordb
        self.documents = documents
        self.semantic_weight = semantic_weight
        self.keyword_weight = keyword_weight
        
        # Initialize retrievers
        self._setup_retrievers()
        
    def _setup_retrievers(self):
        """Setup the individual retrievers."""
        try:
            # Vector retriever (semantic search)
            self.vector_retriever = self.vectordb.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 10}
            )
            
            # BM25 retriever (keyword search)
            self.bm25_retriever = BM25Retriever.from_documents(self.documents)
            self.bm25_retriever.k = 10
            
            # Ensemble retriever (combines both)
            self.ensemble_retriever = EnsembleRetriever(
                retrievers=[self.vector_retriever, self.bm25_retriever],
                weights=[self.semantic_weight, self.keyword_weight]
            )
            
            self.final_retriever = self.ensemble_retriever
            
        except Exception as e:
            st.warning(f"⚠️ Hybrid retriever setup failed: {e}")
            st.info("Falling back to vector search only.")
            self.final_retriever = self.vectordb.as_retriever()
    
    def get_relevant_documents(self, query: str, k: int = 5) -> List[Document]:
        """
        Retrieve relevant documents using hybrid search.
        
        Args:
            query: User query
            k: Number of documents to retrieve
            
        Returns:
            List of relevant documents
        """
        try:
            # Get results from ensemble retriever
            docs = self.final_retriever.get_relevant_documents(query)
            
            # Limit to k documents
            return docs[:k]
            
        except Exception as e:
            st.error(f"❌ Error in hybrid retrieval: {e}")
            # Fallback to vector search only
            return self.vectordb.as_retriever().get_relevant_documents(query)[:k]
    
    def get_relevant_documents_with_scores(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents with scores for analysis.
        
        Args:
            query: User query
            k: Number of documents to retrieve
            
        Returns:
            List of documents with scores and metadata
        """
        try:
            # Get results from both retrievers
            vector_docs = self.vector_retriever.get_relevant_documents(query)
            bm25_docs = self.bm25_retriever.get_relevant_documents(query)
            
            # Combine and score results
            combined_results = self._combine_results(query, vector_docs, bm25_docs, k)
            
            return combined_results
            
        except Exception as e:
            st.error(f"❌ Error in hybrid retrieval with scores: {e}")
            return []
    
    def _combine_results(self, query: str, vector_docs: List[Document], 
                        bm25_docs: List[Document], k: int) -> List[Dict[str, Any]]:
        """
        Combine results from both retrievers with scoring.
        """
        # Create document ID mapping
        doc_scores = {}
        
        # Score vector results
        for i, doc in enumerate(vector_docs):
            doc_id = self._get_doc_id(doc)
            if doc_id not in doc_scores:
                doc_scores[doc_id] = {
                    'document': doc,
                    'vector_score': 1.0 - (i / len(vector_docs)),  # Higher rank = higher score
                    'bm25_score': 0.0,
                    'combined_score': 0.0
                }
        
        # Score BM25 results
        for i, doc in enumerate(bm25_docs):
            doc_id = self._get_doc_id(doc)
            if doc_id in doc_scores:
                doc_scores[doc_id]['bm25_score'] = 1.0 - (i / len(bm25_docs))
            else:
                doc_scores[doc_id] = {
                    'document': doc,
                    'vector_score': 0.0,
                    'bm25_score': 1.0 - (i / len(bm25_docs)),
                    'combined_score': 0.0
                }
        
        # Calculate combined scores
        for doc_id, scores in doc_scores.items():
            scores['combined_score'] = (
                self.semantic_weight * scores['vector_score'] +
                self.keyword_weight * scores['bm25_score']
            )
        
        # Sort by combined score and return top k
        sorted_results = sorted(
            doc_scores.values(),
            key=lambda x: x['combined_score'],
            reverse=True
        )
        
        return sorted_results[:k]
    
    def _get_doc_id(self, doc: Document) -> str:
        """Generate a unique ID for a document."""
        # Use content hash as ID
        import hashlib
        content_hash = hashlib.sha256(doc.page_content.encode()).hexdigest()
        return f"{doc.metadata.get('source', 'unknown')}_{content_hash[:8]}"
    
    def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Analyze the query to determine the best retrieval strategy.
        
        Args:
            query: User query
            
        Returns:
            Analysis results
        """
        analysis = {
            'query_length': len(query),
            'word_count': len(query.split()),
            'has_specific_terms': self._has_specific_terms(query),
            'recommended_weights': self._get_recommended_weights(query),
            'query_type': self._classify_query(query)
        }
        
        return analysis
    
    def _has_specific_terms(self, query: str) -> bool:
        """Check if query contains specific terms that benefit from keyword search."""
        # Look for specific terms, numbers, proper nouns
        specific_patterns = [
            r'\b\d+\b',  # Numbers
            r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b',  # Proper nouns
            r'\b(what|when|where|who|how|why)\b',  # Question words
        ]
        
        for pattern in specific_patterns:
            if re.search(pattern, query):
                return True
        return False
    
    def _get_recommended_weights(self, query: str) -> Dict[str, float]:
        """Get recommended weights based on query analysis."""
        if self._has_specific_terms(query):
            return {
                'semantic_weight': 0.4,
                'keyword_weight': 0.6
            }
        else:
            return {
                'semantic_weight': 0.8,
                'keyword_weight': 0.2
            }
    
    def _classify_query(self, query: str) -> str:
        """Classify the type of query."""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['what', 'when', 'where', 'who']):
            return 'factual'
        elif any(word in query_lower for word in ['how', 'why', 'explain']):
            return 'explanatory'
        elif any(word in query_lower for word in ['compare', 'difference', 'similar']):
            return 'comparative'
        else:
            return 'general' 