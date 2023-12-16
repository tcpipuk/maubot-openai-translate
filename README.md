# OpenAI Translate Maubot

A (fairly) simple [Maubot](https://github.com/maubot/maubot) plugin leveraging OpenAI's translation capabilities. This bot translates messages into a wide range of languages, supporting quick and accurate communication across language barriers.

## Features
- **Translation:** Utilizes OpenAI's advanced language models for accurate translations.
- **Multiple Languages:** Supports a comprehensive list of languages as defined in the `languages.py` file.
- **Easy-to-Use:** Simple commands for quick translations within Matrix rooms.

## Usage
- **Translation Command:** `!tr <language_code> <message>`
   - Translates the `<message>` into the specified `<language_code>`.
   - Example: `!tr fr Hello World` translates "Hello World" into French.
- **Reply Translation:** Reply to a message with `!tr <language_code>`
   - The bot will translate the replied-to message into the specified language.
   - Example: Replying to a message with `!tr es` translates the original message into Spanish.

## Supported Languages
The bot supports a variety of languages, each identified by a unique language code. Refer to the `languages.py` file for the full list of supported languages and their corresponding codes.

## Configuration
To use this plugin:
1. Ensure you have an OpenAI API token.
2. Set up the bot with the required OpenAI credentials in `maubot.yaml`.
3. Deploy the bot in your Matrix environment.

## License
This bot is distributed under the AGPLv3 license. See the `LICENSE` file for more details.
