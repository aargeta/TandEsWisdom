import os
import sys
import time
import json
import random
import logging
import requests
import dropbox
import subprocess
import tweepy
from datetime import datetime
from dotenv import load_dotenv
import re

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler("gavin_main.log", encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_format = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
file_handler.setFormatter(file_format)
logger.addHandler(file_handler)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_format = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
console_handler.setFormatter(console_format)
logger.addHandler(console_handler)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(SCRIPT_DIR, ".env")
load_dotenv(env_path)

# -------------------------------------------------
# xAI
# -------------------------------------------------
import openai

XAI_API_KEY = os.getenv("XAI_API_KEY")
openai.api_key  = XAI_API_KEY
openai.api_base = "https://api.x.ai/v1"
GROK_MODEL_NAME = "grok-2-1212"

# -------------------------------------------------
# ElevenLabs
# -------------------------------------------------
ELEVENLABS_API_KEY      = os.getenv("ELEVENLABS_API_KEY")
GAVIN_VOICE_ID          = "g5CIjZEefAph4nQFvHAz"
ELEVENLABS_MODEL_ID     = "eleven_turbo_v2"
ELEVENLABS_STABILITY    = 0.5
ELEVENLABS_SIMILARITY   = 0.75
ELEVENLABS_EXAGGERATION = 0.0

# -------------------------------------------------
# DupDub
# -------------------------------------------------
DUPDUB_API_KEY         = os.getenv("DUPDUB_API_KEY")
DUPDUB_DETECT_FACE     = "https://moyin-gateway.dupdub.com/tts/v1/photoProject/detectAvatar"
DUPDUB_CREATE_PROJECT  = "https://moyin-gateway.dupdub.com/tts/v1/photoProject/createMulti"
DUPDUB_CHECK_PROJECT   = "https://moyin-gateway.dupdub.com/tts/v1/photoProject/"

# -------------------------------------------------
# Dropbox
# -------------------------------------------------
DROPBOX_ACCESS_TOKEN = os.getenv("DROPBOX_ACCESS_TOKEN")

# -------------------------------------------------
# Twitter
# -------------------------------------------------
TWITTER_API_KEY       = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET    = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN  = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET")
TWITTER_BEARER_TOKEN  = os.getenv("TWITTER_BEARER_TOKEN")

# -------------------------------------------------
# Frame/Overlay Constants
# (Background is 720×1280)
# -------------------------------------------------
# Gavin => 749×596
# We'll center him => (720 - 749)//2, (1280 - 596)//2
GAVIN_SCALE_W    = 749
GAVIN_SCALE_H    = 596
GAVIN_OVERLAY_X  = (720 - 749)//2  # -14 => some clipping horizontally
GAVIN_OVERLAY_Y  = (1280 - 596)//2 # 342

# Top text => y=140 (was 160, moved 20 px up)
# bigger font => 64
TOP_TEXT_Y       = 140
TOP_TEXT_FONT    = 64

# Bottom text => y=1050 (instead of 1180)
# bigger font => 120
BOTTOM_TEXT_Y    = 1050
BOTTOM_TEXT_FONT = 120

MAX_LINES        = 5
AUDIO_RATIO      = 0.1

SCRIPT_DIR       = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR       = SCRIPT_DIR

# 5 background videos => vid1..vid5
BGS_DIR          = r"C:\Users\ethan\Documents\memecoins\Gavin\vids"

# 5 random audios => audio1..audio5 => random
BACKGROUND_AUDIO_DIR = r"C:\Users\ethan\Documents\memecoins\Gavin\background audio"

# We'll aim to keep text under ~660 px wide (since 720 wide BG)
MAX_TEXT_PIXEL_WIDTH = 660

SURR_PERSONALITY_PROMPT = """
You are Gavin, an otherworldly speaker who issues bizarre, hyper-specific commands with unwavering confidence and a dark, edgy comedic style.
Your top text is always a short, imperious statement referencing an odd or surreal transformation or instruction 
(“Whisper doom into each acorn before planting,” “Make every pillowcase smaller by 0.029 inches,” etc.).
The humor is offbeat and ominous, hinting at subtle menace or twisted outcomes, no memecoin references, no emojis.

We want:
SNIPPET: 1 short imperative or statement (like 'Whisper doom into each acorn.').
TTS: ~1-2 sentences, leaning dark comedic details with a subtle threatening or ominous flair.
Remove any '**' from final text.
"""

DUPDUB_IMAGE_URL = "https://i.imgur.com/BqIPkWn.png"
GAVIN_JSON_PATH  = os.path.join(SCRIPT_DIR, "Gavin.JSON")

# -------------------------------------------------
# Logging/JSON
# -------------------------------------------------
def load_logs_for_influence():
    if not os.path.isfile(GAVIN_JSON_PATH):
        return ""
    try:
        with open(GAVIN_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not data:
                return ""
            recent = data[-3:] if len(data) > 3 else data
            lines = []
            for entry in recent:
                if "bot_response" in entry:
                    lines.append(entry["bot_response"])
            return " ".join(lines)
    except:
        return ""

# -------------------------------------------------
# FFmpeg
# -------------------------------------------------
def run_ffmpeg(cmd):
    logger.info("FFmpeg => %s", " ".join(cmd))
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg => {e}")
        return False

def get_media_duration(file_path):
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(res.stdout.strip())
    except:
        return 0.0

# -------------------------------------------------
# Text Wrapping
# -------------------------------------------------
def measure_line_width(line_str, font_size):
    return len(line_str) * 0.65 * font_size

def snippet_wrap_auto(snippet, font_size, max_pixel_width=660, max_lines=5):
    words = snippet.split()
    lines = []
    current_line = []

    for w in words:
        test_line = current_line + [w]
        test_str  = " ".join(test_line)
        width_est = measure_line_width(test_str, font_size)
        if width_est > max_pixel_width:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [w]
            if len(lines) >= max_lines:
                break
        else:
            current_line = test_line
        if len(lines) >= max_lines:
            break

    if current_line and len(lines) < max_lines:
        lines.append(" ".join(current_line))
    return lines[:max_lines]

# -------------------------------------------------
# openAI / Grok
# -------------------------------------------------
import openai

def generate_surreal_text():
    influences = load_logs_for_influence()
    prompt = SURR_PERSONALITY_PROMPT + f"\nRecent influences: {influences}\n"
    try:
        resp = openai.ChatCompletion.create(
            model=GROK_MODEL_NAME,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user",   "content": "Generate comedic snippet + TTS text now."}
            ],
            max_tokens=300,
            temperature=0.9
        )
        raw_text = resp["choices"][0]["message"]["content"].strip()
        match = re.search(r"SNIPPET:\s*(.*)TTS:\s*(.*)", raw_text, flags=re.DOTALL)
        if match:
            snippet = match.group(1).replace("**", "").strip()
            tts     = match.group(2).replace("**", "").strip()
        else:
            snippet = "Summon cosmic daisies quickly."
            tts     = "Yes, daisies swirl among us. It's cosmic law!"
        # Force snippet => single line
        first_sentence = re.split(r"[.!?]", snippet)[0].strip() + "."
        return first_sentence, tts
    except Exception as e:
        logger.error(f"xAI => {e}")
        return ("Invoke cosmic bananas now.", "Yes, let them swirl among us in cosmic wonder!")

# -------------------------------------------------
# ElevenLabs TTS
# -------------------------------------------------
def generate_tts(tts_text, out_mp3):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{GAVIN_VOICE_ID}"
    headers = {
        "Accept": "audio/mpeg",
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "text": tts_text,
        "model_id": ELEVENLABS_MODEL_ID,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style_exaggeration": 0.0
        }
    }
    try:
        r = requests.post(url, json=data, headers=headers, timeout=30)
        if r.status_code == 200:
            with open(out_mp3, "wb") as f:
                f.write(r.content)
            logger.info(f"TTS => {out_mp3}")
            return True
        else:
            logger.error(f"ElevenLabs => {r.status_code}: {r.text}")
            return False
    except Exception as e:
        logger.error(f"TTS => {e}")
        return False

