from typing import List, Dict, Any

from langchain_community.vectorstores import LanceDB
from langchain_ollama import OllamaEmbeddings
from langchain_openai import OpenAIEmbeddings

from core import config

class TextRetriever:
    def __init__(self, provider: str):
        if provider.upper() == "OPENAI":
            self.embedder = OpenAIEmbeddings(model=config.OPENAI_EMBEDDING_MODEL)
        else:
            self.embedder = OllamaEmbeddings(model=config.OLLAMA_EMBEDDING_MODEL)

        self.store = LanceDB(
            embedding=self.embedder,
            uri=str(config.LANCE_DB_PATH),
            table_name="policy_docs",
        )

    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        results = self.store.similarity_search_with_score(query, k=k)
        formatted = []
        for doc, score in results:
            formatted.append(
                {
                    "text": doc.page_content,
                    "metadata": doc.metadata or {},
                    "score": score,
                }
            )
        return formatted
