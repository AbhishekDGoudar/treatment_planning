from dataclasses import dataclass
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_anthropic import ChatAnthropic

from core import config

@dataclass
class PromptPiece:
    role: str
    content: str


class GeneratorFactory:
    def __init__(self):
        provider = config.AI_PROVIDER.upper()
        if provider == "OPENAI":
            self.llm = ChatOpenAI(
                model=config.OPENAI_LLM_MODEL,
                temperature=0,
            )
        elif provider == "ANTHROPIC":
            self.llm = ChatAnthropic(
                model=config.ANTHROPIC_LLM_MODEL,
                temperature=0,
            )
        else:
            self.llm = ChatOllama(
                model=config.OLLAMA_LLM_MODEL,
                temperature=0,
            )

    def generate(self, pieces: list[PromptPiece]) -> str:
        messages = [(p.role, p.content) for p in pieces]
        response = self.llm.invoke(messages)
        return response.content.strip()
