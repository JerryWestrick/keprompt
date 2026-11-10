from .AiOpenAi import AiOpenAi
from .ModelManager import ModelManager


class AiOllama(AiOpenAi):
    """OpenAI-compatible chat completions.

    The request URL is the model's overlay ``source`` (the server base, including
    ``/v1``) plus ``/chat/completions``. The port in that base is what distinguishes
    one local server from another.
    """

    litellm_provider = "ollama"

    def get_api_url(self) -> str:
        source = ModelManager.get_model(self.prompt.model).source.strip().rstrip("/")
        if not source:
            raise ValueError(f"Model {self.prompt.model} has no source URL")
        return f"{source}/chat/completions"

    def get_headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.prompt.api_key:
            headers["Authorization"] = f"Bearer {self.prompt.api_key}"
        return headers


ModelManager.register_handler(provider_name="ollama", handler_class=AiOllama)
