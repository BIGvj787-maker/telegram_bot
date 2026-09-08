import os
import telebot
import threading
import time
import requests
import json
import re
from flask import Flask

# 1. Pull your secret variables securely from Render's cloud settings
BOT_TOKEN = os.environ.get("8882701369:AAHsJKNm36IsxLiZfER50s40grZE4eHV2Mo")
MY_CHAT_ID = os.environ.get("8648190883")

bot = telebot.TeleBot(BOT_TOKEN)

# In-memory queues to monitor what accounts are active
RECORDING_LIST = []
ACTIVE_THREADS = {}

# --- KEEP-ALIVE SERVER: Keeps the Render deployment active ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot status: Online and monitoring live lists."

def run_web_server():
    # Render binds web engines to specified environment ports automatically
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
# -------------------------------------------------------------

# 2. Setup the User Interface Commands for your iPhone Telegram chat
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "👋 Private TikTok Live Recorder Bot Online!\n\n"
                          "Commands:\n"
                          "/record username - Monitor 24/7 and save video when live\n"
                          "/stop - Halt recording session and get your video file instantly\n"
                          "/list - See who you are currently tracking")

@bot.message_handler(commands=['record'])
def start_record_command(message):
    try:
        msg_parts = message.text.split()
        if len(msg_parts) < 2:
            bot.reply_to(message, "❌ Please specify a username. Example: /record username")
            return
            
        username = msg_parts[1].strip().lower().replace("@", "")
        
        if username not in RECORDING_LIST:
            RECORDING_LIST.append(username)
            bot.reply_to(message, f"⏺️ Bot set to monitor @{username}. Running background scan...")
        else:
            bot.reply_to(message, f"⚠️ Already actively monitoring or recording @{username}.")
    except Exception as e:
        bot.reply_to(message, f"❌ Error processing input command: {e}")

@bot.message_handler(commands=['stop'])
def stop_record_command(message):
    if not RECORDING_LIST:
        bot.reply_to(message, "⚠️ No active recording or monitoring sessions are running right now.")
        return
        
    # Grab the target currently active in your queue
    username = RECORDING_LIST[0]
    RECORDING_LIST.remove(username)
    bot.reply_to(message, f"🛑 Stopping background capture loop for @{username}...")
    
    filename = f"{username}_live.mp4"
    if os.path.exists(filename):
        bot.send_message(MY_CHAT_ID, f"📦 Video file found! Processing and uploading data to your iPhone now...")
        try:
            with open(filename, 'rb') as video_file:
                bot.send_video(MY_CHAT_ID, video_file, caption=f"Here is your automatically saved recording for @{username}!")
            os.remove(filename) # Erase media block to preserve storage space on the free server
        except Exception as e:
            bot.send_message(MY_CHAT_ID, f"❌ Error transmitting file payload over network: {e}")
    else:
        bot.send_message(MY_CHAT_ID, f"ℹ️ Stopped monitoring @{username}, but they did not stream long enough to record data packages.")

@bot.message_handler(commands=['list'])
def list_active_targets(message):
    if not RECORDING_LIST:
        bot.reply_to(message, "😴 Not recording or monitoring any profiles currently.")
    else:
        active_users = "\n".join([f"• @{u}" for u in RECORDING_LIST])
        bot.reply_to(message, f"🎥 Active Monitoring List:\n{active_users}")

# 3. Media Network Downloader Function
def stream_download_worker(username, stream_url):
    filename = f"{username}_live.mp4"
    print(f"Opening data network pipe for username: {username}")
    try:
        # Connect to the stream data broadcast server
        response = requests.get(stream_url, stream=True, timeout=15)
        with open(filename, 'wb') as f:
            # Process stream segments piece by piece
            for chunk in response.iter_content(chunk_size=1024*512): # Writes in 512KB data packet sizes
                # Force instant termination if the user runs the /stop command
                if username not in RECORDING_LIST:
                    break
                if chunk:
                    f.write(chunk)
    except Exception as e:
        print(f"Server content broadcast pipe broken for {username}: {e}")

# 4. Invisible 24/7 Server Polling Module
def background_monitor_loop():
    """Scans your tracking profile list by decoding hidden layout arrays securely"""
    while True:
        for username in list(RECORDING_LIST):
            if username in ACTIVE_THREADS and ACTIVE_THREADS[username].is_alive():
                continue # Skip if loop downloader is already processing media arrays
                
            try:
                target_url = f"https://www.tiktok.com/@{username}/live"
                headers = {
                    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
                }
                
                # Fetch raw profile layout payload data
                response = requests.get(target_url, headers=headers, timeout=10)
                
                # Verify structural status flag code (status: 2 confirms user is broadcasting live)
                if '"roomInfo":{"status":2}' in response.text:
                    
                    # Unpack hidden JSON string embedded inside layout tags
                    match = re.search(r'<script id="RENDER_DATA" type="application/json">(.*?)</script>', response.text)
                    if match:
                        raw_payload = requests.utils.unquote(match.group(1))
                        json_array = json.loads(raw_payload)
                        
                        # Dive down the layout dictionary mapping chain to locate streaming feeds
                        room_data = json_array.get("appContext", {}).get("states", {}).get("roomInfo", {})
                        direct_cdn_url = room_data.get("stream_url", {}).get("rtmp_pull_url")
                        
                        if direct_cdn_url:
                            bot.send_message(MY_CHAT_ID, f"🚨 ALERT: @{username} is LIVE! Safely capturing video blocks in the cloud...")
                            
                            # Initialize stream engine on an independent worker thread to ensure your text commands remain active
                            t = threading.Thread(target=stream_download_worker, args=(username, direct_cdn_url), daemon=True)
                            t.start()
                            ACTIVE_THREADS[username] = t
            except Exception as e:
                print(f"Monitoring execution routine exception for username {username}: {e}")
                
        time.sleep(30) # Poll checking cycle interval rate (seconds)

if __name__ == "__main__":
    # Start up the fake keep-alive server proxy to avoid Render deployment freeze rules
    threading.Thread(target=run_web_server, daemon=True).start()
    
    # Run the background monitoring thread scanner loop
    threading.Thread(target=background_monitor_loop, daemon=True).start()
    
    print("Bot loop initialized. Listening to mobile Telegram API incoming packets...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
