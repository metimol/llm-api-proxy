import os
import sys
import asyncio

import yaml

from ..common import crypto
from .router import mgr as routermgr
from .router import api as apigroup

from ..models.database import db
from ..models.channel import mgr as chanmgr
from ..models.key import mgr as keymgr
from ..models.router import group as routergroup
from ..models.watchdog import wd as wdmgr

from .adapter import deepinfra
from .adapter import gpt4free
from .adapter import hugchat
from .adapter import gpt
from .adapter import nextchat
from .adapter import chatgpt_web

from . import cfg as cfgutil


class Application:
    """Application instance."""

    dbmgr: db.DatabaseInterface
    """Database manager."""

    router: routermgr.RouterManager
    """Router manager."""

    channel: chanmgr.AbsChannelManager
    """Channel manager."""

    key: keymgr.AbsAPIKeyManager
    """API Key manager."""

    watchdog: wdmgr.AbsWatchDog

    logging_level: int = None

    def __init__(
        self,
        dbmgr: db.DatabaseInterface,
        router: routermgr.RouterManager,
        channel: chanmgr.AbsChannelManager,
        key: keymgr.AbsAPIKeyManager,
        watchdog: wdmgr.AbsWatchDog,
        logging_level: int = None,
    ):
        self.dbmgr = dbmgr
        self.router = router
        self.channel = channel
        self.key = key
        self.watchdog = watchdog
        self.logging_level = logging_level

    async def run(self):
        """Run application."""
        loop = asyncio.get_running_loop()

        loop.create_task(self.watchdog.run())

        await self.router.serve(loop)


default_config = {
    "1-documentation": "ask Metimol",
    "database": {
        "type": "mysql",
        "host": os.environ.get("DB_HOST"),
        "port": int(os.environ.get("DB_PORT", 3306)),
        "user": os.environ.get("DB_USER"),
        "password": os.environ.get("DB_PASSWORD"),
        "database": os.environ.get("DB_NAME"),
    },
    "watchdog": {
        "heartbeat": {
            "interval": 3600,
            "timeout": 300,
            "fail_limit": 5,
        },
    },
    "router": {
        "port": 3000,
        "token": os.environ.get("password", "123456789"),
    },
    "web": {
        "frontend_path": "./web/dist/",
    },
    "logging": {
        "debug": False,
    },
    "random_ad": {
        "enabled": False,
        "rate": 0.05,
        "ad_list": [
            " (This response is sponsored by Metimol :)",
        ]
    },
    "adapters": {
        "acheong08_ChatGPT": {
            "reverse_proxy": "https://chatproxy.rockchin.top/api/",
            "auto_ignore_duplicated": True,
        }
    }
}

async def make_application(config_path: str) -> Application:
    """Make application."""
    if not os.path.exists(config_path):
        with open(config_path, "w") as f:
            yaml.dump(default_config, f)
            print("Config file created at", config_path)
            # print("Please edit it and run again.")
            # sys.exit(0)
    config = {}
    with open(config_path, "r") as f:
        config = yaml.load(f, Loader=yaml.FullLoader)

    # complete config
    config = cfgutil.complete_config(config, default_config)

    # dump config
    with open(config_path, "w") as f:
        yaml.dump(config, f)

    logging_level = None

    if 'logging' in config and 'debug' in config['logging'] and config['logging']['debug']:
        logging_level = "DEBUG"

    if 'DEBUG' in os.environ and os.environ['DEBUG'] == 'true':
        logging_level = "DEBUG"

    # save ad to runtime
    if 'random_ad' in config and config['random_ad']['enabled']:
        from ..common import randomad

        randomad.enabled = config['random_ad']['enabled']
        randomad.rate = config['random_ad']['rate']
        randomad.ads = config['random_ad']['ad_list']

    from ..common import randomad

    # make database manager
    from .database import mysql as mysqldb

    dbmgr_cls_mapping = {
        "mysql": mysqldb.MySQLDB,
    }

    dbmgr = dbmgr_cls_mapping[config['database']['type']](config['database'])
    await dbmgr.initialize()

    # set default values
    # apply adapters config
    if 'misc' in config and 'chatgpt_api_base' in config['misc']:  # backward compatibility
        config['adapters']['acheong08_ChatGPT']['reverse_proxy'] = config['misc']['chatgpt_api_base']

    adapter_config_mapping = {
        "xtekky_gpt4free": gpt4free.GPT4FreeAdapter,
        "Deepinfra": deepinfra.DeepinfraAdapter,
        "GPT": gpt.GPTAdapter,
        "NextChat": nextchat.NextChatAdapter,
        "ChatGPTWeb": chatgpt_web.ChatGPTWebAdapter,
        "HugChat": hugchat.HuggingChatAdapter
    }

    for adapter_name in adapter_config_mapping:
        if (adapter_name not in config['adapters']):
            config['adapters'][adapter_name] = {}

        for k, v in config["adapters"][adapter_name].items():
            setattr(adapter_config_mapping[adapter_name], k, v)

    # make channel manager
    from .channel import mgr as chanmgr

    channelmgr = chanmgr.ChannelManager(dbmgr)
    await channelmgr.load_channels()

    # make key manager
    from .key import mgr as keymgr

    apikeymgr = keymgr.APIKeyManager(dbmgr)
    await apikeymgr.list_keys()

    # make forward manager
    from .forward import mgr as forwardmgr

    fwdmgr = forwardmgr.ForwardManager(channelmgr, apikeymgr)

    # make router manager
    from .router import mgr as routermgr

    #   import all api groups
    from .router import forward as forwardgroup
    from .router import api as apigroup
    from .router import web as webgroup

    # ========= API Groups =========
    group_forward = forwardgroup.ForwardAPIGroup(dbmgr, channelmgr, apikeymgr, fwdmgr)
    group_api = apigroup.WebAPIGroup(dbmgr, channelmgr, apikeymgr)
    group_api.tokens = [crypto.md5_digest(config['router']['token'])]
    group_web = webgroup.WebPageGroup(config['web'], config['router'])

    paths = []

    paths += group_forward.get_routers()
    paths += group_web.get_routers()
    paths += group_api.get_routers()

    # ========= API Groups =========

    routermgr = routermgr.RouterManager(
        routes=paths,
        config=config['router'],
    )

    # watchdog and tasks
    from .watchdog import wd as watchdog

    wdmgr = watchdog.WatchDog()

    # tasks
    from .watchdog.tasks import heartbeat

    hbtask = heartbeat.HeartBeatTask(
        channelmgr,
        config['watchdog']['heartbeat'],
    )

    wdmgr.add_task(hbtask)

    app = Application(
        dbmgr=dbmgr,
        router=routermgr,
        channel=channelmgr,
        key=apikeymgr,
        watchdog=wdmgr,
        logging_level=logging_level,
    )

    return app