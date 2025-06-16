import os
import math
import logging
import requests
import time
import asyncio
from difflib import get_close_matches
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.error import NetworkError, RetryAfter, TimedOut

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot token & API URL
TOKEN = "7121709733:AAGGdZOnL7gpNZvG6Dv0_7u1L57RUc8gZB0"
FLASK_API_URL = 'http://localhost:5000/api/diagnose'

# Sample autocomplete suggestions
COMMON_SYMPTOMS = [
    "headache", "fever", "cough", "sore throat", "nausea",
    "vomiting", "stomach pain", "fatigue", "chest pain", "dizziness"
]

# Distance helper
def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("📋 Common Symptoms", callback_data="see_symptoms"),
            InlineKeyboardButton("💡 Suggest Symptoms", callback_data="ask_again"),
        ]
    ]
    markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "👋 Hello! I’m your *Smart Healthcare Bot* 🩺\n\n"
        "Just tell me how you're feeling — for example:\n"
        "`I have chest pain and fatigue`\n\n"
        "I’ll:\n"
        "• 🧠 *Analyze your symptoms*\n"
        "• 💊 *Suggest a diagnosis and a solution*\n"
        "• 🧑‍⚕️ *Recommend doctors near you (1–10 km range)*\n\n"
        "🔍 *Need help typing symptoms?*\n"
        "Use `/suggest fever` to get symptom autocomplete.\n\n"
        "💡 *Need ideas?*\n"
        "Use `/symptoms` to see common symptoms.\n\n"
        "📍 You can also share your *location* to get nearby doctor suggestions.\n\n"
        "Let’s get you the care you deserve! 💚",
        parse_mode='Markdown',
        reply_markup=markup
    )

# /symptoms
async def suggest_symptoms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    suggestion_text = "\n".join(f"- {s}" for s in COMMON_SYMPTOMS)
    await update.message.reply_text(
        f"💡 *Common Symptoms You Can Try:*\n{suggestion_text}",
        parse_mode='Markdown'
    )

# /suggest <text>
async def suggest_autocomplete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        query = " ".join(context.args).lower()
        suggestions = get_close_matches(query, COMMON_SYMPTOMS, n=5, cutoff=0.4)
        if suggestions:
            buttons = [[InlineKeyboardButton(s, callback_data=f"suggest_{s}")] for s in suggestions]
            markup = InlineKeyboardMarkup(buttons)
            await update.message.reply_text(f"🔍 Suggestions for `{query}`:", reply_markup=markup, parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ No suggestions found.")
    else:
        await update.message.reply_text("Usage: `/suggest fever`", parse_mode='Markdown')

# Handle plain symptom messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text.strip()
    context.user_data['last_symptom'] = user_message
    await update.message.chat.send_action(action="typing")
    time.sleep(1.5)

    try:
        response = requests.post(FLASK_API_URL, json={"symptoms": user_message})
        response.raise_for_status()
        data = response.json()

        diagnosis = data.get('diagnosis', 'No diagnosis available.')
        doctors = data.get('doctors', [])
        solution = data.get('solution', 'No solution available.')
        confidence = data.get('confidence_score', 0)
        context.user_data['doctors'] = doctors

        doctor_text = "\n\n🧑‍⚕️ *Doctor Recommendations:*\n" if doctors else "❌ No doctor recommendations available."
        for doc in doctors:
            doctor_text += (
                f"• *{doc.get('name', 'N/A')}* ({doc.get('specialization', 'General')})\n"
                f"  🏥 {doc.get('clinic', 'Unknown Clinic')}\n"
                f"  📞 {doc.get('contact', 'N/A')}\n"
            )

        reply = (
            f"🩺 *Diagnosis:* {diagnosis}\n"
            f"📊 *Confidence:* {confidence}%\n"
            f"💊 *Solution:* {solution}\n"
            f"{doctor_text}"
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("📍 Get Nearby Doctors", callback_data='get_nearby_doctors')],
            [InlineKeyboardButton("🔁 Ask Again", callback_data='ask_again')]
        ])

        await update.message.reply_text(reply, parse_mode='Markdown', reply_markup=markup)

    except requests.exceptions.RequestException:
        await update.message.reply_text("⚠️ Error connecting to diagnosis service.")
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text("⚠️ Something went wrong. Please try again.")

# Button handler
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'get_nearby_doctors':
        location_keyboard = [[KeyboardButton("Send Location 📍", request_location=True)]]
        reply_markup = ReplyKeyboardMarkup(location_keyboard, one_time_keyboard=True, resize_keyboard=True)
        await query.message.reply_text(
            "Please share your location to find nearby doctors.", reply_markup=reply_markup
        )

    elif query.data == 'ask_again':
        await query.message.reply_text("📝 Please enter your symptoms again.")

    elif query.data == 'see_symptoms':
        suggestion_text = "\n".join(f"- {s}" for s in COMMON_SYMPTOMS)
        await query.message.reply_text(f"💬 Common symptoms you can try:\n{suggestion_text}")

    elif query.data.startswith("suggest_"):
        selected_symptom = query.data.replace("suggest_", "")
        context.user_data['last_symptom'] = selected_symptom
        await query.message.reply_text(f"📝 You selected: *{selected_symptom}*", parse_mode='Markdown')
        await handle_message(update, context)

# Location handler
async def location_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    loc = update.message.location
    user_lat, user_lon = loc.latitude, loc.longitude
    doctors = context.user_data.get('doctors', [])
    nearby = []

    for doc in doctors:
        if 'lat' in doc and 'lon' in doc:
            dist = haversine_distance(user_lat, user_lon, doc['lat'], doc['lon'])
            if dist <= 10:
                nearby.append((doc, dist))

    if not nearby:
        await update.message.reply_text("❌ No doctors found nearby.")
        return

    nearby.sort(key=lambda x: x[1])
    msg = "📍 *Nearby Doctors (within 10 km):*\n\n"
    for doc, dist in nearby:
        url = f"https://www.google.com/maps/search/?api=1&query={doc['lat']},{doc['lon']}"
        msg += (
            f"• *{doc['name']}* - {doc.get('clinic')}\n"
            f"  📍 {doc.get('address')}\n"
            f"  📞 {doc.get('contact')}\n"
            f"  📏 {dist:.2f} km away\n"
            f"  [🗺️ View on Map]({url})\n\n"
        )
    await update.message.reply_text(msg, parse_mode='Markdown', disable_web_page_preview=True)

# Main loop with retry logic
async def run_bot():
    while True:
        try:
            application = ApplicationBuilder().token(TOKEN).build()

            application.add_handler(CommandHandler("start", start))
            application.add_handler(CommandHandler("symptoms", suggest_symptoms))
            application.add_handler(CommandHandler("suggest", suggest_autocomplete))
            application.add_handler(CallbackQueryHandler(button_handler))
            application.add_handler(MessageHandler(filters.LOCATION, location_handler))
            application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

            print("🤖 Bot is running...")
            await application.run_polling()
            break

        except (NetworkError, RetryAfter, TimedOut) as net_err:
            logger.warning(f"⚠️ Network error: {net_err}. Retrying in 10 seconds...")
            await asyncio.sleep(10)
        except Exception as e:
            logger.error(f"❌ Unhandled exception: {e}")
            break

if __name__ == "__main__":
    import asyncio
    import sys

    if sys.platform.startswith('win') and sys.version_info >= (3, 8):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    import nest_asyncio
    nest_asyncio.apply()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_bot())
