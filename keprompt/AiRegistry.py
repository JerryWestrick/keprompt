from typing import Type
from .AiCompany import AiCompany
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class AiModel:
    company: str
    model: str
    input: float
    output: float
    context: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AiModel':
        return cls(**data)

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return (input_tokens * self.input) + (output_tokens * self.output)


class AiRegistry:
    handlers: Dict[str, Type['AiCompany']] = {}
    models: Dict[str, AiModel] = {}
    _initialized: bool = False

    @classmethod
    def register_handler(cls, company_name: str, handler_class: Type['AiCompany']) -> None:
        cls.handlers[company_name] = handler_class

    @classmethod
    def create_handler(cls, prompt) -> 'AiCompany':
        """Create and return appropriate AI handler instance for given model"""
        model = cls.get_model(prompt.model)
        handler_class = cls.get_handler(model.company)
        return handler_class(prompt=prompt)

    @classmethod
    def get_handler(cls, company_name: str) -> Type['AiCompany']:
        handler = cls.handlers.get(company_name)
        if not handler:
            raise ValueError(f"No handler registered for {company_name}")
        return handler

    @classmethod
    def register_models_from_dict(cls, model_definitions: Dict[str, Dict[str, Any]]) -> None:
        cls.models.update({
            name: AiModel.from_dict(data)
            for name, data in model_definitions.items()
        })

    @classmethod
    def get_model(cls, model_name: str) -> AiModel:
        if model_name not in cls.models:
            raise ValueError(f"Model {model_name} not found in configuration")
        return cls.models[model_name]

