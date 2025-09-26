from typing import List
from models.client import Client
from models.bot import Bot

class ClientService:
    def __init__(self):
        self.clients = {}

    def add_client(self, client_id: str) -> Client:
        if client_id in self.clients:
            raise ValueError("Client already exists.")
        client = Client(client_id)
        self.clients[client_id] = client
        return client

    def remove_client(self, client_id: str) -> None:
        if client_id not in self.clients:
            raise ValueError("Client not found.")
        del self.clients[client_id]

    def get_client(self, client_id: str) -> Client:
        if client_id not in self.clients:
            raise ValueError("Client not found.")
        return self.clients[client_id]

    def list_clients(self) -> List[Client]:
        return list(self.clients.values())

    def add_bot_to_client(self, client_id: str, bot_id: str, bot_token: str) -> Bot:
        client = self.get_client(client_id)
        bot = Bot(bot_id, bot_token)
        client.bots.append(bot)
        return bot

    def remove_bot_from_client(self, client_id: str, bot_id: str) -> None:
        client = self.get_client(client_id)
        client.bots = [bot for bot in client.bots if bot.bot_id != bot_id]