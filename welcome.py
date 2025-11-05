import asyncio
import io
import logging
from .. import loader, utils
from telethon.tl.types import User

logger = logging.getLogger(__name__)

@loader.tds
class WelcomeModule(loader.Module):
    """Модуль приветствия для Hikka userbot. Отправляет приветственное сообщение новым участникам чата.
    Автор: @asko_modules.
    
    В конфигурации модуля укажите:
    - enabled: Включено ли приветствие (True/False).
    - welcome_message: Текст приветствия (используйте {name} для имени пользователя).
    - gif_url: Ссылка на GIF (опционально, оставьте пустым, если не нужно).
    - chat_count: Счетчик чатов (не редактируйте вручную).
    
    Команды:
    - .welcome on — Включить модуль.
    - .welcome off — Выключить модуль.
    - .welcome stats — Посмотреть количество чатов с приветствиями.
    """

    strings = {
        "name": "WelcomeModule",
        "enabled": "🎉 Приветствия включены!",
        "disabled": "🚫 Приветствия выключены!",
        "stats": "🧮 Количество чатов с приветствиями: {}",
        "welcome_sent": "👋 Приветствие отправлено: {}",
        "error": "❗ Ошибка: {}",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "enabled",
                False,
                "Включить/выключить модуль приветствия.",
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "welcome_message",
                "👋 Привет, {name}! Добро пожаловать в чат! Рад тебя видеть!",
                "Текст приветствия (используйте {name} для имени).",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "gif_url",
                "",
                "Ссылка на GIF для приветствия (оставьте пустым, если не нужно).",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "chat_count",
                0,
                "Счетчик чатов с приветствиями (не редактируйте вручную).",
                validator=loader.validators.Integer(),
            ),
        )
        self.welcomed_chats = set()  

    async def client_ready(self, client, db):
        self.client = client

    async def watcher(self, event):
        if not self.config["enabled"] or not event.is_group or event.chat_id in self.welcomed_chats:
            return

        if isinstance(event.user, User) and event.user.is_self:
            return  

        try:
            
            async for msg in self.client.iter_messages(
                event.chat_id, limit=1, from_user=event.user_id
            ):
                if not msg:
                    message = self.config["welcome_message"].format(name=event.user.first_name)
                    if self.config["gif_url"]:
                        await self.client.send_file(
                            event.chat_id,
                            file=self.config["gif_url"],
                            caption=message,
                            reply_to=event.message
                        )
                    else:
                        await self.client.send_message(
                            event.chat_id,
                            message,
                            reply_to=event.message
                        )
                    self.welcomed_chats.add(event.chat_id)
                    self.config["chat_count"] += 1
                    logger.info(self.strings["welcome_sent"].format(event.chat_id))
        except Exception as e:
            logger.error(self.strings["error"].format(str(e)))

    async def welcomecmd(self, message):
        """Управление модулем: .welcome on/off/stats"""
        args = utils.get_args_raw(message).lower()
        if not args:
            await utils.answer(message, "Используйте: .welcome on/off/stats")
            return

        if args == "on":
            self.config["enabled"] = True
            await utils.answer(message, self.strings["enabled"])
        elif args == "off":
            self.config["enabled"] = False
            await utils.answer(message, self.strings["disabled"])
        elif args == "stats":
            await utils.answer(message, self.strings["stats"].format(self.config["chat_count"]))
        else:
            await utils.answer(message, "Используйте: .welcome on/off/stats")
