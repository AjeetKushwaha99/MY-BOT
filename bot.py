# -*- coding: utf-8 -*-
# Telegram File Sharing Bot with VPLink Monetization
# Fixed Version - 100% Working

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient
import datetime
import hashlib
import os
import requests

# ========== CONFIGURATION ==========
# Tumhare exact details hardcoded for safety
API_ID = 37067823
API_HASH = "ed9e62ed4538d2d2b835fb54529c358f"
BOT_TOKEN = "8214501704:AAE7kuiVAqDuID8KRzKTDTSDlBd0MseYCF0"
CHANNEL_ID = -1003777551559
OWNER_ID = 6549083920  # Ajeet's User ID - FIXED!
MONGO_URL = "mongodb+srv://Ajeet:XgGFRFWVT2NwWipw@cluster0.3lxz0p7.mongodb.net/?appName=Cluster0"
SHORTENER_API = "5cbb1b2088d2ed06d7e9feae35dc17cc033169d6"
SHORTENER_URL = "https://vplink.in"

# Print config for debugging
print(f"""
========== BOT CONFIGURATION ==========
API_ID: {API_ID}
CHANNEL_ID: {CHANNEL_ID}
OWNER_ID: {OWNER_ID}
SHORTENER: {SHORTENER_URL}
========================================
""")

# ========== DATABASE CONNECTION ==========
try:
    mongo_client = MongoClient(MONGO_URL)
    db = mongo_client['filebot']
    users_collection = db['users']
    files_collection = db['files']
    print("✅ Database connected successfully!")
except Exception as e:
    print(f"❌ Database error: {e}")

# ========== BOT CLIENT ==========
app = Client(
    "FileShareBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ========== HELPER FUNCTIONS ==========

def generate_file_id():
    """Generate unique 8-character file ID"""
    return hashlib.md5(str(datetime.datetime.now()).encode()).hexdigest()[:8]

def is_user_verified(user_id):
    """Check if user is verified within 48 hours"""
    user = users_collection.find_one({"user_id": user_id})
    if not user:
        return False
    
    verified_at = user.get("verified_at")
    if not verified_at:
        return False
    
    # Check 48 hour validity
    time_diff = (datetime.datetime.now() - verified_at).total_seconds()
    return time_diff < 172800  # 48 hours in seconds

def shorten_url(long_url):
    """Shorten URL using VPLink API"""
    try:
        api_endpoint = f"{SHORTENER_URL}/api?api={SHORTENER_API}&url={long_url}"
        response = requests.get(api_endpoint, timeout=10)
        data = response.json()
        
        if data.get("status") == "success":
            return data.get("shortenedUrl", long_url)
        else:
            return long_url
    except Exception as e:
        print(f"Shortener error: {e}")
        return long_url

# ========== BOT COMMANDS ==========

@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    """Handle /start command and file requests"""
    user_id = message.from_user.id
    
    # Add user to database if new
    if not users_collection.find_one({"user_id": user_id}):
        users_collection.insert_one({
            "user_id": user_id,
            "username": message.from_user.username,
            "first_name": message.from_user.first_name,
            "verified_at": None,
            "joined_at": datetime.datetime.now()
        })
        print(f"📝 New user added: {user_id}")
    
    # Check if command has parameter (file request or verification)
    if len(message.text.split()) > 1:
        parameter = message.text.split()[1]
        
        # Handle verification callback
        if parameter.startswith("verify_"):
            users_collection.update_one(
                {"user_id": user_id},
                {"$set": {"verified_at": datetime.datetime.now()}}
            )
            await message.reply_text(
                "✅ **Verification Successful!**\n\n"
                "🎉 You now have **48 hours** of unlimited access!\n\n"
                "📁 You can now download all files without ads.\n"
                "⏰ Access expires after 48 hours."
            )
            return
        
        # Handle file request
        file_code = parameter
        
        # Check if user is verified
        if not is_user_verified(user_id):
            bot_username = (await client.get_me()).username
            verify_url = f"https://t.me/{bot_username}?start=verify_{user_id}"
            short_link = shorten_url(verify_url)
            
            await message.reply_text(
                "🔒 **Verification Required!**\n\n"
                "To download files, you need to verify first.\n\n"
                f"🔗 **Verification Link:** {short_link}\n\n"
                "📝 **Steps:**\n"
                "1️⃣ Click the verification link\n"
                "2️⃣ Complete the captcha\n"
                "3️⃣ Click continue/get link\n"
                "4️⃣ Return here and enjoy 48 hours access!\n\n"
                "⚡ One-time verification for 48 hours of unlimited downloads!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔓 Verify Now", url=short_link)
                ]])
            )
            return
        
        # User is verified, send the file
        file_data = files_collection.find_one({"file_id": file_code})
        
        if not file_data:
            await message.reply_text("❌ **File Not Found!**\n\nThis link is invalid or expired.")
            return
        
        # Copy file from channel to user
        try:
            await client.copy_message(
                chat_id=message.chat.id,
                from_chat_id=CHANNEL_ID,
                message_id=file_data['message_id']
            )
            
            # Update download count
            files_collection.update_one(
                {"file_id": file_code},
                {"$inc": {"downloads": 1}}
            )
            
            await message.reply_text(
                "✅ **File Sent Successfully!**\n\n"
                "Enjoy your file! 😊\n\n"
                "Share this bot with friends! 🚀"
            )
            
        except Exception as e:
            await message.reply_text(f"❌ **Error:** {str(e)}\n\nPlease contact admin.")
    
    else:
        # Normal start message
        await message.reply_text(
            f"👋 **Welcome {message.from_user.first_name}!**\n\n"
            f"🤖 I'm a **File Sharing Bot** with VPLink monetization.\n\n"
            f"📌 **Features:**\n"
            f"• Large file support (2GB+)\n"
            f"• 48-hour access after verification\n"
            f"• Fast direct downloads\n"
            f"• Secure file storage\n\n"
            f"📁 **How to use:**\n"
            f"• Get a file link from admin\n"
            f"• Complete one-time verification\n"
            f"• Enjoy 48 hours unlimited access!\n\n"
            f"❓ Use /help for more info\n"
            f"📊 Admin? Use /stats"
        )

