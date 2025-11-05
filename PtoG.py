import asyncio
import io
import logging
from PIL import Image
from .. import loader, utils

logger = logging.getLogger(__name__)

@loader.tds
class ImageToGifModule(loader.Module):
    """Модуль для конвертации изображения в GIF.
    Автор: @asko_modules.
    
    В конфигурации модуля укажите:
    - duration: Длительность одной кадровой анимации в секундах (по умолчанию 0.1).
    - loop: Количество повторов GIF (0 = бесконечно, по умолчанию 0).
    
    """

    strings = {
        "name": "ImageToGifModule",
        "processing": "⌛ Конвертация изображения в GIF...",
        "success": "🎉 GIF создан и отправлен!",
        "error": "❗ Ошибка: {}",
        "no_image": "⚠️ Ответьте на изображение командой .img2gif.",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "duration",
                0.1,
                "Длительность одной кадровой анимации в секундах.",
                validator=loader.validators.Float(minimum=0.01),
            ),
            loader.ConfigValue(
                "loop",
                0,
                "Количество повторов GIF (0 = бесконечно).",
                validator=loader.validators.Integer(minimum=0),
            ),
        )

    async def img2gifcmd(self, message):
        """Ответьте на фото для использования команды."""
        if not message.is_reply:
            await utils.answer(message, self.strings["no_image"])
            return

        reply = await message.get_reply_message()
        if not reply or not reply.media or not reply.photo:
            await utils.answer(message, self.strings["no_image"])
            return

        await utils.answer(message, self.strings["processing"])
        try:
            # Скачиваем изображение
            photo = await self.client.download_media(reply, file=io.BytesIO())
            img = Image.open(photo)

            # Конвертация в GIF (3 секунды = 30 кадров при duration=0.1)
            frames = []
            for i in range(30):  # 30 кадров для 3 секунд
                frame = img.copy()
                frames.append(frame)

            # Сохраняем как GIF
            output = io.BytesIO()
            frames[0].save(
                output,
                format="GIF",
                save_all=True,
                append_images=frames[1:],
                duration=int(self.config["duration"] * 1000),  # Конверт в мс
                loop=self.config["loop"],
            )
            output.name = "converted.gif"
            output.seek(0)

            # Отправляем GIF
            await message.client.send_file(
                message.to_id,
                file=output,
                reply_to=reply,
            )
            await utils.answer(message, self.strings["success"])
        except Exception as e:
            await utils.answer(message, self.strings["error"].format(str(e)))

    async def client_ready(self, client, db):
        self.client = client
