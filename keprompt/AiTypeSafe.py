from typing import Dict, List

from .ModelManager import ModelManager
from .AiProvider import AiProvider
from .AiPrompt import AiMessage, AiLdmPart, LDM_ROLE

# A choice takes at most this many options, per TypeSafe's documentation.
MAX_CHOICE_OPTIONS = 255


def normalize_answer(raw: dict) -> dict:
    """TypeSafe's answer -> KePrompt's shape.

    `value` rather than `choice`/`score`/`noul` so that all three primitives read identically and a
    prompt author does not need to know which one answered. The primitive names its own result
    field, so `{"type": "noul", "noul": 0.98}` yields value 0.98.

    `confidence` and `probabilities` are carried through only when present. A `noul` answer has
    neither -- its 0..1 value *is* the answer -- so they are legitimately absent rather than
    synthesised into something that looks measured but is not.
    """
    if not isinstance(raw, dict) or 'type' not in raw:
        raise ValueError(f"LDM answer is not in the expected shape: {raw!r}")

    kind = raw['type']
    if kind not in raw:
        raise ValueError(f"LDM answer of type '{kind}' carries no '{kind}' field: {raw!r}")

    answer = {'value': raw[kind], 'type': kind}
    for field in ('confidence', 'probabilities', 'legend'):
        if field in raw:
            answer[field] = raw[field]
    return answer


class AiTypeSafe(AiProvider):
    """TypeSafe's LDMs. An LDM call is an execute like any other; only its content differs.

    It is sent the LDM message `.evaluate` added -- the question set and the state -- rather than
    the conversation, and its answers are written back into that same message.
    """
    litellm_provider = "typesafe"

    def select_messages(self) -> List[AiMessage]:
        ldm = [m for m in self.prompt.messages if m.role == LDM_ROLE]
        if not ldm:
            raise ValueError("an LDM call needs the LDM message .evaluate adds; there is none")
        return ldm[-1:]

    def request_options(self) -> Dict:
        return {}

    def _part(self, messages: List[AiMessage]) -> AiLdmPart:
        return next(p for p in messages[-1].content if isinstance(p, AiLdmPart))

    def to_company_messages(self, messages: List[AiMessage]) -> List[Dict]:
        part = self._part(messages)
        return [{'state': part.state, 'questions': part.questions}]

    def prepare_request(self, messages: List[Dict]) -> Dict:
        body = messages[-1]
        for name, spec in body['questions'].items():
            options = spec.get('criteria') or {}
            if spec.get('type') == 'choice' and len(options) > MAX_CHOICE_OPTIONS:
                raise ValueError(f"question '{name}' has {len(options)} options; a choice takes "
                                 f"at most {MAX_CHOICE_OPTIONS}")
        return {'state': body['state'],
                'model': ModelManager.get_model(self.prompt.model).get_api_model_name(),
                'questions': body['questions']}

    def get_api_url(self) -> str:
        return "https://api.typesafe.ai/v1/systemone"

    def get_headers(self) -> Dict:
        return {"Authorization": f"Bearer {self.prompt.api_key}", "Content-Type": "application/json"}

    def to_ai_message(self, response: Dict) -> AiMessage:
        message = self.select_messages()[-1]
        part = self._part([message])

        if 'answers' not in response:
            raise ValueError(f"LDM response carries no answers: {response!r}")
        missing = set(part.questions) - set(response['answers'])
        if missing:
            raise ValueError(f"LDM did not answer: {', '.join(sorted(missing))}")

        part.answers = {name: normalize_answer(raw) for name, raw in response['answers'].items()}
        part.model_served = response.get('model', self.prompt.model)
        part.usage = response.get('usage', {})
        return message

    def extract_token_usage(self, response: Dict) -> tuple[int, int]:
        usage = response.get("usage", {})
        return usage.get("input_tokens", 0), usage.get("output_tokens", 0)

    def calculate_costs(self, tokens_in: int, tokens_out: int) -> tuple[float, float]:
        model_info = ModelManager.get_model(self.prompt.model_lookup_key)
        if not model_info:
            return 0.0, 0.0
        return tokens_in * model_info.input_cost, tokens_out * model_info.output_cost


ModelManager.register_handler(provider_name="typesafe", handler_class=AiTypeSafe)
