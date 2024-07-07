import time
import json
import string
import random
import asyncio
import quart

from ...models.forward import mgr as forwardmgr
from ...models.channel import mgr as channelmgr
from ...models.key import mgr as apikeymgr
from ...entities import channel, apikey, request, response, exceptions
from ...common import randomad
from ...models.channel import evaluation

class ForwardManager(forwardmgr.AbsForwardManager):

    def __init__(self, chanmgr: channelmgr.AbsChannelManager, keymgr: apikeymgr.AbsAPIKeyManager):
        self.chanmgr = chanmgr
        self.keymgr = keymgr

    def is_empty_response(self, message: str) -> bool:
        if not message:
            return True
        return all(char in '\u0000' for char in message)

    async def __stream_query_gen(
        self,
        chan: channel.Channel,
        req: request.Request,
        resp_id: str
    ):
        record: evaluation.Record = evaluation.Record()
        record.stream = True
        chan.eval.add_record(record)

        before = time.time()
        record.start_time = before

        req_msg_total_length = sum(len(str(k)) + len(str(v)) for msg in req.messages for k, v in msg.items())
        record.req_messages_length = req_msg_total_length

        t = int(time.time())

        generated_content = ""
        yielded_text = False
        try:
            async for resp in chan.adapter.query(req):
                if record.latency < 0:
                    record.latency = time.time() - before

                if not resp.normal_message and resp.finish_reason == response.FinishReason.NULL:
                    continue

                if self.is_empty_response(resp.normal_message):
                    continue

                record.resp_message_length += len(resp.normal_message)
                generated_content += resp.normal_message
                yielded_text = True

                yield f"data: {json.dumps({'provider': chan.id, 'id': f'chatcmpl-{resp_id}', 'object': 'chat.completion.chunk', 'created': t, 'model': req.model, 'choices': [{'index': 0, 'delta': {'content': resp.normal_message} if resp.normal_message else {}, 'finish_reason': resp.finish_reason.value}]})}\n\n"

            if not generated_content and not yielded_text:
                record.error = ValueError("Generated text is empty")
                record.success = False
                raise ValueError("Generated text is empty")

            if yielded_text:
                record.success = True
                yield "data: [DONE]\n\n"
            else:
                record.error = ValueError("No text content generated, but received DONE")
                record.success = False
                raise ValueError("No text content generated, but received DONE")

        except Exception as e:
            record.error = e
            record.success = False
            raise e

        finally:
            record.commit()

    async def __stream_query(
        self,
        req: request.Request,
        resp_id: str
    ):
        for attempt in range(10):
            try:
                chan: channel.Channel = await self.chanmgr.select_channel("/v1/chat/completions", req, resp_id)

                if req.model in chan.model_mapping:
                    req.model = chan.model_mapping[req.model]

                if chan is None:
                    raise ValueError("Channel not found")

                async for data in self.__stream_query_gen(chan, req, resp_id):
                    yield data
                return
            except Exception as e:
                continue

        yield json.dumps({"error": "Error occurred while handling your request. You can retry or contact your admin."})

    async def __non_stream_query(
        self,
        chan: channel.Channel,
        req: request.Request,
        resp_id: str
    ) -> quart.Response:
        record = evaluation.Record()
        record.stream = False
        chan.eval.add_record(record)

        before = time.time()
        record.start_time = before

        req_msg_total_length = sum(len(str(k)) + len(str(v)) for msg in req.messages for k, v in msg.items())
        record.req_messages_length = req_msg_total_length

        normal_message = ""
        resp_tmp: response.Response = None

        try:
            async for resp in chan.adapter.query(req):
                if record.latency < 0:
                    record.latency = time.time() - before

                if resp.normal_message is not None and not self.is_empty_response(resp.normal_message):
                    resp_tmp = resp
                    normal_message += resp.normal_message
                    record.resp_message_length += len(resp.normal_message)

            if not normal_message:
                record.error = ValueError("Generated text is empty")
                record.success = False
                return quart.jsonify({"error": "Generated text is empty"}), 500

            if randomad.enabled:
                normal_message += ''.join(randomad.generate_ad())

            record.success = True
        except Exception as e:
            record.error = e
            record.success = False
            return quart.jsonify({"error": "Exception occurred"}), 500
        finally:
            record.commit()

        spent_ms = int((time.time() - before) * 1000)
        prompt_tokens = chan.count_tokens(req.model, req.messages)
        completion_tokens = chan.count_tokens(
            req.model,
            [{"role": "assistant", "content": normal_message}]
        )

        result = {
            "provider": chan.id,
            "id": f"chatcmpl-{resp_id}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": req.model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": normal_message,
                    },
                    "finish_reason": resp_tmp.finish_reason.value if resp_tmp else None
                }
            ],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            }
        }

        return quart.jsonify(result)

    async def query(
        self,
        path: str,
        req: request.Request,
        raw_data: dict,
        attempt: int = 0
    ) -> quart.Response:
        if attempt >= 10:
            return quart.Response(
                json.dumps({"error": "Error occurred while handling your request. You can retry or contact your admin."}),
                status=500,
                mimetype='application/json'
            )

        id_suffix = "".join(random.choices(string.ascii_letters + string.digits, k=21))
        try:
            if path == "/v1/chat/completions" and req.stream:
                return quart.Response(
                    self.__stream_query(req, id_suffix),
                    mimetype="text/event-stream",
                    headers={
                        "Content-Type": "text/event-stream",
                        "Transfer-Encoding": "chunked",
                        "Connection": "keep-alive",
                        "Cache-Control": "no-cache",
                        "X-Accel-Buffering": "no",
                    }
                )
            
            chan: channel.Channel = await self.chanmgr.select_channel(path, req, id_suffix)

            if req.model in chan.model_mapping:
                req.model = chan.model_mapping[req.model]

            if chan is None:
                raise ValueError("Channel not found")

            auth = quart.request.headers.get("Authorization")
            if auth and auth.startswith("Bearer "):
                auth = auth[7:]

            response = await self.__non_stream_query(chan, req, id_suffix)

            if response.status_code == 500:
                raise Exception("Query failed, retrying...")

            return response

        except Exception as e:
            return await self.query(path, req, raw_data, attempt + 1)