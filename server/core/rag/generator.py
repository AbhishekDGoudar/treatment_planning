from dataclasses import dataclass
from django.conf import settings

from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama


@dataclass
class PromptPiece:
    role: str
    content: str


class GeneratorFactory:
    def __init__(self):
        if settings.AI_PROVIDER.upper() == "OPENAI":
            self.llm = ChatOpenAI(
                model=settings.OPENAI_LLM_MODEL,
                temperature=0
            )
        else:
            self.llm = ChatOllama(
                model=settings.OLLAMA_LLM_MODEL,
                temperature=0
            )

    def generate(self, pieces: list[PromptPiece]) -> str:
        messages = [(p.role, p.content) for p in pieces]
        response = self.llm.invoke(messages)
        return response.content.strip()
