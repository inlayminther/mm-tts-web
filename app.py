import streamlit as st
import edge_tts
import asyncio
import tempfile
import os
import requests
import json
import base64
import re

# 1. Page Config
st.set_page_config(page_title="Gemini TTS (Final Fix)", page_icon="✅", layout="centered")

# --- Authentication ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

def check_login():
    user = st.session_state.get('input_username', '')
    pwd = st.session_state.get('input_password', '')
    try:
        if "credentials" in st.secrets and \
           user == st.secrets["credentials"]["username"] and \
           pwd == st.secrets["credentials"]["password"]:
            st.session_state['logged_in'] = True
        else:
            st.error("Login Failed!")
    except:
        st.error("Secrets Error")

if not st.session_state['logged_in']:
    st.title("🔐 Login")
    st.text_input("Username", key="input_username")
    st.text_input("Password", type="password", key="input_password")
    st.button("Login", on_click=check_login)
    st.stop()

# ==========================================
# Main App
# ==========================================

st.title("✅ Gemini TTS (Sentence Fix)")
st.caption("Splits long sentences automatically to avoid API errors.")

if st.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

# --- Voice Data ---
VOICE_DATA = {
    "မြန်မာ (Myanmar)": [
        {"name": "Edge - Male (Thiha)", "id": "my-MM-ThihaNeural", "type": "edge"},
        {"name": "Edge - Female (Nilar)", "id": "my-MM-NilarNeural", "type": "edge"},
        {"name": "Gemini AI - Female (Expressive)", "id": "en-US-Journey-F", "type": "google_api", "lang": "en-US"},
        {"name": "Gemini AI - Male (Deep)", "id": "en-US-Journey-D", "type": "google_api", "lang": "en-US"},
    ],
    "အင်္ဂလိပ် (English - US)": [
        {"name": "Gemini AI - Female (Expressive)", "id": "en-US-Journey-F", "type": "google_api", "lang": "en-US"},
        {"name": "Gemini AI - Male (Deep)", "id": "en-US-Journey-D", "type": "google_api", "lang": "en-US"},
        {"name": "Edge - Female (Aria)", "id": "en-US-AriaNeural", "type": "edge"},
        {"name": "Edge - Male (Christopher)", "id": "en-US-ChristopherNeural", "type": "edge"}
    ]
}

# Settings UI
st.subheader("Settings")
selected_language = st.selectbox("ဘာသာစကား", list(VOICE_DATA.keys()))
voice_options = VOICE_DATA[selected_language]
voice_names = [v["name"] for v in voice_options]
selected_voice_name = st.selectbox("အသံ (Voice)", voice_names)
selected_voice_data = next(item for item in voice_options if item["name"] == selected_voice_name)

if selected_language == "မြန်မာ (Myanmar)" and selected_voice_data["type"] == "google_api":
    st.warning("⚠️ English AI (Gemini) ကို မြန်မာစာ ဖတ်ခိုင်းနေပါသည်။")

if selected_voice_data["type"] == "edge":
    speed = st.slider("Speed (Edge Only)", 0.5, 2.0, 1.0, 0.1)
else:
    speed = 1.0

text_input = st.text_area("စာရိုက်ထည့်ပါ:", height=200)

# --- Functions ---

# Helper: Aggressive splitter for Sentence Length Error
# Reduces chunk size to 200 chars and prioritizes punctuation
def split_text_aggressive(text, max_length=200):
    chunks = []
    while len(text) > max_length:
        # Priority 1: Burmese Punctuation (။)
        split_at = text.rfind('။', 0, max_length)
        
        # Priority 2: Burmese Comma (၊)
        if split_at == -1:
            split_at = text.rfind('၊', 0, max_length)
            
        # Priority 3: English Sentence Enders (. ? !)
        if split_at == -1:
            # Simple regex search for last punctuation
            match = re.search(r'[.?!]', text[:max_length][::-1])
            if match:
                split_at = max_length - match.start() - 1

        # Priority 4: Space
        if split_at == -1:
            split_at = text.rfind(' ', 0, max_length)
        
        # Fallback: Hard cut if no punctuation found
        if split_at == -1:
            split_at = max_length
        else:
            split_at += 1 # Include the punctuation
            
        chunks.append(text[:split_at])
        text = text[split_at:]
    
    if text:
        chunks.append(text)
    return chunks

# 1. Edge TTS
async def generate_edge_tts(text, voice, rate_str):
    communicate = edge_tts.Communicate(text, voice, rate=rate_str) if rate_str != "+0%" else edge_tts.Communicate(text, voice)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
        tmp_path = tmp_file.name
    await communicate.save(tmp_path)
    return tmp_path

# 2. Google REST API (Chunked Loop)
def generate_google_api(text, voice_id, lang_code):
    if "gemini_api_key" not in st.secrets:
        return None, "Error: 'gemini_api_key' not found in secrets.toml"
    
    api_key = st.secrets["gemini_api_key"]
    url = f"https://texttospeech.googleapis.com/v1beta1/text:synthesize?key={api_key}"
    headers = {"Content-Type": "application/json"}

    # Step 1: Split Text (Using aggressive limit: 200 chars)
    chunks = split_text_aggressive(text)
    combined_audio = b""
    
    # Step 2: Loop chunks
    for i, chunk in enumerate(chunks):
        if not chunk.strip(): continue
        
        data = {
            "input": {"text": chunk},
            "voice": {"languageCode": lang_code, "name": voice_id},
            "audioConfig": {"audioEncoding": "MP3"}
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            if response.status_code == 200:
                response_json = response.json()
                combined_audio += base64.b64decode(response_json['audioContent'])
            else:
                # If chunk is still rejected, try one generic fallback
                return None, f"Chunk {i+1} Error: {response.json().get('error', {}).get('message', 'Unknown Error')}"
        except Exception as e:
            return None, str(e)
            
    # Step 3: Save Combined
    if combined_audio:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            tmp_file.write(combined_audio)
            tmp_path = tmp_file.name
        return tmp_path, None
    else:
        return None, "No audio generated."

# --- Generate Logic ---

if st.button("Generate Audio", type="primary"):
    if not text_input.strip():
        st.warning("စာရိုက်ထည့်ပါ")
    else:
        with st.spinner("Processing text..."):
            audio_path = None
            err = None
            
            if selected_voice_data["type"] == "edge":
                try:
                    pct = int((speed - 1) * 100)
                    rate = f"+{pct}%" if pct >= 0 else f"{pct}%"
                    if speed == 1.0: rate = "+0%"
                    audio_path = asyncio.run(generate_edge_tts(text_input, selected_voice_data["id"], rate))
                except Exception as e: err = str(e)
            
            elif selected_voice_data["type"] == "google_api":
                audio_path, err = generate_google_api(
                    text_input, 
                    selected_voice_data["id"],
                    selected_voice_data["lang"]
                )

            if err: st.error(err)
            elif audio_path:
                with open(audio_path, "rb") as f:
                    st.session_state['audio_data'] = f.read()
                os.remove(audio_path)

# --- Display ---
if 'audio_data' in st.session_state and st.session_state['audio_data']:
    st.markdown("---")
    st.success("Success!")
    st.audio(st.session_state['audio_data'], format="audio/mp3")
    st.download_button("Download MP3", st.session_state['audio_data'], "audio.mp3", "audio/mp3")
