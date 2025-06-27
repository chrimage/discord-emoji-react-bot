# Discord Emoji React Bot

A delightfully silly Discord bot that uses AI to react to every message with contextually appropriate emojis. Because why should humans have all the fun reacting to things? 🤖

*Yes, this is absolutely ridiculous. No, we don't care. It's surprisingly entertaining watching an AI try to summarize your conversations in emoji form.*

## Features

- 🤖 Uses GPT-4o-mini/gpt-4.1-nano to generate contextual emoji reactions
- 👀 **Image recognition** - Reacts to photos, memes, and visual content
- 🧠 **AI tone classifier** - Knows when reactions are appropriate vs awkward
- 📝 Channel whitelist system - only reacts in explicitly enabled channels  
- 🎯 Simple emoji extraction - let Discord handle validation
- 🤝 Optional bot interaction - can react to other bots too
- 🛡️ Built-in error handling and logging
- ⚡ Lightweight - ~300 lines of code

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Create Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to "Bot" section and create a bot
4. Copy the bot token
5. Copy the client ID from "General Information"

### 3. Get OpenAI API Key

1. Go to [OpenAI API](https://platform.openai.com/api-keys)
2. Create a new API key

### 4. Configure the Bot

Edit `config.yaml`:

```yaml
bot_token: "YOUR_DISCORD_BOT_TOKEN"
client_id: "YOUR_DISCORD_CLIENT_ID"
openai_api_key: "YOUR_OPENAI_API_KEY"
model: "gpt-4o-mini"  # or "gpt-4.1-nano" for vision support
whitelisted_channels:
  - 123456789012345678  # Replace with actual channel IDs
```

### 5. Get Channel IDs

1. Enable Developer Mode in Discord (Settings > Advanced > Developer Mode)
2. Right-click on channels where you want the bot to react
3. Select "Copy Channel ID"
4. Add these IDs to the `whitelisted_channels` list in config.yaml

### 6. Invite Bot to Server

Use the invite URL that appears in the logs when you start the bot, or create one manually:
`https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=2048&scope=bot`

The bot only needs "Add Reactions" permission (2048).

## Usage

```bash
python emoji_bot.py
```

The bot will:
- Listen for messages in whitelisted channels
- **Check tone appropriateness** using AI classifier (avoids awkward reactions)
- Analyze text and images using OpenAI's Vision API  
- Generate contextually appropriate emoji reactions
- React to the original message with that emoji

## How the AI Classifier Works

The bot makes **two AI calls** per message for maximum social awareness:

1. **Tone Classification** (fast) - "Is this appropriate for emoji reactions?"
2. **Emoji Generation** (if appropriate) - "What emoji fits this content?"

**✅ Will React To:**
- Casual conversation and jokes
- Sharing content with enthusiasm ("check this out!")
- Social media style posts
- Questions and discussions with context

**❌ Will Skip (only wildly inappropriate):**
- Serious emergencies or crisis situations
- Genuine distress or calls for help
- Heated arguments or conflicts
- Bad news or tragedy announcements

**✅ Everything Else Gets Reactions:**
- Casual chat, links, questions, sharing
- Jokes, memes, discussions
- Professional communication (why not?)
- Short messages, ambiguous content

## Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `model` | OpenAI model to use (vision models support images) | `gpt-4o-mini` |
| `system_prompt` | Instructions for emoji generation | Predefined prompt |
| `log_level` | Logging verbosity | `INFO` |
| `ignore_bots` | Skip messages from other bots | `true` |
| `check_tone_appropriateness` | Use AI to avoid reacting to emergencies/distress (defaults to YES) | `true` |
| `tone_model` | Model for tone classification (separate from main model) | `gpt-4o-mini` |

## Logs

The bot provides detailed logging:
- INFO: General operation messages
- WARNING: Non-critical issues
- ERROR: Failed operations
- DEBUG: Detailed debugging info (set `log_level: DEBUG`)

## Why Does This Exist?

Good question! Sometimes you just want to watch an AI have opinions about your Discord conversations. It's like having a very enthusiastic friend who only communicates in emoji reactions, but they're powered by a language model that costs money to run. 

The bot is surprisingly good at:
- 😂 Recognizing jokes and memes
- 😍 Appreciating food photos  
- 🤔 Reacting to philosophical discussions
- 🔥 Hyping up achievements
- 😬 Sensing awkward moments

Is it practical? Absolutely not. Is it entertaining? Surprisingly yes.

## License

MIT License