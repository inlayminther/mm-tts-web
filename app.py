import streamlit as st
import edge_tts
import asyncio
import tempfile
import os
import requests
import json

# 1. Page Config
st.set_page_config(page_title="Gemini + Edge Hybrid", page_icon="💎", layout="centered")

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

st.title("💎 Gemini + Edge Hybrid TTS")
st.caption("AI Studio (Gemini) for Intelligence | Edge TTS for Reliability")

if st.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

# --- Voice Data ---
VOICE_DATA = {
    "Gemini (AI Studio - Smart)": [
        {"name": "Gemini - Puck (Upbeat)", "id": "Puck", "type": "gemini_flash"},
        {"name": "Gemini - Charon (Deep)", "id": "Charon", "type": "gemini_flash"},
        {"name": "Gemini - Zephyr (Bright)", "id": "Zephyr", "type": "gemini_flash"},
        {"name": "Gemini - Fenrir (Excited)", "id": "Fenrir", "type": "gemini_flash"},
    ],
    "Edge TTS (Standard - Reliable)": [
        {"name": "Edge - Thiha (Myanmar Male)", "id": "my-MM-ThihaNeural", "type": "edge"},
        {"name": "Edge - Nilar (Myanmar Female)", "id": "my-MM-NilarNeural", "type": "edge"},
        {"name": "Edge - Aria (English)", "id": "en-US-AriaNeural", "type": "edge"}
    ]
}

# Settings UI
st.subheader("Settings")
selected_category = st.selectbox("အမျိုးအစား (Category)", list(VOICE_DATA.keys()))
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

# Helper: Split text
def split_text(text, max_length=500):
    chunks = []
    while len(text) > max_length:
        split_at = text.rfind(' ', 0, max_length)
        if split_at == -1: split_at = max_length
        chunks.append(text[:split_at])
        text = text[split_at:]
    chunks.append(text)
    return chunks

# 1. Edge TTS Function
async def generate_edge_tts(text, voice, rate_str):
    communicate = edge_tts.Communicate(text, voice, rate=rate_str) if rate_str != "+0%" else edge_tts.Communicate(text, voice)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
        tmp_path = tmp_file.name
    await communicate.save(tmp_path)
    return tmp_path

# 2. Gemini 2.0 Flash API (With Retry Logic)
def generate_gemini_flash(text, voice_id):
    if "gemini_api_key" not in st.secrets:
        return None, "Error: 'gemini_api_key' not found in secrets.toml"
    
    api_key = st.secrets["gemini_api_key"]
    url = "https://generativelanguage.googleapis.com/v1beta/openai/audio/speech"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    chunks = split_text(text)
    combined_audio = b""
    
    for i, chunk in enumerate(chunks):
        if not chunk.strip(): continue
        
        # FIX: Try 'gemini-2.0-flash-exp' if 'gemini-2.0-flash' fails
        data = {
            "model": "gemini-2.0-flash-exp", 
            "input": chunk,
            "voice": voice_id
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            if response.status_code == 200:
                combined_audio += response.content
            else:
                # 404 or other error -> Return None to trigger fallback
                return None, f"Gemini Error ({response.status_code}): {response.text}"
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
            
            # --- Logic: Try Gemini -> Fallback to Edge ---
            
            if selected_voice_data["type"] == "gemini_flash":
                # Gemini ကို အရင်စမ်းမယ်
                audio_path, err = generate_gemini_flash(text_input, selected_voice_data["id"])
                
                # အကယ်၍ Error တက်ခဲ့ရင် (404, 500 etc.)
                if err:
                    st.warning(f"⚠️ Gemini API Error: {err}")
                    st.info("🔄 Switching to Edge TTS (Thiha) automatically...")
                    
                    # Edge TTS ကို အလိုအလျောက် ပြောင်းသုံးမယ်
                    try:
                        audio_path = asyncio.run(generate_edge_tts(text_input, "my-MM-ThihaNeural", "+0%"))
                        err = None # Error ကို ဖျောက်ပစ်မယ် (Edge အောင်မြင်ရင်)
                    except Exception as e:
                        err = f"Edge TTS Failed too: {str(e)}"

            elif selected_voice_data["type"] == "edge":
                # Edge TTS ရွေးထားရင် တန်းလုပ်မယ်
                try:
                    pct = int((speed - 1) * 100)
                    rate = f"+{pct}%" if pct >= 0 else f"{pct}%"
                    if speed == 1.0: rate = "+0%"
                    audio_path = asyncio.run(generate_edge_tts(text_input, selected_voice_data["id"], rate))
                except Exception as e: err = str(e)

            # --- Result ---
            if err: 
                st.error("အားနာပါတယ်၊ စနစ်နှစ်ခုလုံး အလုပ်မလုပ်ပါ:")
                st.code(err)
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
