import streamlit as st
import edge_tts
import asyncio
import tempfile
import os
import requests
import base64
import re

# 1. Page Config
st.set_page_config(page_title="Ultimate TTS (Edge + Gemini)", page_icon="🎧", layout="centered")

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

st.title("🎧 Ultimate TTS")
st.caption("Edge TTS (Free) + Gemini Journey (API Key)")

if st.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

# --- Voice Data ---
# Edge TTS နဲ့ Gemini Journey ကို ရောထည့်ပေးထားပါတယ်
VOICE_DATA = {
    "မြန်မာ (Myanmar)": [
        {"name": "Edge - Thiha (Male)", "id": "my-MM-ThihaNeural", "type": "edge"},
        {"name": "Edge - Nilar (Female)", "id": "my-MM-NilarNeural", "type": "edge"},
        # မြန်မာစာကို Gemini ဖတ်ခိုင်းရင် အဆင်မပြေနိုင်ပေမဲ့ ထည့်ပေးထားပါတယ်
        {"name": "Gemini AI - Male (Deep)", "id": "en-US-Journey-D", "type": "google_api", "lang": "en-US"},
        {"name": "Gemini AI - Female (Expressive)", "id": "en-US-Journey-F", "type": "google_api", "lang": "en-US"},
    ],
    "အင်္ဂလိပ် (English - US)": [
        {"name": "Gemini AI - Male (Deep)", "id": "en-US-Journey-D", "type": "google_api", "lang": "en-US"},
        {"name": "Gemini AI - Female (Expressive)", "id": "en-US-Journey-F", "type": "google_api", "lang": "en-US"},
        {"name": "Gemini AI - Female (Soft)", "id": "en-US-Journey-O", "type": "google_api", "lang": "en-US"},
        {"name": "Edge - Aria (Female)", "id": "en-US-AriaNeural", "type": "edge"},
        {"name": "Edge - Christopher (Male)", "id": "en-US-ChristopherNeural", "type": "edge"}
    ]
}

# Settings UI
st.subheader("Settings")
selected_category = st.selectbox("ဘာသာစကား (Language)", list(VOICE_DATA.keys()))
voice_options = VOICE_DATA[selected_category]
voice_names = [v["name"] for v in voice_options]
selected_voice_name = st.selectbox("အသံ (Voice)", voice_names)
selected_voice_data = next(item for item in voice_options if item["name"] == selected_voice_name)

# Speed Slider (Edge Only)
if selected_voice_data["type"] == "edge":
    speed = st.slider("Speed (Edge Only)", 0.5, 2.0, 1.0, 0.1)
else:
    speed = 1.0

text_input = st.text_area("စာရိုက်ထည့်ပါ:", height=200)

# --- Functions ---

# Helper: Split text safely (Google API Limit Fix)
def split_text_safe(text, max_length=200):
    chunks = []
    while len(text) > max_length:
        # Priority: Burmese Punctuation -> English Punctuation -> Space
        split_at = text.rfind('။', 0, max_length)
        if split_at == -1: split_at = text.rfind('၊', 0, max_length)
        if split_at == -1: 
             match = re.search(r'[.?!]', text[:max_length][::-1])
             if match: split_at = max_length - match.start() - 1
        if split_at == -1: split_at = text.rfind(' ', 0, max_length)
        
        if split_at == -1: split_at = max_length
        else: split_at += 1
            
        chunks.append(text[:split_at])
        text = text[split_at:]
    if text: chunks.append(text)
    return chunks

# 1. Edge TTS Function
async def generate_edge_tts(text, voice, rate_str):
    communicate = edge_tts.Communicate(text, voice, rate=rate_str) if rate_str != "+0%" else edge_tts.Communicate(text, voice)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
        tmp_path = tmp_file.name
    await communicate.save(tmp_path)
    return tmp_path

# 2. Google Cloud API (Journey Voices)
def generate_google_api(text, voice_id, lang_code):
    if "gemini_api_key" not in st.secrets:
        return None, "Error: 'gemini_api_key' not found in secrets.toml"
    
    api_key = st.secrets["gemini_api_key"]
    # Stable Endpoint (User enabled this in console)
    url = f"https://texttospeech.googleapis.com/v1beta1/text:synthesize?key={api_key}"
    headers = {"Content-Type": "application/json"}

    chunks = split_text_safe(text)
    combined_audio = b""
    
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
                # Debug Info
                error_msg = f"API Error (Chunk {i+1}): {response.text}"
                return None, error_msg
        except Exception as e:
            return None, str(e)
            
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
        with st.spinner("Processing..."):
            audio_path = None
            err = None
            
            # --- Logic Switcher ---
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

            # --- Result ---
            if err: 
                st.error("Something went wrong!")
                with st.expander("Show Error Details"):
                    st.code(err) # Error အသေးစိတ်ကို ဒီမှာကြည့်နိုင်ပါတယ်
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
