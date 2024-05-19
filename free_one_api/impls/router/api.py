import json
import traceback

import quart

from ...models.router import group as routergroup
from ...models.database import db
from ...models.channel import mgr as channelmgr
from ...models.key import mgr as apikeymgr
from ...entities import channel, apikey
from ...models import adapter


class WebAPIGroup(routergroup.APIGroup):
    
    chanmgr: channelmgr.AbsChannelManager
    
    keymgr: apikeymgr.AbsAPIKeyManager
    
    def __init__(self, dbmgr: db.DatabaseInterface, chanmgr: channelmgr.AbsChannelManager, keymgr: apikeymgr.AbsAPIKeyManager):
        super().__init__(dbmgr)
        self.chanmgr = chanmgr
        self.keymgr = keymgr
        self.group_name = "/api"
        
        @self.api("/channel/list", ["GET"], auth=True)
        async def channel_list():
            # load channels from db to memory
            chan_list = await self.chanmgr.list_channels()
            
            chan_list_json = [channel.Channel.dump_channel(chan) for chan in chan_list]
            chan_list_json = [{
                "id": chan["id"],
                "name": chan["name"],
                "adapter": chan["adapter"]['type'],
                "enabled": chan["enabled"],
                "latency": chan["latency"],
            } for chan in chan_list_json]
            
            return quart.jsonify({
                "code": 0,
                "message": "ok",
                "data": chan_list_json,
            })
        
        @self.api("/channel/create", ["POST"], auth=True)
        async def channel_create():
            try:
                data = await quart.request.get_json()
                
                chan = channel.Channel.load_channel(data)
                
                await self.chanmgr.create_channel(chan)
                
                return quart.jsonify({
                    "code": 0,
                    "message": "ok",
                })
            except Exception as e:
                traceback.print_exc()
                return quart.jsonify({
                    "code": 1,
                    "message": str(e),
                })
            
        @self.api("/channel/delete/<int:chan_id>", ["DELETE"], auth=True)
        async def channel_delete(chan_id: int):
            try:
                await self.chanmgr.delete_channel(chan_id)
                
                return quart.jsonify({
                    "code": 0,
                    "message": "ok",
                })
            except Exception as e:
                return quart.jsonify({
                    "code": 1,
                    "message": str(e),
                })
            
        @self.api("/channel/details/<int:chan_id>", ["GET"], auth=True)
        async def channel_details(chan_id: int):
            try:
                chan = await self.chanmgr.get_channel(chan_id)
                
                return quart.jsonify({
                    "code": 0,
                    "message": "ok",
                    "data": channel.Channel.dump_channel(chan),
                })
            except Exception as e:
                return quart.jsonify({
                    "code": 1,
                    "message": str(e),
                })
            
        @self.api("/channel/update/<int:chan_id>", ["PUT"], auth=True)
        async def channel_update(chan_id: int):
            try:
                chan = channel.Channel.load_channel(await quart.request.get_json())
                chan.id = chan_id
                await self.chanmgr.update_channel(chan)
                
                return quart.jsonify({
                    "code": 0,
                    "message": "ok",
                })
            except Exception as e:
                return quart.jsonify({
                    "code": 1,
                    "message": str(e),
                })
            
        @self.api("/channel/enable/<int:chan_id>", ["POST"], auth=True)
        async def channel_enable(chan_id: int):
            try:
                await self.chanmgr.enable_channel(chan_id)
                
                return quart.jsonify({
                    "code": 0,
                    "message": "ok",
                })
            except Exception as e:
                return quart.jsonify({
                    "code": 1,
                    "message": str(e),
                })
            
        @self.api("/channel/disable/<int:chan_id>", ["POST"], auth=True)
        async def channel_disable(chan_id: int):
            try:
                await self.chanmgr.disable_channel(chan_id)
                
                return quart.jsonify({
                    "code": 0,
                    "message": "ok",
                })
            except Exception as e:
                return quart.jsonify({
                    "code": 1,
                    "message": str(e),
                })
            
        @self.api("/channel/test/<int:chan_id>", ["POST"], auth=True)
        async def channel_test(chan_id: int):
            try:
                latency = await self.chanmgr.test_channel(chan_id)
                
                return quart.jsonify({
                    "code": 0,
                    "message": "ok",
                    "data": {
                        "latency": latency,
                    },
                })
            except Exception as e:
                traceback.print_exc()
                return quart.jsonify({
                    "code": 1,
                    "message": str(e),
                })
            
        @self.api("/adapter/list", ["GET"], auth=True)
        async def adapter_list():
            res = {
                "code": 0,
                "message": "ok",
                "data": adapter.list_adapters(),
            }
            
            return quart.jsonify(res)
            
        @self.api("/key/list", ["GET"], auth=True)
        async def key_list():
            try:
                key_list = await self.keymgr.list_keys()
                
                key_list_json = []
                
                for key in key_list:
                    key_list_json.append({
                        "id": key.id,
                        "name": key.name,
                        "brief": key.raw[:10] + "..." + key.raw[-10:],
                        "created_at": key.created_at,
                    })
                
                return quart.jsonify({
                    "code": 0,
                    "message": "ok",
                    "data": key_list_json,
                })
            except Exception as e:
                return quart.jsonify({
                    "code": 1,
                    "message": str(e),
                })
            
        @self.api("/key/raw/<int:key_id>", ["GET"], auth=True)
        async def key_raw(key_id: int):
            try:
                key = await self.keymgr.get_key(key_id)
                
                return quart.jsonify({
                    "code": 0,
                    "message": "ok",
                    "data": {
                        "key": key.raw,
                    },
                })
            except Exception as e:
                return quart.jsonify({
                    "code": 1,
                    "message": str(e),
                })
            
        @self.api("/key/create", ["POST"], auth=True)
        async def key_create():
            try:
                data = await quart.request.get_json()
                
                key_name = data["name"]
                
                if await self.keymgr.has_key_name(key_name):
                    raise ValueError("key name already exists: "+key_name)
                
                key = apikey.FreeOneAPIKey.make_new(key_name)
                
                await self.keymgr.create_key(key)
                
                return quart.jsonify({
                    "code": 0,
                    "message": "ok",
                    "data": {
                        "id": key.id,
                        "raw": key.raw,
                    },
                })
            except Exception as e:
                return quart.jsonify({
                    "code": 1,
                    "message": str(e),
                })

        @self.api("/key/revoke/<int:key_id>", ["DELETE"], auth=True)
        async def key_revoke(key_id: int):
            try:
                await self.keymgr.revoke_key(key_id)
                
                return quart.jsonify({
                    "code": 0,
                    "message": "ok",
                })
            except Exception as e:
                import traceback
                traceback.print_exc()
                return quart.jsonify({
                    "code": 1,
                    "message": str(e),
                })

        @self.api("/log/list", ["GET"], auth=True)
        async def list_logs():
            try:
                data = quart.request.args
                
                capacity = int(data.get("capacity", 20))
                page = int(data.get("page", 0))
                
                amount = await self.dbmgr.get_logs_amount()
                page_count = (amount + capacity - 1) // capacity
                
                logs = await self.dbmgr.select_logs_page(capacity, page)
                
                return quart.jsonify({
                    "code": 0,
                    "message": "ok",
                    "data": {
                        "page_count": page_count,
                        "logs": [
                            {
                                "id": log[0],
                                "timestamp": log[1],
                                "content": log[2],
                            } for log in logs
                        ],
                    },
                })
            except Exception as e:
                import traceback
                traceback.print_exc()
                return quart.jsonify({
                    "code": 1,
                    "message": str(e),
                })
                
        @self.api("/log/delete", ["DELETE"], auth=True)
        async def delete_logs():
            try:
                data = quart.request.args
                
                start = int(data.get("start", 0))
                end = int(data.get("end", 0))
                
                await self.dbmgr.delete_logs(start, end)
                
                return quart.jsonify({
                    "code": 0,
                    "message": "ok",
                })
            except Exception as e:
                import traceback
                traceback.print_exc()
                return quart.jsonify({
                    "code": 1,
                    "message": str(e),
                })
        
        @self.api("/info/version", ["GET"], auth=False)
        async def info_version():
            try:
            
                from ...common import version
            
                return quart.jsonify({
                    "code": 0,
                    "message": "ok",
                    "data": "v"+version.__version__,
                })
            except Exception as e:
                import traceback
                traceback.print_exc()
                return quart.jsonify({
                    "code": 1,
                    "message": str(e),
                })
