import time
import sqlite3
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

BOT_TOKEN = "8850375131:AAFfM6CASg_vI_vQ5RKvp4y-nlz_dPKyjFA"
ADMIN_ID = 6189671221

bot = telebot.TeleBot(BOT_TOKEN)

# ---------- Пайвастшавӣ ба базаи додаҳо ----------
DB_PATH = "bot_data.db"

def db_connect():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            number TEXT UNIQUE,
            last_seen REAL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS admin_sms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER,
            sender_name TEXT,
            sender_num TEXT,
            text TEXT,
            time REAL
        )
    """)
    conn.commit()
    conn.close()

def db_get_number(user_id):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT number FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

def db_set_number(user_id, number):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users (user_id, first_name, number, last_seen)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET number=excluded.number
    """, (user_id, "", number, time.time()))
    conn.commit()
    conn.close()

def db_get_all_users():
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT user_id, first_name, number, last_seen FROM users")
    rows = cur.fetchall()
    conn.close()
    return rows

def db_get_user_id_by_number(number):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users WHERE number=?", (number,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

def db_update_name_seen(user_id, name):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users (user_id, first_name, number, last_seen)
        VALUES (?, ?, NULL, ?)
        ON CONFLICT(user_id) DO UPDATE SET first_name=excluded.first_name, last_seen=excluded.last_seen
    """, (user_id, name, time.time()))
    conn.commit()
    conn.close()

def db_add_admin_sms(sender_id, sender_name, sender_num, text):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO admin_sms (sender_id, sender_name, sender_num, text, time)
        VALUES (?, ?, ?, ?, ?)
    """, (sender_id, sender_name, sender_num, text, time.time()))
    conn.commit()
    conn.close()

def db_get_admin_sms():
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT sender_name, sender_num, text, time FROM admin_sms ORDER BY id DESC LIMIT 50")
    rows = cur.fetchall()
    conn.close()
    return rows

init_db()

# ---------- Ҳолатҳои муваққатӣ (дар RAM) ----------
admin_states = {}
user_states = {}
waiting_random_users = []
chat_partners = {}

# ---------- Клавиатураҳо ----------
def get_main_keyboard(user_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)

    if user_id == ADMIN_ID:
        if db_get_number(ADMIN_ID):
            my_num = db_get_number(ADMIN_ID)
            btn_num = KeyboardButton(f"📱 Номери ман: +{my_num}")
        else:
            btn_num = KeyboardButton("1️⃣ КМ Сохтани номер")

        markup.add(btn_num, KeyboardButton("2️⃣ СМС"))
        markup.add(KeyboardButton("3️⃣ Дидани одамон"), KeyboardButton("4️⃣ Пайваст шудан"))
        markup.add(KeyboardButton("5️⃣ Хабар ба ҳама"), KeyboardButton("6️⃣ Паёмҳои омада"))
    else:
        if db_get_number(user_id):
            my_num = db_get_number(user_id)
            btn_num = KeyboardButton(f"📱 Номери ман: +{my_num}")
        else:
            btn_num = KeyboardButton("📱 Сохтани номер")

        markup.add(btn_num, KeyboardButton("📞 Занг задан"))
        markup.add(KeyboardButton("✉️ СМС фиристодан"))
        markup.add(KeyboardButton("🔗 Пайваст шудан бо бегонагон"))

    return markup

# ---------- /start ----------
@bot.message_handler(commands=['start'])
def start_handler(message):
    user_id = message.from_user.id
    name = message.from_user.first_name
    db_update_name_seen(user_id, name)

    markup = get_main_keyboard(user_id)

    if user_id == ADMIN_ID:
        text = f"👑 Салом Админ {name}! Панели махсуси шумо кушода шуд:"
    else:
        text = f"Салом {name}! Инҷо телефони телеграми аст. Тугмаҳои поёни экранро истифода баред:"

    bot.send_message(message.chat.id, text, reply_markup=markup)

