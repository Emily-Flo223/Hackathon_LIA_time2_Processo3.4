import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# Carrega as variáveis do ficheiro .env para o ambiente do sistema
load_dotenv()

def get_openrouter_llm(temperature: float = 0.0, model: str = "openai/gpt-4o-mini") -> ChatOpenAI:
    """
    Retorna a instância do modelo LangChain configurada para o OpenRouter.
    Ideal para usar com .with_structured_output(Schema).
    """
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("ERRO: OPENROUTER_API_KEY não encontrada. Verifique se o ficheiro .env está na mesma pasta.")

    return ChatOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        model=model,
        temperature=temperature,
        timeout=30,
        max_retries=2
    )

def call_llm(system_prompt: str, user_prompt: str, temperature: float = 0.0, model: str = "google/gemma-4-31b-it") -> str:
    """
    Função original: faz a chamada simples e devolve uma string.
    """
    llm = get_openrouter_llm(temperature=temperature, model=model)
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_prompt},
    ]
    
    return llm.invoke(messages).content