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
from mautrix.types import (
    EventID,
    MessageType,
    RelatesTo,
    RelationType,
    RoomID,
    TextMessageEventContent,
)
from maubot import MessageEvent, Plugin
from maubot.handlers import command
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
        if not isinstance(self.config, Config):
            self.log.error("Plugin must be configured before use.")
            await self.stop()
        elif not self.config["openai.api_key"]:
            self.log.error("OpenAI API token is not configured.")
            await self.stop()
        else:
            self.config.load_and_update()
            self.log.info("OpenAITranslate has started!")

    @command.new(name="tr", help="Enter `!tr en` to translate to a given language")
    @command.argument("language", pass_raw=True, required=True)
    @command.argument("message", pass_raw=True, required=False)
    async def handle_translate(
        self, evt: MessageEvent, language: str = "en", message: str | None = None
    ) -> None:
        """
        Handles the '!tr' command to translate a message in a Matrix room.

        This method is triggered when a user sends a message starting with '!tr'. It parses
        the message to determine the target language and the text to be translated.

        Args:
            event (MessageEvent): The message event that triggered the command.
            language (str): The language code to which the message should be translated.

        Returns:
            None: Responds directly to the Matrix room with the translated message or error message.
        """
        self.log.info("OpenAITranslate received a request!")
        # Convert the language code to language name
        language_name = LANGUAGES.get(language.lower())

        if not language_name:
            await evt.respond("Invalid or unsupported language code.")
            return

        if evt.content.relates_to and evt.content.relates_to.rel_type == "m.in_reply_to":
            original_message = await self.extract_reply(
                evt.room_id, evt.content.relates_to.event_id
            )
        elif message:
            original_message = evt.content.body.split(" ", 2)[2]
        else:
            self.log.info(f"Couldn't recognise message {original_message}")
            return

        self.log.info(f"Requested to translate into {language_name}: {original_message}")
        translation = await self.translate_with_openai(original_message, language)
        self.log.info(f"Received translation: {translation}")

        content = TextMessageEventContent(
            msgtype=MessageType.TEXT,
            body=f"From {language_name}: {translation}",
            relates_to=RelatesTo(
                rel_type=RelationType("xyz.maubot.translation"), event_id=evt.event_id
            ),
        )
        await evt.respond(content)

    async def extract_reply(self, room_id: RoomID, event_id: EventID) -> str:
        """
        Extracts the content of a message being replied to in a Matrix room.

        Args:
            room_id (RoomID): The ID of the Matrix room.
            event_id (str): The event ID of the message being replied to.

        Returns:
            str: The content of the original message.
        """
        evt = await self.client.get_event(room_id, event_id)
        return evt.content.body if evt else ""

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
        prompt = self.config["openai.prompt"].format(language=language) + text
        payload = {
            "model": self.config["openai_model"],
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": text},
            ],
            "temperature": self.config["openai_temperature"],
            "max_tokens": self.config["openai_max_tokens"],
            "top_p": 1,
            "frequency_penalty": 0,
            "presence_penalty": 0,
        }

        self.log.info(f"Sending payload to OpenAI: {json.dumps(payload)}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    data=json.dumps(payload),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self.log.info(f"Response from OpenAI: {json.dumps(data)}")
                        responses = (
                            data.get("choices", [{}])[0]
                            .get("message", {})
                            .get("content", "")
                            .strip()
                        )
                        return responses
                    else:
                        self.log.error(f"OpenAI API request failed with status {resp.status}")
                        return "Failed to translate the message."
        except Exception as e:
            self.log.error(f"Error during translation: {e}")
            return "Failed to translate the message due to an error."

    @classmethod
    def get_config_class(cls) -> Type[BaseProxyConfig]:
        return Config