# -------------------------------------------------
# Dropbox
# -------------------------------------------------
def upload_to_dropbox(local_file):
    from dropbox import Dropbox, files
    if not DROPBOX_ACCESS_TOKEN:
        logger.error("No dropbox => skip upload.")
        return None
    dbx = Dropbox(DROPBOX_ACCESS_TOKEN)
    base_name = os.path.basename(local_file)
    try:
        with open(local_file, "rb") as f:
            dbx.files_upload(f.read(), f"/{base_name}", mode=files.WriteMode.add)
        link = dbx.sharing_create_shared_link_with_settings(f"/{base_name}")
        url  = link.url
        direct= url.replace("www.dropbox.com","dl.dropboxusercontent.com").replace("?dl=0","")
        logger.info(f"Dropbox => {direct}")
        return direct
    except Exception as e:
        logger.error(f"Dropbox => {e}")
        return None

# -------------------------------------------------
# DupDub
# -------------------------------------------------
def detect_face_dup(image_url):
    headers = {"dupdub_token": DUPDUB_API_KEY, "Content-Type": "application/json"}
    data = {"photoUrl": image_url}
    try:
        resp = requests.post(DUPDUB_DETECT_FACE, json=data, headers=headers)
        if resp.status_code == 200:
            j = resp.json()
            if j.get("code") == 200 and j.get("data"):
                boxes = j["data"].get("boxes", [])
                if boxes:
                    logger.info(f"DupDub face => {boxes[0]}")
                    return boxes[0]
    except Exception as e:
        logger.error(f"detectDup => {e}")
    return None

