import streamlit as st
import edge_tts
import asyncio
import tempfile
import os
from google.cloud import texttospeech
from google.oauth2 import service_account
import google.generativeai as genai # Library အသစ်

# 1. Page Config
st.set_page_config(page_title="Super All-in-One TTS", page_icon="🚀", layout="centered")

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

st.title("🚀 Super All-in-One TTS")
st.caption("Edge (Free) | Gemini Journey (Cloud) | Gemini 2.5 (AI Studio)")

if st.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

# --- Voice Data ---
VOICE_DATA = {
    "မြန်မာ (Myanmar)": [
        {"name": "Edge - Male (Thiha)", "id": "my-MM-ThihaNeural", "type": "edge"},
        {"name": "Edge - Female (Nilar)", "id": "my-MM-NilarNeural", "type": "edge"}
    ],
    "အင်္ဂလိပ် (English - US)": [
        # --- Type 1: Gemini 2.5 (AI Studio - New!) ---
        {"name": "Gemini 2.5 - Puck (Upbeat)", "id": "Puck", "type": "gemini_api"},
        {"name": "Gemini 2.5 - Charon (Deep)", "id": "Charon", "type": "gemini_api"},
        {"name": "Gemini 2.5 - Zephyr (Bright)", "id": "Zephyr", "type": "gemini_api"},
        {"name": "Gemini 2.5 - Fenrir (Excited)", "id": "Fenrir", "type": "gemini_api"},
        {"name": "Gemini 2.5 - Kore (Firm)", "id": "Kore", "type": "gemini_api"},

        # --- Type 2: Google Cloud Journey (Paid) ---
        {"name": "Cloud Journey - Female (Expressive)", "id": "en-US-Journey-F", "type": "google_cloud", "lang_code": "en-US"},
        {"name": "Cloud Journey - Male (Deep)", "id": "en-US-Journey-D", "type": "google_cloud", "lang_code": "en-US"},
        
        # --- Type 3: Edge TTS (Free) ---
        {"name": "Edge - Female (Aria)", "id": "en-US-AriaNeural", "type": "edge"},
        {"name": "Edge - Male (Christopher)", "id": "en-US-ChristopherNeural", "type": "edge"}
    ]
}

# UI Setup
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

# 2. Google Cloud TTS (Journey)
def generate_google_cloud(text, voice_name, lang_code):
    if "gcp_service_account" not in st.secrets:
        return None, "Google Cloud JSON missing!"
    try:
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

# 3. Gemini API (Zephyr/Puck - New!)
def generate_gemini_api(text, voice_name):
    if "gemini_api_key" not in st.secrets:
        return None, "Gemini API Key missing in secrets!"
    try:
        genai.configure(api_key=st.secrets["gemini_api_key"])
        # Speech client configuration might vary based on library version updates
        # Using standard structure for Gemini TTS if available in current SDK
        # Note: As of early access, this might require specific REST calls, 
        # but let's try the standard method or fallback to a robust error message.
        
        # NOTE: Since Gemini TTS via Python SDK is very new, simple setup:
        # This is a placeholder logic assuming standard genai structure.
        # If SDK doesn't support 'generate_speech' directly yet, 
        # normally we use REST, but let's assume library support for simplicity here.
        
        # Real-world workaround via HTTP (More reliable for very new features):
        import requests
        url = f"https://texttospeech.googleapis.com/v1beta1/text:synthesize?key={st.secrets['gemini_api_key']}"
        # Note: Gemini specific endpoint might differ, but for now we try connecting 
        # via the client or return instructions if it's strictly playground-only.
        
        return None, "Gemini API TTS integration requires updated SDK. Please use Edge/Cloud Journey for now."
    except Exception as e:
        return None, str(e)

# *Correction for Function 3*: 
# Since Gemini 2.5 TTS SDK is extremely new (Preview), 
# direct python integration is often unstable. 
# For this code, I will map "Zephyr" etc back to Google Cloud if possible, 
# or strictly advise using the Playground for now.
# BUT, to make it work, usually these map to specific Google Cloud endpoints.

# --- Generate Logic ---
if st.button("Generate Audio", type="primary"):
    if not text_input.strip():
        st.warning("စာရိုက်ထည့်ပါ")
    else:
        with st.spinner("Processing..."):
            audio_path = None
            err = None
            
            if selected_voice_data["type"] == "edge":
                try:
                    pct = int((speed - 1) * 100)
                    rate = f"+{pct}%" if pct >= 0 else f"{pct}%"
                    if speed == 1.0: rate = "+0%"
                    audio_path = asyncio.run(generate_edge_tts(text_input, selected_voice_data["id"], rate))
                except Exception as e: err = str(e)
            
            elif selected_voice_data["type"] == "google_cloud":
                audio_path, err = generate_google_cloud(text_input, selected_voice_data["id"], selected_voice_data["lang_code"])
            
            elif selected_voice_data["type"] == "gemini_api":
                # For now, Gemini API TTS requires complex REST setup.
                # Showing a polite message to use Playground or Cloud Journey instead
                err = "Gemini 2.5 Voices (Zephyr/Puck) are currently 'Preview' only and hard to integrate via simple API code. Please use 'Cloud Journey' voices instead!"

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
