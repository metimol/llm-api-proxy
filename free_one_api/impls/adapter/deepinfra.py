import typing
import random
import httpx
import ujson
import asyncio
import time
from ...models import adapter
from ...models.adapter import llm
from ...entities import request, response
from ...models.channel import evaluation

@adapter.llm_adapter
class DeepinfraAdapter(llm.LLMLibAdapter):
    NAME = "Deepinfra/Deepinfra-API"
    DESCRIPTION = "Use Deepinfra/Deepinfra-API to access official deepinfra API."
    SUPPORTED_MODELS = ['microsoft/WizardLM-2-7B', 'meta-llama/Meta-Llama-3-8B-Instruct', 'meta-llama/Llama-2-7b-chat-hf', 'Qwen/Qwen2-72B-Instruct', 'mistralai/Mixtral-8x22B-v0.1', 'google/codegemma-7b-it', '01-ai/Yi-34B-Chat', 'meta-llama/Meta-Llama-3.1-405B-Instruct', 'meta-llama/Llama-2-13b-chat-hf', 'meta-llama/Meta-Llama-3-70B-Instruct', 'meta-llama/Meta-Llama-3.1-8B-Instruct', 'meta-llama/Llama-2-70b-chat-hf', 'HuggingFaceH4/zephyr-orpo-141b-A35b-v0.1', 'cognitivecomputations/dolphin-2.9.1-llama-3-70b', 'openchat/openchat-3.6-8b', 'mistralai/Mixtral-8x22B-Instruct-v0.1', 'google/gemma-1.1-7b-it', 'databricks/dbrx-instruct', 'lizpreciatior/lzlv_70b_fp16_hf', 'meta-llama/Meta-Llama-3.1-70B-Instruct', 'Sao10K/L3-70B-Euryale-v2.1', 'cognitivecomputations/dolphin-2.6-mixtral-8x7b', 'microsoft/WizardLM-2-8x22B', 'deepinfra/airoboros-70b', 'microsoft/Phi-3-medium-4k-instruct', 'mistralai/Mixtral-8x7B-Instruct-v0.1', 'mistralai/Mistral-7B-Instruct-v0.3', 'google/gemma-2-27b-it', 'llava-hf/llava-1.5-7b-hf', 'google/gemma-2-9b-it']
    CONFIG_COMMENT = "For this website you don't need any key"
    SUPPORTED_PATH = "/v1/chat/completions"
    BASE_URL = "https://api.deepinfra.com/v1/openai/chat/completions"
    PROXY_API_URL = "https://api-proxy-checker.5rgr39.easypanel.host/check_proxies"
    PROXY_API_KEY = "patison2005"

    @classmethod
    def name(cls): return cls.NAME

    @classmethod
    def description(cls): return cls.DESCRIPTION

    def supported_models(self): return self.SUPPORTED_MODELS

    def function_call_supported(self): return False

    def stream_mode_supported(self): return True    

    def multi_round_supported(self): return True

    @classmethod
    def config_comment(cls): return cls.CONFIG_COMMENT

    @classmethod
    def supported_path(cls): return cls.SUPPORTED_PATH

    def __init__(self, config: dict, eval: evaluation.AbsChannelEvaluation):
        self.config = config
        self.eval = eval
        self.use_proxy = config.get('use_proxy', False)
        self.proxy_list = []
        self.last_update = 0
        self.update_interval = 15 * 60

    async def test(self):
        data = {
            "model": "meta-llama/Meta-Llama-3-70B-Instruct",
            "messages": [{"role": "user", "content": "Hi, respond 'Hello, world!' please."}],
            "temperature": 0.7,
            "max_tokens": 15000,
        }
        headers = self._get_headers()
        for _ in range(30):
            try:
                return await self.make_request(self.BASE_URL, data, headers, is_test=True)
            except Exception as e:
                pass
        return False, "Failed after 30 attempts."

    async def query(self, req: request.Request):
        data = {
            "messages": req.messages,
            "model": req.model,
            "stream": True,
            "temperature": 0.7,
            "max_tokens": 15000,
        }
        headers = self._get_headers()
        random_int = random.randint(0, 1000000000)
        for _ in range(30):
            try:
                proxy = await self.get_working_proxy() if self.use_proxy else None
                async with httpx.AsyncClient(proxy=proxy) as client:
                    async with client.stream("POST", self.BASE_URL, json=data, headers=headers) as result:
                        if result.status_code == 200:
                            async for line in result.aiter_lines():
                                if line:
                                    for response_item in self._process_line(line, random_int):
                                        yield response_item
                            return
                        raise Exception(f"HTTP request failed with status code: {result.status_code}")
            except Exception:
                pass
        raise Exception("Failed after 30 attempts.")

    async def make_request(self, url, data, headers, is_test=False):
        proxy = await self.get_working_proxy() if self.use_proxy else None
        async with httpx.AsyncClient(proxy=proxy) as client:
            response = await client.post(url, json=data, headers=headers)
            response.raise_for_status()
            return True, ""

    async def get_proxy_list(self):
        headers = {
            "Authorization": f"Bearer {self.PROXY_API_KEY}"
        }
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(self.PROXY_API_URL, headers=headers)
            response.raise_for_status()
            data = response.json()
            self.proxy_list = data.get("working_proxies", [])
        self.last_update = time.time()

    async def get_working_proxy(self):
        if not self.proxy_list or time.time() - self.last_update > self.update_interval:
            await self.get_proxy_list()
        
        if not self.proxy_list:
            raise Exception("No working proxies available")
        
        return random.choice(self.proxy_list)

    def _get_headers(self):
        return {
            'X-Deepinfra-Source': 'web-page',
            'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
        }

    def _process_line(self, line: str, random_int: int):
        if line.startswith("data: "):
            line = line[6:]
        if line == "[DONE]":
            return [response.Response(
                id=random_int,
                finish_reason=response.FinishReason.STOP,
                normal_message="",
                function_call=None
            )]
        else:
            try:
                chunk = ujson.loads(line)
                if chunk.get("choices") and chunk["choices"][0].get("delta", {}).get("content"):
                    return [response.Response(
                        id=random_int,
                        finish_reason=response.FinishReason.NULL,
                        normal_message=chunk["choices"][0]["delta"]["content"],
                        function_call=None
                    )]
            except ValueError:
                pass
        return []