import typing
import uuid
import random
import httpx
import ujson

from ...models import adapter
from ...models.adapter import llm
from ...entities import request
from ...entities import response, exceptions
from ...models.channel import evaluation

@adapter.llm_adapter
class Gpt4FreeAdapter(llm.LLMLibAdapter):

    @classmethod
    def name(cls) -> str:
        return "xtekky/gpt4free"

    @classmethod
    def description(cls) -> str:
        return "Use Gpt4free UI with openai format."

    def supported_models(self) -> list[str]:
        models_string = self.config.get("models", "gpt-3.5-turbo")
        return models_string.split(",")

    def function_call_supported(self) -> bool:
        return False

    def stream_mode_supported(self) -> bool:
        return True    

    def multi_round_supported(self) -> bool:
        return True

    @classmethod
    def config_comment(cls) -> str:
        return \
"""Please provide necessary parameters:

{
    "url": "your_chat_url",
    "models": "Optional. Default is 'gpt-3.5-turbo'.
It should be a list of available models in this API, separated by commas without spaces. 
For example: 'gpt4,gpt-4-o,gpt-4-turbo'
}
"""

    @classmethod
    def supported_path(cls) -> str:
        return "/v1/chat/completions"

    def __init__(self, config: dict, eval: evaluation.AbsChannelEvaluation):
        self.config = config
        self.eval = eval

    async def test(self) -> typing.Union[bool, str]:
        try:
            api_url = self.config["url"]
            models = self.supported_models()
            model = "gpt-3.5-turbo" if "gpt-3.5-turbo" in models else random.choice(models)
            unique_id = uuid.uuid4()
            data = {
                "id": str(random.randint(1111111, 99999999999999999999)),
                "conversation_id": str(unique_id),
                "model": model,
                "web_search": False,
                "provider": "",
                "messages": [{"role": "user", "content": "Hi, respond 'Hello, world!' please."}],
                "auto_continue": True,
                "api_key": None
            }
            headers = {
                'Accept-Language': 'ru-RU',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Origin': api_url,
                'Pragma': 'no-cache',
                'Referer': f'{api_url}/chat/{unique_id}',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
                'accept': 'text/event-stream',
                'content-type': 'application/json'
            }
            answer = ""

            async with httpx.AsyncClient(timeout=None, verify=False, follow_redirects=True) as client:
                async with client.stream("POST", f"{api_url}/backend-api/v2/conversation", json=data, headers=headers) as model_response:
                    model_response.raise_for_status()
                    async for line in model_response.aiter_lines():
                        if line:
                            line_data = ujson.loads(line)
                            if line_data.get("type") == "content":
                                answer += line_data.get("content", "")

            if answer == "":
                return False, "Gpt4free test failed."
            else:
                return True, ""
        except Exception as e:
            return False, "Gpt4free test failed."

    async def query(self, req: request.Request) -> typing.AsyncGenerator[response.Response, None]:
        messages = req.messages
        model = req.model
        random_int = random.randint(0, 1000000000)
        unique_id = str(uuid.uuid4())
        api_url = self.config["url"]

        async with httpx.AsyncClient(timeout=None, verify=False, follow_redirects=True) as client:
            headers = {
                'Accept-Language': 'ru-RU',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Origin': api_url,
                'Pragma': 'no-cache',
                'Referer': f'{api_url}/chat/{unique_id}',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
                'accept': 'text/event-stream',
                'content-type': 'application/json'
            }
            data = {
                "id": str(random.randint(1111111, 99999999999999999999)),
                "conversation_id": unique_id,
                "model": model,
                "web_search": False,
                "provider": "",
                "messages": messages,
                "auto_continue": True,
                "api_key": None,
                "stream": True
            }
            try:
                async with client.stream("POST", f"{api_url}/backend-api/v2/conversation", json=data, headers=headers) as model_response:
                    model_response.raise_for_status()
                    async for line in model_response.aiter_lines():
                        if line:
                            line_data = ujson.loads(line)
                            if line_data.get("type") == "content":
                                text = line_data.get("content", "")
                                yield response.Response(
                                    id=random_int,
                                    finish_reason=response.FinishReason.NULL,
                                    normal_message=text,
                                    function_call=None
                                )
                    yield response.Response(
                        id=random_int,
                        finish_reason=response.FinishReason.STOP,
                        normal_message="",
                        function_call=None
                    )
            except ValueError as e:
                raise ValueError(f"JSON decoding error: {e}\nLine content: {line}")