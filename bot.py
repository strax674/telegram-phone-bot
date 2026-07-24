import time
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

BOT_TOKEN = "8850375131:AAFfM6CASg_vI_vQ5RKvp4y-nlz_dPKyjFA"
ADMIN_ID = 6189671221

bot = telebot.TeleBot(BOT_TOKEN)

user_numbers = {}          # {user_id: number}
number_to_user = {}        # {number: user_id}
user_names = {}            # {user_id: first_name}
admin_states = {}          # Ҳолати админ
user_states = {}           # Ҳолати корбарон
user_last_seen = {}        # Вақти охирини фаъолият
admin_received_sms = []    # Паёмҳои админ
waiting_random_users = []  # Барои пайвасти тасодуфӣ
chat_partners = {}         # Барои суҳбати тасодуфӣ

def get_main_keyboard(user_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)

    if user_id == ADMIN_ID:
        if ADMIN_ID in user_numbers:
            my_num = user_numbers[ADMIN_ID]
            btn_num = KeyboardButton(f"📱 Номери ман: +{my_num}")
        else:
            btn_num = KeyboardButton("1️⃣ КМ Сохтани номер")

        markup.add(btn_num, KeyboardButton("2️⃣ СМС"))
        markup.add(KeyboardButton("3️⃣ Дидани одамон"), KeyboardButton("4️⃣ Пайваст шудан"))
        markup.add(KeyboardButton("5️⃣ Хабар ба ҳама"), KeyboardButton("6️⃣ Паёмҳои омада"))
    else:
        if user_id in user_numbers:
            my_num = user_numbers[user_id]
            btn_num = KeyboardButton(f"📱 Номери ман: +{my_num}")
        else:
            btn_num = KeyboardButton("📱 Сохтани номер")

        markup.add(btn_num, KeyboardButton("📞 Занг задан"))
        markup.add(KeyboardButton("✉️ СМС фиристодан"))
        markup.add(KeyboardButton("🔗 Пайваст шудан бо бегонагон"))

    return markup

