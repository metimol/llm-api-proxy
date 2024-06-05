import time
import json
import string
import random

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

    async def __stream_query(
        self,
        chan: channel.Channel,
        req: request.Request,
        resp_id: str,
    ) -> quart.Response:
        record: evaluation.Record = evaluation.Record()
        record.stream = True
        chan.eval.add_record(record)

        before = time.time()

        record.start_time = before

        # calc req msg total length
        req_msg_total_length = 0

        for msg in req.messages:
            for k, v in msg.items():
                req_msg_total_length += len(str(k))
                req_msg_total_length += len(str(v))

        record.req_messages_length = req_msg_total_length

        t = int(time.time())

        generated_content = ""

        async def _gen():
            try:
                async for resp in chan.adapter.query(req):

                    if record.latency < 0:
                        record.latency = time.time() - before

                    if (resp.normal_message is None or len(resp.normal_message) == 0) and resp.finish_reason == response.FinishReason.NULL:
                        continue

                    record.resp_message_length += len(resp.normal_message)
                    generated_content+=resp.normal_message

                    yield "data: {}\n\n".format(json.dumps({
                        "id": "chatcmpl-"+resp_id,
                        "object": "chat.completion.chunk",
                        "created": t,
                        "model": req.model,
                        "choices": [{
                            "index": 0,
                            "delta": {
                                "content": resp.normal_message,
                            } if resp.normal_message else {},
                            "finish_reason": resp.finish_reason.value
                        }]
                    }))

                record.success = True

                yield "data: [DONE]\n\n"
            except exceptions.QueryHandlingError as e:

                record.error = e
                record.success = False

                raise ValueError("Internal server error") from e
            except Exception as e:
                record.error = e
                record.success = False
            finally:
                record.commit()
                if generated_content=="":
                    raise ValueError("Generated text is empty")

        spent_ms = int((time.time() - before)*1000)

        headers = {
            "Content-Type": "text/event-stream",
            "Transfer-Encoding": "chunked",
            "Connection": "keep-alive",
            "openai-processing-ms": str(spent_ms),
            "openai-version": "2020-10-01",
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }

        return quart.Response(
            _gen(),
            mimetype="text/event-stream",
            headers=headers,
        )

    async def __non_stream_query(
        self,
        chan: channel.Channel,
        req: request.Request,
        resp_id: str,
    ) -> quart.Response:

        record = evaluation.Record()
        record.stream = False

        chan.eval.add_record(record)

        before = time.time()

        record.start_time = before

        # calc req msg total length
        req_msg_total_length = 0

        for msg in req.messages:
            for k, v in msg.items():
                req_msg_total_length += len(str(k))
                req_msg_total_length += len(str(v))

        record.req_messages_length = req_msg_total_length

        normal_message = ""

        resp_tmp: response.Response = None

        try:

            async for resp in chan.adapter.query(req):
                if record.latency < 0:
                    record.latency = time.time() - before

                if resp.normal_message is not None:
                    resp_tmp = resp
                    normal_message += resp.normal_message
                    record.resp_message_length += len(resp.normal_message)

            if randomad.enabled:
                for word in randomad.generate_ad():
                    normal_message += word

            record.success = True

        except exceptions.QueryHandlingError as e:
            record.error = e
            record.success = False

            # check for custom error raised by adapter
            raise ValueError("Internal server error") from e
        except Exception as e:
            record.error = e
            record.success = False

            # check for other error
            raise ValueError("Internal server error") from e
        finally:
            record.commit()

        # Проверка на пустой сгенерированный текст
        if not normal_message.strip():
            raise ValueError("Generated text is empty")

        spent_ms = int((time.time() - before)*1000)

        prompt_tokens = chan.count_tokens(req.model, req.messages)
        completion_tokens = chan.count_tokens(
            req.model,
            [{
                "role": "assistant",
                "content": normal_message,
            }]
        )

        result = {
            "id": "chatcmpl-"+resp_id,
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
                    "finish_reason": resp_tmp.finish_reason.value
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
    ) -> quart.Response:

        id_suffix = "".join(random.choices(string.ascii_letters+string.digits, k=21))
        chan: channel.Channel = await self.chanmgr.select_channel(
            path,
            req,
            id_suffix
        )

        # find model replacement
        if len(chan.model_mapping.keys()) > 0:
            if req.model in chan.model_mapping.keys():
                req.model = chan.model_mapping[req.model]

        if chan is None:
            pass

        resp_id = ""
        resp_id += "{}".format(chan.id).zfill(3)
        resp_id += chan.adapter.__class__.__name__[:5]

        resp_id += id_suffix

        auth = quart.request.headers.get("Authorization")
        if auth.startswith("Bearer "):
            auth = auth[7:]

        if req.stream:
            return await self.__stream_query(chan, req, resp_id)
        else:
            return await self.__non_stream_query(chan, req, resp_id)