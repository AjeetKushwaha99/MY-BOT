# -*- coding: utf-8 -*-
# Telegram File Sharing Bot - FINAL WORKING VERSION
# Fixed all issues: Owner ID, Channel ID, Bot self-messages

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient
import datetime, hashlib, os, requests

# ========== CONFIG ==========
API_ID = 37067823
API_HASH = "ed9e62ed4538d2d2b835fb54529c358f"
BOT_TOKEN = "8214501704:AAE7kuiVAqDuID8KRzKTDTSDlBd0MseYCF0"
CHANNEL_ID = -1003777551559  # Storage channel
OWNER_ID = 6549083920  # Ajeet's User ID
MONGO_URL = "mongodb+srv://Ajeet:XgGFRFWVT2NwWipw@cluster0.3lxz0p7.mongodb.net/?appName=Cluster0"
SHORTENER_API = "5cbb1b2088d2ed06d7e9feae35dc17cc033169d6"
SHORTENER_URL = "https://vplink.in"

print("=" * 50)
print("🤖 BOT STARTING...")
print(f"👑 Owner ID: {OWNER_ID}")
print(f"📁 Channel ID: {CHANNEL_ID}")
print("=" * 50)

# ========== DATABASE ==========
try:
    mongo = MongoClient(MONGO_URL)
    db = mongo['filebot']
    users = db['users']
    files = db['files']
    print("✅ Database connected!")
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
    
    # IGNORE BOT'S OWN MESSAGES
    if uid == 8214501704:  # Bot's ID (from token)
        print("🤖 Ignoring bot's own message")
        return
    
    if not users.find_one({"user_id": uid}):
        users.insert_one({
            "user_id": uid,
            "username": m.from_user.username,
            "first_name": m.from_user.first_name,
            "verified_at": None,
            "joined_at": datetime.datetime.now()
        })
        print(f"📝 New user: {uid}")
    
    if len(m.text.split()) > 1:
        code = m.text.split()[1]
        
        if code.startswith("verify_"):
            users.update_one({"user_id": uid}, {"$set": {"verified_at": datetime.datetime.now()}})
            await m.reply("✅ **Verified!**\n\n🎉 48 hours access activated!")
            return
        
        if not verified(uid):
            bot_username = (await c.get_me()).username
            link = shorten(f"https://t.me/{bot_username}?start=verify_{uid}")
            await m.reply(
                f"🔒 **Verify Required!**\n\n🔗 {link}\n\n⏰ 48hr access!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔓 Verify", url=link)]])
            )
            return
        
        f = files.find_one({"file_id": code})
        if not f:
            await m.reply("❌ File not found!")
            return
        
        try:
            await c.copy_message(m.chat.id, CHANNEL_ID, f['message_id'])
            files.update_one({"file_id": code}, {"$inc": {"downloads": 1}})
            await m.reply("✅ File sent!")
        except Exception as e:
            await m.reply(f"❌ Error: {e}")
    else:
        await m.reply(
            f"👋 **Welcome {m.from_user.first_name}!**\n\n"
            f"🤖 File Sharing Bot\n\n"
            f"📁 Admin uploads → Get link\n"
            f"🔗 Users verify → Download\n\n"
            f"❓ /help"
        )

@app.on_message(filters.command("stats") & filters.private)
async def stats(c, m):
    uid = m.from_user.id
    
    # IGNORE BOT'S OWN MESSAGES
    if uid == 8214501704:
        return
    
    if uid != OWNER_ID:
        await m.reply(f"❌ Admin only!\n\nYour ID: `{uid}`\nOwner: `{OWNER_ID}`")
        return
    
    total = users.count_documents({})
    ver = users.count_documents({"verified_at": {"$ne": None}})
    fil = files.count_documents({})
    
    await m.reply(f"📊 **Stats**\n\n👥 Users: {total}\n✅ Verified: {ver}\n📁 Files: {fil}")

