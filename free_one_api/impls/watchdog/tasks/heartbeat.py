import asyncio
import traceback
import logging
import random

from ....models.watchdog import task
from ....models.channel import mgr as chanmgr
from ....entities import channel


class HeartBeatTask(task.AbsTask):
    """HeartBeat task."""

    channel: chanmgr.AbsChannelManager
    
    cfg: dict

    def __init__(self, chan: chanmgr.AbsChannelManager, cfg: dict):
        self.channel = chan
        self.cfg = cfg
        
        self.delay = 5
        self.interval = cfg['interval']

    async def trigger(self):
        """Trigger this task."""
        
        process_task = []
        
        for chan in self.channel.channels:
            if chan.enabled:
                async def process(ch: channel.Channel):
                    random_delay = random.randint(0, 30)
                    await asyncio.sleep(random_delay)
                    
                    fail_count = await ch.heartbeat(timeout=self.cfg["timeout"])
                    if fail_count >= self.cfg["fail_limit"]:
                        try:
                            await self.channel.disable_channel(ch.id)
                            ch.fail_count = 0
                            logging.info(f"Disabled channel {ch.id} due to heartbeat failed {fail_count} times")
                        except Exception:
                            logging.warn(f"Failed to disable channel {ch.id}, traceback: {traceback.format_exc()}")
                    await self.channel.update_channel(ch)
                    
                process_task.append(process(chan))
                
        logging.info(f"Start heartbeat task, {len(process_task)} channels to process")
        await asyncio.gather(*process_task)
 