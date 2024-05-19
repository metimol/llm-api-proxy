"""Channel management."""
import time
import asyncio
import random
import logging
import json
import os

from ...entities import channel, request, exceptions
from ...models.database import db
from ...models.channel import mgr


class ChannelManager(mgr.AbsChannelManager):
    """Channel manager.
    
    Provides channel creation, deletion, updating and listing,
    or selecting channel according to load balance algorithm.
    """
    
    dump_score_records: bool = False

    def __init__(
        self,
        dbmgr: db.DatabaseInterface,
    ):
        self.dbmgr = dbmgr
        self.channels = []
        self.dump_score_records = os.getenv("DUMP_SCORE_RECORDS", "false").lower() == "true"
        
    async def has_channel(self, channel_id: int) -> bool:
        for chan in self.channels:
            if chan.id == channel_id:
                return True
        return False
    
    async def has_channel_in_db(self, channel_id: int) -> bool:
        for chan in await self.dbmgr.list_channels():
            if chan.id == channel_id:
                return True
        return False
    
    async def get_channel(self, channel_id: int) -> channel.Channel:
        """Get a channel."""
        for chan in self.channels:
            if chan.id == channel_id:
                return chan
        raise ValueError("Channel not found.")

    async def list_channels(self) -> list[channel.Channel]:
        """List all channels."""
        # self.channels = await self.dbmgr.list_channels()
        
        return self.channels
    
    async def load_channels(self) -> None:
        """Load all channels from database."""
        self.channels = await self.dbmgr.list_channels()
    
    async def create_channel(self, chan: channel.Channel) -> None:
        """Create a channel."""
        assert not await self.has_channel(chan.id)
        
        await self.dbmgr.insert_channel(chan)
        self.channels.append(chan)

    async def delete_channel(self, channel_id: int) -> None:
        """Delete a channel."""
        assert await self.has_channel(channel_id)
        
        await self.dbmgr.delete_channel(channel_id)
        for i in range(len(self.channels)):
            if self.channels[i].id == channel_id:
                del self.channels[i]
                break

    async def update_channel(self, chan: channel.Channel) -> None:
        """Update a channel."""
        assert await self.has_channel(chan.id)
        
        await self.dbmgr.update_channel(chan)
        for i in range(len(self.channels)):
            if self.channels[i].id == chan.id:
                chan.preserve_runtime_vars(self.channels[i])
                self.channels[i] = chan
                break

    async def enable_channel(self, channel_id: int) -> None:
        """Enable a channel."""
        assert await self.has_channel(channel_id)
        
        chan = await self.get_channel(channel_id)
        chan.enabled = True
        await self.update_channel(chan)
        
    async def disable_channel(self, channel_id: int) -> None:
        """Disable a channel."""
        assert await self.has_channel(channel_id)
        
        chan = await self.get_channel(channel_id)
        chan.enabled = False
        await self.update_channel(chan)
        
    async def test_channel(self, channel_id: int) -> int:
        assert await self.has_channel(channel_id)
        
        chan = await self.get_channel(channel_id)
        # 计时
        now = time.time()
        latency = -1
        try:
            res, error = await chan.adapter.test()
            if not res:
                raise ValueError(error)
            latency = int((time.time() - now)*100)/100
        except Exception as e:
            raise ValueError("Test failed.") from e
        finally:
            chan.latency = latency
            await self.update_channel(chan)
        return latency

    async def select_channel(
        self,
        path: str,
        req: request.Request,
        id_suffix: str="",
    ) -> channel.Channel:
        """Select a channel.
        
        Method here will filter channels and select the best one.
        
        Hard filters, which channel not match these conditions will be excluded:
        1. disabled channels.
        2. path the client request.
        3. model name the client request.
        
        Soft filters, these filter give score to each channel,
        the channel with the highest score will be selected:
        1. support for stream mode matching the client request.
        2. support for multi-round matching the client request.
        3. support for function calling.
        4. usage times in lifetime.
        
        Args:
            path: path of this request.
            req: request object.
            id_suffix: suffix of channel id.
            
        """
        stream_mode = req.stream
        has_functions = req.functions is not None and len(req.functions) > 0
        is_multi_round = req.messages is not None and len(req.messages) > 0
        
        model_name = req.model
        
        channel_copy = self.channels.copy()
        
        # delete disabled channels
        channel_copy = list(filter(lambda chan: chan.enabled, channel_copy))
        
        # delete not matched path
        channel_copy = list(filter(lambda chan: chan.adapter.supported_path() == path, channel_copy))
        
        # delete not matched model name
        channel_copy_tmp = []
        
        for chan in channel_copy:
            models = []
            left_model_names = list(chan.model_mapping.keys())
            models.extend(left_model_names)
            models.extend(chan.adapter.supported_models())
            
            if model_name in models:
                channel_copy_tmp.append(chan)
                
        channel_copy: list[channel.Channel] = channel_copy_tmp
        
        if len(channel_copy) == 0:
            raise exceptions.QueryHandlingError(
                404,
                "channel_not_found",
                "No suitable channel found. You may need to contact your admin or check the documentation at https://github.com/RockChinQ/free-one-api",
            )
        
        # get scores of each option
        evaluated_objects = await asyncio.gather(*[obj.eval.evaluate() for obj in channel_copy])
        evaluated_objects = [int(v*100)/100 for v in evaluated_objects]
        
        combined = zip(channel_copy, evaluated_objects)

        scores = sorted(
            combined,
            key=lambda x: x[1],
            reverse=True,
        )
        
        score_dump = []
        
        for chan, score in scores:
            score_dump.append({
                "name": chan.name,
                "id": chan.id,
                "score": score,
            })
        
        logging.info(f"Scores: {json.dumps(score_dump)}, id_suffix: {id_suffix}")
        
        # check if there are channels with the same score in the head
        # if so, randomly select one of them
        max_score = scores[0][1]
    
        max_score_channels = []
        
        for chan in scores:
            if chan[1] == max_score:
                max_score_channels.append(chan[0])
            else:
                break

        random.seed(time.time())
        return random.choice(max_score_channels)