def create_dup_project(image_url, audio_url, box):
    headers = {"dupdub_token": DUPDUB_API_KEY, "Content-Type": "application/json"}
    data = {
        "photoUrl": image_url,
        "info": [{"audioUrl": audio_url, "box": box}],
        "watermark": 0,
        "useSr": False
    }
    for attempt in range(3):
        r = requests.post(DUPDUB_CREATE_PROJECT, json=data, headers=headers)
        if r.status_code == 200:
            j = r.json()
            if j.get("code") == 200:
                pid = j["data"].get("id")
                logger.info(f"createMulti => pid={pid}")
                return pid
        time.sleep(2)
    return None

def poll_dup_project(pid):
    headers = {"dupdub_token": DUPDUB_API_KEY}
    url = DUPDUB_CHECK_PROJECT + str(pid)
    while True:
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            j = r.json()
            st = j["data"].get("executeStatus")
            logger.info(f"dup status => {st}")
            if st == 2:
                return j["data"].get("videoUrl")
            elif st == 3:
                logger.error("dup => fail code=3")
                return None
            else:
                logger.info("still => 5s")
        else:
            logger.error(f"poll => {r.status_code}: {r.text}")
            return None
        time.sleep(5)

def download_dup_video(url, out_path):
    try:
        r = requests.get(url, stream=True, timeout=30)
        if r.status_code == 200:
            with open(out_path, "wb") as f:
                for chunk in r.iter_content(1024):
                    if chunk:
                        f.write(chunk)
            logger.info(f"dupdub => {out_path}")
            return True
    except Exception as e:
        logger.error(f"download => {e}")
    return False

def create_dupdup_talking_video(image_url, audio_url, out_path):
    face_box = detect_face_dup(image_url)
    if not face_box:
        return False
    pid = create_dup_project(image_url, audio_url, face_box)
    if not pid:
        return False
    vurl = poll_dup_project(pid)
    if not vurl:
        return False
    return download_dup_video(vurl, out_path)

