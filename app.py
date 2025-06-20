import os
import json
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from contextlib import contextmanager

from flask import Flask, request, jsonify, session
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from thefuzz import fuzz
import nltk
from nltk.corpus import wordnet
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuration class
class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-fallback-key')
    MYSQL_HOST = os.getenv('MYSQL_HOST')
    MYSQL_USER = os.getenv('MYSQL_USER')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
    MYSQL_DB = os.getenv('MYSQL_DB')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))
    RATE_LIMIT = os.getenv('RATE_LIMIT', "200 per day,50 per hour")

app.config.from_object(Config)
app.secret_key = app.config['SECRET_KEY']

# Rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[app.config['RATE_LIMIT']],
    storage_uri="memory://"
)

# Logging
if not os.path.exists('logs'):
    os.mkdir('logs')
file_handler = RotatingFileHandler('logs/chatbot.log', maxBytes=10240, backupCount=10)
file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)

# Load and expand medical data
with open('data.json', 'r') as f:
    raw_data = json.load(f)

medical_data = {}
if isinstance(raw_data, list):
    for item in raw_data:
        symptom = item.get("symptom", "").lower()
        if symptom:
            medical_data[symptom] = {
                "diagnosis": item.get("diagnosis", "Unknown"),
                "solution": item.get("solution", "Please consult a doctor."),
                "doctors": item.get("doctors", [])
            }
else:
    medical_data = raw_data

# Download required NLTK data
nltk.download('wordnet', quiet=True)
nltk.download('punkt', quiet=True)

