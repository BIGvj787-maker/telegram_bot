import os
import telebot
import threading
import time
import requests
from flask import Flask

# 1. Grab your keys safely from Render's settings
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
MY_CHAT_ID = os.environ.get("MY_CHAT_ID")

bot = telebot.TeleBot(BOT_TOKEN)

# Track users who are actively being monitored / recorded
RECORDING_LIST = []
ACTIVE_THREADS = {}

# --- TRICK RENDER: Fake Web Server Setup ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot status: Online and tracking."

def run_web_server():
    # Render automatically tells our app what port to use
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
# -------------------------------------------

# 2. Command handlers for your iPhone Telegram App
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "👋 Private Live Recorder Bot Online!\n\n"
                          "Commands:\n"
                          "/record username - Monitor 24/7 and record when live\n"
                          "/stop - Stop recording current target and get your video\n"
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
            bot.reply_to(message, f"⏺️ Bot set to record @{username}. Checking for live activity...")
        else:
            bot.reply_to(message, f"⚠️ Already actively monitoring or recording @{username}.")
    except Exception as e:
        bot.reply_to(message, f"❌ Error processing command: {e}")

@bot.message_handler(commands=['stop'])
def stop_record_command(message):
    if not RECORDING_LIST:
        bot.reply_to(message, "⚠️ No active recording or monitoring sessions are running right now.")
        return
        
    username = RECORDING_LIST[0] 
    RECORDING_LIST.remove(username)
    bot.reply_to(message, f"🛑 Stopping background capture for @{username}...")
    
    filename = f"{username}_live.mp4"
    if os.path.exists(filename):
        bot.send_message(MY_CHAT_ID, f"📦 Video file packaged! Sending raw stream data to your phone now...")
        try:
            with open(filename, 'rb') as video_file:
                bot.send_video(MY_CHAT_ID, video_file, caption=f"Here is your automatically saved recording for @{username}!")
            os.remove(filename) 
        except Exception as e:
            bot.send_message(MY_CHAT_ID, f"❌ Error sending file: {e}")
    else:
        bot.send_message(MY_CHAT_ID, f"ℹ️ Stopped monitoring @{username}, but they didn't broadcast while I was watching, so no file was saved.")

@bot.message_handler(commands=['list'])
def list_active_targets(message):
    if not RECORDING_LIST:
        bot.reply_to(message, "😴 Not recording or monitoring any targets currently.")
    else:
        active_users = "\n".join([f"• @{u}" for u in RECORDING_LIST])
        bot.reply_to(message, f"🎥 Active Recording/Monitoring List:\n{active_users}")

# 3. Dynamic Stream Capture Engine
def stream_download_worker(username, stream_url):
    filename = f"{username}_live.mp4"
    try:
        response = requests.get(stream_url, stream=True, timeout=15)
        with open(filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024*1024): 
                if username not in RECORDING_LIST:
                    break
                if chunk:
                    f.write(chunk)
    except Exception as e:
        print(f"Data stream interrupted for {username}: {e}")

def background_monitor_loop():
    while True:
        for username in list(RECORDING_LIST):
            if username in ACTIVE_THREADS and ACTIVE_THREADS[username].is_alive():
                continue 
                
            try:
                url = f"https://tiktok.com@{username}/live"
                headers = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)"}
                response = requests.get(url, headers=headers, timeout=10)
                
                if '"roomInfo":{"status":2}' in response.text:
                    bot.send_message(MY_CHAT_ID, f"🚨 ALERT: @{username} is LIVE! Recording stream blocks in the cloud...")
                    target_stream_url = "http://example.com"
                    
                    t = threading.Thread(target=stream_download_worker, args=(username, target_stream_url), daemon=True)
                    t.start()
                    ACTIVE_THREADS[username] = t
            except Exception as e:
                print(f"Error monitoring {username}: {e}")
                
        time.sleep(60)

if __name__ == "__main__":
    # Start the fake web server so Render is happy
    threading.Thread(target=run_web_server, daemon=True).start()
    
    # Start background polling routine
    threading.Thread(target=background_monitor_loop, daemon=True).start()
    
    print("Bot listening for Telegram commands...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
