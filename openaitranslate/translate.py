"""
Translate messages using the OpenAI API (or compatible alternatives) in Matrix chat rooms.

This module provides a Maubot plugin that integrates with OpenAI's language models to offer
translation services. It processes commands, sends translation requests to the OpenAI API,
and responds in Matrix rooms.

Dependencies:
    aiohttp: For asynchronous HTTP requests to the OpenAI API
    maubot: For plugin and command handling
    mautrix: For Matrix protocol types and utilities
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

import aiohttp
from maubot.handlers import command
from maubot.plugin_base import Plugin
from mautrix.util.config import BaseProxyConfig, ConfigUpdateHelper

from .languages import LANGUAGES

if TYPE_CHECKING:
    from maubot.matrix import MaubotMatrixClient as MatrixClient
    from maubot.matrix import MaubotMessageEvent as MessageEvent


class Config(BaseProxyConfig):
    """
    Manage configuration for the OpenAITranslate plugin.

    Manages the configuration settings used by the OpenAITranslate plugin, the parameters are read
    from the 'base-config.yaml' file and control the behavior of the translation bot.

    Attributes:
        bot.rate_limit (int): Maximum translation requests per rate window (0 disables limit)
        bot.rate_window (int): Duration in seconds for rate limiting (default: 3600)
        bot.rate_message (str): Response when user exceeds rate limit (blank sends nothing)
        bot.empty_message (str): Response when request has no text to translate
        bot.unknown_message (str): Response for unrecognised language codes
        languages.replace_list (bool): Whether to replace or update the default language list
        languages.codes (dict): Custom language codes and names
        openai.api_key (str): OpenAI API authentication key
        openai.model (str): GPT model to use (default: gpt-3.5-turbo)
        openai.max_tokens (int): Maximum token limit for responses
        openai.temperature (float): Translation creativity level (lower is more literal)
        openai.prompt (str): System prompt for translation instructions
        openai.custom_endpoint (str): Alternative API endpoint URL (blank uses OpenAI)
    """

    @staticmethod
    def do_update(helper: ConfigUpdateHelper) -> None:
        """
        Update configuration from base config.

        Args:
            helper (ConfigUpdateHelper): Helper to copy config values
        """
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
    Translate messages in Matrix rooms using OpenAI's language models.

    This class extends the Maubot Plugin class and handles the initialisation and command
    processing required to translate messages. It interacts with the OpenAI API to perform
    the translations and responds directly in the Matrix chat rooms.

    Attributes:
        config (Config): API keys and settings
        user_translations (dict): Translation timestamps for rate limiting
        languages (dict): Available language codes and names
    """

    def __init__(self, *args: Any, client: MatrixClient, **kwargs: Any) -> None:
        """
        Initialise the OpenAITranslate plugin.

        Args:
            client: The Matrix client instance
            *args: Variable length argument list
            **kwargs: Arbitrary keyword arguments
        """
        super().__init__(*args, client=client, **kwargs)
        self.languages: dict[str, str] = {}
        self.user_translations: dict[str, list[datetime]] = {}

    async def start(self) -> None:
        """
        Initialise the plugin and load configuration.

        Validates the OpenAI API token and logs warnings if not properly configured.
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
        Process translation commands in Matrix rooms.

        Handles the '!tr' command by parsing the target language and text,
        then returning the translation to the room.

        Args:
            evt (MessageEvent): The triggering message event
            args (str): The command arguments containing language code and text
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
                self.config["bot.unknown_message"].format(language_code=language_code),  # type:ignore
                **reply_config,  # type:ignore
            )
            return
        # Handle commands that were replying to other messages
        if not message and evt.content.get_reply_to():  # type:ignore
            reply_evt = await self.client.get_event(evt.room_id, evt.content.get_reply_to())  # type:ignore
            message = reply_evt.content.body
        else:
            reply_evt = False
        # Handle translation replying to original message
        if message:
            if not await self.check_limit(evt.sender):
                if self.config["bot.rate_message"]:  # type:ignore
                    await evt.respond(str(self.config["bot.rate_message"]), **reply_config)  # type:ignore
            else:
                translation = await self.translate_with_openai(message, language_name)
                if reply_evt:
                    await reply_evt.respond(
                        f"{language_code.upper()}: {translation}",
                        **reply_config,
                    )
                else:
                    await evt.respond(translation, **reply_config)  # type:ignore
        # Warn when nothing to translate
        else:
            await evt.respond(
                self.config["bot.empty_message"].format(language_code=language_code),  # type:ignore
                **reply_config,  # type:ignore
            )
        return

    def update_language_list(self) -> None:
        """
        Update the available languages based on configuration.

        Clears the self.languages dictionary and repopulates it from LANGUAGES. Starts with the
        original language list and then, if the `languages.replace_list` config is not True,
        updates with extra/updated language codes specified in the `languages.codes` config.
        """
        if self.config["languages.replace_list"]:  # type:ignore
            self.log.info("Replacing language list!")
            self.languages.clear()
        else:
            self.log.info("Updating existing language list!")
            self.languages = LANGUAGES.copy()
        self.languages.update(self.config["languages.codes"])  # type:ignore
        self.log.info("Language list has been updated!")

    async def check_limit(self, user_id: str) -> bool:
        """
        Check if a user has exceeded their translation rate limit.

        Manages rate limiting by tracking the time of each user's translation requests over a
        specified time window, defined in the bot's configuration.

        Maintains dictionary (`user_translations`) where each key is a user ID, and value is a list
        of timestamps representing their translation requests. It removes timestamps outside the
        current rate limit window and checks if the number of requests is within the allowed limit.
        If the user has not exceeded the limit, their new request timestamp is added to the list.

        Args:
            user_id (str): The Matrix user ID to check

        Returns:
            bool: True if translation is allowed, False if rate limited

        Note: When the rate limiting is set to zero in the config, this always returns True.
        """
        current_time = datetime.now(timezone.utc)
        # Remove expired entries before counting ratelimit
        self.user_translations = {
            user: [
                t
                for t in times
                if current_time - t < timedelta(seconds=self.config["bot.rate_window"])  # type:ignore
            ]
            for user, times in self.user_translations.items()
            if times  # Keep users who have made translations
        }
        # Skip processing if no rate limit
        if int(self.config["bot.rate_limit"]) == 0:  # type:ignore
            return True
        # Create entry if this user not seen before
        if user_id not in self.user_translations:
            self.user_translations[user_id] = [current_time]
            return True
        # Add new timestmap for user if already exists
        if len(self.user_translations[user_id]) < int(self.config["bot.rate_limit"]):  # type:ignore
            self.user_translations[user_id].append(current_time)
            return True
        # Failed ratelimit check
        return False

    async def translate_with_openai(self, text: str, language: str) -> str:
        """
        Send text to OpenAI API for translation.

        Makes an API request to OpenAI with the text and desired language,
        then processes the response.

        Args:
            text (str): Text to translate
            language (str): Target language name

        Returns:
            str: Translated text or error message if request fails
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
            async with aiohttp.ClientSession() as session, session.post(
                self.config["openai.custom_endpoint"]
                or "https://api.openai.com/v1/chat/completions",
                headers=headers,
                data=json.dumps(payload),
            ) as resp:
                if resp.ok:
                    data = await resp.json()
                    return (
                        data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                    )
                # Handle errors
                self.log.error("OpenAI API request failed with status %s", resp.status)
                return "Failed to translate the message."
        except Exception:
            self.log.exception("Error during translation")
            return "Failed to translate the message due to an error."

    @classmethod
    def get_config_class(cls) -> type[BaseProxyConfig]:
        """
        Return the configuration class for this plugin.

        Returns:
            type[BaseProxyConfig]: The Config class for this plugin
        """
        return Config
