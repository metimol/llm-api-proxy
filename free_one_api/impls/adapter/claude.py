import typing
import traceback
import uuid
import random

import claude_api as claude

from free_one_api.entities import request, response

from ...models import adapter
from ...models.adapter import llm
from ...entities import request, response, exceptions
from ...models.channel import evaluation


@adapter.llm_adapter
class ClaudeAdapter(llm.LLMLibAdapter):
    
    @classmethod
    def name(cls) -> str:
        return "KoushikNavuluri/Claude-API"
    
    @classmethod
    def description(self) -> str:
        return "Use KoushikNavuluri/Claude-API to access Claude web edition."

    def supported_models(self) -> list[str]:
        return [
            "gpt-3.5-turbo",
            "gpt-4"
        ]

    def function_call_supported(self) -> bool:
        return False

    def stream_mode_supported(self) -> bool:
        return False

    def multi_round_supported(self) -> bool:
        return True
    
    @classmethod
    def config_comment(cls) -> str:
        return \
"""Currently supports non stream mode only.
You should provide cookie string as `cookie` in config:
{
    "cookie": "your cookie string"
}

Method of getting cookie string, please refer to https://github.com/KoushikNavuluri/Claude-API
"""

    @classmethod
    def supported_path(cls) -> str:
        return "/v1/chat/completions"
    
    _chatbot: claude.Client = None

    @property
    def chatbot(self) -> claude.Client:
        if self._chatbot is None:
            self._chatbot = claude.Client(self.config["cookie"])
        return self._chatbot
    
    def __init__(self, config: dict, eval: evaluation.AbsChannelEvaluation):
        self.config = config
        self.eval = eval
        
    async def test(self) -> typing.Union[bool, str]:
        try:
            conversation_id = self.chatbot.create_new_chat()['uuid']
            response = self.chatbot.send_message("Hello, Claude!", conversation_id)
            return True, ""
        except Exception as e:
            traceback.print_exc()
            return False, str(e)
        
    async def query(self, req: request.Request) -> typing.AsyncGenerator[response.Response, None]:
        prompt = ""
        
        for msg in req.messages:
            prompt += f"{msg['role']}: {msg['content']}\n"
        
        prompt += "assistant: "
        
        random_int = random.randint(0, 1000000000)
        
        conversation_id = self.chatbot.create_new_chat()['uuid']
        resp_text = self.chatbot.send_message(prompt, conversation_id)
        
        self.chatbot.delete_conversation(conversation_id)
        
        yield response.Response(
            id=random_int,
            finish_reason=response.FinishReason.STOP,
            normal_message=resp_text,
            function_call=None
        )
