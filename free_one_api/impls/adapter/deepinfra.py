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
class DeepinfraAdapter(llm.LLMLibAdapter):

    @classmethod
    def name(cls) -> str:
        return "Deepinfra/Deepinfra-API"

    @classmethod
    def description(cls) -> str:
        return "Use Deepinfra/Deepinfra-API to access official deepinfra API."

    def supported_models(self) -> list[str]:
        return [
            "bigcode/starcoder2-15b",
            "openchat/openchat_3.5",
            "lizpreciatior/lzlv_70b_fp16_hf",
            "codellama/CodeLlama-34b-Instruct-hf",
            "DeepInfra/pygmalion-13b-4bit-128g",
            "deepinfra/airoboros-70b",
            "mistralai/Mixtral-8x7B-Instruct-v0.1",
            "mistralai/Mixtral-8x22B-Instruct-v0.1",
            "HuggingFaceH4/zephyr-orpo-141b-A35b-v0.1",
            "mistralai/Mistral-7B-Instruct-v0.1",
            "mistralai/Mistral-7B-Instruct-v0.2",
            "cognitivecomputations/dolphin-2.6-mixtral-8x7b",
            "meta-llama/Llama-2-7b-chat-hf",
            "codellama/CodeLlama-70b-Instruct-hf",
            "meta-llama/Llama-2-70b-chat-hf",
            "meta-llama/Llama-2-13b-chat-hf",
            "meta-llama/Meta-Llama-3-70B-Instruct",
            "meta-llama/Meta-Llama-3-8B-Instruct",
            "google/gemma-7b-it",
            "google/gemma-1.1-7b-it",
            "llava-hf/llava-1.5-7b-hf",
            "databricks/dbrx-instruct",
            "microsoft/WizardLM-2-8x22B",
            "microsoft/WizardLM-2-7B",
            "mistralai/Mistral-7B-Instruct-v0.3"
        ]

    def function_call_supported(self) -> bool:
        return False

    def stream_mode_supported(self) -> bool:
        return True    

    def multi_round_supported(self) -> bool:
        return True

    @classmethod
    def config_comment(cls) -> str:
        return \
"""Please provide your Deepinfra API key:

{
    "key": "your_api_key"
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
            api_url = "https://api.deepinfra.com/v1/openai/chat/completions"
            data = {
                "model": "openchat/openchat_3.5",
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
            async with client.stream("POST", "https://api.deepinfra.com/v1/openai/chat/completions", json=data, headers=headers) as model_response:
                model_response.raise_for_status()
                async for line in model_response.aiter_lines():
                    print(line)
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