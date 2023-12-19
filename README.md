# OpenAI Translate Maubot Plugin

A (fairly) simple [Maubot](https://github.com/maubot/maubot) plugin that uses OpenAI's GPT models to provide quick and accurate translations for [Matrix](https://matrix.org/docs/chat_basics/matrix-for-im/) chat rooms.

OpenAI's GPT models cost money to query, however even the cheapest models typically excel at translation, not only better replicating the tone/style of the original, but also understanding the context, so the translation more accurately maintains the spirit of the original too.

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
  - `openai.api_key`: Your API key for accessing OpenAI's services, the bot will not work without it.
  - `openai.model`: GPT model used for translations, the default is `gpt-3.5-turbo`.
  - `openai.max_tokens`: Provides an upper limit for translation length by setting the maximum number of tokens (words/pieces of words) in each response.
  - `openai.temperature`: Determines the 'creativity' level of translations. A lower temperature (like the default 0.4) ensures more literal translations.
  - `openai.prompt`: System prompt sent to OpenAI. The default is simple and reliable, but you may wish to modify it for your own needs.
- **Deployment:** Deploy the bot in your Matrix rooms, job done!

**Note: OpenAI's API costs money. Make sure to set a spending limit in your OpenAI account, and monitor usage to avoid any surprises.**

## License

The OpenAI Translate Maubot is distributed under the AGPLv3 license. Please refer to the `LICENSE` file for detailed licensing information.