@app.on_message((filters.document | filters.video | filters.audio | filters.photo) & filters.private)
async def upload(c, m):
    uid = m.from_user.id
    
    # CRITICAL FIX: IGNORE BOT'S OWN MESSAGES
    if uid == 8214501704:  # Bot ka ID (token se)
        print("🤖 Bot tried to upload file - ignoring")
        return
    
    print(f"📤 Upload by: {uid} (Owner: {OWNER_ID})")
    
    # Check if user is owner
    if uid != OWNER_ID:
        await m.reply(
            f"❌ **Access Denied!**\n\n"
            f"📛 Your ID: `{uid}`\n"
            f"👑 Owner ID: `{OWNER_ID}`\n\n"
            f"Only bot owner can upload files."
        )
        return
    
    # Owner confirmed
    await m.reply("⏳ Uploading...")
    
    try:
        # Test channel connection first
        print(f"📁 Testing channel: {CHANNEL_ID}")
        
        # Forward to channel
        fwd = await m.forward(CHANNEL_ID)
        print(f"✅ Forwarded to channel, Message ID: {fwd.id}")
        
        # Generate file ID
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
            f"✅ **Uploaded!**\n\n"
            f"📁 **File:** `{fname}`\n"
            f"📊 **Size:** `{size}`\n"
            f"🆔 **ID:** `{fid}`\n\n"
            f"🔗 **Link:**\n`{link}`\n\n"
            f"📤 Share with users!",
            quote=True
        )
        
        print(f"✅ Upload success: {fid}")
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Upload error: {error_msg}")
        
        if "Peer id invalid" in error_msg or "CHANNEL_INVALID" in error_msg:
            await m.reply(
                f"❌ **Channel Error!**\n\n"
                f"Channel ID: `{CHANNEL_ID}`\n\n"
                f"**Please check:**\n"
                f"1. Bot is ADMIN in the channel\n"
                f"2. Channel ID is correct\n"
                f"3. Channel is PRIVATE\n"
                f"4. Bot has all permissions\n\n"
                f"**Fix:**\n"
                f"• Go to channel settings\n"
                f"• Add bot as ADMIN\n"
                f"• Give ALL permissions\n"
                f"• Try again!"
            )
        else:
            await m.reply(f"❌ **Error:** `{error_msg}`")

@app.on_message(filters.command("help") & filters.private)
async def help_cmd(c, m):
    uid = m.from_user.id
    
    # IGNORE BOT'S OWN MESSAGES
    if uid == 8214501704:
        return
    
    if uid == OWNER_ID:
        txt = "📖 **Admin Help**\n\n• Send file → Get link\n• /stats → Statistics\n• Share links with users!"
    else:
        txt = "📖 **Help**\n\n• Click link → Verify → Download\n• 48hr access after verification!"
    await m.reply(txt)

@app.on_message(filters.command("test") & filters.private)
async def test(c, m):
    """Test channel connection"""
    uid = m.from_user.id
    
    if uid != OWNER_ID:
        return
    
    try:
        # Try to get channel info
        chat = await c.get_chat(CHANNEL_ID)
        await m.reply(
            f"✅ **Channel Connected!**\n\n"
            f"📛 Name: {chat.title}\n"
            f"🆔 ID: {chat.id}\n"
            f"👥 Type: {chat.type}\n\n"
            f"Bot status: Connected ✓"
        )
    except Exception as e:
        await m.reply(
            f"❌ **Channel Error!**\n\n"
            f"Error: `{e}`\n\n"
            f"**Possible issues:**\n"
            f"1. Bot not admin in channel\n"
            f"2. Channel ID wrong\n"
            f"3. Channel deleted\n\n"
            f"**Fix:**\n"
            f"1. Add bot as ADMIN in channel\n"
            f"2. Check channel ID\n"
            f"3. Make sure channel exists"
        )

@app.on_message(filters.command("fix") & filters.private)
async def fix_cmd(c, m):
    """Force fix owner issue"""
    uid = m.from_user.id
    
    if uid == OWNER_ID:
        # Force add as verified
        users.update_one({"user_id": uid}, {"$set": {"verified_at": datetime.datetime.now()}}, upsert=True)
        await m.reply(
            f"✅ **Owner Force Fixed!**\n\n"
            f"👑 Your ID: `{uid}`\n"
            f"✅ Now you can upload files!\n\n"
            f"Try sending a file now!"
        )
    else:
        await m.reply("❌ Only owner can use this!")

# ========== START BOT ==========
print("🚀 Starting bot...")
try:
    app.run()
    print("✅ Bot running!")
except Exception as e:
    print(f"❌ Bot failed: {e}")
