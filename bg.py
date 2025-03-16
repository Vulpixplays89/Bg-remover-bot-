import os
import io
import telebot
import pymongo
from PIL import Image, ImageEnhance
from rembg import remove
from threading import Thread 
from flask import Flask


# Bot Configuration
BOT_TOKEN = "7566967249:AAG2m_RY09eYRpgZZrwKEX9aKhXdD4DtB6M"
MONGO_URI = "mongodb+srv://botplays90:botplays90@botplays.ycka9.mongodb.net/?retryWrites=true&w=majority&appName=botplays"

# Initialize Bot & Database
bot = telebot.TeleBot(BOT_TOKEN)
client = pymongo.MongoClient(MONGO_URI)
db = client["BackgroundRemoverBot"]  # Database name
users_col = db["users"]  # Collection name

app = Flask(__name__)

@app.route('/')
def home():
    return "I am alive"

def run_http_server():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    Thread(target=run_http_server).start()

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "User"

    # Check if user already exists
    if not users_col.find_one({"user_id": user_id}):
        users_col.insert_one({"user_id": user_id, "name": user_name})

    bot.reply_to(message, f"👋 Hi {user_name}!\n\nSend me an image, and I'll remove its background! ✨\n\n📸 Just send a photo and I'll do the magic!\n\n⚠️ Note: Sometimes the bot may not give 100% perfect results (depends on the image).")

def enhance_image(image):
    """Enhance brightness & contrast for better background removal."""
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(1.1)  # Slightly increase contrast
    enhancer = ImageEnhance.Brightness(image)
    image = enhancer.enhance(1.1)  # Slightly increase brightness
    return image

@bot.message_handler(content_types=['photo'])
def remove_bg(message):
    try:
        # Notify user that processing has started
        status_msg = bot.reply_to(message, "⏳ Image received! Removing background... 🔄")

        # Download Image
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        # Convert Image to PIL
        input_img = Image.open(io.BytesIO(downloaded_file)).convert("RGBA")

        # Apply enhancement for better quality
        enhanced_img = enhance_image(input_img)

        # Apply Background Removal
        output_img = remove(enhanced_img)

        # Convert Output to Bytes
        output_io = io.BytesIO()
        output_img.save(output_io, format="PNG")  # Highest quality PNG
        output_io.seek(0)

        # Send Processed Image
        bot.send_document(message.chat.id, output_io, caption="✅ Here is your background-removed image! 🎉", visible_file_name="no_bg.png")

        # Delete processing message
        bot.delete_message(message.chat.id, status_msg.message_id)

    except Exception as e:
        bot.reply_to(message, f"❌ Error processing image: `{str(e)}`")

@bot.message_handler(commands=['users'])
def get_users(message):
    users = users_col.find({})
    user_list = [f"{user['name']} - `{user['user_id']}`" for user in users]

    if user_list:
        bot.reply_to(message, "👥 Registered Users:\n\n" + "\n".join(user_list), parse_mode="Markdown")
    else:
        bot.reply_to(message, "🚫 No users found!")

@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if message.reply_to_message:
        text = message.reply_to_message.text
        users = users_col.find({})
        sent_count = 0
        failed_count = 0

        for user in users:
            try:
                bot.send_message(user['user_id'], f"📢 Broadcast Message:\n\n{text}", parse_mode="Markdown")
                sent_count += 1
            except:
                failed_count += 1  # Count failed messages

        bot.reply_to(
            message, 
            f"✅ Broadcast Summary:\n\n📤 Sent: {sent_count}\n❌ Failed: {failed_count}"
        )
    else:
        bot.reply_to(message, "⚠️ Reply to a message to broadcast it to all users!")

@bot.message_handler(commands=['stats'])
def stats(message):
    total_users = users_col.count_documents({})  # Count total users in MongoDB
    bot.reply_to(message, f"📊 Bot Statistics:\n\n👥 Total Users: `{total_users}`", parse_mode="Markdown")

keep_alive()

while True:
    try:
        print("🚀 Bot is running...")
        bot.polling(none_stop=True, interval=3, timeout=30)
    except Exception as e:
        print(f"⚠️ Bot crashed due to: {e}")
        time.sleep(5)  # Wait 5 seconds before restarting
