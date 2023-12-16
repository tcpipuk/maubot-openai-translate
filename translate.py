import aiohttp
import json
import maubot
from maubot import Plugin, MessageEvent
from maubot.handlers import command
from mautrix.types import RoomID
from .languages import LANGUAGES


class Config(maubot.Config):
    openai_key: str
    openai_model: str = "gpt-3.5-turbo"
    openai_max_tokens: int = 2048
    openai_temperature: float = 0.4
    openai_prompt: str = (
        "Translate the following message to {language}. Write nothing except the translation."
    )


class OpenAITranslate(Plugin):
    async def start(self) -> None:
        self.config: Config = Config(**self.config)
        if not self.config.openai_token:
            self.log.warning("OpenAI API token is not configured.")

    @command.new("tr", help="Translates a message")
    @command.argument("language", pass_raw=True, required=False)
    async def handle_translate(self, event: MessageEvent, language: str) -> None:
        # Convert the language code to language name
        language_name = LANGUAGES.get(language.lower())

        if not language_name:
            await event.respond("Invalid or unsupported language code.")
            return

        if event.content.relates_to and event.content.relates_to.rel_type == "m.in_reply_to":
            original_message = await self.extract_reply(
                event.room_id, event.content.relates_to.event_id
            )
        elif language and event.content.body.strip() != "!tr " + language:
            original_message = event.content.body.split(" ", 2)[2]
        else:
            return

        formatted_text = f"Language: {language_name}\nMessage: {original_message}"
        translation = await self.translate_with_openai(formatted_text, language)

        await event.respond(translation)

    async def extract_reply(self, room_id: RoomID, event_id: str) -> str:
        event = await self.client.get_event(room_id, event_id)
        return event.content.body if event else ""

    async def translate_with_openai(self, text: str, language: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.config.openai_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.config.openai_model,
            "messages": [
                {"role": "system", "content": self.config.openai_prompt.format(language=language)},
                {"role": "user", "content": text},
            ],
            "temperature": self.config.openai_temperature,
            "max_tokens": self.config.openai_max_tokens,
            "top_p": 1,
            "frequency_penalty": 0,
            "presence_penalty": 0,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                data=json.dumps(payload),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    responses = (
                        data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                    )
                    return responses
                else:
                    self.log.error(f"OpenAI API request failed with status {resp.status}")
                    return "Failed to translate the message."


def get_class():
    return OpenAITranslate
