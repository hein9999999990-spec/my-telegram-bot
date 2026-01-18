import telebot
from telebot import types
import json
import os
import time
from flask import Flask, request
import threading

# --- Settings ---
# Render Environment Variables မှ ဆွဲယူရန် ပြောင်းလဲထားပါသည်
TOKEN = os.environ.get("BOT_TOKEN") 
ADMIN_ID = os.environ.get("ADMIN_ID")
PAYMENT_CHANNEL = "@HHPayMentChannel"

# Channel အသစ် "@MaiRo879" ကို MUST_JOIN ထဲမှာ ထည့်သွင်းထားပါတယ်။
MUST_JOIN = ["@HHPayMentChannel", "@mbfree1930channel", "@hmovie19", "@hhfreemoney3"]
LOGO_URL = "https://i.ibb.co/v4S8L8Y/HH-Logo.jpg"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__) # Hosting (IP Check) အတွက် Flask Setup
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
    if hasattr(message, 'from_user'):
        uid = str(message.from_user.id)
    else:
        uid = str(message.chat.id)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("💰 Wallet", "👥 Referral")
    markup.add("🎁 Daily Bonus", "🏆 Leaderboard")
    markup.add("📤 Withdraw", "📜 History")

    caption_text = "👋 HH Free Money Bot မှ ကြိုဆိုပါတယ်!"
    try:
        bot.send_photo(uid, LOGO_URL, caption=caption_text, reply_markup=markup)
    except:
        bot.send_message(uid, caption_text, reply_markup=markup)

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
            'is_verified': False # Phone Verification Status
        }
        save_data()

    if users[uid].get('is_banned'):
        return bot.send_message(uid, "❌ သင်သည် Ban ခံထားရပါသည်။")

    # [1] Membership Check
    if not check_join(uid):
        markup = types.InlineKeyboardMarkup()
        for ch in MUST_JOIN:
            markup.add(types.InlineKeyboardButton(text=f"Join {ch}", url=f"https://t.me/{ch[1:]}"))
        markup.add(types.InlineKeyboardButton(text="Check Join ✅", callback_data="check"))
        return bot.send_message(uid, "⚠️ Bot သုံးရန် အောက်ပါ Channel များ Join ပါ။", reply_markup=markup)

    # [2] Phone Number Verification Check
    if not users[uid].get('is_verified'):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(types.KeyboardButton("🛡️ Verify Account (Share Phone)", request_contact=True))
        return bot.send_message(uid, "🛡️ Referral စနစ်အတွက် ဖုန်းနံပါတ် Verify လုပ်ရန် လိုအပ်ပါသည်။ (အောက်က Button ကို နှိပ်ပါ)", reply_markup=markup)

    show_menu(message)

# --- Phone Verification Handler ---
@bot.message_handler(content_types=['contact'])
def contact_handler(message):
    uid = str(message.from_user.id)
    if message.contact.user_id != message.from_user.id:
        bot.send_message(uid, "❌ မိမိကိုယ်ပိုင် ဖုန်းနံပါတ်ကိုသာ အသုံးပြုပါ။")
    else:
        users[uid]['is_verified'] = True
        users[uid]['phone'] = message.contact.phone_number
        save_data()
        bot.send_message(uid, "✅ Verification အောင်မြင်ပါသည်။")
        show_menu(message)

# --- [3] IP & Device Detection (Flask) ---
@app.route('/')
def home():
    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    return f"Bot is online. IP Logged: {user_ip}"

# --- Withdraw Flow ---
@bot.message_handler(func=lambda m: m.text == "📤 Withdraw")
def wd_1(message):
    uid = str(message.from_user.id)
    if users[uid].get('balance', 0) < 500:
        return bot.reply_to(message, "❌ ၅၀၀ ကျပ်မပြည့်သေးပါ။")

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("WavePay 💸", callback_data="wd_wave"),
               types.InlineKeyboardButton("KPay 💳", callback_data="wd_kpay"))
    bot.send_message(message.chat.id, "💳 ငွေထုတ်မည့် နည်းလမ်းကို ရွေးပါ-", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("wd_"))
