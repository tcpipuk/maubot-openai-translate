# OpenAI Translate Maubot Plugin

A (fairly) simple [Maubot](https://github.com/maubot/maubot) plugin using OpenAI's GPT models for quick and accurate translations in [Matrix](https://matrix.org/docs/chat_basics/matrix-for-im/) chat rooms.

OpenAI's GPT models incur a cost for queries, however even the cheapest models can excel at translation. It not only replicates the tone and style of the original text, but also attempts to understand the context, so the translation more accurately maintains the spirit of the original too.

## Usage Instructions

- **Direct Translation:** Use `!tr <language_code> <message>` to translate a specific message.
  - Example: `!tr fr Hello World` translates "Hello World" into French.
- **Reply Translation:** Reply to an existing message with `!tr <language_code>`, and the bot will reply to the same message in the chosen language.
  - Example: Replying with `!tr de` to a message translates it into German.

## Supported Languages

The plugin supports a wide array of languages, listed in the `languages.py` file with their respective ISO 639-1 two-letter codes. This expansive list includes commonly spoken languages like English, Spanish, French, as well as lesser-known ones, and you could customise to additional custom ones if required - I've added some IETF languages (e.g. `en-gb`, `fr-ca`, `pt-br`) to demonstrate how language variants can be added.

## Configuration and Setup

- **Prerequisites:** An active OpenAI API token is required for the bot's operation.
- **Configuration:** Enter your OpenAI credentials and configure bot settings in the Maubot instance tab. The settings include:
  - `bot.rate_limit`: The maximum number of translations a user can request per hour. Zero disables the limit.
  - `bot.rate_window`: The time frame, in seconds, for the rate limit (default is 3600 seconds, i.e. 1 hour).
  - `bot.rate_message`: The message displayed when a user exceeds the rate limit. Leaving it blank disables this message.
  - `bot.empty_message`: Custom message displayed when the bot receives a command without a message to translate.
  - `bot.unknown_message`: Message displayed when a user requests translation in an unrecognized language code.
  - `languages.codes`: A list of `co-de: Language Name` definitions to teach the bot new ways to translate (e.g. `en-cockney: Cockney English`).
  - `languages.replace_list`: Whether to replace the built-in list with the ones defined above, or just add/update the list with your changes.
  - `openai.api_key`: Your unique API key for accessing OpenAI's services.
  - `openai.custom_endpoint`: If you want to use another OpenAI Chat Completions compatible API, provide the full URL here, otherwise leave blank to use `https://api.openai.com/v1/chat/completions`.
  - `openai.model`: Specifies the GPT model for translations. Default is `gpt-3.5-turbo`.
  - `openai.max_tokens`: Sets the maximum number of tokens (words/pieces of words) for each translation response.
  - `openai.temperature`: Determines the 'creativity' level of translations. A lower temperature, like the default 0.4, provides more literal translations.
  - `openai.prompt`: The system prompt sent to OpenAI, instructing the model for translation tasks.
- **Deployment:** Deploy the bot in your Matrix rooms for seamless translation services.

**Note: OpenAI's API incurs costs. It's recommended to set a spending limit in your OpenAI account and monitor usage to manage expenses effectively.**

## License

The OpenAI Translate Maubot is distributed under the AGPLv3 license. For detailed licensing information, please refer to the `LICENSE` file.
