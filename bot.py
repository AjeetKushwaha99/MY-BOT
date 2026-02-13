# -*- coding: utf-8 -*-
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

print(f"✅ Owner ID loaded: {OWNER_ID} (type: {type(OWNER_ID)})")

# Database
mongo = MongoClient(MONGO_URL)
db = mongo['filebot']
users = db['users']
files = db['files']

# Bot
app = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

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

@app.on_message(filters.command("start") & filters.private)
async def start(c, m):
    uid = m.from_user.id
    if not users.find_one({"user_id": uid}):
        users.insert_one({"user_id": uid, "username": m.from_user.username, "verified_at": None, "joined_at": datetime.datetime.now()})
    
    if len(m.text.split()) > 1:
        code = m.text.split()[1]
        
        if code.startswith("verify_"):
            users.update_one({"user_id": uid}, {"$set": {"verified_at": datetime.datetime.now()}})
            await m.reply("✅ **Verified!**\n\n🎉 48 hours access activated!")
            return
        
        if not verified(uid):
            link = shorten(f"https://t.me/{(await c.get_me()).username}?start=verify_{uid}")
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
    # DETAILED CHECK
    print(f"Stats command by: {m.from_user.id}, Owner: {OWNER_ID}, Match: {m.from_user.id == OWNER_ID}")
    
    if m.from_user.id != OWNER_ID:
        await m.reply(f"❌ Admin only!\n\nYour ID: `{m.from_user.id}`\nOwner: `{OWNER_ID}`")
        return
    
    await m.reply(f"📊 **Stats**\n\n👥 Users: {users.count_documents({})}\n📁 Files: {files.count_documents({})}")

@app.on_message((filters.document | filters.video | filters.audio | filters.photo) & filters.private)
async def upload(c, m):
    uid = m.from_user.id
    
    # DETAILED DEBUG
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"📤 Upload attempt")
    print(f"User ID: {uid} (type: {type(uid)})")
    print(f"Owner ID: {OWNER_ID} (type: {type(OWNER_ID)})")
    print(f"Match: {uid == OWNER_ID}")
    print(f"User: @{m.from_user.username} ({m.from_user.first_name})")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    # MULTIPLE CHECKS
    is_owner = (uid == OWNER_ID) or (uid == 6549083920) or (str(uid) == "6549083920")
    
    if not is_owner:
        await m.reply(
            f"❌ **Access Denied!**\n\n"
            f"📛 Your ID: `{uid}`\n"
            f"📛 Your Username: @{m.from_user.username}\n"
            f"👑 Owner ID: `{OWNER_ID}`\n\n"
            f"🔍 **Debug:**\n"
            f"• ID Type: `{type(uid)}`\n"
            f"• Owner Type: `{type(OWNER_ID)}`\n"
            f"• Match: `{uid == OWNER_ID}`\n\n"
            f"If you're the owner, send this screenshot to developer!"
        )
        return
    
    # SUCCESS - Owner confirmed!
    await m.reply("⏳ Uploading...")
    
    try:
        fwd = await m.forward(CHANNEL_ID)
        fid = gen_id()
        
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
            fsize = 0
        
        files.insert_one({
            "file_id": fid,
            "message_id": fwd.id,
            "file_name": fname,
            "file_size": fsize,
            "uploaded_at": datetime.datetime.now(),
            "downloads": 0
        })
        
        link = f"https://t.me/{(await c.get_me()).username}?start={fid}"
        
        # Size format
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
        await m.reply(f"❌ **Failed!**\n\nError: `{e}`")
        print(f"❌ Error: {e}")

@app.on_message(filters.command("help"))
async def help_cmd(c, m):
    if m.from_user.id == OWNER_ID:
        txt = "📖 **Admin Help**\n\n• Send file → Get link\n• /stats → Statistics\n• Share links!"
    else:
        txt = "📖 **Help**\n\n• Click link → Verify → Download\n• 48hr access!"
    await m.reply(txt)

@app.on_message(filters.command("myid"))
async def myid(c, m):
    """Debug command - check your ID"""
    await m.reply(
        f"🆔 **Your Information**\n\n"
        f"User ID: `{m.from_user.id}`\n"
        f"Username: @{m.from_user.username}\n"
        f"First Name: {m.from_user.first_name}\n\n"
        f"Owner ID: `{OWNER_ID}`\n"
        f"Are you owner? {m.from_user.id == OWNER_ID}"
    )

print("🚀 Starting bot...")
print(f"👑 Owner: {OWNER_ID}")
app.run()
print("✅ Running!")
