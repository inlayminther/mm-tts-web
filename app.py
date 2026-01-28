import streamlit as st
import edge_tts
import asyncio
import tempfile
import os
from google.cloud import texttospeech
from google.oauth2 import service_account

# 1. Page Config
st.set_page_config(page_title="Hybrid TTS App", page_icon="🤖", layout="centered")

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

st.title("🤖 Hybrid Text-to-Speech")
st.caption("Supports: Edge TTS (Free) & Google Cloud TTS (Premium)")

# Logout
if st.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

# --- Voice Data Configuration ---
# Type ခွဲခြားထားပါတယ် (edge vs google)
VOICE_DATA = {
    "မြန်မာ (Myanmar)": [
        {"name": "Male (Thiha)", "id": "my-MM-ThihaNeural", "type": "edge"},
        {"name": "Female (Nilar)", "id": "my-MM-NilarNeural", "type": "edge"}
    ],
    "အင်္ဂလိပ် (English - US)": [
        {"name": "Edge - Female (Aria)", "id": "en-US-AriaNeural", "type": "edge"},
        {"name": "Edge - Male (Christopher)", "id": "en-US-ChristopherNeural", "type": "edge"},
        {"name": "Google - Studio Male", "id": "en-US-Studio-M", "type": "google", "lang_code": "en-US"},
        {"name": "Google - Studio Female", "id": "en-US-Studio-O", "type": "google", "lang_code": "en-US"},
        {"name": "Google - Journey (Expressive)", "id": "en-US-Journey-F", "type": "google", "lang_code": "en-US"}
    ]
}

# Settings UI
st.subheader("Settings")
selected_language = st.selectbox("ဘာသာစကား (Language)", list(VOICE_DATA.keys()))

# Voice Options ယူမယ်
voice_options = VOICE_DATA[selected_language]
# Display Name တွေကိုပဲ စာရင်းလုပ်မယ်
voice_names = [v["name"] for v in voice_options]
selected_voice_name = st.selectbox("အသံ (Voice)", voice_names)

# ရွေးလိုက်တဲ့ နာမည်နဲ့ သက်ဆိုင်တဲ့ Data အပြည့်အစုံကို ပြန်ရှာမယ်
selected_voice_data = next(item for item in voice_options if item["name"] == selected_voice_name)

speed = st.slider("Speed (Edge Only)", 0.5, 2.0, 1.0, 0.1)

text_input = st.text_area("စာရိုက်ထည့်ပါ:", height=150)

# --- Functions ---

# 1. Edge TTS Function (Async)
async def generate_edge_tts(text, voice, rate_str):
    communicate = edge_tts.Communicate(text, voice, rate=rate_str) if rate_str != "+0%" else edge_tts.Communicate(text, voice)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
        tmp_path = tmp_file.name
    await communicate.save(tmp_path)
    return tmp_path

# 2. Google Cloud TTS Function (Sync)
def generate_google_tts(text, voice_name, lang_code):
    try:
        # Secrets မှ Credentials ဖတ်ခြင်း
        if "gcp_service_account" not in st.secrets:
            return None, "Google Cloud Credentials not found in secrets!"
            
        creds = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"]
        )
        client = texttospeech.TextToSpeechClient(credentials=creds)

        input_text = texttospeech.SynthesisInput(text=text)
        
        # Voice Selection
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

        # File သိမ်းခြင်း
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            tmp_file.write(response.audio_content)
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

            # EDGE TTS
            if selected_voice_data["type"] == "edge":
                try:
                    # Edge Speed Calculation
                    pct = int((speed - 1) * 100)
                    rate_str = f"+{pct}%" if pct >= 0 else f"{pct}%"
                    if speed == 1.0: rate_str = "+0%"
                    
                    audio_file_path = asyncio.run(generate_edge_tts(text_input, selected_voice_data["id"], rate_str))
                except Exception as e:
                    error_msg = str(e)

            # GOOGLE TTS
            elif selected_voice_data["type"] == "google":
                audio_file_path, error_msg = generate_google_tts(
                    text_input, 
                    selected_voice_data["id"], 
                    selected_voice_data["lang_code"]
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
    st.success("အသံဖိုင် ရပါပြီ!")
    st.audio(st.session_state['audio_data'], format="audio/mp3")
    
    st.download_button(
        label="Download MP3",
        data=st.session_state['audio_data'],
        file_name="hybrid_tts.mp3",
        mime="audio/mp3"
    )
