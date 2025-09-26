from typing import Dict, List
from .bot_instance import BotInstance

class BotManager:
    def __init__(self):
        self.clients_bots: Dict[str, List[BotInstance]] = {}

    def add_bot(self, client_id: str, bot_token: str) -> BotInstance:
        bot_instance = BotInstance(bot_token)
        if client_id not in self.clients_bots:
            self.clients_bots[client_id] = []
        self.clients_bots[client_id].append(bot_instance)
        return bot_instance

    def start_bot(self, client_id: str, bot_id: int) -> bool:
        bot_instance = self.get_bot_instance(client_id, bot_id)
        if bot_instance:
            bot_instance.start()
            return True
        return False

    def stop_bot(self, client_id: str, bot_id: int) -> bool:
        bot_instance = self.get_bot_instance(client_id, bot_id)
        if bot_instance:
            bot_instance.stop()
            return True
        return False

    def get_bot_instance(self, client_id: str, bot_id: int) -> BotInstance:
        if client_id in self.clients_bots:
            for bot in self.clients_bots[client_id]:
                if bot.bot_id == bot_id:
                    return bot
        return None

    def list_bots(self, client_id: str) -> List[Dict]:
        if client_id in self.clients_bots:
            return [bot.to_dict() for bot in self.clients_bots[client_id]]
        return []

    def remove_bot(self, client_id: str, bot_id: int) -> bool:
        if client_id in self.clients_bots:
            self.clients_bots[client_id] = [
                bot for bot in self.clients_bots[client_id] if bot.bot_id != bot_id
            ]
            return True
        return False