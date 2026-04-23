import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, List

import aiohttp
import typer
import yaml

import blivedm

logger: logging.Logger = logging.getLogger("BiliBili_Livestream_Reminder")
logger.setLevel(logging.INFO)
stream_handler: logging.StreamHandler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
logger.addHandler(stream_handler)

HEADERS: Dict[str, str] = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
}

@dataclass
class BotConfig:
    bot_token: str
    chat_id: str
    room_ids: List[int]

async def get_live_room_info(session: aiohttp.ClientSession, room_id: int) -> Optional[Dict]:
    url = f"https://api.live.bilibili.com/room/v1/Room/get_info?room_id={room_id}"
    try:
        async with session.get(url, headers=HEADERS, timeout=10) as response:
            if response.status != 200:
                logger.error("获取直播间信息失败: HTTP 状态码 %s", response.status)
                return None
            data = await response.json()
            if data["code"] != 0:
                logger.error("获取直播间信息失败: %s", data["message"])
                return None
            return data["data"]
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        logger.error("获取直播间网络异常: %s", e)
        return None

async def get_user_info(session: aiohttp.ClientSession, uid: int) -> Optional[Dict]:
    url = f"https://api.live.bilibili.com/live_user/v1/Master/info?uid={uid}"
    try:
        async with session.get(url, headers=HEADERS, timeout=10) as response:
            if response.status != 200:
                logger.error("获取用户信息失败: HTTP 状态码 %s", response.status)
                return None
            data = await response.json()
            if data["code"] != 0:
                logger.error("获取用户信息失败: %s", data["message"])
                return None
            return data["data"]
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        logger.error("获取用户信息网络异常: %s", e)
        return None

async def send_telegram_notification(session: aiohttp.ClientSession, config: BotConfig, text: str, photo_url: Optional[str] = None) -> bool:
    try:
        if photo_url:
            url = f"https://api.telegram.org/bot{config.bot_token}/sendPhoto"
            payload = {"chat_id": config.chat_id, "photo": photo_url, "caption": text}
        else:
            url = f"https://api.telegram.org/bot{config.bot_token}/sendMessage"
            payload = {"chat_id": config.chat_id, "text": text}
        
        async with session.post(url, data=payload, timeout=10) as response:
            response.raise_for_status()
            return True
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        logger.error("Telegram API 推送失败: %s", e)
        return False

class LiveRoom:
    def __init__(self, room_id: int, config: BotConfig, session: aiohttp.ClientSession):
        self.room_id: int = room_id
        self.config: BotConfig = config
        self.session: aiohttp.ClientSession = session
        self.is_live: bool = False

    async def on_preparing(self):
        self.is_live = False

    async def on_live(self):
        if self.is_live:
            return
        
        # State locked to prevent concurrent triggers on the same event
        self.is_live = True
        
        live_room_info = await get_live_room_info(self.session, self.room_id)
        if live_room_info is None:
            self.is_live = False
            return
        
        user_info = await get_user_info(self.session, live_room_info["uid"])
        if user_info is None:
            self.is_live = False
            return
            
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        uname = user_info["info"]["uname"]
        title = live_room_info["title"]
        room_url = f"https://live.bilibili.com/{live_room_info['room_id']}"
        
        caption = (
            f"[LIVE - Bilibili] | Time: {current_time}\n"
            f"{title}\n"
            f"{uname}\n"
            f"{room_url}"
        )

        success = await send_telegram_notification(self.session, self.config, caption, live_room_info.get("user_cover"))
        if not success:
            # Revert state to allow retry on the next ping
            self.is_live = False

class MyHandler(blivedm.BaseHandler):
    def __init__(self, config: BotConfig, session: aiohttp.ClientSession):
        super().__init__()
        self.config = config
        self.session = session
        self.rooms: Dict[int, LiveRoom] = {}

    def add_room(self, room_id: int):
        self.rooms[room_id] = LiveRoom(room_id, self.config, self.session)

    def _on_preparing(self, client: blivedm.BLiveClient, command: Dict):
        logger.info("[%d] PREPARING, command=%s", client.room_id, command)
        room = self.rooms.get(client.room_id)
        if room:
            asyncio.create_task(room.on_preparing())

    def _on_live(self, client: blivedm.BLiveClient, command: Dict):
        logger.info("[%d] LIVE, command=%s", client.room_id, command)
        room = self.rooms.get(client.room_id)
        if room:
            asyncio.create_task(room.on_live())

    # RISK DOCUMENTATION: Overriding protected attribute _CMD_CALLBACK_DICT.
    # If the blivedm library updates its command dispatch logic, this mechanism may fail.
    # Requires monitoring against library updates since there is no public API method for this registration.
    _CMD_CALLBACK_DICT: Dict[str, callable] = blivedm.BaseHandler._CMD_CALLBACK_DICT.copy()
    _CMD_CALLBACK_DICT["PREPARING"] = _on_preparing
    _CMD_CALLBACK_DICT["LIVE"] = _on_live

async def reminder(config: BotConfig):
    async with aiohttp.ClientSession() as session:
        handler = MyHandler(config, session)
        for room_id in config.room_ids:
            live_room_info = await get_live_room_info(session, room_id)
            if live_room_info is None:
                continue
            
            actual_room_id = live_room_info["room_id"]
            handler.add_room(actual_room_id)

        clients = [blivedm.BLiveClient(room_id) for room_id in handler.rooms.keys()]
        
        for client in clients:
            client.set_handler(handler)
            client.start()

        try:
            await asyncio.gather(*(client.join() for client in clients))
        finally:
            await asyncio.gather(*(client.stop_and_close() for client in clients))

def main(config: str = "config.yaml"):
    if not os.path.isabs(config):
        cwd = os.getcwd()
        config = os.path.join(cwd, config)

    with open(config, "r") as file:
        c = yaml.safe_load(file)
        
    bot_config = BotConfig(
        bot_token=c["telegram-bot-token"],
        chat_id=str(c["telegram-chat-id"]),
        room_ids=c["room-ids"]
    )

    asyncio.run(reminder(bot_config))

if __name__ == "__main__":
    typer.run(main)
