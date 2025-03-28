import typing, uuid, random, requests, ujson, httpx, json

from ...models import adapter
from ...models.adapter import llm
from ...entities import request
from ...entities import response, exceptions
from ...models.channel import evaluation


@adapter.llm_adapter
class GPTAdapter(llm.LLMLibAdapter):

    @classmethod
    def name(cls) -> str:
        return "Openai/GPT"

    @classmethod
    def description(cls) -> str:
        return "Use all APIs with openai format."

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
"""Please provide your Openai API key, and Openai API base:

{
    "key": "your_api_key",
    "url": "your_openai_api_base",
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
            data = {
                "model": model,
                "messages": [{"role": "user", "content": "Hi, respond 'Hello, world!' please."}],
            }
            api_key = self.config["key"]
            headers = {
                "Authorization": f"Bearer {api_key}"
            }
            async with httpx.AsyncClient() as client:
                response = await client.post(api_url, json=data, headers=headers, timeout=None)
                response_data = response.json()
                response_content = response_data["choices"][0]["message"]["content"]

            return True, ""
        except Exception as e:
            return False, str(e)

    async def create_completion_data(self, chunk):
        try:
            return ujson.loads(chunk)
        except ValueError as e:
            raise ValueError(f"Error loading JSON from chunk: {e}\nChunk: {chunk}")

    async def query(self, req: request.Request) -> typing.AsyncGenerator[response.Response, None]:        
        messages = req.messages
        model = req.model
        random_int = random.randint(0, 1000000000)

        async with httpx.AsyncClient(timeout=None) as client:
            api_key = self.config["key"]
            headers = {
                "Authorization": f"Bearer {api_key}"
            }
            data = {
                "model": model,
                "messages": messages,
                "stream": True
            }
            async with client.stream("POST", self.config["url"], json=data, headers=headers) as model_response:
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
                            if chunk["choices"][0]["finish_reason"]=="stop":
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
