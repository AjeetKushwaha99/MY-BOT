# -*- coding: utf-8 -*-
# Telegram File Sharing Bot - CLEAN & PROFESSIONAL
# All bugs fixed: No duplicate messages, clean interface

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient
import datetime, hashlib, os, requests

# ========== CONFIG ==========
API_ID = 37067823
API_HASH = "ed9e62ed4538d2d2b835fb54529c358f"
BOT_TOKEN = "8214501704:AAE7kuiVAqDuID8KRzKTDTSDlBd0MseYCF0"
CHANNEL_ID = -1003777551559
OWNER_ID = 6549083920
MONGO_URL = "mongodb+srv://Ajeet:XgGFRFWVT2NwWipw@cluster0.3lxz0p7.mongodb.net/?appName=Cluster0"
SHORTENER_API = "5cbb1b2088d2ed06d7e9feae35dc17cc033169d6"
SHORTENER_URL = "https://vplink.in"

print("🤖 Bot starting...")

# ========== DATABASE ==========
try:
    mongo = MongoClient(MONGO_URL)
    db = mongo['filebot']
    users = db['users']
    files = db['files']
    print("✅ Database connected")
except Exception as e:
    print(f"❌ Database error: {e}")

# ========== BOT ==========
app = Client("FileBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ========== FUNCTIONS ==========
def gen_id():
    return hashlib.md5(str(datetime.datetime.now()).encode()).hexdigest()[:8]

def verified(uid):
    u = users.find_one({"user_id": uid})
    if not u or not u.get("verified_at"): return False
    return (datetime.datetime.now() - u["verified_at"]).total_seconds() < 172800

def shorten(url):
    try:
        r = requests.get(f"{SHORTENER_URL}/api?api={SHORTENER_API}&url={url}", timeout=10).json()
        return r.get("shortenedUrl", url)
    except: return url

# ========== COMMANDS ==========
@app.on_message(filters.command("start") & filters.private)
async def start(c, m):
    uid = m.from_user.id
    
    # IGNORE BOT'S OWN MESSAGES COMPLETELY
    if uid == 8214501704:
        return
    
    # Add user to database
    if not users.find_one({"user_id": uid}):
        users.insert_one({
            "user_id": uid,
            "username": m.from_user.username,
            "first_name": m.from_user.first_name,
            "verified_at": None,
            "joined_at": datetime.datetime.now()
        })
    
    # Check if file request
    if len(m.text.split()) > 1:
        code = m.text.split()[1]
        
        # Verification callback
        if code.startswith("verify_"):
            users.update_one({"user_id": uid}, {"$set": {"verified_at": datetime.datetime.now()}})
            await m.reply(
                "🎉 **Verification Successful!**\n\n"
                "✅ You now have **48 hours** of unlimited access!\n\n"
                "📁 You can download all files without any restrictions.\n"
                "⏰ Access will expire after 48 hours."
            )
            return
        
        # File download request
        if not verified(uid):
            bot_username = (await c.get_me()).username
            link = shorten(f"https://t.me/{bot_username}?start=verify_{uid}")
            
            await m.reply(
                "🔒 **Verification Required**\n\n"
                "To access files, please verify first.\n\n"
                f"🔗 **Click below to verify:**",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅ Verify Now", url=link)
                ]])
            )
            return
        
        # User verified, send file
        f = files.find_one({"file_id": code})
        if not f:
            await m.reply("❌ **File Not Found**\n\nThis link may be expired or invalid.")
            return
        
        try:
            await c.copy_message(m.chat.id, CHANNEL_ID, f['message_id'])
            files.update_one({"file_id": code}, {"$inc": {"downloads": 1}})
            # NO EXTRA MESSAGE - file itself is enough
        except Exception as e:
            await m.reply(f"❌ **Error:** {str(e)}")
    
    else:
        # Welcome message
        await m.reply(
            f"👋 **Welcome {m.from_user.first_name}!**\n\n"
            "🤖 **FileShare Bot**\n\n"
            "📌 **Features:**\n"
            "• Fast file downloads\n"
            "• One-time verification\n"
            "• 48-hour access\n"
            "• Secure & reliable\n\n"
            "📁 **How to use:**\n"
            "1. Get a file link\n"
            "2. Verify once (free)\n"
            "3. Download instantly!\n\n"
            "❓ Need help? Use /help"
        )

