import asyncio
import websockets
import json
import logging



class WebSocketConnector:
    def __init__(self, exchange_url, subscribe_message, handler):
        self.exchange_url = exchange_url
        self.subscribe_message = subscribe_message
        self.handler = handler

    async def connect(self):
        async with websockets.connect(self.exchange_url) as websocket:
            await websocket.send(json.dumps(self.subscribe_message))
            logging.info(f"Subscribed: {self.subscribe_message}")

            async for message in websocket:
                data = json.loads(message)
                await self.handler(data)
