import asyncio
import random

from ....models.watchdog import task
from ....models.channel import mgr as chanmgr
from ....entities import channel


class HeartBeatTask(task.AbsTask):
    """HeartBeat task."""

    def __init__(self, chan: chanmgr.AbsChannelManager, cfg: dict):
        self.channel = chan
        self.cfg = cfg
        self.delay = 5
        self.interval = cfg['interval']

    async def process_channel(self, ch: channel.Channel):
        """Process single channel heartbeat."""
        try:
            random_delay = random.randint(0, 30)
            await asyncio.sleep(random_delay)

            fail_count = await ch.heartbeat(timeout=self.cfg["timeout"])
            if fail_count >= self.cfg["fail_limit"]:
                try:
                    await self.channel.disable_channel(ch.id)
                    ch.fail_count = 0
                except Exception as e:
                    print(f"Error disabling channel {ch.id}: {str(e)}")
            await self.channel.update_channel(ch)
        except Exception as e:
            print(f"Error processing channel {ch.id}: {str(e)}")

    async def trigger(self):
        """Trigger this task."""
        enabled_channels = [chan for chan in self.channel.channels if chan.enabled]
        tasks = [self.process_channel(chan) for chan in enabled_channels]
        await asyncio.gather(*tasks)

    async def loop(self):
        """Main loop for periodic execution."""
        while True:
            try:
                await self.trigger()
            except Exception as e:
                print(f"Error in heartbeat loop: {str(e)}")
            await asyncio.sleep(self.interval)