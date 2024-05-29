import typing, traceback, uuid, random, requests, ujson, httpx, json

from ...models import adapter
from ...models.adapter import llm
from ...entities import request
from ...entities import response, exceptions
from ...models.channel import evaluation


@adapter.llm_adapter
class ChatGPTWebAdapter(llm.LLMLibAdapter):

    @classmethod
    def name(cls) -> str:
        return "Chatgpt-web/GPT"

    @classmethod
    def description(cls) -> str:
        return "Use Chatgpt-web with openai format."

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

    async def format_prompt(messages):
        formatted = "\n".join([f'{message["role"].capitalize()}: {message["content"]}' for message in messages])
        return f"{formatted}\nAssistant:"

    async def test(self) -> typing.Union[bool, str]:
        try:
            api_url = self.config["url"]
            models = self.supported_models()
            model = "gpt-3.5-turbo" if "gpt-3.5-turbo" in models else random.choice(models)
            messages = [{"role": "user", "content": "Hi, respond 'Hello, world!' please."}]
            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Content-Type': 'application/json',
                'DNT': '1',
                'Connection': 'keep-alive',
            }
            data = {
                "prompt": await format_prompt(messages),
                "model": model,
                "options": {{}},
                "systemMessage": "You are ChatGPT. Respond in the language the user is speaking to you. Use markdown formatting in your response.",
                "temperature": 0.9,
                "presence_penalty": 0,
                "frequency_penalty": 0,
                "top_p": 1,
                "max_tokens": 4000,
                "user": str(uuid.uuid4())
            }
            answer = ""
            async with client.stream("POST", f"{api_url}/api/chat-process", json=data, headers=headers) as model_response:
                model_response.raise_for_status()
                async for line in model_response.aiter_lines():
                    if line:
                        line = ujson.loads(line)
                        if "detail" not in line:
                            raise RuntimeError(f"Response: {{line}}")
                        if content := line["detail"]["choices"][0]["delta"].get("content"):
                            answer+=content

            return True, ""
        except Exception as e:
            return False, f"Chatgpt-Web est failed. Error: {e}"

    async def query(self, req: request.Request) -> typing.AsyncGenerator[response.Response, None]:        
        messages = req.messages
        model = req.model
        api_url = self.config["url"]

        async with httpx.AsyncClient(timeout=None, verify=False, follow_redirects=True) as client:
            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Content-Type': 'application/json',
                'DNT': '1',
                'Connection': 'keep-alive',
            }
            data = {
                "prompt": format_prompt(messages),
                "model": model,
                "options": {{}},
                "systemMessage": "You are ChatGPT. Respond in the language the user is speaking to you. Use markdown formatting in your response.",
                "temperature": 0.9,
                "presence_penalty": 0,
                "frequency_penalty": 0,
                "top_p": 1,
                "max_tokens": 4000,
                "user": str(uuid.uuid4())
            }
            async with client.stream("POST", f"{api_url}/api/chat-process", json=data, headers=headers) as model_response:
                model_response.raise_for_status()
                async for line in model_response.aiter_lines():
                    if line:
                        line = ujson.loads(line)
                        if "detail" not in line:
                            raise RuntimeError(f"Response: {{line}}")
                        if content := line["detail"]["choices"][0]["delta"].get("content"):
                            yield response.Response(
                                id=random_int,
                                finish_reason=response.FinishReason.NULL,
                                normal_message=content,
                                function_call=None
                            )
                yield response.Response(
                    id=random_int,
                    finish_reason=response.FinishReason.STOP,
                    normal_message="",
                    function_call=None
                )