# ---------- Ҳама паёмҳо ----------
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    if not message.from_user:
        return
    user_id = message.from_user.id
    name = message.from_user.first_name or "Муштарӣ"
    db_update_name_seen(user_id, name)
    text = (message.text or "").strip()

    if user_id in chat_partners:
        partner_id = chat_partners[user_id]
        try:
            bot.send_message(partner_id, f"💬 {name}: {text}")
        except:
            pass
        return

    if "Номери ман" in text:
        my_num = db_get_number(user_id)
        if my_num:
            bot.reply_to(message, f"📱 Номери сохтагиатон: `+{my_num}`\nИн номер сабт шудааст ва дигар алиш намешавад.", parse_mode="Markdown")
        else:
            bot.reply_to(message, "📱 Шумо ҳоло номер надоред. Тугмаи 📱 Сохтани номерро пахш кунед.")
        return

    if text == "🔗 Пайваст шудан бо бегонагон":
        if user_id in chat_partners:
            bot.reply_to(message, "⚠️ Шумо аллакай бо касе пайваст ҳастед!")
            return

        if user_id in waiting_random_users:
            bot.reply_to(message, "⏳ Шумо дар навбат ҳастед. Интизор бошед...")
            return

        if waiting_random_users:
            partner_id = waiting_random_users.pop(0)
            if partner_id == user_id:
                waiting_random_users.append(user_id)
                bot.reply_to(message, "⏳ Касе сухбат надорад, 1 минут интизор шавед...")
                return

            chat_partners[user_id] = partner_id
            chat_partners[partner_id] = user_id

            p_name = (bot.get_chat(partner_id).first_name if True else "Бегона") or "Бегона"
            u_name = name

            markup_hang = InlineKeyboardMarkup()
            markup_hang.add(InlineKeyboardButton("📴 Хомӯш кардан", callback_data="random_hangup"))

            try:
                bot.send_message(partner_id, f"Муҳтарам *{u_name}* пайваст шуди бо вай", reply_markup=markup_hang, parse_mode="Markdown")
            except:
                pass
            bot.send_message(user_id, f"Муҳтарам *{p_name}* пайваст шуди бо вай", reply_markup=markup_hang, parse_mode="Markdown")
        else:
            waiting_random_users.append(user_id)
            bot.reply_to(message, "⏳ Касе сухбат надорад, 1 минут интизор шавед...")
        return

    # Ҳолати интизории паём
    if user_id in user_states and isinstance(user_states[user_id], dict):
        state_data = user_states[user_id]
        if state_data.get("state") == "waiting_sms_to_admin":
            user_states.pop(user_id, None)
            sender_num = db_get_number(user_id) or "Номаълум"
            sender_name = name

            db_add_admin_sms(user_id, sender_name, sender_num, text)

            bot.reply_to(message, "Паём рафт")
            try:
                bot.send_message(ADMIN_ID, f"📩 Паёми нав аз муҳтарам *{sender_name}* (+{sender_num}): {text}", parse_mode="Markdown")
            except:
                pass
            return

        elif state_data.get("state") == "waiting_user_sms_text":
            data = user_states.pop(user_id)
            target_id = data["target"]
            sender_name = name

            bot.reply_to(message, "Паём рафт")
            try:
                bot.send_message(target_id, f"✉️ Паём аз тарафи муҳтарам *{sender_name}*: {text}", parse_mode="Markdown")
            except:
                pass
            return

    # Админ амалҳо
    if user_id == ADMIN_ID:
        if user_id in admin_states and isinstance(admin_states[user_id], dict) and admin_states[user_id].get("state") == "adm_waiting_sms_text":
            data = admin_states.pop(user_id)
            target_id = data["target"]
            bot.reply_to(message, "Паём рафт")
            try:
                bot.send_message(target_id, f"✉️ Паём аз тарафи муҳтарам *Админ*: {text}")
            except:
                pass
            return

        if text == "1️⃣ КМ Сохтани номер":
            if db_get_number(ADMIN_ID):
                bot.reply_to(message, f"Шумо аллакай номер доред: +{db_get_number(ADMIN_ID)}")
                return
            admin_states[ADMIN_ID] = "adm_custom_number"
            bot.reply_to(message, "📱 Номери дилхоҳи худро (8 рақам) нависед:")
            return

        elif text == "2️⃣ СМС":
            admin_states[ADMIN_ID] = "adm_sms_num"
            bot.reply_to(message, "✉️ Ба кадом номер СМС равон мекунед? Рақамро нависед:")
            return

        elif text == "3️⃣ Дидани одамон":
            users = db_get_all_users()
            if not users:
                bot.reply_to(message, "📭 Ҳоло ягон кас номер насохтааст.")
            else:
                text_list = "📋 Рӯйхати одамони номер сохтагӣ:\n\n"
                current_time = time.time()
                for uid, uname, num, last_t in users:
                    status = "🟢 Онлайн" if (current_time - last_t < 300) else "🔴 Офлайн"
                    text_list += f"👤 {uname or 'Номаълум'} — +{num} | {status} (ID: {uid})\n"
            bot.reply_to(message, text_list)
            return

        elif text == "4️⃣ Пайваст шудан":
            admin_states[ADMIN_ID] = "adm_connect_num"
            bot.reply_to(message, "🔗 Номери дилхоҳро нависед то бевосита пайваст шавед:")
            return

        elif text == "5️⃣ Хабар ба ҳама":
            admin_states[ADMIN_ID] = "adm_broadcast_text"
            bot.reply_to(message, "📢 Хабари худро нависед то ба ҳама равад:")
            return

        elif text == "6️⃣ Паёмҳои омада":
            rows = db_get_admin_sms()
            if not rows:
                bot.reply_to(message, "📭 Ҳоло ягон кас ба админ паём нафиристодааст.")
            else:
                text_sms = "📥 Паёмҳои омада ба админ:\n\n"
                for idx, (sname, snum, stxt, stime) in enumerate(rows, 1):
                    t_str = time.strftime('%Y-%m-%d %H:%M', time.localtime(stime))
                    text_sms += f"{idx}. Аз: {sname} (Рақам: +{snum})\n💬 Паём: {stxt}\n⏱ Вақт: {t_str}\n-------------------\n"
                bot.reply_to(message, text_sms)
            return

        if user_id in admin_states:
            state = admin_states.pop(user_id)
            if state == "adm_custom_number":
                if not text.isdigit() or len(text) != 8:
                    bot.reply_to(message, "❌ Рақам бояд дақиқ 8 рақам бошад!")
                    admin_states[ADMIN_ID] = "adm_custom_number"
                    return
                if db_get_user_id_by_number(text):
                    bot.reply_to(message, "❌ Инхел номер аллакай ҳаст! Рақами дигар нависед:")
                    admin_states[ADMIN_ID] = "adm_custom_number"
                    return
                db_set_number(ADMIN_ID, text)
                bot.send_message(message.chat.id, f"✅ Номери админ сохта шуд: +{text}", reply_markup=get_main_keyboard(ADMIN_ID))
                return
            elif state == "adm_connect_num":
                target_id = db_get_user_id_by_number(text)
                if not target_id:
                    bot.reply_to(message, "❌ Инхел номер нест!")
                else:
                    markup_call = InlineKeyboardMarkup()
                    markup_call.add(InlineKeyboardButton("📴 Хомӯш кардан", callback_data=f"hangup_{user_id}"))
                    try:
                        bot.send_message(target_id, f"🔗 Шумо бо муҳтарам админ пайваст шудед.", reply_markup=markup_call)
                    except:
                        pass
                    bot.reply_to(message, f"✅ Админ бо шумо пайваст аст (+{text}).")
                return
            elif state == "adm_broadcast_text":
                count = 0
                users = db_get_all_users()
                for uid, _, _, _ in users:
                    try:
                        bot.send_message(uid, f"📢 Хабар аз админ:\n\n{text}")
                        count += 1
                    except:
                        pass
                bot.reply_to(message, f"✅ Хабар ба {count} нафар фиристода шуд.")
                return
            elif state == "adm_sms_num":
                target_id = db_get_user_id_by_number(text)
                if not target_id:
                    bot.reply_to(message, "❌ Хато! Инхел номер вуҷуд надорад.")
                else:
                    admin_states[ADMIN_ID] = {"state": "adm_waiting_sms_text", "target": target_id}
                    bot.reply_to(message, "Чӣ гуфтан мехоҳед? Нависед:")
                return

    # Корбари оддӣ
    if text == "📱 Сохтани номер":
        if db_get_number(user_id):
            bot.reply_to(message, f"Шумо аллакай номер доред: +{db_get_number(user_id)}")
            return
        user_states[user_id] = "waiting_custom_number"
        bot.reply_to(message, "📱 Лутфан рақами дилхоҳи худро (8 рақам) нависед:")
        return

    elif text == "📞 Занг задан":
        user_states[user_id] = "waiting_user_call_num"
        bot.reply_to(message, "📞 Кадом номереро мехоҳед занг занед? Рақамашро нависед:")
        return

    elif text == "✉️ СМС фиристодан":
        user_states[user_id] = "waiting_user_sms_num"
        bot.reply_to(message, "✉️ Ба кадом номер СМС мезанед? Рақамро нависед:")
        return

    if user_id in user_states and user_states[user_id] == "waiting_custom_number":
        if not text.isdigit() or len(text) != 8:
            bot.reply_to(message, "❌ Рақам бояд дақиқ 8 рақам бошад!")
            return
        if db_get_user_id_by_number(text):
            bot.reply_to(message, "❌ Инхел номер аллакай ҳаст! Рақами дигар нависед:")
            return

        user_states.pop(user_id, None)
        db_set_number(user_id, text)
        bot.send_message(message.chat.id, f"✅ Номери нави шумо сохта шуд: `+{text}`", parse_mode="Markdown", reply_markup=get_main_keyboard(user_id))
        return

    if user_id in user_states:
        state = user_states[user_id]
        if state == "waiting_user_sms_num":
            if not text.isdigit() or len(text) != 8:
                bot.reply_to(message, "❌ Рақам бояд дақиқ 8 рақам бошад!")
                return
            target_id = db_get_user_id_by_number(text)
            if not target_id:
                bot.reply_to(message, "❌ Хато! Инхел номер вуҷуд надорад.")
                user_states.pop(user_id, None)
                return

            if target_id == ADMIN_ID:
                user_states[user_id] = {"state": "waiting_sms_to_admin"}
                bot.reply_to(message, "Пайваст шуда наметонед, паём нависед, ин админ аст")
                return

            target_name = name
            try:
                target_name = bot.get_chat(target_id).first_name or "Соҳиби номер"
            except:
                pass
            user_states[user_id] = {"state": "waiting_user_sms_text", "target": target_id}
            bot.reply_to(message, f"Муҳтарам *{target_name}*, чӣ гуфтан мехоҳед?", parse_mode="Markdown")
            return

        elif state == "waiting_user_call_num":
            user_states.pop(user_id, None)
            if not text.isdigit() or len(text) != 8:
                bot.reply_to(message, "❌ Рақам бояд дақиқ 8 рақам бошад!")
                return

            target_id = db_get_user_id_by_number(text)
            if not target_id:
                bot.reply_to(message, "❌ Хато! Инхел номер нест.")
                return

            if target_id == ADMIN_ID:
                bot.reply_to(message, "Пайваст шуда наметонед, паём нависед, ин админ аст")
                return
            if target_id == user_id:
                bot.reply_to(message, "⚠️ Шумо ба номери худ занг зада наметавонед!")
                return

            target_name = "Шахс"
            caller_name = name
            try:
                target_name = bot.get_chat(target_id).first_name or "Шахс"
            except:
                pass

            markup_call = InlineKeyboardMarkup()
            markup_call.row(
                InlineKeyboardButton("📞 Бардоштан", callback_data=f"ans_{user_id}"),
                InlineKeyboardButton("📴 Хомӯш кардан", callback_data=f"rej_{user_id}")
            )
            try:
                bot.send_message(target_id, f"🎶 Рингтон мелодия...\n📞 Муҳтарам *{target_name}*, муҳтарам *{caller_name}* ба шумо занг мезанад!", reply_markup=markup_call, parse_mode="Markdown")
                bot.reply_to(message, "Занг рафт...")
            except:
                bot.reply_to(message, f"Муҳтарам *{target_name}* дар телеграм нест", parse_mode="Markdown")
            return

    # Мустақиман задани рақам дар чат
    if text.isdigit() and len(text) == 8:
        target_id = db_get_user_id_by_number(text)
        if not target_id:
            bot.reply_to(message, "❌ Инхел номер нест!")
            return

        if target_id == ADMIN_ID:
            user_states[user_id] = {"state": "waiting_sms_to_admin"}
            bot.reply_to(message, "Пайваст шуда наметонед, паём нависед, ин админ аст")
            return
        if target_id == user_id:
            bot.reply_to(message, "⚠️ Шумо ба номери худ навишта наметавонед!")
            return

        target_name = "Соҳиби номер"
        try:
            target_name = bot.get_chat(target_id).first_name or "Соҳиби номер"
        except:
            pass
        user_states[user_id] = {"state": "waiting_user_sms_text", "target": target_id}
        bot.reply_to(message, f"Муҳтарам *{target_name}*, чӣ гуфтан мехоҳед?", parse_mode="Markdown")
        return