# Synonym normalization
synonym_map = {
    # Cold-related
    "cold": "cold", "nasal discharge": "cold", "runny nose": "cold", "flu": "cold",
    "rhinorrhea": "cold", "sneezing": "cold", "blocked nose": "cold", "congestion": "cold",
    "sinus": "cold", "sinus pressure": "cold", "cold symptoms": "cold", "i have a cold": "cold",
    "my nose is runny": "cold", "stuffed nose": "cold", "nose block": "cold",

    # Fatigue-related
    "fatigue": "fatigue", "tired": "fatigue", "lethargy": "fatigue", "exhausted": "fatigue",
    "weakness": "fatigue", "no energy": "fatigue", "sluggish": "fatigue", "feeling tired": "fatigue",
    "low energy": "fatigue", "feeling weak": "fatigue",

    # Vomiting-related
    "vomiting": "vomiting", "throwing up": "vomiting", "nausea": "vomiting", "queasiness": "vomiting",
    "retching": "vomiting", "feeling sick": "vomiting", "upset tummy": "vomiting", "i threw up": "vomiting",
    "threw up": "vomiting", "vomited": "vomiting", "puking": "vomiting", "i puked": "vomiting",
    "i feel like puking": "vomiting", "feel like throwing up": "vomiting", "i want to puke": "vomiting",
    "feeling to vomit": "vomiting", "feel nauseous": "vomiting",

    # Stomach pain-related
    "stomach pain": "stomach pain", "upset stomach": "stomach pain", "stomach ache": "stomach pain",
    "abdominal pain": "stomach pain", "belly pain": "stomach pain", "gastric pain": "stomach pain",
    "cramps": "stomach pain", "tummy pain": "stomach pain", "pain in abdomen": "stomach pain",
    "pain in stomach": "stomach pain", "gas pain": "stomach pain", "my stomach hurts": "stomach pain",

    # Blurred vision
    "blurred vision": "blurred vision", "dizziness": "blurred vision", "lightheadedness": "blurred vision",
    "vision problem": "blurred vision", "foggy vision": "blurred vision", "blurry vision": "blurred vision",
    "i feel dizzy": "blurred vision", "vision is blurry": "blurred vision",

    # Headache
    "headache": "headache", "migraine": "headache", "pain in head": "headache",
    "pressure in head": "headache", "head pain": "headache", "my head hurts": "headache",
    "throbbing head": "headache",

    # Fever
    "fever": "fever", "high temperature": "fever", "chills": "fever", "shivering": "fever",
    "hot body": "fever", "i feel hot": "fever", "my body is hot": "fever", "temperature": "fever",
    "high fever": "fever", "feverish": "fever",

    # Body ache
    "body ache": "body ache", "whole body pain": "body ache", "body pain": "body ache",
    "general pain": "body ache", "my body hurts": "body ache", "sore body": "body ache",

    # Joint pain
    "joint pain": "joint pain", "pain in joints": "joint pain", "arthritis pain": "joint pain",
    "joint stiffness": "joint pain", "aching joints": "joint pain", "swollen joints": "joint pain",

    # Muscle stiffness
    "muscle stiffness": "muscle stiffness", "tight muscles": "muscle stiffness",
    "rigid muscles": "muscle stiffness", "tense muscles": "muscle stiffness",
    "sore muscles": "muscle stiffness", "muscles feel tight": "muscle stiffness",

    # Back pain
    "back pain": "back pain", "lower back ache": "back pain", "spine pain": "back pain",
    "pain in back": "back pain", "aching back": "back pain", "my back hurts": "back pain",

    # Chest pain
    "chest pain": "chest pain", "tight chest": "chest pain", "pressure in chest": "chest pain",
    "chest tightness": "chest pain", "pain in chest": "chest pain", "hurts to breathe": "chest pain",

    # Shortness of breath
    "shortness of breath": "shortness of breath", "breathlessness": "shortness of breath",
    "difficulty breathing": "shortness of breath", "can't breathe": "shortness of breath",
    "trouble breathing": "shortness of breath", "hard to breathe": "shortness of breath",

    # Sweating
    "sweating": "sweating", "excessive sweat": "sweating", "sweating a lot": "sweating",
    "too much sweating": "sweating", "i'm sweating": "sweating", "sweating heavily": "sweating",

    # Skin rash
    "skin rash": "skin rash", "rashes": "skin rash", "patches on skin": "skin rash",
    "skin spots": "skin rash", "rash on skin": "skin rash", "itchy rash": "skin rash",

    # Itching
    "itching": "itching", "skin irritation": "itching", "scratching": "itching",
    "itchy skin": "itching", "skin is itchy": "itching", "itchy": "itching",

    # Redness
    "redness": "redness", "red patches": "redness", "inflamed skin": "redness",
    "red skin": "redness", "skin looks red": "redness", "red spots": "redness",

    # Sore throat
    "sore throat": "sore throat", "throat pain": "sore throat", "painful swallowing": "sore throat",
    "throat irritation": "sore throat", "scratchy throat": "sore throat", "my throat hurts": "sore throat",

    # Difficulty swallowing
    "difficulty swallowing": "difficulty swallowing", "hard to swallow": "difficulty swallowing",
    "can't swallow": "difficulty swallowing", "trouble swallowing": "difficulty swallowing",

    # Frequent urination
    "frequent urination": "frequent urination", "peeing often": "frequent urination",
    "urinating frequently": "frequent urination", "going to toilet often": "frequent urination",

    # Burning sensation
    "burning sensation": "burning sensation", "burning urination": "burning sensation",
    "painful urination": "burning sensation", "burn while peeing": "burning sensation",
    "pee burns": "burning sensation",

    # Cough
    "cough": "cough", "dry cough": "cough", "wet cough": "cough", "persistent cough": "cough",
    "continuous cough": "cough", "i'm coughing": "cough", "coughing a lot": "cough",

    # Swelling
    "swelling": "swelling", "inflammation": "swelling", "puffy": "swelling", "pufffy": "swelling",
    "puffy face": "swelling", "puffy hands": "swelling", "swollen": "swelling",
    "swollen feet": "swelling", "fluid retention": "swelling", "bloating": "swelling",
    "water retention": "swelling", "face is swollen": "swelling", "legs are swollen": "swelling",

    # Morning stiffness
    "morning stiffness": "morning stiffness", "stiff in the morning": "morning stiffness",
    "feel stiff in morning": "morning stiffness", "joint stiffness in morning": "morning stiffness",
    
    # Asthma-related
    "shortness of breath": "asthma", "wheezing": "asthma", "tight chest": "asthma",
    "can't breathe properly": "asthma", "difficulty breathing": "asthma", "breathlessness": "asthma",

    # Anxiety-related
    "palpitations": "anxiety", "nervous": "anxiety", "sweaty palms": "anxiety",
    "anxious": "anxiety", "panic attack": "anxiety", "chest flutter": "anxiety",

    # Dehydration-related
    "dry mouth": "dehydration", "no urine": "dehydration", "dark urine": "dehydration",
    "dry lips": "dehydration", "thirsty all the time": "dehydration", "dizzy and thirsty": "dehydration",

    # Food Poisoning-related
    "vomiting after eating": "food poisoning", "stomach cramps": "food poisoning",
    "diarrhea after food": "food poisoning", "bad food reaction": "food poisoning",

    # Indigestion-related
    "bloating": "indigestion", "gas": "indigestion", "acid reflux": "indigestion",
    "burping a lot": "indigestion", "discomfort after eating": "indigestion",

    # GERD-related
    "heartburn": "gerd", "acid taste": "gerd", "chest burning": "gerd", "sour burps": "gerd",

    # UTI-related
    "burning while peeing": "uti", "frequent urination": "uti", "cloudy urine": "uti",
    "painful urination": "uti", "pee smells bad": "uti",

    # Sinusitis-related
    "facial pressure": "sinusitis", "pain in cheeks": "sinusitis", "nasal pain": "sinusitis",
    "stuffed nose": "sinusitis", "sinus headache": "sinusitis",

    # Dengue-related
    "high fever": "dengue", "joint pain with fever": "dengue", "rash with fever": "dengue",
    "eye pain": "dengue", "platelet drop": "dengue",

    # Typhoid-related
    "fever for days": "typhoid", "loss of appetite": "typhoid", "weakness with fever": "typhoid",
    "slow pulse": "typhoid",

    # Malaria-related
    "fever with chills": "malaria", "sweating at night": "malaria", "body pain and fever": "malaria",
    "recurring fever": "malaria",

    # PCOD-related
    "irregular periods": "pcod", "weight gain": "pcod", "facial hair": "pcod", "acne": "pcod",

    # Diabetes-related
    "high blood sugar": "diabetes", "sugar in urine": "diabetes", "excessive thirst": "diabetes",
    "frequent peeing": "diabetes", "unexplained weight loss": "diabetes",

    # Hypertension-related
    "high bp": "hypertension", "blood pressure": "hypertension", "headache with pressure": "hypertension",

    # Hypothyroidism
    "dry skin": "hypothyroidism", "weight gain": "hypothyroidism", "cold hands and feet": "hypothyroidism",
    "fatigue": "hypothyroidism", "slow heart rate": "hypothyroidism",

    # Hyperthyroidism
    "sweaty all the time": "hyperthyroidism", "rapid heartbeat": "hyperthyroidism",
    "weight loss despite eating": "hyperthyroidism", "trembling hands": "hyperthyroidism",

    # Ear Infection
    "earache": "ear infection", "fluid from ear": "ear infection", "trouble hearing": "ear infection",
    "itchy ear": "ear infection",

    # Conjunctivitis
    "red eyes": "conjunctivitis", "eye discharge": "conjunctivitis", "itchy eyes": "conjunctivitis",
    "sticky eyes": "conjunctivitis", "swollen eyes": "conjunctivitis",

    # Pink Eye
    "eye redness": "conjunctivitis", "teary eyes": "conjunctivitis",

    # Anemia
    "pale skin": "anemia", "tired always": "anemia", "dizzy often": "anemia",
    "low hemoglobin": "anemia",

    # COVID-19
    "loss of taste": "covid-19", "loss of smell": "covid-19", "dry cough": "covid-19",
    "body pain with fever": "covid-19", "difficulty breathing": "covid-19",

    # Chickenpox
    "red spots": "chickenpox", "itchy rash": "chickenpox", "blisters on skin": "chickenpox",

    # Measles
    "koplik spots": "measles", "rash behind ears": "measles", "fever with rash": "measles",

    # Acne
    "pimples": "acne", "whiteheads": "acne", "blackheads": "acne", "oily skin": "acne",

    # Depression
    "low mood": "depression", "not interested in anything": "depression", "always sad": "depression",
    "feeling hopeless": "depression",

    # Insomnia
    "trouble sleeping": "insomnia", "wake up at night": "insomnia", "can't sleep": "insomnia",

    # Migraine
    "throbbing headache": "migraine", "light sensitivity": "migraine", "sound sensitivity": "migraine",
    "one-sided headache": "migraine",

    # Heart Attack
    "chest pain": "heart attack", "pain in left arm": "heart attack", "sweating suddenly": "heart attack",
    "short breath with chest pain": "heart attack",

    # Stroke
    "face drooping": "stroke", "slurred speech": "stroke", "arm weakness": "stroke",
    "sudden confusion": "stroke"
}

