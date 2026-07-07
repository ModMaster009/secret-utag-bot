import asyncio
import os
from pyrogram import Client, filters
from pyrogram.errors import FloodWait, SessionPasswordNeeded

# ================= SOZLAMALAR =================
# My.telegram.org saytidan olishingiz mumkin
API_ID = 36427121  # O'zingiznikini qo'yishingiz mumkin
API_HASH = "f4b857c7d7e08dce9244615ef32d7cc7"

# BotFather'dan olingan YANGI bot tokeni (maxfiy bot uchun)
BOT_TOKEN = "8879978489:AAFT6PGszB7wFyKJ3SH2G99GNwGsVzS2tx8"
# ==============================================

bot_app = Client("utag_manager_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Vaqtinchalik xotira
user_states = {}
login_data = {}
user_clients = {}
active_tags = {}

async def start_user_client(user_id):
    """Foydalanuvchi akkauntini fonda ishga tushirish va buyruqlarni biriktirish"""
    session_name = f"session_{user_id}"
    if os.path.exists(f"{session_name}.session"):
        client = Client(session_name, api_id=API_ID, api_hash=API_HASH)
        
        try:
            await client.connect()
            # Tizimga haqiqatan kirilganligini tekshiramiz
            me = await client.get_me()
            if not me:
                raise Exception("Not authorized")
        except Exception:
            await client.disconnect()
            # Chala qolgan yoki xato sessiyani o'chirib tashlaymiz
            if os.path.exists(f"{session_name}.session"):
                os.remove(f"{session_name}.session")
            return False
        
        # .atag buyrug'ini foydalanuvchi akkauntiga ulash
        @client.on_message(filters.regex(r"^\.atag(?:\s+|$)") & filters.me)
        async def start_atag(cli, message):
            chat_id = message.chat.id
            if len(message.text.split()) > 1:
                text_to_add = message.text.split(None, 1)[1]
            else:
                text_to_add = ""
                
            await message.edit_text("⏳ **Maxfiy U-Tag boshlanmoqda...**")
            active_tags[f"{user_id}_{chat_id}"] = True
            
            try:
                members = []
                async for member in cli.get_chat_members(chat_id):
                    if not active_tags.get(f"{user_id}_{chat_id}"):
                        break
                    if member.user.is_bot or member.user.is_deleted:
                        continue
                    if member.user.username:
                        members.append(f"@{member.user.username}")
                
                if not members:
                    await message.edit_text("❌ Guruhdan @username'li foydalanuvchilar topilmadi.")
                    return
                    
                await message.delete()
                
                for mention in members:
                    if not active_tags.get(f"{user_id}_{chat_id}"):
                        await cli.send_message(chat_id, "🛑 **U-Tag to'xtatildi.**")
                        break
                        
                    tag_text = mention
                    if text_to_add:
                        tag_text += f"\n\n{text_to_add}"
                        
                    try:
                        await cli.send_message(chat_id, tag_text)
                        await asyncio.sleep(3) # Anti-spam
                    except FloodWait as e:
                        await asyncio.sleep(e.value + 2)
                    except Exception as e:
                        print(f"Xatolik: {e}")
                        
                if active_tags.get(f"{user_id}_{chat_id}"):
                    await cli.send_message(chat_id, "✅ **U-Tag yakunlandi!**")
                    active_tags.pop(f"{user_id}_{chat_id}", None)
                    
            except Exception as e:
                await message.edit_text(f"❌ Xatolik yuz berdi: {e}")

        # .stop buyrug'ini biriktirish
        @client.on_message(filters.regex(r"^\.stop(?:\s+|$)") & filters.me)
        async def stop_atag(cli, message):
            chat_id = message.chat.id
            if active_tags.get(f"{user_id}_{chat_id}"):
                active_tags[f"{user_id}_{chat_id}"] = False
                await message.edit_text("🛑 **To'xtatilmoqda...**")
            else:
                await message.edit_text("⚠️ Hozir bu guruhda U-Tag jarayoni ketmayapti. Boshlash uchun `.atag` yozing")

        # Start call endi telefon raqam so'ramaydi, chunki biz auth qilinganini tekshirdik
        if not client.is_initialized:
            await client.initialize()
        return True
    return False

# ================= BOT INTERFEYSI =================

@bot_app.on_message(filters.regex(r"^/start") & filters.private)
async def start_cmd(client, message):
    user_id = message.from_user.id
    
    # Oldingi login urinishlarini bekor qilish (double allow ga qarshi)
    if user_id in login_data and "client" in login_data[user_id]:
        try:
            await login_data[user_id]["client"].disconnect()
        except:
            pass
    login_data.pop(user_id, None)
    
    if await start_user_client(user_id):
        user_states.pop(user_id, None)
        await message.reply_text("✅ Siz allaqachon tizimga kirgansiz!\n\nIstalgan guruhga kirib `.atag matn` yoki to'xtatish uchun `.stop` buyruqlarini ishlatavering.")
    else:
        user_states[user_id] = "wait_phone"
        await message.reply_text("👋 Assalomu alaykum! Maxfiy U-Tag botiga xush kelibsiz.\n\n📱 Iltimos, Telegram raqamingizni xalqaro formatda yuboring (masalan: +998901234567):")

@bot_app.on_message(filters.text & filters.private)
async def handle_text(client, message):
    user_id = message.from_user.id
    state = user_states.get(user_id)
    text = message.text
    
    if state == "wait_phone":
        phone = text.strip()
        # Nomerda + bo'lmasa, uni qo'shib qo'yamiz (Qirg'iziston va boshqalar uchun Telegram talabi)
        phone_cleaned = "".join(c for c in phone if c.isdigit())
        phone = "+" + phone_cleaned
        
        login_data[user_id] = {"phone": phone}
        temp_client = Client(f"session_{user_id}", api_id=API_ID, api_hash=API_HASH)
        await temp_client.connect()
        login_data[user_id]["client"] = temp_client
        
        try:
            sent_code = await temp_client.send_code(phone)
            login_data[user_id]["phone_code_hash"] = sent_code.phone_code_hash
            user_states[user_id] = "wait_code"
            await message.reply_text("📩 Telegramingizga kod yuborildi!\n\nIltimos kodni yozing (masalan: `12345` bo'lsa `1 2 3 4 5` shaklida bo'sh joy tashlab yozing):")
        except Exception as e:
            await message.reply_text(f"❌ Xatolik yuz berdi: {e}\n\nRaqamni to'g'ri kiritganingizga ishonch hosil qiling va /start bosing (Mobodo kod orasini ochishni unutgan bo'lsangiz, qaytadan login qiling).")
            
    elif state == "wait_code":
        code = text.replace(" ", "")
        temp_client = login_data[user_id]["client"]
        phone = login_data[user_id]["phone"]
        phone_code_hash = login_data[user_id]["phone_code_hash"]
        
        try:
            await temp_client.sign_in(phone, phone_code_hash, code)
            await message.reply_text("✅ Tizimga muvaffaqiyatli kirdingiz!\n\nEndi istalgan guruhga borib `.atag salom` deb yozishingiz mumkin. Bot sizning o'rningizga ishlaydi.")
            user_states.pop(user_id, None)
            await temp_client.disconnect()
            await start_user_client(user_id) # Fonda ishga tushirish
        except SessionPasswordNeeded:
            user_states[user_id] = "wait_password"
            await message.reply_text("🔐 Ikki bosqichli parol o'rnatilgan ekan.\nIltimos, parolingizni kiriting:")
        except Exception as e:
            await message.reply_text(f"❌ Xato kod kiritildi: {e}\n\nQaytadan /start bosing.")

    elif state == "wait_password":
        password = text
        temp_client = login_data[user_id]["client"]
        try:
            await temp_client.check_password(password)
            await message.reply_text("✅ Tizimga muvaffaqiyatli kirdingiz!\n\nEndi istalgan guruhga borib `.atag salom` deb yozishingiz mumkin.")
            user_states.pop(user_id, None)
            await temp_client.disconnect()
            await start_user_client(user_id) # Fonda ishga tushirish
        except Exception as e:
            await message.reply_text(f"❌ Noto'g'ri parol: {e}\n\nQaytadan urinib ko'ring yoki /start bosing.")

if __name__ == "__main__":
    print("=========================================")
    print(" MAXFIY U-TAG MENEJER BOTI ISHGA TUSHDI")
    print("=========================================")
    
    # Avvaldan mavjud sessiyalarni avtomatik fonda ishga tushirish
    for file in os.listdir():
        if file.startswith("session_") and file.endswith(".session"):
            uid = file.split("_")[1].split(".")[0]
            try:
                bot_app.loop.run_until_complete(start_user_client(int(uid)))
                print(f"{uid} uchun sessiya faollashtirildi.")
            except:
                pass
                
    bot_app.run()