def wd_callback(call):
    method = "WavePay" if call.data == "wd_wave" else "KPay"
    msg = bot.send_message(call.message.chat.id, f"💰 {method} ဖြင့်ထုတ်မည့် ပမာဏကို ရိုက်ပါ- (အနည်းဆုံး ၅၀၀)")
    bot.register_next_step_handler(msg, wd_amount_step, method)

def wd_amount_step(message, method):
    try:
        amt = int(message.text)
        if amt < 500:
            return bot.send_message(message.chat.id, "❌ အနည်းဆုံး ၅၀၀ ကျပ်မှ စထုတ်နိုင်ပါသည်။")
        msg = bot.send_message(message.chat.id, f"📱 {method} ဖုန်းနံပါတ်ကို ရိုက်ပါ-")
        bot.register_next_step_handler(msg, wd_phone_step, method, amt)
    except:
        bot.send_message(message.chat.id, "⚠️ ဂဏန်းပဲ ရိုက်ပေးပါ။")
        show_menu(message)

def wd_phone_step(message, method, amt):
    phone = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True).add("✅ အတည်ပြုမည်", "🔙 နောက်သို့")
    bot.send_message(message.chat.id, f"💠 Method: {method}\n💰 Amount: {amt} MMK\n📱 Phone: {phone}\n\nမှန်ပါသလား?", reply_markup=markup)
    bot.register_next_step_handler(message, wd_final, method, amt, phone)

def wd_final(message, method, amt, phone):
    uid = str(message.from_user.id)
    if message.text == "✅ အတည်ပြုမည်":
        if users[uid].get('balance', 0) < amt:
            return bot.send_message(uid, "❌ ငွေမလုံလောက်ပါ။")

        users[uid]['balance'] -= amt
        users[uid].setdefault('history', []).append({'date': time.strftime("%d/%m/%Y"), 'amt': f"{amt} ({method})", 'status': 'Pending ⏳'})
        save_data()

        markup = types.InlineKeyboardMarkup()
        pay_data = f"confirm_{uid}_{amt}_{method}"
        markup.add(types.InlineKeyboardButton("Confirm Payment ✅", callback_data=pay_data))

        bot.send_message(ADMIN_ID, f"🔔 **ထုတ်ယူမှုသစ်!**\nID: `{uid}`\nName: {message.from_user.first_name}\nပမာဏ: {amt}\nနည်းလမ်း: {method}\nဖုန်း: {phone}", reply_markup=markup)
        bot.send_message(uid, "✅ တောင်းဆိုမှု အောင်မြင်သည်။ Admin မှ စစ်ဆေးပြီး လွှဲပေးပါလိမ့်မည်။")
        show_menu(message)
    else:
        show_menu(message)

# --- Confirm Payment & Auto Post ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_"))
def confirm_payment(call):
    _, uid, amt, method = call.data.split("_")
    if uid in users:
        for record in reversed(users[uid]['history']):
            if record['status'] == 'Pending ⏳':
                record['status'] = 'Paid ✅'
                break
        save_data()
        user_name = users[uid].get('name', 'User')
        post_text = (
            f"[ 1 ] 💰 ငွေထုတ်ယူမှု အောင်မြင်ပါသည် 🔊\n\n"
            f"Name 👤 - {user_name}\n"
            f"Aumont 💰 - {amt} MMK\n"
            f"Pay ment - {method}\n"
            f"Bot Link - @HHFreemoneybot"
        )
        try:
            bot.send_message(PAYMENT_CHANNEL, post_text)
            bot.send_message(uid, f"✅ Admin မှ {amt} ကျပ် ကို {method} ဖြင့် လွှဲပေးပြီးပါပြီ။")
            bot.answer_callback_query(call.id, "✅ Channel သို့ တင်ပြီးပါပြီ။")
            bot.edit_message_text(f"✅ ပေးချေမှု အောင်မြင်ပြီး Channel သို့ တင်ပြီးပါပြီ။\nID: {uid} | {amt} MMK", call.message.chat.id, call.message.message_id)
        except Exception as e:
            bot.answer_callback_query(call.id, f"Error: {e}")

