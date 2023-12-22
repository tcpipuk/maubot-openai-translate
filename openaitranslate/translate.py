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
    Configuration manager for the OpenAITranslate plugin, extending BaseProxyConfig.

    Manages the configuration settings used by the OpenAITranslate plugin, the parameters are read
    from the 'base-config.yaml' file and control the behavior of the translation bot.

    Configuration Parameters:
        bot.rate_limit (int): Limit on translation requests per rate_window. Zero disables limit.
        bot.rate_window (int): Duration of rate limit measurement. Default 3600 seconds (1 hour).
        bot.rate_message (str): Reply message when user exceeds the rate limit. Blank sends nothing.
        bot.empty_message (str): Reply message when a request is received with nothing to translate.
        bot.unknown_message (str): Reply when an unrecognised language code is used.
        languages.replace_list (bool): Whether to replace default language list with codes below or
                                       just update the language with new/updated ones.
        languages.codes (dict): Custom language codes and names to extend/replace language list.
        openai.api_key (str): The API key for accessing OpenAI's services.
        openai.model (str): Which OpenAI GPT model to use for requests. Default is gpt-3.5-turbo.
        openai.max_tokens (int): Maximum number of tokens (pieces of words) for OpenAI responses.
        openai.temperature (float): The 'creativity' of translations, lower values are more literal.
        openai.prompt (str): System prompt sent to OpenAI, instructing the model for translation.
        openai.custom_endpoint (str): URL of OpenAI chat completions similar API. Blank uses OpenAI.

    Methods:
        do_update(helper: ConfigUpdateHelper): Updates the configuration parameters from the
                                               Maubot interface when changes are made.

    Note: This class relies on the BaseProxyConfig from the Maubot framework for base functionality.
    """

    def do_update(self, helper: ConfigUpdateHelper) -> None:
        helper.copy("openai.api_key")
        helper.copy("openai.model")
        helper.copy("openai.max_tokens")
        helper.copy("openai.temperature")
        helper.copy("openai.prompt")
        helper.copy("openai.custom_endpoint")
        helper.copy("bot.rate_limit")
        helper.copy("bot.rate_window")
        helper.copy("bot.rate_message")
        helper.copy("bot.empty_message")
        helper.copy("bot.unknown_message")
        helper.copy("languages.replace_list")
        helper.copy("languages.codes")


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

    languages = {}
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
        # Update language list as needed from the config
        self.update_language_list()

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
        # Update language list
        self.update_language_list()
        # Identify language
        parts = args.split(" ", 1)
        language_code, message = parts[0], parts[1] if len(parts) > 1 else None
        language_name = self.languages.get(language_code.lower())
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

    def update_language_list(self):
        """
        Updates the language list based on the current configuration.

        Clears the self.languages dictionary and repopulates it from LANGUAGES. Starts with the
        original language list and then, if the `languages.replace_list` config is not True, updates
        with extra/updated language codes specified in the `languages.codes` config.
        """
        if self.config["languages.replace_list"]:
            self.log.info("Replacing language list!")
            self.languages.clear()
        else:
            self.log.info("Updating existing language list!")
            self.languages = LANGUAGES.copy()
        self.languages.update(self.config["languages.codes"])
        self.log.info("Language list has been updated!")

    async def check_limit(self, user_id: str) -> bool:
        """
        Checks if a user has exceeded the rate limit for translation requests.

        Manages rate limiting by tracking the time of each user's translation requests over a
        specified time window, defined in the bot's configuration.

        Maintains dictionary (`user_translations`) where each key is a user ID, and value is a list
        of timestamps representing their translation requests. It removes timestamps outside the
        current rate limit window and checks if the number of requests is within the allowed limit.
        If the user has not exceeded the limit, their new request timestamp is added to the list.

        Args:
            user_id (str): The unique identifier of the user making the translation request.

        Returns:
            bool: True if the user can make a translation request,
                  False if the user has exceeded the rate limit.

        Note: When the rate limiting is set to zero in the config, this always returns True.
        """
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
        # Skip processing if no rate limit
        if int(self.config["bot.rate_limit"]) == 0:
            return True
        # Create entry if this user not seen before
        if user_id not in self.user_translations:
            self.user_translations[user_id] = [current_time]
            return True
        # Add new timestmap for user if already exists
        if len(self.user_translations[user_id]) < int(self.config["bot.rate_limit"]):
            self.user_translations[user_id].append(current_time)
            return True
        # Failed ratelimit check
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
                    self.config["openai.custom_endpoint"]
                    if self.config["openai.custom_endpoint"]
                    else "https://api.openai.com/v1/chat/completions",
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