@app.on_message(filters.command("stats") & filters.private)
async def stats(c, m):
    uid = m.from_user.id
    
    if uid != OWNER_ID:
        return  # Silent ignore for non-owners
    
    total = users.count_documents({})
    ver = users.count_documents({"verified_at": {"$ne": None}})
    fil = files.count_documents({})
    
    await m.reply(
        f"📊 **Bot Statistics**\n\n"
        f"👥 Total Users: `{total}`\n"
        f"✅ Verified Users: `{ver}`\n"
        f"📁 Total Files: `{fil}`\n\n"
        f"⚡ Status: **Active**"
    )

@app.on_message((filters.document | filters.video | filters.audio | filters.photo) & filters.private)
async def upload(c, m):
    uid = m.from_user.id
    
    # CRITICAL: IGNORE BOT'S OWN MESSAGES
    if uid == 8214501704:
        return
    
    # Check if owner
    if uid != OWNER_ID:
        # Silent ignore for non-owners
        return
    
    # Owner confirmed - upload file
    try:
        fwd = await m.forward(CHANNEL_ID)
        fid = gen_id()
        
        # Get file info
        fname = "file"
        fsize = 0
        
        if m.document:
            fname = m.document.file_name
            fsize = m.document.file_size
        elif m.video:
            fname = "video.mp4"
            fsize = m.video.file_size
        elif m.audio:
            fname = m.audio.file_name or "audio.mp3"
            fsize = m.audio.file_size
        elif m.photo:
            fname = "photo.jpg"
        
        # Save to database
        files.insert_one({
            "file_id": fid,
            "message_id": fwd.id,
            "file_name": fname,
            "file_size": fsize,
            "uploaded_at": datetime.datetime.now(),
            "downloads": 0
        })
        
        # Generate share link
        bot_username = (await c.get_me()).username
        link = f"https://t.me/{bot_username}?start={fid}"
        
        # Format size
        if fsize > 1024*1024:
            size = f"{fsize/(1024*1024):.2f} MB"
        elif fsize > 1024:
            size = f"{fsize/1024:.2f} KB"
        else:
            size = f"{fsize} B"
        
        await m.reply(
            f"✅ **File Uploaded Successfully!**\n\n"
            f"📁 **File:** `{fname}`\n"
            f"📊 **Size:** `{size}`\n"
            f"🆔 **ID:** `{fid}`\n\n"
            f"🔗 **Share Link:**\n`{link}`\n\n"
            f"📤 Share this link with users!",
            quote=True
        )
        
    except Exception as e:
        await m.reply(
            f"❌ **Upload Failed**\n\n"
            f"Error: `{str(e)}`\n\n"
            f"Please check:\n"
            f"• Bot is admin in channel\n"
            f"• Channel exists\n"
            f"• Database is connected"
        )

@app.on_message(filters.command("help") & filters.private)
async def help_cmd(c, m):
    uid = m.from_user.id
    
    if uid == OWNER_ID:
        txt = (
            "👑 **Admin Help**\n\n"
            "**Commands:**\n"
            "• Send any file → Get shareable link\n"
            "• /stats → View bot statistics\n\n"
            "**How it works:**\n"
            "1. You upload files\n"
            "2. Get shareable links\n"
            "3. Users verify once\n"
            "4. They get 48-hour access\n\n"
            "**Earnings:** Check VPLink dashboard!"
        )
    else:
        txt = (
            "📖 **User Guide**\n\n"
            "**How to download files:**\n"
            "1. Click on file link\n"
            "2. Complete one-time verification\n"
            "3. Enjoy 48 hours of unlimited downloads!\n\n"
            "**Why verification?**\n"
            "• Keeps the bot free for everyone\n"
            "• One-time process for 48 hours\n"
            "• Quick & simple\n\n"
            "**Need support?** Contact the bot admin."
        )
    
    await m.reply(txt)

@app.on_message(filters.command("about") & filters.private)
async def about(c, m):
    await m.reply(
        "🤖 **FileShare Bot**\n\n"
        "A fast and secure file sharing bot with VPLink monetization.\n\n"
        "**Features:**\n"
        "• Large file support\n"
        "• One-time verification\n"
        "• 48-hour access\n"
        "• Secure downloads\n\n"
        "Made with ❤️ for Telegram users!"
    )

# ========== START BOT ==========
print("🚀 Starting bot...")
app.run()
print("✅ Bot running!")
