import streamlit as st
import edge_tts
import asyncio
import tempfile
import os
from google.cloud import texttospeech
from google.oauth2 import service_account
import google.generativeai as genai

# 1. Page Config
st.set_page_config(page_title="Pro TTS (Force Mode)", page_icon="🔥", layout="centered")

# --- Authentication Logic ---
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

st.title("🔥 Pro TTS (Experimental)")
st.caption("Using English AI Models to read Myanmar Text (Experimental)")

if st.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

# --- Voice Data Configuration ---
# ဒီနေရာမှာ ပြင်ထားပါတယ် - မြန်မာအောက်မှာ English Journey တွေကို ထည့်လိုက်ပါတယ်
VOICE_DATA = {
    "မြန်မာ (Myanmar)": [
        # --- Native Myanmar Voices (အသံမှန်) ---
        {"name": "Edge - Male (Thiha)", "id": "my-MM-ThihaNeural", "type": "edge"},
        {"name": "Edge - Female (Nilar)", "id": "my-MM-NilarNeural", "type": "edge"},
        
        # --- Gemini Journey (Forced English AI) ---
        # lang_code ကို en-US ထားမှ Google က လက်ခံမှာမို့ en-US ပဲ ထားထားပါတယ်
        {"name": "Gemini AI - Female (Expressive)", "id": "en-US-Journey-F", "type": "google_cloud", "lang_code": "en-US"},
        {"name": "Gemini AI - Male (Deep)", "id": "en-US-Journey-D", "type": "google_cloud", "lang_code": "en-US"},
        {"name": "Gemini AI - Female (Soft)", "id": "en-US-Journey-O", "type": "google_cloud", "lang_code": "en-US"}
    ],
    "အင်္ဂလိပ် (English - US)": [
        {"name": "Gemini Journey - Female (Expressive)", "id": "en-US-Journey-F", "type": "google_cloud", "lang_code": "en-US"},
        {"name": "Gemini Journey - Male (Deep)", "id": "en-US-Journey-D", "type": "google_cloud", "lang_code": "en-US"},
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

# Warning Message for Experimental Voices
if selected_language == "မြန်မာ (Myanmar)" and selected_voice_data["type"] == "google_cloud":
    st.warning("⚠️ သတိပေးချက်: သင်သည် English AI ကို မြန်မာစာ ဖတ်ခိုင်းနေပါသည်။ 'Burglish' (ဥပမာ - Mingalarpar) ရိုက်ထည့်ပါက ပိုအဆင်ပြေနိုင်ပါသည်။")

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

# 2. Google Cloud TTS (Journey)
def generate_google_cloud(text, voice_name, lang_code):
    if "gcp_service_account" not in st.secrets:
        return None, "Google Cloud JSON missing!"
    try:
        creds = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"])
        client = texttospeech.TextToSpeechClient(credentials=creds)
        
        input_text = texttospeech.SynthesisInput(text=text)
        
        # Force Enable: Language Code ကို Dictionary ထဲကအတိုင်း (en-US) ပို့ပါမယ်
        voice = texttospeech.VoiceSelectionParams(
            language_code=lang_code, 
            name=voice_name
        )
        
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )

        response = client.synthesize_speech(
            input=input_text, voice=voice, audio_config=audio_config
        )
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            tmp_file.write(response.audio_content)
            tmp_path = tmp_file.name
        return tmp_path, None
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
            
            # Type B: Google Cloud (Journey)
            elif selected_voice_data["type"] == "google_cloud":
                audio_path, err = generate_google_cloud(
                    text_input, 
                    selected_voice_data["id"], 
                    selected_voice_data["lang_code"] # ဒီမှာ en-US ပါသွားပါလိမ့်မယ်
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
