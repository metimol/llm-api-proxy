import typing
import traceback
import uuid
import random
import logging

import revChatGPT.V1 as chatgpt

from ...models import adapter
from ...models.adapter import llm
from ...entities import request
from ...entities import response, exceptions
from ...models.channel import evaluation


@adapter.llm_adapter
class RevChatGPTAdapter(llm.LLMLibAdapter):
    
    @classmethod
    def name(cls) -> str:
        return "acheong08/ChatGPT"
    
    @classmethod
    def description(self) -> str:
        return "Use acheong08/ChatGPT to access reverse engineering OpenAI ChatGPT web edition."

    def supported_models(self) -> list[str]:
        return [
            "gpt-3.5-turbo",
            "gpt-4"
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
"""You can provide `access_token` or `email/password` to config as:
{
    "access_token": "your access token"
}
or
{
    "email": "your email",
    "password": "your password"
}
and you can also provide other optional params supported by acheong08/ChatGPT:
{
  "conversation_id": "UUID...",
  "parent_id": "UUID...",
  "proxy": "...",
  "model": "gpt-4", // gpt-4-browsing, text-davinci-002-render-sha, gpt-4, gpt-4-plugins
  "plugin_ids": ["plugin-d1d6eb04-3375-40aa-940a-c2fc57ce0f51"], // Wolfram Alpha example
  "disable_history": true,
  "PUID": "<_puid cookie for plus accounts>", // Only if you have a plus account and use GPT-4
  "unverified_plugin_domains":["showme.redstarplugin.com"] // Unverfied plugins to install
}

RevChatGPT now need a reverse proxy to access the API, 
use a proxy address set up by RockChinQ by default, but it may be unstable.
Consider set up your own reverse proxy: https://github.com/acheong08/ChatGPT-Proxy-V4
If you have set up your own reverse proxy, you can set it in config as:
{
    "reverse_proxy": "https://your-reverse-proxy-address.com/api/"
}

Also you can set your own proxy address in config file, 
please refer to the documentation of Free One API.

Please refer to https://github.com/acheong08/ChatGPT
"""
    
    @classmethod
    def supported_path(self) -> str:
        return "/v1/chat/completions"
    
    cfg: dict = None
    reverse_proxy: str = "https://chatproxy.rockchin.top/api/"
    auto_ignore_duplicated: bool = True

    _chatbot: chatgpt.AsyncChatbot = None
    
    @property
    def chatbot(self) -> chatgpt.AsyncChatbot:
        if self._chatbot is None:
            self._chatbot = chatgpt.AsyncChatbot(
                config=self.cfg,
                base_url=self.reverse_proxy,
            )
        return self._chatbot
    
    def __init__(self, config: dict, eval: evaluation.AbsChannelEvaluation):
        self.config = config
        self.eval = eval
        
        config_copy = config.copy()

        reverse_proxy = RevChatGPTAdapter.reverse_proxy
        auto_ignore_duplicated = RevChatGPTAdapter.auto_ignore_duplicated
        
        if 'reverse_proxy' in config_copy:
            reverse_proxy = config_copy['reverse_proxy']
            
            # delete reverse_proxy from config
            del config_copy['reverse_proxy']
            
        if 'auto_ignore_duplicated' in config_copy:
            self.auto_ignore_duplicated = config_copy['auto_ignore_duplicated']
            del config_copy['auto_ignore_duplicated']

        self.cfg = config_copy
        self.reverse_proxy = reverse_proxy
        self.auto_ignore_duplicated = auto_ignore_duplicated
    
    async def test(self) -> typing.Union[bool, str]:
        conversation_id = ""
        try:
            prev_text = ""
            self.chatbot.conversation_id = None
            async for data in self.chatbot.ask(
                "Hi, respond 'Hello, world!' please.",
            ):
                message = data["message"][len(prev_text):]
                prev_text = data["message"]
                conversation_id = data["conversation_id"]
                
            await self.chatbot.delete_conversation(conversation_id)
            return True, ""
        except Exception as e:
            if conversation_id != "":
                try:
                    await self.chatbot.delete_conversation(conversation_id)
                except:
                    pass
            traceback.print_exc()
            return False, str(e)

    async def query(self, req: request.Request) -> typing.AsyncGenerator[response.Response, None]:        
        new_messages = []

        assistant_messages: list[str] = []

        for i in range(len(req.messages)):
            if req.messages[i]['role'] == "assistant":
                assistant_messages.append(req.messages[i]['content'])

            new_messages.append({
                "id": str(uuid.uuid4()),
                "author": {"role": req.messages[i]['role']},
                "content": {
                    "content_type": "text",
                    "parts": [
                        req.messages[i]['content']
                    ]
                }
            })
        
        logging.debug(f'assistant_messages: {assistant_messages}')
        
        random_int = random.randint(0, 1000000000)
        
        prev_text = ""
        
        try:
            conversation_id = ""
            self.chatbot.conversation_id = None
            async for data in self.chatbot.post_messages(
                messages=new_messages,
            ):
                message = data["message"][len(prev_text):]
                
                if not message:
                    continue
                
                # skip if:
                # 1. message in any elements of the income assistant messages
                # and 2. auto_ignore_duplicated is True
                if any([message == msg for msg in assistant_messages]) and \
                    self.auto_ignore_duplicated:
                    continue
                
                prev_text = data["message"] if prev_text in data["message"] else prev_text
                conversation_id = data["conversation_id"]

                yield response.Response(
                    id=random_int,
                    finish_reason=response.FinishReason.NULL,
                    normal_message=message,
                    function_call=None
                )
                random_int += 1
                
            yield response.Response(
                id=random_int,
                finish_reason=response.FinishReason.STOP,
                normal_message="",
                function_call=None
            )
            
            await self.chatbot.delete_conversation(conversation_id)
        except chatgpt.t.Error as e:
            assert isinstance(e, chatgpt.t.ErrorType)
            code = e.code.name.lower()
            
            raise exceptions.QueryHandlingError(
                status_code=500,
                code=code,
                message=e.message,
            )
