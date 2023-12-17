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
from maubot.matrix import MaubotMessageEvent as MessageEvent
from maubot.plugin_base import Plugin
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
        # Check if config exists
        if not isinstance(self.config, Config):
            self.log.error("Plugin must be configured before use.")
            await self.stop()
            return
        # Load in config and check for API key
        self.config.load_and_update()
        if not self.config["openai.api_key"]:
            self.log.error("OpenAI API token is not configured.")
            await self.stop()
            return

    @command.new(name="tr", help="Translate a message. Usage: !tr <language_code> <message>")
    @command.argument("args", pass_raw=True, required=True)
    async def tr(self, evt: MessageEvent, args: str) -> None:
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
        # Identify language
        parts = args.split(" ", 1)
        language_code, message = parts[0], parts[1] if len(parts) > 1 else None
        language_name = LANGUAGES.get(language_code.lower())
        if not language_name:
            await evt.respond(f"I don't recognise language '{language_code}', sorry!", reply=True)
            return
        # Handle command replying to original message
        if message:
            translation = await self.translate_with_openai(message, language_code)
            await evt.respond(content=translation, markdown=True, reply=True)
        elif not message and evt.content.get_reply_to():
            reply_evt = await self.client.get_event(evt.room_id, evt.content.get_reply_to())
            translation = await self.translate_with_openai(reply_evt.content.body, language_name)
            await reply_evt.respond(
                content=f"{language_code.upper()}: {translation}", markdown=True, reply=True
            )
        # Warn when nothing to translate
        else:
            await evt.respond(
                "I didn't see a message: try using `!tr {language_code}` to reply to it.",
                markdown=True,
                reply=True,
            )
            return

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
        if not self.config:
            return "Sorry, I'm not configured yet!"
        # Build request
        headers = {
            "Authorization": f"Bearer {self.config['openai.api_key']}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.config["openai.model"],
            "messages": [
                {
                    "role": "system",
                    "content": self.config["openai.prompt"].format(language=language),
                },
                {"role": "user", "content": text},
            ],
            "temperature": self.config["openai.temperature"],
            "max_tokens": self.config["openai.max_tokens"],
            "top_p": 1,
            "frequency_penalty": 0,
            "presence_penalty": 0,
        }
        # Send request to OpenAI
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    data=json.dumps(payload),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
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
