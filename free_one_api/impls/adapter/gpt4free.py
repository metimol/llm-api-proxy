import typing
import uuid
import random
import requests
import ujson
import httpx
import json

from ...models import adapter
from ...models.adapter import llm
from ...entities import request
from ...entities import response, exceptions
from ...models.channel import evaluation


@adapter.llm_adapter
class NextChatAdapter(llm.LLMLibAdapter):

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
                "id": str(random.randint(1111111, 99999999999999999999")),
                "conversation_id": unique_id,
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
            async with client.stream("POST", f"{api_url}/backend-api/v2/conversation", json=data, headers=headers) as model_response:
                model_response.raise_for_status()
                async for line in model_response.aiter_lines():
                    if line:
                        line = ujson.loads(line)
                        if line.get("type") == "content":
                            answer+=line.get("content", "")

            if content=="":
                return False, "Gpt4free test failed."
            else:
                return True, ""
        except:
            return False, "Gpt4free test failed."

    async def query(self, req: request.Request) -> typing.AsyncGenerator[response.Response, None]:        
        messages = req.messages
        model = req.model
        random_int = random.randint(0, 1000000000)
        api_url = self.config["url"]

        async with httpx.AsyncClient(timeout=None, verify=False, follow_redirects=True) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0",
                "Accept": "text/event-stream",
                "Accept-Language": "de,en-US;q=0.7,en;q=0.3",
                "Accept-Encoding": "gzip, deflate, br",
                "Content-Type": "application/json",
                "Referer": api_url,
                "x-requested-with": "XMLHttpRequest",
                "Origin": api_url,
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "Connection": "keep-alive",
                "Alt-Used": api_url,
            }
            data = {
                "model": model,
                "messages": messages,
                "stream": True
            }
            async with client.stream("POST", f"{api_url}/api/openai/v1/chat/completions", json=data, headers=headers) as model_response:
                model_response.raise_for_status()
                async for line in model_response.aiter_lines():
                    if line:
                        line_content = line[6:]
                        if line_content == "[DONE]":
                            yield response.Response(
                                id=random_int,
                                finish_reason=response.FinishReason.STOP,
                                normal_message="",
                                function_call=None
                            )
                            break
                        try:
                            chunk = await self.create_completion_data(line_content)
                            if chunk["choices"][0]["finish_reason"] == "stop":
                                yield response.Response(
                                    id=random_int,
                                    finish_reason=response.FinishReason.NULL,
                                    normal_message=text,
                                    function_call=None
                                )
                            else:
                                text = chunk["choices"][0]["delta"]["content"]
                                yield response.Response(
                                    id=random_int,
                                    finish_reason=response.FinishReason.NULL,
                                    normal_message=text,
                                    function_call=None
                                )
                        except ValueError as e:
                            raise ValueError(f"JSON decoding error: {e}\nLine content: {line_content}")