# ---------- Callback-ҳо ----------
@bot.callback_query_handler(func=lambda call: call.data.startswith(("ans_", "rej_", "hangup_", "random_hangup")))
def call_callbacks(call):
    data = call.data
    user_id = call.from_user.id
    name = call.from_user.first_name or "Муҳтарам"

    if data == "random_hangup":
        if user_id in chat_partners:
            partner_id = chat_partners[user_id]
            p_name = name
            chat_partners.pop(user_id, None)
            chat_partners.pop(partner_id, None)
            try:
                bot.edit_message_text(f"Муҳтарам *{p_name}* зангро кат кард", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
            except:
                pass
            try:
                bot.send_message(partner_id, f"Муҳтарам *{p_name}* зангро кат кард", parse_mode="Markdown")
            except:
                pass
        bot.answer_callback_query(call.id)
        return

    if data.startswith("ans_"):
        caller_id = int(data.split("_")[1])
        caller_name = "Шахс"
        target_name = name
        try:
            caller_name = bot.get_chat(caller_id).first_name or "Шахс"
        except:
            pass

        markup_h = InlineKeyboardMarkup()
        markup_h.add(InlineKeyboardButton("📴 Хомӯш кардан", callback_data=f"hangup_{caller_id}"))

        try:
            bot.edit_message_text(f"Муҳтарам *{target_name}*, муҳтарам *{caller_name}* пайваст шуди бо вай", call.message.chat.id, call.message.message_id, reply_markup=markup_h, parse_mode="Markdown")
        except:
            pass
        try:
            bot.send_message(caller_id, f"Муҳтарам *{caller_name}*, муҳтарам *{target_name}* пайваст шуди бо вай", reply_markup=markup_h, parse_mode="Markdown")
        except:
            pass

    elif data.startswith("rej_"):
        caller_id = int(data.split("_")[1])
        target_name = name
        try:
            bot.edit_message_text("📴 Занг рад карда шуд.", call.message.chat.id, call.message.message_id)
        except:
            pass
        try:
            bot.send_message(caller_id, f"Муҳтарам *{target_name}* зангро кат кард ё бардошт", parse_mode="Markdown")
        except:
            pass

    elif data.startswith("hangup_"):
        caller_id = int(data.split("_")[1])
        target_name = name
        try:
            bot.edit_message_text("📴 Хомӯш карда шуд", call.message.chat.id, call.message.message_id)
        except:
            pass
        try:
            bot.send_message(caller_id, f"Муҳтарам *{target_name}* зангро кат кард", parse_mode="Markdown")
        except:
            pass

    bot.answer_callback_query(call.id)

# ---------- Иҷрои бот ----------
if __name__ == "__main__":
    print("🤖 Бот бомуваффақият ба кор омад...")
    bot.infinity_polling()