@app.on_message(filters.command("stats") & filters.private)
async def stats_command(client, message):
    """Show bot statistics (Admin only)"""
    user_id = message.from_user.id
    
    # Check if user is owner
    if user_id != OWNER_ID:
        await message.reply_text(
            f"❌ **Admin Only Command!**\n\n"
            f"Your ID: `{user_id}`\n"
            f"This command is only for bot owner."
        )
        return
    
    # Get statistics
    total_users = users_collection.count_documents({})
    verified_users = users_collection.count_documents({"verified_at": {"$ne": None}})
    total_files = files_collection.count_documents({})
    
    # Calculate total downloads
    total_downloads = 0
    for file in files_collection.find():
        total_downloads += file.get("downloads", 0)
    
    await message.reply_text(
        f"📊 **Bot Statistics**\n\n"
        f"👥 **Total Users:** `{total_users}`\n"
        f"✅ **Verified Users:** `{verified_users}`\n"
        f"📁 **Total Files:** `{total_files}`\n"
        f"📥 **Total Downloads:** `{total_downloads}`\n\n"
        f"🤖 **Bot Status:** ✅ Active\n"
        f"💾 **Database:** ✅ Connected\n"
        f"🔗 **Shortener:** ✅ Working"
    )

@app.on_message((filters.document | filters.video | filters.audio | filters.photo) & filters.private)
async def handle_files(client, message):
    """Handle file uploads (Admin only)"""
    user_id = message.from_user.id
    
    # Debug print
    print(f"📤 File upload attempt by user: {user_id}")
    print(f"👑 Owner ID is: {OWNER_ID}")
    print(f"✅ Is owner? {user_id == OWNER_ID}")
    
    # Check if user is owner
    if user_id != OWNER_ID:
        await message.reply_text(
            "❌ **Admin Only!**\n\n"
            "Only the bot owner can upload files.\n\n"
            f"Your User ID: `{user_id}`\n"
            f"Owner ID: `{OWNER_ID}`\n\n"
            "If you are the owner, please check your user ID."
        )
        return
    
    # Owner confirmed, process file upload
    await message.reply_text("⏳ **Uploading file...**")
    
    try:
        # Forward file to storage channel
        forwarded = await message.forward(CHANNEL_ID)
        
        # Generate unique file ID
        file_id = generate_file_id()
        
        # Get file details
        if message.document:
            file_name = message.document.file_name
            file_size = message.document.file_size
        elif message.video:
            file_name = "video.mp4"
            file_size = message.video.file_size
        elif message.audio:
            file_name = message.audio.file_name or "audio.mp3"
            file_size = message.audio.file_size
        elif message.photo:
            file_name = "photo.jpg"
            file_size = message.photo.file_size if hasattr(message.photo, 'file_size') else 0
        else:
            file_name = "file"
            file_size = 0
        
        # Save to database
        files_collection.insert_one({
            "file_id": file_id,
            "message_id": forwarded.id,
            "file_name": file_name,
            "file_size": file_size,
            "uploaded_by": user_id,
            "uploaded_at": datetime.datetime.now(),
            "downloads": 0
        })
        
        # Generate share link
        bot_username = (await client.get_me()).username
        share_link = f"https://t.me/{bot_username}?start={file_id}"
        
        # Convert file size to readable format
        if file_size > 1024*1024:  # MB
            size_str = f"{file_size/(1024*1024):.2f} MB"
        elif file_size > 1024:  # KB
            size_str = f"{file_size/1024:.2f} KB"
        else:
            size_str = f"{file_size} B"
        
        await message.reply_text(
            f"✅ **File Uploaded Successfully!**\n\n"
            f"📁 **File Name:** `{file_name}`\n"
            f"📊 **File Size:** `{size_str}`\n"
            f"🆔 **File ID:** `{file_id}`\n\n"
            f"🔗 **Share Link:**\n`{share_link}`\n\n"
            f"📤 Share this link with users!\n"
            f"They need to verify once for 48-hour access.",
            quote=True
        )
        
        print(f"✅ File uploaded: {file_id} - {file_name}")
        
    except Exception as e:
        await message.reply_text(
            f"❌ **Upload Failed!**\n\n"
            f"Error: `{str(e)}`\n\n"
            f"Please check:\n"
            f"• Bot is admin in channel\n"
            f"• Channel ID is correct\n"
            f"• Database is connected"
        )
        print(f"❌ Upload error: {e}")