from nltk.corpus import wordnet as wn

def expand_symptoms(data):
    expanded_data = {}
    for symptom in data:
        expanded_data[symptom] = data[symptom]
        synonyms = set()
        for word in symptom.split():
            for syn in wn.synsets(word):
                for lemma in syn.lemmas():
                    synonyms.add(lemma.name().replace("_", " ").lower())
        for syn in synonyms:
            if syn not in expanded_data:
                expanded_data[syn] = data[symptom]
    return expanded_data

medical_data = expand_symptoms(medical_data)
# Synonym normalization
def get_synonyms(word):
    synonyms = set()
    for syn in wordnet.synsets(word):
        for lemma in syn.lemmas():
            synonyms.add(lemma.name().replace("_", " ").lower())
    synonyms.add(word.lower())
    return list(synonyms)

def generate_synonym_map(medical_data):
    synonym_map = {}
    for key in medical_data.keys():
        synonyms = get_synonyms(key)
        for synonym in synonyms:
            synonym_map[synonym] = key
    return synonym_map

def normalize_with_synonyms(text, synonym_map):
    text = text.lower().strip()
    if text in synonym_map:
        return synonym_map[text]
    for key in sorted(synonym_map, key=len, reverse=True):
        if key in text:
            text = text.replace(key, synonym_map[key])
    return text

