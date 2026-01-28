import streamlit as st
import edge_tts
import asyncio
import tempfile
import os
import requests  # API လှမ်းခေါ်ရန်
from google.cloud import texttospeech
from google.oauth2 import service_account

# 1. Page Config
st.set_page_config(page_title="Gemini 2.5 TTS App", page_icon="🤖", layout="centered")

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

st.title("🤖 Gemini 2.5 + Edge TTS")
st.caption("Now supporting: Zephyr, Puck, Charon (via Gemini API)")

if st.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

# --- Voice Data Configuration ---
VOICE_DATA = {
    "မြန်မာ (Myanmar)": [
        # --- Edge TTS (Native) ---
        {"name": "Edge - Male (Thiha)", "id": "my-MM-ThihaNeural", "type": "edge"},
        {"name": "Edge - Female (Nilar)", "id": "my-MM-NilarNeural", "type": "edge"},
        
        # --- Gemini 2.5 Voices (AI Studio Voices) ---
        # ဒါတွေက AI Studio မှာ မြင်ရတဲ့ အသံတွေပါ
        {"name": "Gemini 2.5 - Puck (Upbeat)", "id": "Puck", "type": "gemini_api"},
        {"name": "Gemini 2.5 - Charon (Deep)", "id": "Charon", "type": "gemini_api"},
        {"name": "Gemini 2.5 - Zephyr (Bright)", "id": "Zephyr", "type": "gemini_api"},
        {"name": "Gemini 2.5 - Fenrir (Excited)", "id": "Fenrir", "type": "gemini_api"},
        {"name": "Gemini 2.5 - Kore (Firm)", "id": "Kore", "type": "gemini_api"}
    ],
    "အင်္ဂလိပ် (English - US)": [
        {"name": "Gemini 2.5 - Puck (Upbeat)", "id": "Puck", "type": "gemini_api"},
        {"name": "Gemini 2.5 - Zephyr (Bright)", "id": "Zephyr", "type": "gemini_api"},
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

# Speed Slider (Edge Only)
if selected_voice_data["type"] == "edge":
    speed = st.slider("Speed (Edge Only)", 0.5, 2.0, 1.0, 0.1)
else:
    speed = 1.0

text_input = st.text_area("စာရိုက်ထည့်ပါ:", height=150)

# --- Functions ---

# 1. Edge TTS
async def generate_edge_tts(text, voice, rate_str):
    communicate = edge_tts.Communicate(text, voice, rate=rate_str) if rate_str != "+0%" else edge_tts.Communicate(text, voice)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
        tmp_path = tmp_file.name
    await communicate.save(tmp_path)
    return tmp_path

# 2. Gemini API (Direct Request via OpenAI-Compatible Endpoint)
# ဒီ Function က AI Studio က အသံတွေကို တိုက်ရိုက်ဆွဲထုတ်ပေးပါမယ်
def generate_gemini_api(text, voice_id):
    if "gemini_api_key" not in st.secrets:
        return None, "Gemini API Key မရှိပါ။ secrets.toml တွင် ထည့်ပေးပါ။"
    
    api_key = st.secrets["gemini_api_key"]
    # Google ၏ Speech Endpoint (OpenAI Compatible)
    url = "https://generativelanguage.googleapis.com/v1beta/openai/audio/speech"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "gemini-2.0-flash", # AI Studio သုံး Model
        "input": text,
        "voice": voice_id # Puck, Zephyr, etc.
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
                tmp_file.write(response.content)
                tmp_path = tmp_file.name
            return tmp_path, None
        else:
            return None, f"API Error: {response.status_code} - {response.text}"
            
    except Exception as e:
        return None, str(e)

# --- Generate Logic ---

if st.button("Generate Audio", type="primary"):
    if not text_input.strip():
        st.warning("စာရိုက်ထည့်ပါ")
    else:
        with st.spinner("Creating Audio..."):
            audio_path = None
            err = None
            
            # Type A: Edge TTS
            if selected_voice_data["type"] == "edge":
                try:
                    pct = int((speed - 1) * 100)
                    rate = f"+{pct}%" if pct >= 0 else f"{pct}%"
                    if speed == 1.0: rate = "+0%"
                    audio_path = asyncio.run(generate_edge_tts(text_input, selected_voice_data["id"], rate))
                except Exception as e: err = str(e)
            
            # Type B: Gemini API (AI Studio Voices)
            elif selected_voice_data["type"] == "gemini_api":
                audio_path, err = generate_gemini_api(
                    text_input, 
                    selected_voice_data["id"]
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
