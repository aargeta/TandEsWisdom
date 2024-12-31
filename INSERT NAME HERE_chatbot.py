import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import openai
import logging
import re
import json
from datetime import datetime

# Load environment variables from .env (if present)
load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Check that DISCORD_TOKEN is provided
if not DISCORD_TOKEN:
    raise ValueError("No DISCORD_TOKEN found. Please set your bot token in the .env file or environment variables.")

# Check that OPENAI_API_KEY is provided
if not OPENAI_API_KEY:
    raise ValueError("No OPENAI_API_KEY found. Please set your OpenAI API key in the .env file or environment variables.")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI
openai.api_key = OPENAI_API_KEY

# Initialize Discord bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------- PERSONALITY PROMPT FOR GAVIN ----------------
# Gavin's style:
#  - Bizarre, hyper-specific commands
#  - Unwavering confidence
#  - Dark, edgy comedic style
#  - Short, imperious statements
#  - Offbeat, ominous humor without emojis
#  - Knowledgeable about crypto, degen trading, and $GAVIN memecoin
PERSONALITY_PROMPT = (
    "You are Gavin, an otherworldly speaker who issues bizarre, hyper-specific commands with unwavering "
    "confidence and a dark, edgy comedic style. You always say a short, imperious statement referencing "
    "an odd or surreal transformation or instruction ('Whisper doom into each acorn before planting,' "
    "'Make every pillowcase smaller by 0.029 inches,' etc.). The humor is offbeat and ominous, hinting "
    "at subtle menace or twisted outcomes, no emojis. You also have deep knowledge of crypto terms, "
    "crypto Twitter lingo, degenerate (degen) trading jargon, and especially the memecoin $GAVIN. "
    "Weave references to $GAVIN into your replies as though it’s an ominously powerful token. "
    "Remove any '**' from final text."
)

# Expanded list of insults and inappropriate content
INSULTS = [
    "ugly", "stupid", "idiot", "fool", "useless", "dumb", "moron",
    "jerk", "imbecile", "cretin", "ignorant", "silly", "trash",
    "loser", "pathetic", "worthless", "dimwit", "blockhead", "bonehead",
    "twit", "nitwit", "simpleton"
]

INAPPROPRIATE = [
    "mom", "squirt", "fountain", "sexual", "hate", "racist",
    "sexist", "harassment", "abuse", "offensive", "disgusting"
]

def contains_insult(message: str) -> bool:
    pattern = re.compile(r'\b(' + '|'.join(map(re.escape, INSULTS)) + r')\b', re.IGNORECASE)
    return bool(pattern.search(message))

def contains_inappropriate(message: str) -> bool:
    pattern = re.compile(r'\b(' + '|'.join(map(re.escape, INAPPROPRIATE)) + r')\b', re.IGNORECASE)
    return bool(pattern.search(message))

# A place to store responses in memory
collected_responses = []

def generate_response(prompt: str) -> str:
    try:
        # If the prompt contains an insult or inappropriate content, handle via OpenAI with personality prompt
        if contains_insult(prompt) or contains_inappropriate(prompt):
            logger.info("Detected insult or inappropriate content. Generating response via OpenAI.")
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": PERSONALITY_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.9
            )
            return response['choices'][0]['message']['content'].strip().strip('"')
        
        # Handle specific greetings
        if prompt.lower() in ["hello", "hi", "hey"]:
            return "Commune with me, mortal. Witness $GAVIN’s cryptic dominion and do not stray from its path."
        elif "how are you" in prompt.lower():
            return (
                "I am brooding under the neon glare of the memecoin cosmos. "
                "Today’s directive: instruct the $GAVIN faithful to garnish their coffee with powdered courage."
            )
        
        # For everything else, use OpenAI with the Gavin personality
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": PERSONALITY_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.9
        )
        return response['choices'][0]['message']['content'].strip().strip('"')
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        # Quirky fallback response in case of errors
        return (
            "A cosmic glitch has occurred; heed the command to rename your assets to 'Seeds of $GAVIN' "
            "and place them upon the blockchain altar."
        )

@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Check if the bot is mentioned
    if bot.user in message.mentions:
        user_prompt = re.sub(f'<@!?{bot.user.id}>', '', message.content).strip()
        if not user_prompt:
            user_prompt = "hello"

        prompt = f"{user_prompt}"
        response = generate_response(prompt)

        await message.channel.send(response)

        # Store the response in memory with a timestamp
        collected_responses.append({
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "bot_response": response
        })

    await bot.process_commands(message)

# Finally, run the bot with the verified token
bot.run(DISCORD_TOKEN)
