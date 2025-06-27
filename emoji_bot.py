import asyncio
from base64 import b64encode
import logging
import re
from typing import Optional

import discord
from discord.ext import commands
import httpx
from openai import AsyncOpenAI
import yaml


def load_config(filename: str = "config.yaml") -> dict:
    """Load configuration from YAML file"""
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        logging.error(f"Config file {filename} not found!")
        raise
    except yaml.YAMLError as e:
        logging.error(f"Error parsing config file: {e}")
        raise


def setup_logging(log_level: str = "INFO"):
    """Setup logging configuration"""
    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )


class EmojiReactBot:
    def __init__(self, config: dict):
        self.config = config
        self.openai_client = AsyncOpenAI(api_key=config['openai_api_key'])
        self.httpx_client = httpx.AsyncClient()
        
        # Check if model supports vision
        self.supports_vision = self.is_vision_model(config['model'])
        
        # Discord bot setup
        intents = discord.Intents.default()
        intents.message_content = True
        
        self.bot = commands.Bot(
            command_prefix=None,  # No commands needed
            intents=intents,
            help_command=None
        )
        
        # Setup event handlers
        self.bot.event(self.on_ready)
        self.bot.event(self.on_message)
    
    def is_vision_model(self, model: str) -> bool:
        """Check if the model supports vision/image processing"""
        vision_indicators = ("gpt-4", "gpt-4o", "gpt-4.1", "vision", "claude", "gemini")
        return any(indicator in model.lower() for indicator in vision_indicators)
    
    def should_ignore_message(self, message: discord.Message) -> bool:
        """Check if message should be ignored based on content type"""
        content = message.content.strip()
        
        # Ignore bot messages if configured
        if self.config.get('ignore_bots', True) and message.author.bot:
            return True
            
        # Skip empty messages (unless they have images/embeds)
        if not content and not message.embeds and not message.attachments:
            return True
            
        # Ignore system messages
        if message.type != discord.MessageType.default and message.type != discord.MessageType.reply:
            return True
            
        return False
    
    async def on_ready(self):
        """Called when bot is ready"""
        logging.info(f"Emoji React Bot logged in as {self.bot.user}")
        logging.info(f"Bot ID: {self.bot.user.id}")
        logging.info(f"Vision support: {'✅ Enabled' if self.supports_vision else '❌ Disabled'} (model: {self.config['model']})")
        if self.config.get('client_id'):
            logging.info(f"Invite URL: https://discord.com/oauth2/authorize?client_id={self.config['client_id']}&permissions=2048&scope=bot")
    
    async def on_message(self, message: discord.Message):
        """Handle incoming messages"""
        # Check if channel is whitelisted
        if message.channel.id not in self.config.get('whitelisted_channels', []):
            return
        
        # Check if message should be ignored
        if self.should_ignore_message(message):
            logging.debug(f"Ignoring message from {message.author}: {message.content[:50]}...")
            return
        
        logging.info(f"Processing message from {message.author} in #{message.channel.name}: {message.content[:100]}")
        
        try:
            # Check if tone is appropriate for emoji reactions (if enabled)
            if self.config.get('check_tone_appropriateness', True):
                is_appropriate = await self.is_tone_appropriate(message)
                if not is_appropriate:
                    logging.debug(f"Skipping emoji reaction - inappropriate tone detected")
                    return
            
            # Get emoji from LLM (with image support)
            emoji = await self.get_emoji_reaction(message)
            if emoji:
                await self.add_reaction(message, emoji)
            else:
                logging.warning("No valid emoji returned from LLM")
        except Exception as e:
            logging.error(f"Error processing message: {e}")
    
    async def get_emoji_reaction(self, message: discord.Message) -> Optional[str]:
        """Get emoji reaction from OpenAI with image support"""
        try:
            # Prepare message content with images if vision is supported
            content = await self.prepare_message_content(message)
            
            response = await self.openai_client.chat.completions.create(
                model=self.config['model'],
                messages=[
                    {"role": "system", "content": self.config['system_prompt']},
                    {"role": "user", "content": content}
                ],
                max_tokens=10,  # Keep it short - just need one emoji
                temperature=0.7
            )
            
            emoji_response = response.choices[0].message.content.strip()
            logging.debug(f"LLM response: {emoji_response}")
            
            # Extract emoji from response
            return self.extract_emoji(emoji_response)
            
        except Exception as e:
            logging.error(f"Error calling OpenAI API: {e}")
            return None
    
    async def prepare_message_content(self, message: discord.Message):
        """Prepare message content with text and images for OpenAI Vision API"""
        content_parts = []
        
        # Add text content if available
        if message.content.strip():
            content_parts.append({"type": "text", "text": message.content.strip()})
        
        # Add images if vision is supported and images are present
        if self.supports_vision and message.attachments:
            image_attachments = [att for att in message.attachments 
                               if att.content_type and att.content_type.startswith("image")]
            
            if image_attachments:
                logging.info(f"Processing {len(image_attachments)} image(s)")
                
                # Download and encode images
                for attachment in image_attachments[:3]:  # Limit to 3 images to avoid token limits
                    try:
                        response = await self.httpx_client.get(attachment.url)
                        if response.status_code == 200:
                            image_data = b64encode(response.content).decode('utf-8')
                            content_parts.append({
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{attachment.content_type};base64,{image_data}"
                                }
                            })
                            logging.debug(f"Added image: {attachment.filename}")
                    except Exception as e:
                        logging.error(f"Failed to process image {attachment.filename}: {e}")
        
        # Fallback content if nothing was added
        if not content_parts:
            if message.embeds:
                content_parts.append({"type": "text", "text": "[embed content]"})
            else:
                content_parts.append({"type": "text", "text": "[message]"})
        
        # Return single text content or multimodal content
        return content_parts[0]["text"] if len(content_parts) == 1 and content_parts[0]["type"] == "text" else content_parts
    
    async def is_tone_appropriate(self, message: discord.Message) -> bool:
        """Check if the message tone is appropriate for emoji reactions"""
        try:
            # Prepare simplified content for tone analysis (text only for speed)
            content = message.content.strip() or "[image/media content]"
            
            tone_check_prompt = """You are a tone classifier for emoji reactions. Determine if the message tone is appropriate for adding emoji reactions.

RESPOND WITH ONLY: YES or NO

Appropriate for emoji reactions:
- Casual conversation, jokes, memes
- Sharing content with context/enthusiasm
- Questions, discussions, observations
- Positive, neutral, or lighthearted content
- Social media style posts

NOT appropriate for emoji reactions:
- Solo links without context or commentary
- Minimal content with ambiguous intent
- Serious discussions about sensitive topics
- Arguments, conflicts, heated debates
- Personal problems, venting, emotional distress
- Bad news, emergencies, urgent matters
- Professional/formal communications
- Messages asking for help with serious issues

Message to classify:"""

            response = await self.openai_client.chat.completions.create(
                model=self.config.get('tone_model', 'gpt-4o-mini'),  # Use faster model for classification
                messages=[
                    {"role": "system", "content": tone_check_prompt},
                    {"role": "user", "content": content}
                ],
                max_tokens=5,
                temperature=0.1  # Low temperature for consistent classification
            )
            
            result = response.choices[0].message.content.strip().upper()
            is_appropriate = result.startswith("YES")
            
            logging.debug(f"Tone check result: {result} -> {'Appropriate' if is_appropriate else 'Inappropriate'}")
            return is_appropriate
            
        except Exception as e:
            logging.error(f"Error in tone classification: {e}")
            # Default to allowing reactions if classification fails
            return True
    
    def extract_emoji(self, text: str) -> Optional[str]:
        """Extract first character as emoji - keep it simple"""
        if not text:
            return None
        
        # Just return the first character - if it's not an emoji, Discord will reject it
        # Let Discord handle the validation instead of complex regex
        return text.strip()[0] if text.strip() else None
    
    async def add_reaction(self, message: discord.Message, emoji: str):
        """Add emoji reaction to message"""
        try:
            await message.add_reaction(emoji)
            logging.info(f"Added reaction {emoji} to message from {message.author}")
        except discord.Forbidden:
            logging.error(f"Missing permissions to add reactions in #{message.channel.name}")
        except discord.NotFound:
            logging.error(f"Emoji {emoji} not found or message deleted")
        except discord.InvalidArgument:
            logging.error(f"Invalid emoji format: {emoji}")
        except discord.HTTPException as e:
            logging.error(f"Failed to add reaction {emoji}: {e}")
        except Exception as e:
            logging.error(f"Unexpected error adding reaction: {e}")
    
    async def start(self):
        """Start the bot"""
        try:
            await self.bot.start(self.config['bot_token'])
        except KeyboardInterrupt:
            logging.info("Bot shutdown requested")
        except Exception as e:
            logging.error(f"Bot error: {e}")
        finally:
            await self.bot.close()
            await self.openai_client.close()
            await self.httpx_client.aclose()


async def main():
    """Main function"""
    # Load configuration
    config = load_config()
    
    # Setup logging
    setup_logging(config.get('log_level', 'INFO'))
    
    # Validate required config
    required_keys = ['bot_token', 'openai_api_key']
    for key in required_keys:
        if not config.get(key):
            logging.error(f"Missing required config: {key}")
            return
    
    if not config.get('whitelisted_channels'):
        logging.warning("No whitelisted channels configured - bot won't react to any messages")
    
    # Create and start bot
    bot = EmojiReactBot(config)
    await bot.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")