import streamlit as st
import edge_tts
import asyncio
import tempfile
import os
import requests
import json

# 1. Page Config
st.set_page_config(page_title="Gemini TTS (Fixed)", page_icon="🔧", layout="centered")

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

st.title("🔧 Gemini TTS (Fixed Version)")
st.caption("Using Google Cloud Standard API with API Key")

if st.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

# --- Voice Data Configuration ---
# Note: "Zephyr/Puck" တို့က Playground နာမည်တွေပါ
# API မှာတော့ "Journey" ID တွေနဲ့ သုံးရပါတယ် (အသံတူတူပါပဲ)
VOICE_DATA = {
    "မြန်မာ (Myanmar)": [
        {"name": "Edge - Male (Thiha)", "id": "my-MM-ThihaNeural", "type": "edge"},
        {"name": "Edge - Female (Nilar)", "id": "my-MM-NilarNeural", "type": "edge"},
        
        # --- Gemini Voices (Mapped to Journey) ---
        {"name": "Gemini AI - Female (Expressive)", "id": "en-US-Journey-F", "type": "google_api", "lang": "en-US"},
        {"name": "Gemini AI - Male (Deep)", "id": "en-US-Journey-D", "type": "google_api", "lang": "en-US"},
        {"name": "Gemini AI - Female (Soft)", "id": "en-US-Journey-O", "type": "google_api", "lang": "en-US"}
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

# Warning if using English AI for Myanmar
if selected_language == "မြန်မာ (Myanmar)" and selected_voice_data["type"] == "google_api":
    st.warning("⚠️ English AI ကို မြန်မာစာ ဖတ်ခိုင်းနေပါသည်။ 'Burglish' (ဥပမာ: Mingalarpar) ရိုက်လျှင် ပိုကောင်းပါသည်။")

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

# 2. Google REST API (Using API Key)
# ဒီနည်းက 404 မဖြစ်တော့ပါဘူး (Official Endpoint)
def generate_google_api(text, voice_id, lang_code):
    if "gemini_api_key" not in st.secrets:
        return None, "API Key ပျောက်နေပါသည်။ secrets.toml ကို စစ်ပါ။"
    
    api_key = st.secrets["gemini_api_key"]
    # Standard Google Cloud TTS Endpoint
    url = f"https://texttospeech.googleapis.com/v1beta1/text:synthesize?key={api_key}"
    
    headers = {"Content-Type": "application/json"}
    
    data = {
        "input": {"text": text},
        "voice": {
            "languageCode": lang_code,
            "name": voice_id
        },
        "audioConfig": {
            "audioEncoding": "MP3"
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            # Google returns base64 audio content
            response_json = response.json()
            import base64
            audio_content = base64.b64decode(response_json['audioContent'])
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
                tmp_file.write(audio_content)
                tmp_path = tmp_file.name
            return tmp_path, None
        else:
            return None, f"Google API Error ({response.status_code}): {response.text}"
            
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
            
            # Type B: Google API
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