@bot.message_handler(commands=['start'])
def start_handler(message):
    user_id = message.from_user.id
    name = message.from_user.first_name
    user_names[user_id] = name
    user_last_seen[user_id] = time.time()

    markup = get_main_keyboard(user_id)

    if user_id == ADMIN_ID:
        text = f"👑 Салом Админ {name}! Панели махсуси шумо кушода шуд:"
    else:
        text = f"Салом {name}! Инҷо телефони телеграми аст. Тугмаҳои поёни экранро истифода баред:"

    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    name = message.from_user.first_name
    user_names[user_id] = name
    user_last_seen[user_id] = time.time()
    text = message.text.strip()

    if user_id in chat_partners:
        partner_id = chat_partners[user_id]
        try:
            bot.send_message(partner_id, f"💬 {name}: {text}")
        except:
            pass
        return

    if "Номери ман" in text:
        my_num = user_numbers.get(user_id, "Мавҷуд нест")
        bot.reply_to(message, f"📱 Номери сохтагиатон: `+{my_num}`\nИн номер сабт шудааст ва дигар алиш намешавад.", parse_mode="Markdown")
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
            while partner_id not in user_names and waiting_random_users:
                partner_id = waiting_random_users.pop(0)

            if partner_id == user_id:
                waiting_random_users.append(user_id)
                bot.reply_to(message, "⏳ Касе сухбат надорад, 1 минут интизор шавед...")
                return

            chat_partners[user_id] = partner_id
            chat_partners[partner_id] = user_id

            p_name = user_names.get(partner_id, "Бегона")
            u_name = user_names.get(user_id, "Бегона")

            markup_hang = InlineKeyboardMarkup()
            markup_hang.add(InlineKeyboardButton("📴 Хомӯш кардан", callback_data="random_hangup"))

            bot.send_message(user_id, f"Муҳтарам *{p_name}* пайваст шуди бо вай", reply_markup=markup_hang, parse_mode="Markdown")
            bot.send_message(partner_id, f"Муҳтарам *{u_name}* пайваст шуди бо вай", reply_markup=markup_hang, parse_mode="Markdown")
        else:
            waiting_random_users.append(user_id)
            bot.reply_to(message, "⏳ Касе сухбат надорад, 1 минут интизор шавед...")
        return

    # 1. Санҷиши паём фиристодан ба Админ
    if user_id in user_states and isinstance(user_states[user_id], dict):
        state_data = user_states[user_id]
        if state_data.get("state") == "waiting_sms_to_admin":
            user_states.pop(user_id, None)
            sender_num = user_numbers.get(user_id, "Номаълум")
            sender_name = user_names.get(user_id, "Муштарӣ")

            admin_received_sms.append({
                "sender_id": user_id,
                "sender_name": sender_name,
                "sender_num": sender_num,
                "text": text,
                "time": time.time()
            })

            bot.reply_to(message, "Паём рафт")
            try:
                bot.send_message(ADMIN_ID, f"📩 Паёми нав аз муҳтарам *{sender_name}* (+{sender_num}): {text}", parse_mode="Markdown")
            except:
                pass
            return

        elif state_data.get("state") == "waiting_user_sms_text":
            data = user_states.pop(user_id)
            target_id = data["target"]
            sender_name = user_names.get(user_id, "Муштарӣ")

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
            if ADMIN_ID in user_numbers:
                bot.reply_to(message, f"Шумо аллакай номер доред: +{user_numbers[ADMIN_ID]}")
                return
            admin_states[ADMIN_ID] = "adm_custom_number"
            bot.reply_to(message, "📱 Номери дилхоҳи худро (8 рақам) нависед:")
            return

        elif text == "2️⃣ СМС":
            admin_states[ADMIN_ID] = "adm_sms_num"
            bot.reply_to(message, "✉️ Ба кадом номер СМС равон мекунед? Рақамро нависед:")
            return

        elif text == "3️⃣ Дидани одамон":
            if not user_numbers:
                text_list = "📭 Ҳоло ягон кас номер насохтааст."
            else:
                text_list = "📋 Рӯйхати одамони номер сохтагӣ:\n\n"
                current_time = time.time()
                for uid, num in user_numbers.items():
                    uname = user_names.get(uid, "Номаълум")
                    last_t = user_last_seen.get(uid, 0)
                    status = "🟢 Онлайн" if (current_time - last_t < 300) else "🔴 Офлайн"
                    text_list += f"👤 {uname} — +{num} | {status} (ID: {uid})\n"
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
            if not admin_received_sms:
                bot.reply_to(message, "📭 Ҳоло ягон кас ба админ паём нафиристодааст.")
            else:
                text_sms = "📥 Паёмҳои омада ба админ:\n\n"
                for idx, item in enumerate(admin_received_sms, 1):
                    t_str = time.strftime('%Y-%m-%d %H:%M', time.localtime(item['time']))
                    text_sms += f"{idx}. Аз: {item['sender_name']} (Рақам: +{item['sender_num']})\n💬 Паём: {item['text']}\n⏱ Вақт: {t_str}\n-------------------\n"
                bot.reply_to(message, text_sms)
            return

        if user_id in admin_states:
            state = admin_states.pop(user_id)
            if state == "adm_custom_number":
                if not text.isdigit() or len(text) != 8:
                    bot.reply_to(message, "❌ Рақам бояд дақиқ 8 рақам бошад!")
                    admin_states[ADMIN_ID] = "adm_custom_number"
                    return
                user_numbers[ADMIN_ID] = text
                number_to_user[text] = ADMIN_ID
                bot.send_message(message.chat.id, f"✅ Номери админ сохта шуд: +{text}", reply_markup=get_main_keyboard(ADMIN_ID))
                return
            elif state == "adm_connect_num":
                if text not in number_to_user:
                    bot.reply_to(message, "❌ Инхел номер нест!")
                else:
                    target_id = number_to_user[text]
                    markup_call = InlineKeyboardMarkup()
                    markup_call.add(InlineKeyboardButton("📴 Хомӯш кардан", callback_data=f"hangup_{user_id}"))
                    bot.send_message(target_id, f"🔗 Шумо бо муҳтарам админ пайваст шудед.", reply_markup=markup_call)
                    bot.reply_to(message, f"✅ Админ бо шумо пайваст аст (+{text}).")
                return
            elif state == "adm_broadcast_text":
                count = 0
                for uid in user_numbers.keys():
                    try:
                        bot.send_message(uid, f"📢 Хабар аз админ:\n\n{text}")
                        count += 1
                    except:
                        pass
                bot.reply_to(message, f"✅ Хабар ба {count} нафар фиристода шуд.")
                return
            elif state == "adm_sms_num":
                if text not in number_to_user:
                    bot.reply_to(message, "❌ Хато! Инхел номер вуҷуд надорад.")
                else:
                    target_id = number_to_user[text]
                    admin_states[ADMIN_ID] = {"state": "adm_waiting_sms_text", "target": target_id}
                    bot.reply_to(message, "Чӣ гуфтан мехоҳед? Нависед:")
                return

    # Корбари оддӣ
    if text == "📱 Сохтани номер":
        if user_id in user_numbers:
            bot.reply_to(message, f"Шумо аллакай номер доред: +{user_numbers[user_id]}")
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
        if text in number_to_user:
            bot.reply_to(message, "❌ Инхел номер аллакай ҳаст! Рақами дигар нависед:")
            return

        user_states.pop(user_id, None)
        user_numbers[user_id] = text
        number_to_user[text] = user_id
        bot.send_message(message.chat.id, f"✅ Номери нави шумо сохта шуд: `+{text}`", parse_mode="Markdown", reply_markup=get_main_keyboard(user_id))
        return

    if user_id in user_states:
        state = user_states[user_id]
        if state == "waiting_user_sms_num":
            if not text.isdigit() or len(text) != 8:
                bot.reply_to(message, "❌ Рақам бояд дақиқ 8 рақам бошад!")
                return
            if text not in number_to_user:
                bot.reply_to(message, "❌ Хато! Инхел номер вуҷуд надорад.")
                user_states.pop(user_id, None)
                return

            target_id = number_to_user[text]
            if target_id == ADMIN_ID:
                user_states[user_id] = {"state": "waiting_sms_to_admin"}
                bot.reply_to(message, "Пайваст шуда наметонед, паём нависед, ин админ аст")
                return

            target_name = user_names.get(target_id, "Соҳиби номер")
            user_states[user_id] = {"state": "waiting_user_sms_text", "target": target_id}
            bot.reply_to(message, f"Муҳтарам *{target_name}*, чӣ гуфтан мехоҳед?", parse_mode="Markdown")
            return

        elif state == "waiting_user_call_num":
            user_states.pop(user_id, None)
            if not text.isdigit() or len(text) != 8:
                bot.reply_to(message, "❌ Рақам бояд дақиқ 8 рақам бошад!")
                return

            if text not in number_to_user:
                bot.reply_to(message, "❌ Хато! Инхел номер нест.")
                return

            target_id = number_to_user[text]
            if target_id == ADMIN_ID:
                bot.reply_to(message, "Пайваст шуда наметонед, паём нависед, ин админ аст")
                return
            if target_id == user_id:
                bot.reply_to(message, "⚠️ Шумо ба номери худ занг зада наметавонед!")
                return

            target_name = user_names.get(target_id, "Шахс")
            caller_name = user_names.get(user_id, "Муштарӣ")

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
        if text not in number_to_user:
            bot.reply_to(message, "❌ Инхел номер нест!")
            return

        target_id = number_to_user[text]
        if target_id == ADMIN_ID:
            user_states[user_id] = {"state": "waiting_sms_to_admin"}
            bot.reply_to(message, "Пайваст шуда наметонед, паём нависед, ин админ аст")
            return
        if target_id == user_id:
            bot.reply_to(message, "⚠️ Шумо ба номери худ навишта наметавонед!")
            return

        target_name = user_names.get(target_id, "Соҳиби номер")
        user_states[user_id] = {"state": "waiting_user_sms_text", "target": target_id}
        bot.reply_to(message, f"Муҳтарам *{target_name}*, чӣ гуфтан мехоҳед?", parse_mode="Markdown")
        return

