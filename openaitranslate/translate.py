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
from datetime import datetime, timedelta
import json
import aiohttp
from mautrix.util.config import BaseProxyConfig, ConfigUpdateHelper
from maubot.matrix import MaubotMessageEvent as MessageEvent
from maubot.plugin_base import Plugin
from maubot.handlers import command
from .languages import LANGUAGES


class Config(BaseProxyConfig):
    """
    Extends the BaseProxyConfig from the Maubot framework to manage the configuration settings
    for the OpenAITranslate plugin. Uses the config parameters from the 'base-config.yaml' file.

    Configuration Parameters:
        bot.rate_limit (int): Limit on translations each user can do per hour, zero disables limit.
        bot.rate_window (int): Seconds to ratelimit over, default 3600 for 1 hour.
        bot.rate_message (str): Message to reply with when limit exceeded (blank means no reply)
        openai.api_key (str): The API key for accessing OpenAI's services.
        openai.model (str): Specifies model of GPT (e.g., gpt-3.5-turbo) to use for translations.
        openai.max_tokens (int): Provides an upper limit for translation length by setting the
                                 maximum number of tokens (words/pieces of words) in each response.
        openai.temperature (float): Sets 'creativity' temperature for translation, which should be
                                    low for a normal translation.
        openai.prompt (str): System prompt sent to OpenAI, tells the model what to do with the text.

    Methods:
        do_update(helper: ConfigUpdateHelper): Updates config parameters from the Maubot interface.
    """

    def do_update(self, helper: ConfigUpdateHelper) -> None:
        helper.copy("bot.rate_limit")
        helper.copy("bot.rate_window")
        helper.copy("bot.rate_message")
        helper.copy("bot.empty_message")
        helper.copy("bot.unknown_message")
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
        user_translations (dict): Dict of timestamps of translations for rate limiting.
    """

    user_translations = {}

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
        reply_config = {"markdown": True, "reply": True}
        # Identify language
        parts = args.split(" ", 1)
        language_code, message = parts[0], parts[1] if len(parts) > 1 else None
        language_name = LANGUAGES.get(language_code.lower())
        if not language_name:
            await evt.respond(
                self.config["bot.unknown_message"].format(language_code=language_code),
                **reply_config,
            )
            return
        # Handle commands that were replying to other messages
        if not message and evt.content.get_reply_to():
            reply_evt = await self.client.get_event(evt.room_id, evt.content.get_reply_to())
            message = reply_evt.content.body
        else:
            reply_evt = False
        # Handle translation replying to original message
        if message:
            if not await self.check_limit(evt.sender):
                if self.config["bot.rate_message"]:
                    await evt.respond(str(self.config["bot.rate_message"]), **reply_config)
            else:
                translation = await self.translate_with_openai(message, language_name)
                if reply_evt:
                    await reply_evt.respond(
                        f"{language_code.upper()}: {translation}", **reply_config
                    )
                else:
                    await evt.respond(translation, **reply_config)
        # Warn when nothing to translate
        else:
            await evt.respond(
                self.config["bot.empty_message"].format(language_code=language_code), **reply_config
            )
        return

    async def check_limit(self, user_id):
        current_time = datetime.now()
        # Remove expired entries before counting ratelimit
        self.user_translations = {
            user: [
                t
                for t in times
                if current_time - t < timedelta(seconds=self.config["bot.rate_window"])
            ]
            for user, times in self.user_translations.items()
            if times  # Keep users who have made translations
        }
        # Check limit for this user
        if user_id not in self.user_translations:
            self.user_translations[user_id] = [current_time]
            return True
        elif len(self.user_translations[user_id]) <= self.config["bot.rate_limit"]:
            self.user_translations[user_id].append(current_time)
            return True
        else:
            return False

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
