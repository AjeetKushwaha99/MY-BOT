# -*- coding: utf-8 -*-
# Telegram File Sharing Bot - LITE Version
# Mobile-friendly code by AI Assistant

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient
import datetime
import hashlib
import os

# ========== CONFIG ==========
API_ID = int(os.environ.get("API_ID", "37067823"))
API_HASH = os.environ.get("API_HASH", "ed9e62ed4538d2d2b835fb54529c358f")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8214501704:AAE7kuiVAqDuID8KRzKTDTSDlBd0MseYCF0")
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", "-1003777551559"))
OWNER_ID = int(os.environ.get("OWNER_ID", "6549083920"))
MONGO_URL = os.environ.get("MONGO_URL", "mongodb+srv://Ajeet:NEWPASSWORD@cluster0.3lxz0p7.mongodb.net/filebot?retryWrites=true&w=majority")
SHORTENER_API = os.environ.get("SHORTENER_API", "5cbb1b2088d2ed06d7e9feae35dc17cc033169d6")
SHORTENER_URL = os.environ.get("SHORTENER_URL", "https://vplink.in")

# ========== DATABASE SETUP ==========
mongo_client = MongoClient(MONGO_URL)
db = mongo_client['filebot']
users_collection = db['users']
files_collection = db['files']

# ========== BOT INITIALIZE ==========
app = Client(
    "FileShareBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ========== HELPER FUNCTIONS ==========

def generate_file_id():
    """Unique file ID banata hai"""
    return hashlib.md5(str(datetime.datetime.now()).encode()).hexdigest()[:8]

def is_user_verified(user_id):
    """Check karta hai user verified hai ya nahi"""
    user = users_collection.find_one({"user_id": user_id})
    if not user:
        return False
    
    verified_at = user.get("verified_at")
    if not verified_at:
        return False
    
    # 48 hours = 172800 seconds
    time_diff = (datetime.datetime.now() - verified_at).total_seconds()
    
    if time_diff < 172800:  # 48 hours
        return True
    else:
        return False

def shorten_url(long_url):
    """VPLinks se URL shorten karta hai"""
    import requests
    
    api_url = f"https://vplink.in/api?api={SHORTENER_API}&url={long_url}"
    
    try:
        response = requests.get(api_url).json()
        if response.get("status") == "success":
            return response.get("shortenedUrl")
        else:
            return long_url
    except:
        return long_url

# ========== BOT COMMANDS ==========

@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    user_id = message.from_user.id
    
    # Agar user database mein nahi hai to add karo
    if not users_collection.find_one({"user_id": user_id}):
        users_collection.insert_one({
            "user_id": user_id,
            "username": message.from_user.username,
            "verified_at": None,
            "joined_at": datetime.datetime.now()
        })
    
    # Agar link ke saath aaya hai (file request)
    if len(message.text.split()) > 1:
        file_code = message.text.split()[1]
        
        # Check if user verified hai
        if not is_user_verified(user_id):
            # Shortener link bhejo
            verify_url = f"https://telegram.me/{(await client.get_me()).username}?start=verify_{user_id}"
            short_link = shorten_url(verify_url)
            
            await message.reply_text(
                f"⚠️ **Access Denied!**\n\n"
                f"Bot use karne ke liye pehle **verify** karo.\n\n"
                f"🔗 **Verify Link:** {short_link}\n\n"
                f"✅ Verify karne ke baad **48 hours** tak bot use kar sakte ho!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔓 Verify Now", url=short_link)
                ]])
            )
            return
        
        # User verified hai - file bhejo
        file_data = files_collection.find_one({"file_id": file_code})
        
        if not file_data:
            await message.reply_text("❌ **File not found!**\n\nYe link invalid ya expired hai.")
            return
        
        # Channel se file copy karke bhejo
        try:
            await client.copy_message(
                chat_id=message.chat.id,
                from_chat_id=CHANNEL_ID,
                message_id=file_data['message_id']
            )
            
            # Download count badhao
            files_collection.update_one(
                {"file_id": file_code},
                {"$inc": {"downloads": 1}}
            )
            
            await message.reply_text("✅ **File delivered successfully!**")
            
        except Exception as e:
            await message.reply_text(f"❌ Error: {str(e)}")
            
    else:
        # Normal start message
        await message.reply_text(
            f"👋 **Welcome {message.from_user.first_name}!**\n\n"
            f"Main ek **File Sharing Bot** hoon.\n\n"
            f"📁 Files share karne ke liye mujhe file bhejo (Admin only)\n"
            f"🔗 Link se file download karne ke liye verify karo\n\n"
            f"❓ Help ke liye: /help"
        )

@app.on_message(filters.command("verify") & filters.private)
async def verify_command(client, message):
    user_id = message.from_user.id
    
    # User ko verify karo
    users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"verified_at": datetime.datetime.now()}},
        upsert=True
    )
    
    await message.reply_text(
        "✅ **Verification Successful!**\n\n"
        "🎉 Tumhe **48 hours** ka access mil gaya hai!\n\n"
        "Ab tum bot se files download kar sakte ho. 😊"
    )

@app.on_message(filters.command("stats") & filters.private & filters.user(OWNER_ID))
async def stats_command(client, message):
    """Admin ke liye stats"""
    total_users = users_collection.count_documents({})
    total_files = files_collection.count_documents({})
    verified_users = users_collection.count_documents({"verified_at": {"$ne": None}})
    
    await message.reply_text(
        f"📊 **Bot Statistics**\n\n"
        f"👥 Total Users: **{total_users}**\n"
        f"✅ Verified Users: **{verified_users}**\n"
        f"📁 Total Files: **{total_files}**"
    )

@app.on_message(filters.document | filters.video | filters.audio | filters.photo)
async def handle_files(client, message):
    """File upload handle karta hai (Admin only)"""
    user_id = message.from_user.id
    
    if user_id != OWNER_ID:
        await message.reply_text("❌ Only admin can upload files!")
        return
    
    # File ko channel mein forward karo
    try:
        forwarded = await message.forward(CHANNEL_ID)
        
        # Unique file ID generate karo
        file_id = generate_file_id()
        
        # Database mein save karo
        files_collection.insert_one({
            "file_id": file_id,
            "message_id": forwarded.id,
            "file_name": getattr(message.document or message.video or message.audio, 'file_name', 'Unknown'),
            "uploaded_at": datetime.datetime.now(),
            "downloads": 0
        })
        
        # Share link banao
        bot_username = (await client.get_me()).username
        share_link = f"https://t.me/{bot_username}?start={file_id}"
        
        await message.reply_text(
            f"✅ **File uploaded successfully!**\n\n"
            f"🔗 **Share Link:**\n`{share_link}`\n\n"
            f"📋 **File ID:** `{file_id}`",
            quote=True
        )
        
    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")

@app.on_message(filters.command("help"))
async def help_command(client, message):
    help_text = """
📖 **Help Guide**

**For Users:**
🔗 Link pe click karo
✅ Verify karo (ads dekhne padenge)
📥 File download karo
⏰ 48 hours tak access milega

**For Admin:**
📤 Mujhe file bhejo
🔗 Share link mil jayega
📊 Stats: /stats

**Need Support?**
Contact: @YourSupportChannel
"""
    await message.reply_text(help_text)

# ========== BOT START ==========
print("🚀 Bot starting...")
app.run()
print("✅ Bot is running!")