@bot.callback_query_handler(func=lambda call: call.data.startswith(("ans_", "rej_", "hangup_", "random_hangup")))
def call_callbacks(call):
    data = call.data
    user_id = call.from_user.id

    if data == "random_hangup":
        if user_id in chat_partners:
            partner_id = chat_partners[user_id]
            p_name = user_names.get(user_id, "Муҳтарам")
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
        caller_name = user_names.get(caller_id, "Шахс")
        target_name = user_names.get(user_id, "Шахс")

        markup_h = InlineKeyboardMarkup()
        markup_h.add(InlineKeyboardButton("📴 Хомӯш кардан", callback_data=f"hangup_{caller_id}"))

        bot.edit_message_text(f"Муҳтарам *{target_name}*, муҳтарам *{caller_name}* пайваст шуди бо вай", call.message.chat.id, call.message.message_id, reply_markup=markup_h, parse_mode="Markdown")
        try:
            bot.send_message(caller_id, f"Муҳтарам *{caller_name}*, муҳтарам *{target_name}* пайваст шуди бо вай", reply_markup=markup_h, parse_mode="Markdown")
        except:
            pass

    elif data.startswith("rej_"):
        caller_id = int(data.split("_")[1])
        target_name = user_names.get(user_id, "Муҳтарам")
        bot.edit_message_text("📴 Занг рад карда шуд.", call.message.chat.id, call.message.message_id)
        try:
            bot.send_message(caller_id, f"Муҳтарам *{target_name}* зангро кат кард ё бардошт", parse_mode="Markdown")
        except:
            pass

    elif data.startswith("hangup_"):
        caller_id = int(data.split("_")[1])
        target_name = user_names.get(user_id, "Муҳтарам")
        bot.edit_message_text("📴 Хомӯш карда шуд", call.message.chat.id, call.message.message_id)
        try:
            bot.send_message(caller_id, f"Муҳтарам *{target_name}* зангро кат кард", parse_mode="Markdown")
        except:
            pass

    bot.answer_callback_query(call.id)

print("🤖 Бот бомуваффақият ба кор омад...")
bot.infinity_polling()