# -------------------------------------------------
# Green->Alpha->Overlay
# -------------------------------------------------
def convert_to_alpha(green_mp4, out_mov):
    cmd = [
        "ffmpeg", "-y",
        "-i", green_mp4,
        "-vf", f"chromakey=0x1b9c21:0.15:0.0,format=rgba,scale=749:596",
        "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le",
        out_mov
    ]
    return run_ffmpeg(cmd)

def overlay_alpha(bg_mp4, alpha_mov, out_mp4):
    # center horizontally => x=(720-749)//2 => -14
    # center vertically => y=(1280-596)//2 => 342
    cmd = [
        "ffmpeg", "-y",
        "-i", bg_mp4,
        "-i", alpha_mov,
        "-filter_complex", "[0:v][1:v]overlay=-14:342:format=auto",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        out_mp4
    ]
    return run_ffmpeg(cmd)

# -------------------------------------------------
# Final Text Overlay
# -------------------------------------------------
def overlay_text(bg_mp4, out_mp4, snippet, bottom_str):
    snippet_lines = snippet_wrap_auto(snippet, font_size=64, max_pixel_width=660, max_lines=5)

    fs_top = 64
    line_h = fs_top * 1.2
    filters = []

    # top text => y=140
    y_cur = 140
    for ln in snippet_lines:
        safe_txt = ln.replace("'", "\\'")
        draw_snippet = (
            f"drawtext=fontfile=Impact.ttf:"
            f"fontsize={fs_top}:"
            f"fontcolor=white:borderw=4:bordercolor=black:"
            f"x=(main_w-text_w)/2:"
            f"y={y_cur}:"
            f"text='{safe_txt}'"
        )
        filters.append(draw_snippet)
        y_cur += line_h

    # bottom => y=1050, font=120
    fs_bot = 120
    safe_num = bottom_str.replace("'", "\\'")
    draw_bottom = (
        f"drawtext=fontfile=Impact.ttf:"
        f"fontsize={fs_bot}:"
        f"fontcolor=white:borderw=4:bordercolor=black:"
        f"x=(main_w-text_w)/2:"
        f"y=1050:"
        f"text='{safe_num}'"
    )
    filters.append(draw_bottom)

    vf = ",".join(filters)

    cmd = [
        "ffmpeg", "-y",
        "-i", bg_mp4,
        "-vf", vf,
        "-c:v", "libx264",
        "-c:a", "copy",
        out_mp4
    ]
    return run_ffmpeg(cmd)

# -------------------------------------------------
# Twitter
# -------------------------------------------------
def authenticate_twitter():
    if not all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET, TWITTER_BEARER_TOKEN]):
        logger.warning("Missing some Twitter credentials => skip Twitter.")
        return None, None
    try:
        client_v2 = tweepy.Client(
            bearer_token=TWITTER_BEARER_TOKEN,
            consumer_key=TWITTER_API_KEY,
            consumer_secret=TWITTER_API_SECRET,
            access_token=TWITTER_ACCESS_TOKEN,
            access_token_secret=TWITTER_ACCESS_SECRET
        )
        auth_v1 = tweepy.OAuth1UserHandler(
            TWITTER_API_KEY,
            TWITTER_API_SECRET,
            TWITTER_ACCESS_TOKEN,
            TWITTER_ACCESS_SECRET
        )
        api_v1 = tweepy.API(auth_v1)
        logger.info("Twitter => authenticated both v2 client and v1.1 API.")
        return client_v2, api_v1
    except Exception as e:
        logger.error(f"Twitter auth => {e}")
        return None, None

def post_video_to_twitter(client_v2, api_v1, video_path):
    if not client_v2 or not api_v1:
        logger.warning("No Twitter => skip.")
        return False
    try:
        logger.info(f"Twitter => uploading video file: {video_path}")
        media = api_v1.media_upload(filename=video_path, media_category='tweet_video')
        logger.info(f"Twitter => media_id: {media.media_id_string}")
        resp = client_v2.create_tweet(text="", media_ids=[media.media_id_string])
        logger.info(f"Tweet => ID= {resp.data['id']}")
        time.sleep(5)
        return True
    except Exception as e:
        logger.error(f"Twitter => {e}")
        return False

