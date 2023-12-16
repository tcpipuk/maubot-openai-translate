"""
Maubot plugin to handle translation commands using the OpenAI API.

This module defines the OpenAITranslate class, which integrates with OpenAI's language model to
provide translation services within Matrix chat rooms. It handles command parsing, translation
requests to the OpenAI API, and responding to user messages with translated text.

Dependencies:
- aiohttp: For making asynchronous HTTP requests to the OpenAI API.
- maubot: For plugin and command handling within the Maubot framework.
- mautrix: For types and utilities related to the Matrix protocol.
"""
from typing import Type
import json
import aiohttp
from mautrix.util.config import BaseProxyConfig, ConfigUpdateHelper
from mautrix.types import RoomID
from maubot import MessageEvent, Plugin
from maubot.handlers import event, command
from .languages import LANGUAGES


class Config(BaseProxyConfig):
    def do_update(self, helper: ConfigUpdateHelper) -> None:
        helper.copy("openai.api_key")
        helper.copy("openai.model")
        helper.copy("openai.max_tokens")
        helper.copy("openai.temperature")
        helper.copy("openai.prompt")


class OpenAITranslate(Plugin):
    """
    A plugin for translating messages in Matrix rooms using OpenAI's language models.

    This class extends the Maubot Plugin class and handles the initialization and command
    processing required to translate messages. It interacts with the OpenAI API to perform
    the translations and responds directly in the Matrix chat rooms.

    Attributes:
        config (Config): A configuration object holding API keys and settings.
    """

    async def start(self) -> None:
        """
        Initializes the plugin by loading the configuration.

        Ensures that the OpenAI API token is configured. Logs a warning if not.
        """
        await super().start()
        self.config.load_and_update()

        if not self.config["openai.api_key"]:
            self.log.warning("OpenAI API token is not configured.")

    @command.new("tr", help="Translates a message")
    @command.argument("language", pass_raw=True, required=False)
    async def handle_translate(self, event: MessageEvent, language: str) -> None:
        """
        Handles the '!tr' command to translate a message in a Matrix room.

        This method is triggered when a user sends a message starting with '!tr'. It parses
        the message to determine the target language and the text to be translated.

        Args:
            event (MessageEvent): The message event that triggered the command.
            language (str): The language code to which the message should be translated.

        Returns:
            None: Responds directly to the Matrix room with the translated message or an error message.
        """
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
        """
        Extracts the content of a message being replied to in a Matrix room.

        Args:
            room_id (RoomID): The ID of the Matrix room.
            event_id (str): The event ID of the message being replied to.

        Returns:
            str: The content of the original message.
        """
        event = await self.client.get_event(room_id, event_id)
        return event.content.body if event else ""

    async def translate_with_openai(self, text: str, language: str) -> str:
        """
        Translates a given text into the specified language using OpenAI's API.

        Constructs the request payload and sends it to the OpenAI API, then processes
        the response to extract the translated text.

        Args:
            text (str): The text to be translated.
            language (str): The target language code for the translation.

        Returns:
            str: The translated text or an error message if the API call fails.
        """
        headers = {
            "Authorization": f"Bearer {self.config['openai_key']}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.config["openai_model"],
            "messages": [
                {
                    "role": "system",
                    "content": self.config["openai_prompt"].format(language=language),
                },
                {"role": "user", "content": text},
            ],
            "temperature": self.config["openai_temperature"],
            "max_tokens": self.config["openai_max_tokens"],
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

    @classmethod
    def get_config_class(cls) -> Type[BaseProxyConfig]:
        return Config
