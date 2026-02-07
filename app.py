import streamlit as st
import edge_tts
import asyncio
import os

# 1. Page Config
st.set_page_config(page_title="Secure Edge TTS", page_icon="🔒", layout="centered")


# ==========================================
# Main App (Login ဝင်ပြီးမှ မြင်ရမည့်အပိုင်း)
# ==========================================

st.title("Simple Edge TTS")
st.caption("Free & Unlimited (Myanmar + English)")

# --- Session State for Audio ---
if 'audio_bytes' not in st.session_state:
    st.session_state['audio_bytes'] = None

# --- Voice Settings ---
language = st.radio("ဘာသာစကား (Language):", ["မြန်မာ (Myanmar)", "အင်္ဂလိပ် (English)"], horizontal=True)

if language == "မြန်မာ (Myanmar)":
    voice_options = {
        "Thiha (Male) - သီဟ": "my-MM-ThihaNeural",
        "Nilar (Female) - နီလာ": "my-MM-NilarNeural"
    }
else:
    voice_options = {
        "Aria (Female) - US": "en-US-AriaNeural",
        "Christopher (Male) - US": "en-US-ChristopherNeural",
        "Guy (Male) - US": "en-US-GuyNeural",
        "Jenny (Female) - US": "en-US-JennyNeural",
        "Brian (Male) - UK": "en-GB-BrianNeural",
        "Sonia (Female) - UK": "en-GB-SoniaNeural"
    }

selected_voice_name = st.selectbox("အသံရွေးပါ (Select Voice):", list(voice_options.keys()))
selected_voice_id = voice_options[selected_voice_name]

# --- Speed Control ---
speed = st.slider("အသံအမြန်နှုန်း (Speed):", min_value=0.5, max_value=2.0, value=1.0, step=0.1)

# --- Text Input ---
text_input = st.text_area("စာရိုက်ထည့်ပါ (Enter Text):", height=200, placeholder="ဒီမှာ စာရိုက်ပါ...")

# --- Logic ---
async def generate_audio(text, voice, speed_val):
    percentage = int((speed_val - 1) * 100)
    if percentage >= 0:
        rate_str = f"+{percentage}%"
    else:
        rate_str = f"{percentage}%"
    
    communicate = edge_tts.Communicate(text, voice, rate=rate_str)
    
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
            
    return audio_data

# Generate Button
if st.button("Generate Audio", type="primary"):
    if not text_input.strip():
        st.warning("စာရိုက်ထည့်ပါ...")
    else:
        with st.spinner("Generating..."):
            try:
                audio_data = asyncio.run(generate_audio(text_input, selected_voice_id, speed))
                st.session_state['audio_bytes'] = audio_data
            except Exception as e:
                st.error(f"Error: {e}")

# --- Display Result ---
if st.session_state['audio_bytes']:
    st.markdown("---")
    st.success("Success! အသံဖိုင် ရပါပြီ။")
    st.audio(st.session_state['audio_bytes'], format="audio/mp3")
    st.download_button(
        label="Download MP3",
        data=st.session_state['audio_bytes'],
        file_name="tts_audio.mp3",
        mime="audio/mp3",
        key="download_btn"
    )