# --- Callbacks for Check Join ---
@bot.callback_query_handler(func=lambda call: call.data == "check")
def check_callback(call):
    uid = str(call.from_user.id)
    if check_join(uid):
        inviter_id = users[uid].get('referred_by')
        if inviter_id and not users[uid].get('referral_rewarded'):
            if inviter_id in users and inviter_id != uid:
                users[inviter_id]['balance'] += 50
                users[inviter_id]['referrals'] += 1
                users[uid]['referral_rewarded'] = True
                save_data()
                try: bot.send_message(inviter_id, f"🎉 သင့် Link မှ လူတစ်ယောက် Channel Join သဖြင့် 50 ကျပ် ရရှိပါပြီ!")
                except: pass
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        # Check ပြီးရင် Start ကို ပြန်ခေါ်ပြီး Phone Verify စစ်ပါမယ်
        start(call.message) 
    else:
        bot.answer_callback_query(call.id, "⚠️ Channel အားလုံးကို အရင် Join ပါဦး။", show_alert=True)

# --- Other Functions ---
@bot.message_handler(func=lambda m: m.text == "💰 Wallet")
def wallet(message):
    uid = str(message.from_user.id)
    bot.reply_to(message, f"💰 လက်ကျန်ငွေ: {users[uid].get('balance', 0)} ကျပ်")

@bot.message_handler(func=lambda m: m.text == "📜 History")
def history(message):
    uid = str(message.from_user.id)
    h = users[uid].get('history', [])
    if h:
        txt = "📜 **မှတ်တမ်း:**\n\n" + "\n".join([f"📅 {i['date']} | 💰 {i['amt']} | {i['status']}" for i in h])
    else:
        txt = "မှတ်တမ်းမရှိပါ။"
    bot.reply_to(message, txt, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🎁 Daily Bonus")
def bonus(message):
    uid = str(message.from_user.id)
    now = time.time()
    if now - users[uid].get('last_bonus', 0) < 86400:
        return bot.reply_to(message, "❌ ၂၄ နာရီ မပြည့်သေးပါ။")
    users[uid]['balance'] += 125
    users[uid]['last_bonus'] = now
    save_data()
    bot.reply_to(message, "✅ 125ကျပ် ရရှိပါပြီ။")

@bot.message_handler(func=lambda m: m.text == "👥 Referral")
def referral(message):
    uid = str(message.from_user.id)
    bot.reply_to(message, f"👥 ဖိတ်ခေါ်သူ: {users[uid].get('referrals', 0)} ဦး\n🔗 Link: `https://t.me/{bot.get_me().username}?start={uid}`", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🏆 Leaderboard")
def leader(message):
    top = sorted(users.items(), key=lambda x: x[1].get('referrals', 0), reverse=True)[:5]
    txt = "🏆 **Top 5 Referrals:**\n\n"
    for i, (k, v) in enumerate(top): txt += f"{i+1}. {v.get('name', 'User')} — {v.get('referrals', 0)} ယောက်\n"
    bot.reply_to(message, txt, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🔙 နောက်သို့")
def back(message): show_menu(message)

# --- Admin Commands ---
@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if str(message.from_user.id) == ADMIN_ID:
        msg_text = message.text.replace("/broadcast ", "")
        if msg_text == "/broadcast": return bot.reply_to(message, "ပို့ချင်တဲ့ စာသားရိုက်ပေးပါ")
        count = 0
        all_users = list(users.keys())
        for u in all_users:
            try:
                bot.send_message(u, f"📢 **သတင်းစကား:**\n\n{msg_text}", parse_mode="Markdown")
                count += 1
            except: pass
        bot.reply_to(message, f"✅ User {count} ဦးကို စာပို့ပြီးပါပြီ။")

# --- Run Server & Bot ---
def run_bot():
    bot.polling(none_stop=True)

if __name__ == "__main__":
    # Bot ကို Thread ဖြင့် Run
    threading.Thread(target=run_bot).start()
    # Flask Server (Render အတွက်)
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
