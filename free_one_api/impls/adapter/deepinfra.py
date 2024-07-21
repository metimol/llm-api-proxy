import typing
import random
import httpx
import ujson
from fake_useragent import UserAgent

from ...models import adapter
from ...models.adapter import llm
from ...entities import request, response
from ...models.channel import evaluation

@adapter.llm_adapter
class DeepinfraAdapter(llm.LLMLibAdapter):
    @classmethod
    def name(cls) -> str:
        return "Deepinfra/Deepinfra-API"

    @classmethod
    def description(cls) -> str:
        return "Use Deepinfra/Deepinfra-API to access official deepinfra API."

    def supported_models(self) -> list[str]:
        return ['deepinfra/airoboros-70b', 'cognitivecomputations/dolphin-2.6-mixtral-8x7b', 'openchat/openchat-3.6-8b', 'mistralai/Mixtral-8x22B-Instruct-v0.1', 'google/codegemma-7b-it', 'microsoft/WizardLM-2-8x22B', 'HuggingFaceH4/zephyr-orpo-141b-A35b-v0.1', 'databricks/dbrx-instruct', 'mistralai/Mistral-7B-Instruct-v0.3', 'meta-llama/Llama-2-70b-chat-hf', 'mistralai/Mixtral-8x7B-Instruct-v0.1', 'meta-llama/Meta-Llama-3-8B-Instruct', 'mistralai/Mixtral-8x22B-v0.1', '01-ai/Yi-34B-Chat', 'meta-llama/Llama-2-7b-chat-hf', 'nvidia/Nemotron-4-340B-Instruct', 'meta-llama/Llama-2-13b-chat-hf', 'google/gemma-1.1-7b-it', 'Qwen/Qwen2-72B-Instruct', 'microsoft/Phi-3-medium-4k-instruct', 'Sao10K/L3-70B-Euryale-v2.1', 'cognitivecomputations/dolphin-2.9.1-llama-3-70b', 'meta-llama/Meta-Llama-3-70B-Instruct', 'lizpreciatior/lzlv_70b_fp16_hf', 'microsoft/WizardLM-2-7B']

    def function_call_supported(self) -> bool:
        return False

    def stream_mode_supported(self) -> bool:
        return True    

    def multi_round_supported(self) -> bool:
        return True

    @classmethod
    def config_comment(cls) -> str:
        return "For this website you don't need any key"

    @classmethod
    def supported_path(cls) -> str:
        return "/v1/chat/completions"

    def __init__(self, config: dict, eval: evaluation.AbsChannelEvaluation):
        self.config = config
        self.eval = eval
        self.url = "https://api.deepinfra.com/v1/openai/chat/completions"
        self.ua = UserAgent()

    async def test(self) -> typing.Union[bool, str]:
        try:
            data = {
                "model": "meta-llama/Meta-Llama-3-70B-Instruct",
                "messages": [{"role": "user", "content": "Hi, respond 'Hello, world!' please."}],
                "temperature": 0.7,
                "max_tokens": 15000,
                "top_p": 0.9,
                "top_k": 0.0,
                "presence_penalty": 0.0,
                "frequency_penalty": 0.0
            }
            headers = {
                'X-Deepinfra-Source': 'web-page',
                'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
            }
            async with httpx.AsyncClient() as client:
                response = await client.post(self.url, json=data, headers=headers)
                response.raise_for_status()
                response_data = response.json()
                return True, ""
        except Exception as e:
            return False, str(e)

    async def query(self, req: request.Request) -> typing.AsyncGenerator[response.Response, None]:        
        messages = req.messages
        model = req.model
        random_int = random.randint(0, 1000000000)

        data = {
            "messages": messages,
            "model": model,
            "stream": True,
            "temperature": 0.7,
            "max_tokens": 15000,
            "top_p": 0.9,
            "top_k": 0.0,
            "presence_penalty": 0.0,
            "frequency_penalty": 0.0
        }

        headers = {
            'X-Deepinfra-Source': 'web-page',
            'User-Agent': self.ua.random
        }

        async with httpx.AsyncClient() as client:
            async with client.stream("POST", self.url, json=data, headers=headers) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        if line.startswith("data: "):
                            line = line[6:]
                        if line == "[DONE]":
                            yield response.Response(
                                id=random_int,
                                finish_reason=response.FinishReason.STOP,
                                normal_message="",
                                function_call=None
                            )
                            break
                        try:
                            chunk = ujson.loads(line)
                            if chunk.get("choices") and chunk["choices"][0].get("delta", {}).get("content"):
                                text = chunk["choices"][0]["delta"]["content"]
                                yield response.Response(
                                    id=random_int,
                                    finish_reason=response.FinishReason.NULL,
                                    normal_message=text,
                                    function_call=None
                                )
                        except ValueError as e:
                            raise ValueError(f"JSON decoding error: {e}\nLine content: {line}")