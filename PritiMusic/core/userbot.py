from pyrogram import Client
from pyrogram.enums import ParseMode

import config
from ..logging import LOGGER

assistants = []
assistantids = []


class Userbot:
    def __init__(self):
        self.one = Client(
            name="LuckyXAss1",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=str(config.STRING1),
            no_updates=True,
        ) if config.STRING1 else None
        self.two = Client(
            name="LuckyXAss2",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=str(config.STRING2),
            no_updates=True,
        ) if config.STRING2 else None
        self.three = Client(
            name="LuckyXAss3",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=str(config.STRING3),
            no_updates=True,
        ) if config.STRING3 else None
        self.four = Client(
            name="LuckyXAss4",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=str(config.STRING4),
            no_updates=True,
        ) if config.STRING4 else None
        self.five = Client(
            name="LuckyXAss5",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=str(config.STRING5),
            no_updates=True,
        ) if config.STRING5 else None

    async def _start_assistant(self, client, num):
        """Start a single assistant client with proper error handling."""
        if client is None:
            return
        try:
            await client.start()
            me = client.me
            if not me:
                LOGGER(__name__).error(f"Assistant {num}: could not fetch user info.")
                return
            client.id = me.id
            client.username = me.username or ""
            try:
                client.name = me.mention
            except Exception:
                client.name = f'<a href="tg://user?id={me.id}">{me.first_name}</a>'

            try:
                await client.join_chat("unhealed_notess")
            except Exception:
                pass

            try:
                await client.send_message(config.LOGGER_ID, f"Assistant {num} Started")
            except Exception as e:
                LOGGER(__name__).warning(
                    f"Assistant {num} could not send message to log group: {type(e).__name__}: {e}"
                )

            assistants.append(num)
            assistantids.append(client.id)
            LOGGER(__name__).info(f"Assistant {num} Started as {client.name}")
        except Exception as e:
            LOGGER(__name__).error(
                f"Failed to start Assistant {num}: {type(e).__name__}: {e}"
            )

    async def start(self):
        LOGGER(__name__).info("Starting Assistants...")
        if not config.LOGGER_ID:
            LOGGER(__name__).error("LOGGER_ID is not set in config!")
            exit()

        await self._start_assistant(self.one, 1)
        await self._start_assistant(self.two, 2)
        await self._start_assistant(self.three, 3)
        await self._start_assistant(self.four, 4)
        await self._start_assistant(self.five, 5)

        if not assistants:
            LOGGER(__name__).error(
                "No assistant clients started successfully. "
                "Make sure at least STRING_SESSION is set correctly."
            )
            exit()

    async def stop(self):
        LOGGER(__name__).info("Stopping Assistants...")
        for client in [self.one, self.two, self.three, self.four, self.five]:
            if client is not None:
                try:
                    await client.stop()
                except Exception:
                    pass