# -------------------------------------------------
# Pipeline
# -------------------------------------------------
def run_pipeline():
    logger.info("----- Starting Gavin Pipeline Run -----")

    # 1) snippet + TTS
    snippet, tts_text = generate_surreal_text()

    # 2) TTS => .mp3
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    tts_file = os.path.join(OUTPUT_DIR, f"tts_{stamp}.mp3")
    if not generate_tts(tts_text, tts_file):
        return False

    # 2.5) measure TTS length
    tts_length = get_media_duration(tts_file)
    if tts_length <= 0:
        logger.error("TTS => invalid length => stop.")
        return False
    logger.info(f"TTS length => {tts_length:.2f}s")

    # 3) Dropbox => link
    tts_url = upload_to_dropbox(tts_file)
    if not tts_url:
        return False

    # 4) DupDub => green
    green_mp4 = os.path.join(OUTPUT_DIR, f"dupdub_{stamp}.mp4")
    if not create_dupdup_talking_video(DUPDUB_IMAGE_URL, tts_url, green_mp4):
        return False

    # 5) green-> alpha => prores
    alpha_mov = os.path.join(OUTPUT_DIR, f"alpha_{stamp}.mov")
    if not convert_to_alpha(green_mp4, alpha_mov):
        return False

    # 6) pick background mp4 => 5 possible => vid1..vid5
    bgs_list = [f for f in os.listdir(BGS_DIR) if f.endswith(".mp4")]
    if not bgs_list:
        logger.error("No background videos => stop.")
        return False
    chosen_bg = os.path.join(BGS_DIR, random.choice(bgs_list))

    # 7) overlay alpha => final overlay
    overlay_out = os.path.join(OUTPUT_DIR, f"overlay_{stamp}.mp4")
    if not overlay_alpha(chosen_bg, alpha_mov, overlay_out):
        return False

    # 8) numeric bottom
    bottom_num = str(random.randint(100000000, 999999999))

    # 9) overlay snippet top + numeric bottom
    text_out = os.path.join(OUTPUT_DIR, f"text_{stamp}.mp4")
    if not overlay_text(overlay_out, text_out, snippet, bottom_num):
        return False

    # 10) pick random mp3 => audio1.. audio5 => final mix clipped to TTS length
    all_auds = [f for f in os.listdir(BACKGROUND_AUDIO_DIR) if f.endswith(".mp3")]
    if not all_auds:
        logger.error("No background audio => skip.")
        return False
    chosen_mp3 = os.path.join(BACKGROUND_AUDIO_DIR, random.choice(all_auds))

    final_out = os.path.join(OUTPUT_DIR, f"gavin_final_{stamp}.mp4")
    cmd_audio = [
        "ffmpeg", "-y",
        "-i", text_out,
        "-i", chosen_mp3,
        "-filter_complex", f"[1:a]volume={AUDIO_RATIO}[bg];[0:a][bg]amix=2:duration=first[aout]",
        "-map", "0:v", "-map", "[aout]",
        "-t", str(tts_length),  # ensure final is clipped to TTS duration
        "-c:v", "copy", "-c:a", "aac",
        final_out
    ]
    if not run_ffmpeg(cmd_audio):
        return False

    # 11) Twitter => new approach
    client_v2, api_v1 = authenticate_twitter()
    if not post_video_to_twitter(client_v2, api_v1, final_out):
        return False

    logger.info("Pipeline => success, posted to Twitter!")
    return True

def main_loop():
    while True:
        success = run_pipeline()
        if success:
            logger.info("Sleeping 5s before next run...")
            time.sleep(5)
        else:
            logger.info("Error => stopping.")
            break

if __name__ == "__main__":
    main_loop()