# Chat history saving
def save_chat_to_file(user_input, bot_response):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("chat_history.txt", "a", encoding="utf-8") as file:
        file.write(f"{timestamp} - User: {user_input}\n")
        file.write(f"{timestamp} - Bot: {bot_response}\n\n")

# Routes
@app.route("/api/diagnose", methods=["POST"])
@limiter.limit("10 per minute")
def api_diagnose():
    app.logger.info("📥 Received POST /api/diagnose")

    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    symptoms_input = data.get("symptoms", "")

    if isinstance(symptoms_input, list):
        symptoms = " ".join(symptoms_input).lower().strip()
    elif isinstance(symptoms_input, str):
        symptoms = symptoms_input.lower().strip()
    else:
        return jsonify({"error": "Symptoms must be a string or list of strings"}), 400

    if not symptoms:
        return jsonify({"error": "Symptoms parameter is required"}), 400

    synonym_map = generate_synonym_map(medical_data)
    normalized_input = normalize_with_synonyms(symptoms, synonym_map)

    best_match = None
    highest_score = 0

    for symptom in medical_data.keys():
        score = fuzz.partial_ratio(normalized_input, symptom.lower())
        if score > highest_score:
            highest_score = score
            best_match = symptom

    if best_match and highest_score > 60:
        diagnosis_info = medical_data[best_match]
        diagnosis = diagnosis_info.get("diagnosis", "Diagnosis not available.")
        solution = diagnosis_info.get("solution", "No solution provided.")
        doctors = diagnosis_info.get("doctors", [])

        response_json = {
            "diagnosis": diagnosis,
            "solution": solution,
            "doctors": doctors,
            "matched_symptom": best_match,
            "match_score": highest_score
        }

        if "chat_history" not in session:
            session["chat_history"] = []

        session["chat_history"].append({
            "sender": "user",
            "message": symptoms,
            "timestamp": datetime.now().isoformat()
        })
        session["chat_history"].append({
            "sender": "bot",
            "message": response_json,
            "timestamp": datetime.now().isoformat()
        })
        session.modified = True

        save_chat_to_file(symptoms, json.dumps(response_json, indent=2))
        return jsonify(response_json)
    else:
        return jsonify({"error": "No matching symptom found."}), 404

@app.route("/api/symptoms", methods=["GET"])
def get_symptoms():
    return jsonify(list(medical_data.keys()))

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f"Server Error: {error}")
    return jsonify({"error": "Internal server error"}), 500

# Windows event loop fix
import asyncio

if __name__ == "__main__":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception as loop_err:
        app.logger.error(f"❌ Event loop policy error: {str(loop_err)}")
    app.run(debug=True)
