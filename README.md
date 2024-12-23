# OpenAI Translate Maubot Plugin

1. [Usage Instructions](#usage-instructions)
2. [Supported Languages](#supported-languages)
3. [Prerequisites](#prerequisites)
4. [Releases](#releases)
5. [Configuration](#configuration)
6. [License](#license)

A (fairly) simple [Maubot](https://github.com/maubot/maubot) plugin that uses Large Language Models
for quick and accurate translations in [Matrix](https://matrix.org/docs/chat_basics/matrix-for-im/)
chat rooms.

Modern LLMs excel at translation tasks, as they not only replicate the tone and style of the
original text but also attempt to understand the context, helping maintain the spirit of the
original message.

The plugin _should_ work with any service offering an OpenAI-compatible Chat Completions API,
including:

- OpenAI's own GPT models (the default configuration)
- Self-hosted solutions (e.g. [LocalAI](https://localai.io/))
- Alternative providers (e.g. [Claude](https://docs.anthropic.com/claude/docs/getting-started-with-claude)
  or [Azure OpenAI](https://learn.microsoft.com/en-us/azure/ai-services/openai/reference))

**Note:** If you do not self-host an LLM, you will likely be charged for the use of the LLM API.
Suggested models like `gpt-4o-mini` are very cheap, but these costs can add up if you make your bot
public, inviteable in rooms, and/or don't set rate limits.

## Usage Instructions

- **Direct Translation:** Use `!tr <language_code> <message>` to translate a specific message.
  - Example: `!tr fr Hello World` translates "Hello World" into French.
- **Reply Translation:** Reply to an existing message with `!tr <language_code>`, and the bot will
  reply to the same message in the chosen language.
  - Example: Replying with `!tr de` to a message translates it into German.

## Supported Languages

The plugin supports a wide array of languages, listed in the `languages.py` file with their
respective ISO 639-1 two-letter codes. This expansive list includes commonly spoken languages like
English, Spanish, French, as well as lesser-known ones. You can customise it to include additional
custom ones if required. For example, I have added some IETF languages (e.g. `en-gb`, `fr-ca`,
`pt-br`) to demonstrate how language variants can be added.

## Prerequisites

- An active OpenAI API token is required for the bot's operation.

## Releases

You can find the latest `.mdp` file to upload to your Maubot instance on the
[releases page](https://github.com/tcpipuk/maubot-openai-translate/releases).

## Configuration

Enter your OpenAI credentials and configure bot settings in the Maubot instance tab. The settings include:

- `bot.rate_limit`: The maximum number of translations a user can request per hour. On by default
  to help protect your wallet from potential abuse, but zero disables the limit.
- `bot.rate_window`: The time frame, in seconds, for the rate limit (default is 3600 seconds,
  1 hour).
- `bot.rate_message`: The message displayed when a user exceeds the rate limit. Leaving it blank
  disables this message.
- `bot.empty_message`: Custom message displayed when the bot receives a command without a message
  to translate.
- `bot.unknown_message`: Message displayed when a user requests translation in an unrecognised
  language code.
- `bot.auth_message`: Custom message displayed when authentication with the LLM API fails.
- `bot.bot_rate_message`: Message shown when the bot hits the LLM API's rate limits.
- `bot.network_message`: Message displayed when network errors occur.
- `bot.unexpected_message`: Message shown for unexpected translation errors.
- `languages.codes`: A list of `co-de: Language Name` options to tell the bot extra ways to
  translate (e.g. `en-cockney: Cockney English`).
- `languages.replace_list`: Whether to replace the built-in list with the ones defined above,
  or just add/update the list with your changes.
- `openai.api_key`: Your unique API key for accessing OpenAI's services.
- `openai.custom_endpoint`: If you want to use another OpenAI Chat Completions compatible API,
  provide the full URL here (e.g. `http://localhost:8080/v1/chat/completions` for LocalAI),
  otherwise leave blank to use `https://api.openai.com/v1/chat/completions`.
- `openai.model`: Specifies the GPT model for translations. Default is `gpt-4o-mini`, but you
  should set this to match your chosen provider's model names (e.g. `gpt-3.5-turbo` for OpenAI,
  or `ggml-gpt4all-j` for LocalAI).
- `openai.max_tokens`: Sets the maximum number of tokens (words/pieces of words) for each
  translation response.
- `openai.temperature`: Determines the 'creativity' level of translations. The default (0.4)
  provides fairly realistic translations, whereas a lower one (e.g. 0.1) would be more literal,
  but also more robotic.
- `openai.prompt`: The system prompt sent to OpenAI, instructing the model for translation tasks.

**Note:** While OpenAI's API incurs costs, you can use alternative providers like LocalAI to run
models locally or choose other commercial providers. It's still recommended to set appropriate
rate limits to manage resource usage effectively.

## License

The OpenAI Translate Maubot is distributed under the AGPLv3 license. For detailed licensing
information, please refer to the `LICENSE` file.