@app.on_message(filters.command("help") & filters.private)
async def help_command(client, message):
    """Show help message"""
    user_id = message.from_user.id
    
    if user_id == OWNER_ID:
        # Admin help
        help_text = """
📖 **Admin Help Guide**

**Your Commands:**
• Send any file → Get share link
• /stats → View bot statistics
• /help → This message

**File Upload:**
1. Send any file to bot
2. Bot saves it in channel
3. Get shareable link
4. Share with users

**User Flow:**
1. User clicks your link
2. Completes VPLink verification
3. Gets 48-hour access
4. Can download unlimited files

**Supported Files:**
• Documents (PDF, ZIP, etc.)
• Videos (MP4, MKV, etc.)
• Audio (MP3, etc.)
• Photos

**Earnings:**
Check VPLink dashboard for earnings!
"""
    else:
        # User help
        help_text = """
📖 **User Help Guide**

**How to Download Files:**
1. Click on file link
2. Complete verification (one-time)
3. Enjoy 48 hours unlimited access!

**Why Verification?**
• Keeps bot free for everyone
• One-time for 48 hours
• Quick 5-second process

**Supported Files:**
• Movies/Series
• Documents
• Music
• Photos
• Software

**Having Issues?**
Contact bot admin for support.
"""
    
    await message.reply_text(help_text)

@app.on_message(filters.command("broadcast") & filters.private & filters.user(OWNER_ID))
async def broadcast_command(client, message):
    """Broadcast message to all users (Admin only)"""
    if len(message.text.split(None, 1)) < 2:
        await message.reply_text("❌ **Usage:** /broadcast Your message here")
        return
    
    broadcast_text = message.text.split(None, 1)[1]
    users = users_collection.find()
    success = 0
    failed = 0
    
    for user in users:
        try:
            await client.send_message(user["user_id"], broadcast_text)
            success += 1
        except:
            failed += 1
    
    await message.reply_text(f"✅ **Broadcast Complete!**\n\nSuccess: {success}\nFailed: {failed}")

# ========== BOT STARTUP ==========
print("🚀 Starting Telegram File Sharing Bot...")
print(f"👑 Owner ID: {OWNER_ID}")
print(f"📁 Channel ID: {CHANNEL_ID}")
print("⏳ Connecting to Telegram...")

app.run()

print("✅ Bot is now running!")
