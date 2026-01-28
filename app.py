import streamlit as st
import edge_tts
import asyncio
import tempfile
import os
from google.cloud import texttospeech
from google.oauth2 import service_account
from gtts import gTTS  # gTTS library အသစ်ထည့်ထားပါတယ်

# 1. Page Config
st.set_page_config(page_title="Super Hybrid TTS", page_icon="🔊", layout="centered")

# --- Authentication Logic (Login) ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

def check_login():
    user = st.session_state.get('input_username', '')
    pwd = st.session_state.get('input_password', '')
    try:
        # Secrets စစ်ဆေးခြင်း
        if "credentials" in st.secrets and \
           user == st.secrets["credentials"]["username"] and \
           pwd == st.secrets["credentials"]["password"]:
            st.session_state['logged_in'] = True
        else:
            st.error("Login Failed")
    except Exception:
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

st.title("🔊 Super Hybrid Text-to-Speech")
st.caption("Includes: Edge TTS, Google Cloud API & gTTS (Google Translate)")

# Logout
if st.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

# --- Voice Data Configuration ---
# Type (3) မျိုး ခွဲထားပါတယ်: edge, google, gtts
VOICE_DATA = {
    "မြန်မာ (Myanmar)": [
        {"name": "Edge - Male (Thiha)", "id": "my-MM-ThihaNeural", "type": "edge"},
        {"name": "Edge - Female (Nilar)", "id": "my-MM-NilarNeural", "type": "edge"},
        {"name": "Google Translate (gTTS)", "id": "my", "type": "gtts"} # gTTS အတွက် မြန်မာ code က 'my' ပါ
    ],
    "အင်္ဂလိပ် (English - US)": [
        {"name": "Edge - Female (Aria)", "id": "en-US-AriaNeural", "type": "edge"},
        {"name": "Edge - Male (Christopher)", "id": "en-US-ChristopherNeural", "type": "edge"},
        {"name": "gTTS - English US", "id": "en", "type": "gtts", "tld": "us"},
        {"name": "Google Cloud - Studio Male", "id": "en-US-Studio-M", "type": "google", "lang_code": "en-US"}
    ]
}

# Settings UI
st.subheader("Settings")
selected_language = st.selectbox("ဘာသာစကား (Language)", list(VOICE_DATA.keys()))

# Voice Options
voice_options = VOICE_DATA[selected_language]
voice_names = [v["name"] for v in voice_options]
selected_voice_name = st.selectbox("အသံ (Voice)", voice_names)

# Get selected voice data
selected_voice_data = next(item for item in voice_options if item["name"] == selected_voice_name)

# Speed Slider (Show only for Edge)
if selected_voice_data["type"] == "edge":
    speed = st.slider("Speed (Edge Only)", 0.5, 2.0, 1.0, 0.1)
else:
    speed = 1.0 # Default

text_input = st.text_area("စာရိုက်ထည့်ပါ:", height=150)

# --- Functions ---

# 1. Edge TTS Function
async def generate_edge_tts(text, voice, rate_str):
    communicate = edge_tts.Communicate(text, voice, rate=rate_str) if rate_str != "+0%" else edge_tts.Communicate(text, voice)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
        tmp_path = tmp_file.name
    await communicate.save(tmp_path)
    return tmp_path

# 2. Google Cloud TTS Function
def generate_google_cloud_tts(text, voice_name, lang_code):
    try:
        if "gcp_service_account" not in st.secrets:
            return None, "Google Cloud Credentials not found!"
        creds = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"])
        client = texttospeech.TextToSpeechClient(credentials=creds)
        input_text = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(language_code=lang_code, name=voice_name)
        audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
        response = client.synthesize_speech(input=input_text, voice=voice, audio_config=audio_config)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            tmp_file.write(response.audio_content)
            tmp_path = tmp_file.name
        return tmp_path, None
    except Exception as e:
        return None, str(e)

# 3. gTTS Function (New!)
def generate_gtts(text, lang_code, tld='com'):
    try:
        # gTTS object တည်ဆောက်ခြင်း
        tts = gTTS(text=text, lang=lang_code, tld=tld, slow=False)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            # gTTS save method
            tts.save(tmp_file.name)
            tmp_path = tmp_file.name
        return tmp_path, None
    except Exception as e:
        return None, str(e)

# --- Generate Button Logic ---

if st.button("Generate Audio", type="primary"):
    if not text_input.strip():
        st.warning("စာရိုက်ထည့်ပါ")
    else:
        with st.spinner("Processing..."):
            audio_file_path = None
            error_msg = None
            
            # TYPE စစ်ဆေးပြီး သက်ဆိုင်ရာ Function ကို ခေါ်မယ်
            
            # === TYPE A: EDGE TTS ===
            if selected_voice_data["type"] == "edge":
                try:
                    pct = int((speed - 1) * 100)
                    rate_str = f"+{pct}%" if pct >= 0 else f"{pct}%"
                    if speed == 1.0: rate_str = "+0%"
                    audio_file_path = asyncio.run(generate_edge_tts(text_input, selected_voice_data["id"], rate_str))
                except Exception as e:
                    error_msg = str(e)

            # === TYPE B: GOOGLE CLOUD ===
            elif selected_voice_data["type"] == "google":
                audio_file_path, error_msg = generate_google_cloud_tts(
                    text_input, 
                    selected_voice_data["id"], 
                    selected_voice_data["lang_code"]
                )
            
            # === TYPE C: gTTS (FREE GOOGLE) ===
            elif selected_voice_data["type"] == "gtts":
                # English အတွက် accent (tld) ပါရင် ထည့်ပေးမယ်
                tld = selected_voice_data.get("tld", "com") 
                audio_file_path, error_msg = generate_gtts(
                    text_input,
                    selected_voice_data["id"], # 'my' or 'en'
                    tld
                )

            # Result Handling
            if error_msg:
                st.error(f"Error: {error_msg}")
            elif audio_file_path:
                with open(audio_file_path, "rb") as f:
                    audio_bytes = f.read()
                    st.session_state['audio_data'] = audio_bytes
                os.remove(audio_file_path)

# --- Display & Download ---
if 'audio_data' in st.session_state and st.session_state['audio_data']:
    st.markdown("---")
    st.success("Success!")
    st.audio(st.session_state['audio_data'], format="audio/mp3")
    
    st.download_button(
        label="Download MP3",
        data=st.session_state['audio_data'],
        file_name="tts_audio.mp3",
        mime="audio/mp3"
    )
