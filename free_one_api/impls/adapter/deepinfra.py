import typing
import random
import httpx
import ujson
import asyncio
from ...models import adapter
from ...models.adapter import llm
from ...entities import request, response
from ...models.channel import evaluation

@adapter.llm_adapter
class DeepinfraAdapter(llm.LLMLibAdapter):
    NAME = "Deepinfra/Deepinfra-API"
    DESCRIPTION = "Use Deepinfra/Deepinfra-API to access official deepinfra API."
    SUPPORTED_MODELS = [
        'deepinfra/airoboros-70b', 'cognitivecomputations/dolphin-2.6-mixtral-8x7b', 'openchat/openchat-3.6-8b',
        'mistralai/Mixtral-8x22B-Instruct-v0.1', 'google/codegemma-7b-it', 'microsoft/WizardLM-2-8x22B',
        'HuggingFaceH4/zephyr-orpo-141b-A35b-v0.1', 'databricks/dbrx-instruct', 'mistralai/Mistral-7B-Instruct-v0.3',
        'meta-llama/Llama-2-70b-chat-hf', 'mistralai/Mixtral-8x7B-Instruct-v0.1', 'meta-llama/Meta-Llama-3-8B-Instruct',
        'mistralai/Mixtral-8x22B-v0.1', '01-ai/Yi-34B-Chat', 'meta-llama/Llama-2-7b-chat-hf', 'nvidia/Nemotron-4-340B-Instruct',
        'meta-llama/Llama-2-13b-chat-hf', 'google/gemma-1.1-7b-it', 'Qwen/Qwen2-72B-Instruct', 'microsoft/Phi-3-medium-4k-instruct',
        'Sao10K/L3-70B-Euryale-v2.1', 'cognitivecomputations/dolphin-2.9.1-llama-3-70b', 'meta-llama/Meta-Llama-3-70B-Instruct', 
        'lizpreciatior/lzlv_70b_fp16_hf', 'microsoft/WizardLM-2-7B', 'llava-hf/llava-1.5-7b-hf', 'google/gemma-2-9b-it', 'google/gemma-2-27b-it'
    ]
    CONFIG_COMMENT = "For this website you don't need any key"
    SUPPORTED_PATH = "/v1/chat/completions"
    BASE_URL = "https://api.deepinfra.com/v1/openai/chat/completions"

    @classmethod
    def name(cls) -> str:
        return cls.NAME

    @classmethod
    def description(cls) -> str:
        return cls.DESCRIPTION

    def supported_models(self) -> list[str]:
        return self.SUPPORTED_MODELS

    def function_call_supported(self) -> bool:
        return False

    def stream_mode_supported(self) -> bool:
        return True    

    def multi_round_supported(self) -> bool:
        return True

    @classmethod
    def config_comment(cls) -> str:
        return cls.CONFIG_COMMENT

    @classmethod
    def supported_path(cls) -> str:
        return cls.SUPPORTED_PATH

    def __init__(self, config: dict, eval: evaluation.AbsChannelEvaluation):
        self.config = config
        self.eval = eval
        self.use_proxy = config.get('use_proxy', False)
        self.proxy_list = asyncio.Queue()
        self.proxy_semaphore = asyncio.Semaphore(10)  # Ограничение одновременных запросов к прокси

    async def test(self) -> typing.Union[bool, str]:
        data = {
            "model": "meta-llama/Meta-Llama-3-70B-Instruct",
            "messages": [{"role": "user", "content": "Hi, respond 'Hello, world!' please."}],
            "temperature": 0.7,
            "max_tokens": 15000,
        }
        headers = self._get_headers()
        return await self.make_request(self.BASE_URL, data, headers, is_test=True)

    async def query(self, req: request.Request) -> typing.AsyncGenerator[response.Response, None]:
        data = {
            "messages": req.messages,
            "model": req.model,
            "stream": True,
            "temperature": 0.7,
            "max_tokens": 15000,
        }
        headers = self._get_headers()
        random_int = random.randint(0, 1000000000)

        proxy = await self.get_working_proxy() if self.use_proxy else None

        async with httpx.AsyncClient(proxy=proxy) as client:
            async with client.stream("POST", self.BASE_URL, json=data, headers=headers) as result:
                if result.status_code == 200:
                    async for line in result.aiter_lines():
                        if line:
                            for response_item in self._process_line(line, random_int):
                                yield response_item
                else:
                    raise Exception(f"HTTP request failed with status code: {result.status_code}")

    async def make_request(self, url, data, headers, is_test=False):
        proxy = await self.get_working_proxy() if self.use_proxy else None

        async with httpx.AsyncClient(proxy=proxy) as client:
            response = await client.post(url, json=data, headers=headers)
            response.raise_for_status()
            return True, ""

    async def get_proxy_list(self):
        proxy_url = "https://api.proxyscrape.com/v3/free-proxy-list/get?request=displayproxies&protocol=http&proxy_format=protocolipport&format=text&anonymity=Elite,Anonymous&timeout=5015"
        async with httpx.AsyncClient() as client:
            response = await client.get(proxy_url)
            response.raise_for_status()
            all_proxies = [proxy.strip() for proxy in response.text.strip().split("\n")]
            random.shuffle(all_proxies)

        await self.check_proxies(all_proxies)

    async def check_single_proxy(self, proxy):
        test_url = "https://api.deepinfra.com/v1/openai/models"
        try:
            async with httpx.AsyncClient(proxy=proxy, timeout=2) as client:
                response = await client.get(test_url)
                if response.status_code == 200:
                    await self.proxy_list.put(proxy)
        except:
            pass

    async def check_proxies(self, proxies):
        tasks = [self.check_single_proxy(proxy) for proxy in proxies]
        await asyncio.gather(*tasks)

    async def get_working_proxy(self):
        if self.proxy_list.empty():
            await self.get_proxy_list()
        
        async with self.proxy_semaphore:
            return await self.proxy_list.get()

    def _get_headers(self):
        return {
            'X-Deepinfra-Source': 'web-page',
            'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
        }

    def _process_line(self, line: str, random_int: int) -> list[response.Response]:
        responses = []
        if line.startswith("data: "):
            line = line[6:]
        if line == "[DONE]":
            responses.append(response.Response(
                id=random_int,
                finish_reason=response.FinishReason.STOP,
                normal_message="",
                function_call=None
            ))
        else:
            try:
                chunk = ujson.loads(line)
                if chunk.get("choices") and chunk["choices"][0].get("delta", {}).get("content"):
                    text = chunk["choices"][0]["delta"]["content"]
                    responses.append(response.Response(
                        id=random_int,
                        finish_reason=response.FinishReason.NULL,
                        normal_message=text,
                        function_call=None
                    ))
            except ValueError as e:
                raise ValueError(f"JSON decoding error: {e}\nLine content: {line}")
        return responses