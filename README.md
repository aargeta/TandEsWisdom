# TandEsWisdom
This is da way. Learn here BITCHES

readme
This project generates short, surreal talking videos featuring “INSERT NAME HERE,” an otherworldly speaker who delivers bizarre, darkly comedic commands. The script uses several APIs and tools to:

Generate a surreal text snippet and accompanying TTS audio.
Create a lip-synced “talking head” video via DupDub.
Overlay a background video plus text.
Post the final video to Twitter automatically.
Key Features
GPT/Grok (OpenAI) – Generates the surreal snippet (SNIPPET) and longer TTS text (TTS), with a darkly comedic, edgy tone.
ElevenLabs – Converts the TTS text into synthesized speech (MP3).
DupDub – Produces a green-screen “talking” video of INSER NAME HERE based on the TTS audio.
FFmpeg – Composites multiple video layers, sets alpha channels, overlays text, and merges background audio.
Dropbox – Uploads the TTS MP3 files for external hosting (used by DupDub).
Twitter – Automatically uploads and posts the final video to the configured account using both Twitter’s v1.1 (for chunked media upload) and v2 (for tweeting).
Requirements
Python 3.9+ (or a recent 3.x version).

Dependencies (install via pip):

bash
Copy code
pip install requests dropbox tweepy openai python-dotenv
FFmpeg (and ffprobe) available on your system’s PATH.

A .env file containing your API credentials:

makefile
Copy code
XAI_API_KEY=...
ELEVENLABS_API_KEY=...
DUPDUB_API_KEY=...
DROPBOX_ACCESS_TOKEN=...

TWITTER_API_KEY=...
TWITTER_API_SECRET=...
TWITTER_ACCESS_TOKEN=...
TWITTER_ACCESS_SECRET=...
TWITTER_BEARER_TOKEN=...
How It Works
TTS Generation

The script calls Grok (OpenAI) to create a snippet (short directive) and a comedic TTS text.
The TTS text is then sent to ElevenLabs to produce an MP3 audio file.
DupDub

Uploads the TTS audio to Dropbox and uses that direct link.
Calls DupDub with the hosted audio and an image of INSERT NAME HERE.
Receives a green-screen lip-sync video.
FFmpeg Processing

Converts the green background to alpha (ProRes 4444).
Overlays INSERT NAME HERE onto a random background video.
Adds top and bottom text overlays.
Merges with a random background audio track, clipping to the TTS duration.
Twitter Post

Authenticates both Tweepy v2 (for tweeting) and v1.1 (for chunked video upload).
Uploads the final MP4.
Posts the tweet with no text (or minimal text).
Usage
Install all required dependencies and place ffmpeg in your PATH.
Create and fill in a .env file with your credentials.
Run the script:
bash
Copy code
python INSERT NAME HERE_main.py
The script loops, generating a new surreal talking video each run, then sleeps 5 seconds before repeating.
License
This project is for demonstration/educational purposes. Check the license terms of the various APIs (OpenAI, ElevenLabs, DupDub, Dropbox, Twitter) for usage constraints. Use responsibly and have fun!