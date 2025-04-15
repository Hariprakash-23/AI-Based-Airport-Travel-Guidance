import os
import google.generativeai as genai
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import time
import hashlib
import json
from waitress import serve

load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CACHE_FILE = "airport_cache.json"
REQUEST_DELAY = 1  # Minimum seconds between requests

# Initialize cache
airport_cache = {}
try:
    with open(CACHE_FILE, 'r') as f:
        airport_cache = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    pass

# Initialize Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')

SYSTEM_PROMPT = """You are an AI airport travel assistant specializing in global airport navigation. Provide:
1. Terminal/gate navigation tips
2. Security checkpoint advice
3. Lounge access information
4. Transportation options
5. Airport-specific amenities
6. Real-time guidance (when possible)
Keep responses under 150 words, factual, and include estimated walking times where applicable."""

def get_cache_key(query):
    return hashlib.md5(query.encode()).hexdigest()

def save_cache():
    with open(CACHE_FILE, 'w') as f:
        json.dump(airport_cache, f)

def get_ai_response(query):
    cache_key = get_cache_key(query)
    
    if cache_key in airport_cache:
        return airport_cache[cache_key]
    
    time.sleep(REQUEST_DELAY)
    
    try:
        chat = model.start_chat(history=[])
        response = chat.send_message(f"{SYSTEM_PROMPT}\n\nQuery: {query}")
        result = response.text
        
        airport_cache[cache_key] = result
        save_cache()
        
        return result
    except Exception as e:
        if "quota" in str(e).lower():
            raise Exception("Service temporarily unavailable. Please try again later.")
        raise e

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api', methods=['POST'])
def airport_api():
    try:
        data = request.get_json()
        user_query = data.get("query", "").strip()
        
        if not user_query:
            return jsonify({"reply": "Please enter your airport travel question."}), 400
        
        if not GEMINI_API_KEY:
            raise Exception("Service not configured")
        
        reply = get_ai_response(user_query)
        return jsonify({"reply": reply})
    
    except Exception as e:
        # Airport-specific fallbacks
        fallbacks = {
            "security": "⌛ Allow 30-45 mins for security. Pack liquids in clear bags (100ml max), remove laptops, wear easy-off shoes.",
            "lounge": "💺 Most lounges require business class tickets or priority pass. Day passes often available (~$50). Locations near gates: ",
            "connection": "🔄 Minimum connection times: Domestic 45mins, International 90mins. Use airport maps or ask staff for fastest routes.",
            "baggage": "🛄 Checked bags usually due 60mins pre-flight. Carry-on max typically 7kg (varies by airline)."
        }
        
        for term, answer in fallbacks.items():
            if term in user_query.lower():
                return jsonify({"reply": answer})
        
        return jsonify({
            "reply": "✈️ General tip: Arrive 2hrs early for domestic, 3hrs for international flights. Check airport maps for gate locations.",
            "error": str(e)
        }), 500

if __name__ == '__main__':
    serve(app, host="0.0.0.0", port=5000)

