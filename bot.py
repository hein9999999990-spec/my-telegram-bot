import telebot
from telebot import types
import json
import os
import time
from flask import Flask, request
import threading

# --- Settings (Security Layer) ---
TOKEN = os.environ.get("BOT_TOKEN") 
# ADMIN_ID ကို နံပါတ်အဖြစ် သေချာပြောင်းလဲခြင်း
admin_env = os.environ.get("ADMIN_ID")
ADMIN_ID = int(admin_env) if admin_env else None

PAYMENT_CHANNEL = "@HHPayMentChannel"
MUST_JOIN = ["@HHPayMentChannel", "@mbfree1930channel", "@hmovie19", "@hhfreemoney3"]
LOGO_URL = "https://i.ibb.co/v4S8L8Y/HH-Logo.jpg"
# Render URL မှန်ကန်အောင် ပြင်ဆင်ထားသည်
RENDER_URL = "https://my-telegram-bot-6-vo9u.onrender.com" 

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
DATA_FILE = "users_data.json"

# --- Data Management ---
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        try:
            users = json.load(f)
        except:
            users = {}
else:
    users = {}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(users, f, indent=4)

def check_join(user_id):
    for channel in MUST_JOIN:
        try:
            status = bot.get_chat_member(channel, user_id).status
            if status == "left":
                return False
        except:
            return False
    return True

def show_menu(message):
    uid = str(message.from_user.id) if hasattr(message, 'from_user') else str(message.chat.id)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("💰 Wallet", "👥 Referral")
    markup.add("🎁 Daily Bonus", "🏆 Leaderboard")
    markup.add("📤 Withdraw", "📜 History")

    caption_text = "👋 HH Free Money Bot မှ ကြိုဆိုပါတယ်!"
    try:
        bot.send_photo(uid, LOGO_URL, caption=caption_text, reply_markup=markup)
    except:
        bot.send_message(uid, caption_text, reply_markup=markup)

# --- [3] IP & Device Verification Route ---
@app.route('/verify-device/<uid>')
def verify_device(uid):
    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent')
    
    if uid in users:
        for u in users:
            if users[u].get('user_ip') == user_ip and u != uid:
                return "<h1>Access Denied!</h1><p>ဒီ IP နဲ့ အခြားအကောင့်တစ်ခု ရှိပြီးသားမို့ ထပ်လုပ်လို့မရပါဘူး။</p>"

        users[uid]['ip_verified'] = True
        users[uid]['user_ip'] = user_ip
        users[uid]['device_info'] = user_agent
        save_data()
        bot.send_message(uid, "✅ IP & Device Verification အောင်မြင်ပါသည်။ /start ကို ပြန်နှိပ်ပါ။")
        return "<h1>Verification Success!</h1><p>Bot ထဲသို့ ပြန်သွားနိုင်ပါပြီ။</p>"
    return "Invalid User ID"

@app.route('/')
def home():
    return "Bot is running!"

# --- Start & Registration ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = str(message.from_user.id)
    args = message.text.split()

    if uid not in users:
        users[uid] = {
            'name': message.from_user.first_name,
            'balance': 0,
            'referrals': 0,
            'is_banned': False,
            'last_bonus': 0,
            'history': [],
            'referred_by': args[1] if len(args) > 1 else None,
            'referral_rewarded': False,
            'is_verified': False,
            'ip_verified': False
        }
        save_data()

    if users[uid].get('is_banned'):
        return bot.send_message(uid, "❌ သင်သည် Ban ခံထားရပါသည်။")

    if not check_join(uid):
        markup = types.InlineKeyboardMarkup()
        for ch in MUST_JOIN:
            markup.add(types.InlineKeyboardButton(text=f"Join {ch}", url=f"https://t.me/{ch[1:]}"))
        markup.add(types.InlineKeyboardButton(text="Check Join ✅", callback_data="check"))
        return bot.send_message(uid, "⚠️ Bot သုံးရန် အောက်ပါ Channel များ Join ပါ။", reply_markup=markup)

    # အဆင့် ၂ - IP Verification (ip_verified false ဖြစ်နေမှ Button ပေါ်မည်)
    if not users[uid].get('ip_verified'):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🛡️ Verify IP & Device", url=f"{RENDER_URL}/verify-device/{uid}"))
        return bot.send_message(uid, "🔒 လုံခြုံရေးအတွက် အောက်က Link ကိုနှိပ်ပြီး IP/Device အရင်စစ်ပေးပါ။", reply_markup=markup)

    if not users[uid].get('is_verified'):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(types.KeyboardButton("🛡️ Verify Phone (Share Phone)", request_contact=True))
        return bot.send_message(uid, "🛡️ Referral စနစ်အတွက် ဖုန်းနံပါတ် Verify လုပ်ရန် လိုအပ်ပါသည်။", reply_markup=markup)

    show_menu(message)

# --- Phone Verification Handler ---
@bot.message_handler(content_types=['contact'])
def contact_handler(message):
    uid = str(message.from_user.id)
    if message.contact.user_id != message.from_user.id:
        bot.send_message(uid, "❌ မိမိကိုယ်ပိုင် ဖုန်းနံပါတ်ကိုသာ အသုံးပြုပါ။")
    else:
        users[uid]['is_verified'] = True
        save_data()
        bot.send_message(uid, "✅ Verification အောင်မြင်ပါသည်။")
        show_menu(message)

# --- Admin Broadcast ---
@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    # ADMIN_ID ကို integer နဲ့ တိုက်စစ်သည်
    if message.from_user.id == ADMIN_ID:
        msg_text = message.text.replace("/broadcast ", "")
        if msg_text == "/broadcast":
            return bot.reply_to(message, "ပို့ချင်တဲ့ စာသားရိုက်ပေးပါ")
        count = 0
        for u in list(users.keys()):
            try:
                bot.send_message(u, f"📢 **သတင်းစကား:**\n\n{msg_text}", parse_mode="Markdown")
                count += 1
            except: pass
        bot.reply_to(message, f"✅ User {count} ဦးကို စာပို့ပြီးပါပြီ။")

# --- Run Server & Bot ---
def run_bot():
    print("Bot Polling started...")
    bot.infinity_polling()

if __name__ == "__main__":
    # Bot ကို Thread ထဲမှာ အရင် Run မည်
    t = threading.Thread(target=run_bot)
    t.daemon = True
    t.start()
    
    # Flask Server ကို Main Thread မှာ Run မည်
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
