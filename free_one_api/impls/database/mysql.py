import os
import json
import aiomysql

from ...models.database import db as dbmod
from ...models import adapter
from ...entities import channel, apikey
from ..channel import eval as evl

channel_table_sql = """
CREATE TABLE IF NOT EXISTS channel (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    adapter JSON NOT NULL,
    model_mapping JSON NOT NULL,
    enabled TINYINT(1) NOT NULL,
    latency INT NOT NULL
)
"""

key_table_sql = """
CREATE TABLE IF NOT EXISTS apikey (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    created_at BIGINT NOT NULL,
    raw TEXT NOT NULL
)
"""

class MySQLDB(dbmod.DatabaseInterface):

    def __init__(self, config: dict):
        self.config = config
        self.db_host = config['host']
        self.db_port = config['port']
        self.db_user = config['user']
        self.db_password = config['password']
        self.db_name = config['database']

    async def get_connection(self):
        return await aiomysql.connect(
            host=self.db_host,
            port=self.db_port,
            user=self.db_user,
            password=self.db_password,
            db=self.db_name,
            autocommit=True
        )

    async def initialize(self):
        conn = await self.get_connection()
        async with conn.cursor() as cursor:
            await cursor.execute(channel_table_sql)
            await cursor.execute(key_table_sql)
        conn.close()

    async def list_channels(self) -> list[channel.Channel]:
        conn = await self.get_connection()
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT * FROM channel")
            rows = await cursor.fetchall()

            channels = []
            for row in rows:
                try:
                    channels.append(channel.Channel(
                        id=row[0],
                        name=row[1],
                        adapter=adapter.load_adapter(json.loads(row[2]), evl),
                        model_mapping=json.loads(row[3]),
                        enabled=bool(row[4]),
                        latency=row[5],
                        eval=evl.ChannelEvaluation(),
                    ))
                except Exception as e:
                    pass  # Handle the error appropriately
        conn.close()
        return channels

    async def insert_channel(self, chan: channel.Channel) -> None:
        conn = await self.get_connection()
        async with conn.cursor() as cursor:
            await cursor.execute("INSERT INTO channel (name, adapter, model_mapping, enabled, latency) VALUES (%s, %s, %s, %s, %s)", (
                chan.name,
                json.dumps(adapter.dump_adapter(chan.adapter)),
                json.dumps(chan.model_mapping),
                int(chan.enabled),
                chan.latency,
            ))
            await cursor.execute("SELECT LAST_INSERT_ID()")
            row = await cursor.fetchone()
            chan.id = row[0]
        conn.close()

    async def update_channel(self, chan: channel.Channel) -> None:
        conn = await self.get_connection()
        async with conn.cursor() as cursor:
            await cursor.execute("UPDATE channel SET name = %s, adapter = %s, model_mapping = %s, enabled = %s, latency = %s WHERE id = %s", (
                chan.name,
                json.dumps(adapter.dump_adapter(chan.adapter)),
                json.dumps(chan.model_mapping),
                int(chan.enabled),
                chan.latency,
                chan.id,
            ))
        conn.close()

    async def delete_channel(self, channel_id: int) -> None:
        conn = await self.get_connection()
        async with conn.cursor() as cursor:
            await cursor.execute("DELETE FROM channel WHERE id = %s", (channel_id,))
        conn.close()

    async def list_keys(self) -> list[apikey.FreeOneAPIKey]:
        conn = await self.get_connection()
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT * FROM apikey")
            rows = await cursor.fetchall()
            return [apikey.FreeOneAPIKey(
                id=row[0],
                name=row[1],
                created_at=row[2],
                raw=row[3],
            ) for row in rows]
        conn.close()

    async def insert_key(self, key: apikey.FreeOneAPIKey) -> None:
        conn = await self.get_connection()
        async with conn.cursor() as cursor:
            await cursor.execute("INSERT INTO apikey (name, created_at, raw) VALUES (%s, %s, %s)", (
                key.name,
                key.created_at,
                key.raw,
            ))
            await cursor.execute("SELECT LAST_INSERT_ID()")
            row = await cursor.fetchone()
            key.id = row[0]
        conn.close()

    async def update_key(self, key: apikey.FreeOneAPIKey) -> None:
        conn = await self.get_connection()
        async with conn.cursor() as cursor:
            await cursor.execute("UPDATE apikey SET name = %s, created_at = %s, raw = %s WHERE id = %s", (
                key.name,
                key.created_at,
                key.raw,
                key.id,
            ))
        conn.close()

    async def delete_key(self, key_id: int) -> None:
        conn = await self.get_connection()
        async with conn.cursor() as cursor:
            await cursor.execute("DELETE FROM apikey WHERE id = %s", (key_id,))
        conn.close()