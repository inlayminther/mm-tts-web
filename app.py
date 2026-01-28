import streamlit as st
import edge_tts
import asyncio
import tempfile
import os
import requests
import base64
import re

# 1. Page Config
st.set_page_config(page_title="Smart TTS (Final)", page_icon="🎧", layout="centered")

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

st.title("🎧 Smart TTS (No Errors)")
st.caption("မြန်မာစာဆို Thiha နဲ့ဖတ်မယ်၊ English ဆို Gemini နဲ့ဖတ်မယ်။ (Auto-Switch)")

if st.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

# --- Voice Setup ---
# Gemini Voices (English Only)
GEMINI_VOICES = {
    "Puck Style (Expressive)": "en-US-Journey-F",
    "Charon Style (Deep)": "en-US-Journey-D",
    "Soft Style": "en-US-Journey-O",
}

# Edge Voices (Myanmar)
EDGE_VOICES = {
    "Thiha (Male)": "my-MM-ThihaNeural",
    "Nilar (Female)": "my-MM-NilarNeural"
}

# UI Selection
col1, col2 = st.columns(2)
with col1:
    # User က English Voice ကိုပဲ ရွေးထားမယ် (မြန်မာစာအတွက် စက်က အလိုလိုလုပ်ပေးလိမ့်မယ်)
    selected_gemini_name = st.selectbox("English Voice (Gemini)", list(GEMINI_VOICES.keys()))
    selected_gemini_id = GEMINI_VOICES[selected_gemini_name]

with col2:
    # မြန်မာစာအတွက် Fallback Voice
    selected_edge_name = st.selectbox("Myanmar Voice (Edge)", list(EDGE_VOICES.keys()))
    selected_edge_id = EDGE_VOICES[selected_edge_name]

text_input = st.text_area("စာရိုက်ထည့်ပါ:", height=200, placeholder="မြန်မာလို (သို့) English/Burglish ရိုက်ပါ...")

# --- Functions ---

# 1. Check if text has Myanmar characters
def is_myanmar_text(text):
    return bool(re.search(r'[\u1000-\u109F]', text))

# 2. Text Splitting (Safe Limit)
def split_text_safe(text, max_length=500):
    chunks = []
    while len(text) > max_length:
        split_at = text.rfind('။', 0, max_length)
        if split_at == -1: split_at = text.rfind(' ', 0, max_length)
        if split_at == -1: split_at = max_length
        else: split_at += 1
        chunks.append(text[:split_at])
        text = text[split_at:]
    chunks.append(text)
    return chunks

# 3. Edge TTS (For Myanmar)
async def generate_edge_tts(text, voice):
    communicate = edge_tts.Communicate(text, voice)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
        tmp_path = tmp_file.name
    await communicate.save(tmp_path)
    return tmp_path

# 4. Google Cloud TTS (For English - Journey Voice)
def generate_google_tts(text, voice_id):
    if "gemini_api_key" not in st.secrets:
        return None, "API Key Missing"
    
    api_key = st.secrets["gemini_api_key"]
    # Only using Text-to-Speech API (Not Generative Language) - This avoids 404
    url = f"https://texttospeech.googleapis.com/v1beta1/text:synthesize?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    chunks = split_text_safe(text)
    combined_audio = b""
    
    for chunk in chunks:
        if not chunk.strip(): continue
        data = {
            "input": {"text": chunk},
            "voice": {"languageCode": "en-US", "name": voice_id},
            "audioConfig": {"audioEncoding": "MP3"}
        }
        try:
            response = requests.post(url, headers=headers, json=data)
            if response.status_code == 200:
                combined_audio += base64.b64decode(response.json()['audioContent'])
            else:
                return None, f"TTS Error: {response.text}"
        except Exception as e:
            return None, str(e)
            
    if combined_audio:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            tmp_file.write(combined_audio)
            tmp_path = tmp_file.name
        return tmp_path, None
    else:
        return None, "No Audio"

# --- Main Logic ---

if st.button("Generate Audio", type="primary"):
    if not text_input.strip():
        st.warning("စာရိုက်ထည့်ပါ")
    else:
        audio_path = None
        err = None
        
        # --- SMART DECISION ENGINE ---
        if is_myanmar_text(text_input):
            # မြန်မာစာပါရင် Edge TTS (Thiha/Nilar) ကိုသုံးမယ် (ဂြိုလ်သားသံ ကာကွယ်ရန်)
            st.info(f"🇲🇲 Myanmar text detected: Using {selected_edge_name}")
            with st.spinner("Reading Myanmar text..."):
                try:
                    audio_path = asyncio.run(generate_edge_tts(text_input, selected_edge_id))
                except Exception as e:
                    err = str(e)
        else:
            # မြန်မာစာမပါရင် (English/Burglish) Gemini Voice ကိုသုံးမယ်
            st.info(f"🇺🇸 English/Burglish detected: Using {selected_gemini_name}")
            with st.spinner("Generating AI Voice..."):
                audio_path, err = generate_google_tts(text_input, selected_gemini_id)

        # --- Result ---
        if err:
            st.error("Error ဖြစ်သွားပါသည်:")
            st.code(err)
        elif audio_path:
            with open(audio_path, "rb") as f:
                st.session_state['audio_data'] = f.read()
            os.remove(audio_path)
            st.success("Success!")

if 'audio_data' in st.session_state and st.session_state['audio_data']:
    st.audio(st.session_state['audio_data'], format="audio/mp3")
    st.download_button("Download MP3", st.session_state['audio_data'], "audio.mp3", "audio/mp3")
