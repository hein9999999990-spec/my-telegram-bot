import telebot
from telebot import types
import json
import os
import time

# --- Settings ---
# GitHub က မသိအောင် ဤနေရာတွင် Token ကို ဖျောက်ထားပါသည်
TOKEN = os.environ.get('BOT_TOKEN') 
ADMIN_ID = "8176057500"
PAYMENT_CHANNEL = "@HHPayMentChannel"
MUST_JOIN = ["@MaiRo879", "@HHPayMentChannel", "@mbfree1930channel", "@hmovie19", "@hhfreemoney3"]
LOGO_URL = "https://i.ibb.co/v4S8L8Y/HH-Logo.jpg"

bot = telebot.TeleBot(TOKEN)
DATA_FILE = "users_data.json"

# --- Data Management ---
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        try: users = json.load(f)
        except: users = {}
else:
    users = {}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(users, f, indent=4)

def check_join(user_id):
    for channel in MUST_JOIN:
        try:
            status = bot.get_chat_member(channel, user_id).status
            if status == "left": return False
        except: return False
    return True

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
            'verified': False
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

    show_menu(message)

# --- Verification Logic ---
@bot.callback_query_handler(func=lambda call: call.data == "check")
def check_callback(call):
    uid = str(call.from_user.id)
    if check_join(uid):
        if not users[uid].get('verified'):
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            button = types.KeyboardButton(text="📱 Verify Phone Number", request_contact=True)
            markup.add(button)
            bot.send_message(uid, "🛡️ Fake Refer တားဆီးရန် အောက်ပါခလုတ်ကိုနှိပ်၍ Phone Number Share ပေးပါ။", reply_markup=markup)
        else:
            show_menu(call.message)
    else:
        bot.answer_callback_query(call.id, "⚠️ Channel အားလုံးကို အရင် Join ပါဦး။", show_alert=True)

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    uid = str(message.from_user.id)
    contact = message.contact
    if contact.user_id != message.from_user.id:
        return bot.send_message(uid, "❌ မိမိအကောင့်နံပါတ်သာ ဖြစ်ရပါမည်။")
    phone_no = contact.phone_number
    if not (phone_no.startswith("95") or phone_no.startswith("+95") or phone_no.startswith("09")):
        return bot.send_message(uid, "❌ မြန်မာဖုန်းနံပါတ်သာ လက်ခံပါသည်။")

    users[uid]['verified'] = True
    inviter_id = users[uid].get('referred_by')
    if inviter_id and not users[uid].get('referral_rewarded'):
        if inviter_id in users and inviter_id != uid:
            users[inviter_id]['balance'] += 50
            users[inviter_id]['referrals'] += 1
            users[uid]['referral_rewarded'] = True
            save_data()
            try: bot.send_message(inviter_id, f"🎉 သင့် Link မှ လူတစ်ယောက် Join သဖြင့် 50 ကျပ် ရရှိပါပြီ!")
            except: pass
    save_data()
    bot.send_message(uid, "✅ အတည်ပြုခြင်း အောင်မြင်ပါသည်။", reply_markup=types.ReplyKeyboardRemove())
    show_menu(message)

def show_menu(message):
    uid = str(message.chat.id if hasattr(message, 'chat') else message.from_user.id)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("💰 Wallet", "👥 Referral")
    markup.add("🎁 Daily Bonus", "🏆 Leaderboard")
    markup.add("📤 Withdraw", "📜 History")
    bot.send_photo(uid, LOGO_URL, caption="👋 HH Free Money Bot မှ ကြိုဆိုပါတယ်!", reply_markup=markup)

# --- Withdraw Flow ---
@bot.message_handler(func=lambda m: m.text == "📤 Withdraw")
def wd_1(message):
    uid = str(message.from_user.id)
    if users[uid].get('referrals', 0) < 5:
        return bot.reply_to(message, f"❌ ငွေထုတ်ရန် အနည်းဆုံး Referral ၅ ယောက်ရှိရပါမည်။ (လက်ရှိ: {users[uid]['referrals']} ယောက်)")
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
        if amt < 500: return bot.send_message(message.chat.id, "❌ အနည်းဆုံး ၅၀၀ ကျပ်မှ စထုတ်နိုင်ပါသည်။")
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
        if users[uid].get('balance', 0) < amt: return bot.send_message(uid, "❌ ငွေမလုံလောက်ပါ။")
        users[uid]['balance'] -= amt
        users[uid].setdefault('history', []).append({'date': time.strftime("%d/%m/%Y"), 'amt': f"{amt} ({method})", 'status': 'Pending ⏳'})
        save_data()
        markup = types.InlineKeyboardMarkup()
        pay_data = f"confirm_{uid}_{amt}_{method}"
        markup.add(types.InlineKeyboardButton("Confirm Payment ✅", callback_data=pay_data))
        bot.send_message(ADMIN_ID, f"🔔 **ထုတ်ယူမှုသစ်!**\nID: `{uid}`\nပမာဏ: {amt}\nနည်းလမ်း: {method}\nဖုန်း: {phone}", reply_markup=markup)
        bot.send_message(uid, "✅ တောင်းဆိုမှု အောင်မြင်သည်။ Admin မှ စစ်ဆေးပြီး လွှဲပေးပါလိမ့်မည်။")
        show_menu(message)
    else: show_menu(message)

# --- Admin & Other Functions ---
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
        post_text = (f"[ 1 ] 💰 ငွေထုတ်ယူမှု အောင်မြင်ပါသည် 🔊\n\nName 👤 - {user_name}\nAumont 💰 - {amt} MMK\nPay ment - {method}\nBot Link - @HHFreemoneybot")
        try:
            bot.send_message(PAYMENT_CHANNEL, post_text)
            bot.send_message(uid, f"✅ Admin မှ {amt} ကျပ် ကို {method} ဖြင့် လွှဲပေးပြီးပါပြီ။")
            bot.edit_message_text(f"✅ ပေးချေမှု အောင်မြင်ပြီး Channel သို့ တင်ပြီးပါပြီ။", call.message.chat.id, call.message.message_id)
        except: pass

@bot.message_handler(func=lambda m: m.text == "💰 Wallet")
def wallet(message):
    uid = str(message.from_user.id)
    bot.reply_to(message, f"💰 လက်ကျန်ငွေ: {users[uid].get('balance', 0)} ကျပ်")

@bot.message_handler(func=lambda m: m.text == "📜 History")
def history(message):
    uid = str(message.from_user.id)
    h = users[uid].get('history', [])
    txt = "📜 **မှတ်တမ်း:**\n\n" + "\n".join([f"📅 {i['date']} | 💰 {i['amt']} | {i['status']}" for i in h]) if h else "မှတ်တမ်းမရှိပါ။"
    bot.reply_to(message, txt, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🎁 Daily Bonus")
def bonus(message):
    uid = str(message.from_user.id)
    now = time.time()
    if now - users[uid].get('last_bonus', 0) < 86400: return bot.reply_to(message, "❌ ၂၄ နာရီ မပြည့်သေးပါ။")
    users[uid]['balance'] += 10
    users[uid]['last_bonus'] = now
    save_data()
    bot.reply_to(message, "✅ 10 ကျပ် ရရှိပါပြီ။")

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

@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if str(message.from_user.id) == ADMIN_ID:
        msg_text = message.text.replace("/broadcast ", "")
        for u in list(users.keys()):
            try: bot.send_message(u, f"📢 **သတင်းစကား:**\n\n{msg_text}", parse_mode="Markdown")
            except: pass
        bot.reply_to(message, "✅ ပို့ပြီးပါပြီ။")

bot.polling(none_stop=True)
