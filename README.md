# OpenAI Translate Maubot Plugin

A (fairly) simple [Maubot](https://github.com/maubot/maubot) plugin that uses OpenAI's GPT models to provide quick and accurate translations in a more natural style than traditional translation services.

## Usage Instructions

- **Direct Translation:** Use `!tr <language_code> <message>` to translate a specific message.
  - Example: `!tr fr Hello World` will translate "Hello World" into French.
- **Reply Translation:** Reply to an existing message with `!tr <language_code>`, and the bot will reply to the same message in the chosen language.
  - Example: Replying with `!tr de` to a message will translate it into German.

## Supported Languages

A comprehensive list of supported languages and their respective ISO 639-1 two-letter codes can be found in the `languages.py` file. This includes widely spoken languages like English, Spanish, French, as well as less commonly used languages, providing broad accessibility.

## Configuration and Setup

- **Prerequisites:** An active OpenAI API token is required for the bot's operation.
- **Configuration:** Enter your OpenAI credentials in the Instance tab in Maubot and tweak the other OpenAI values according to your needs.
- **Deployment:** Deploy the bot in your Matrix rooms to start enjoying seamless translation services.

**Note: OpenAI's API costs money. Make sure to set a spending limit in your OpenAI account, and monitor usage to avoid any surprises.**

## License

The OpenAI Translate Maubot is distributed under the AGPLv3 license. Please refer to the `LICENSE` file for detailed licensing information.
