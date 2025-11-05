import asyncio
import io
import logging
from .. import loader, utils

try:
    import google.generativeai as genai
except ImportError:
    genai = None

try:
    import openai
except ImportError:
    openai = None

logger = logging.getLogger(__name__)

@loader.tds
class AIModule(loader.Module):
    """AI модуль для Hikka userbot. Поддерживает несколько нейронок через API (Gemini, OpenAI и т.д.).
    Автор: @asko_modules.
    
    В конфигурации модуля укажите:
    - provider: Выберите нейронку ('gemini' или 'openai').
    - api_key: API ключ для выбранного провайдера (для Gemini: https://aistudio.google.com/app/apikey; для OpenAI: https://platform.openai.com/api-keys).
    - model: Модель для выбранного провайдера (например, 'gemini-1.5-flash' для Gemini или 'gpt-4o-mini' для OpenAI).
    - system_prompt: Системный промпт для AI, который определяет поведение (по умолчанию пустой).
    
    Команда: .ai <запрос> — отправляет запрос AI и возвращает ответ.
    Если ответ слишком длинный, он отправляется как файл.
    """

    strings = {
        "name": "AIModule",
        "processing": "⌛ Обработка запроса...",
        "error": "❗ Ошибка: {}",
        "no_query": "⚠️ Укажите запрос после .ai",
        "no_api_key": "❗ API ключ не указан в конфиге.",
        "invalid_provider": "❗ Неподдерживаемый провайдер. Выберите 'gemini' или 'openai'.",
        "missing_library": "❗ Библиотека для {} не установлена. Установите {} через pip.",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "provider",
                "gemini",
                "Провайдер AI (gemini или openai).",
                validator=loader.validators.Choice(["gemini", "openai"]),
            ),
            loader.ConfigValue(
                "api_key",
                None,
                "API ключ для выбранного провайдера.",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "model",
                "gemini-1.5-flash",
                "Модель для выбранного провайдера.",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "system_prompt",
                "",
                "Системный промпт для AI (определяет стиль ответов).",
                validator=loader.validators.String(),
            ),
        )
        self.ai_client = None
        self.model = None

    async def client_ready(self, client, db):
        provider = self.config["provider"]
        api_key = self.config["api_key"]
        model = self.config["model"]
        system_prompt = self.config["system_prompt"]

        if not api_key:
            logger.warning(self.strings["no_api_key"])
            return

        if provider == "gemini":
            if not genai:
                await utils.answer(None, self.strings["missing_library"].format("Gemini", "google-generativeai"))
                return
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(
                model,
                system_instruction=system_prompt,
            )
        elif provider == "openai":
            if not openai:
                await utils.answer(None, self.strings["missing_library"].format("OpenAI", "openai"))
                return
            self.ai_client = openai.AsyncOpenAI(api_key=api_key)
            self.model = model  # Для OpenAI модель указывается в запросе
            self.system_prompt = system_prompt
        else:
            logger.warning(self.strings["invalid_provider"])

    async def aicmd(self, message):
        """Генерировать ответ от AI: .ai <запрос>"""
        query = utils.get_args_raw(message)
        if not query:
            await utils.answer(message, self.strings["no_query"])
            return

        if not self.config["api_key"]:
            await utils.answer(message, self.strings["no_api_key"])
            return

        provider = self.config["provider"]
        if provider not in ["gemini", "openai"]:
            await utils.answer(message, self.strings["invalid_provider"])
            return

        await utils.answer(message, self.strings["processing"])
        try:
            if provider == "gemini":
                if not self.model:
                    raise ValueError("Gemini модель не инициализирована.")
                response = await asyncio.to_thread(self.model.generate_content, query)
                text = response.text
            elif provider == "openai":
                if not self.ai_client:
                    raise ValueError("OpenAI клиент не инициализирован.")
                messages = []
                if self.system_prompt:
                    messages.append({"role": "system", "content": self.system_prompt})
                messages.append({"role": "user", "content": query})
                response = await self.ai_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                )
                text = response.choices[0].message.content

            if len(text) > 4096:
                file = io.BytesIO(text.encode())
                file.name = "ai_response.txt"
                await message.client.send_file(message.to_id, file, reply_to=message)
            else:
