import streamlit as st
import edge_tts
import asyncio
import tempfile
import os

# 1. Page Config
st.set_page_config(page_title="Simple Edge TTS", page_icon="🎵", layout="centered")

st.title("🎵 Simple Edge TTS")
st.caption("No API Keys. Free & Unlimited. (Myanmar + English)")

# --- Voice Settings ---
# ဘာသာစကား ရွေးချယ်ခြင်း
language = st.radio("ဘာသာစကား (Language):", ["မြန်မာ (Myanmar)", "အင်္ဂလိပ် (English)"], horizontal=True)

# အသံရွေးချယ်ခြင်း
if language == "မြန်မာ (Myanmar)":
    # မြန်မာအသံများ
    voice_options = {
        "Thiha (Male) - သီဟ": "my-MM-ThihaNeural",
        "Nilar (Female) - နီလာ": "my-MM-NilarNeural"
    }
else:
    # အင်္ဂလိပ်အသံများ
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
# 0.5 (နှေး) မှ 2.0 (မြန်) အထိ
speed = st.slider("အသံအမြန်နှုန်း (Speed):", min_value=0.5, max_value=2.0, value=1.0, step=0.1)

# --- Text Input ---
text_input = st.text_area("စာရိုက်ထည့်ပါ (Enter Text):", height=200, placeholder="ဒီမှာ စာရိုက်ပါ...")

# --- Generation Logic ---

async def generate_audio(text, voice, speed_val):
    # Speed ကို Edge TTS နားလည်တဲ့ ပုံစံပြောင်းခြင်း (ဥပမာ: +50%, -10%)
    percentage = int((speed_val - 1) * 100)
    if percentage >= 0:
        rate_str = f"+{percentage}%"
    else:
        rate_str = f"{percentage}%"
    
    communicate = edge_tts.Communicate(text, voice, rate=rate_str)
    
    # Temp file သုံးပြီး သိမ်းခြင်း
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
        tmp_path = tmp_file.name
        
    await communicate.save(tmp_path)
    return tmp_path

if st.button("Generate Audio 🔊", type="primary"):
    if not text_input.strip():
        st.warning("ကျေးဇူးပြု၍ စာရိုက်ထည့်ပါ (Please enter text).")
    else:
        with st.spinner("အသံဖိုင် ထုတ်လုပ်နေသည် (Generating)..."):
            try:
                # Run Async Function
                audio_path = asyncio.run(generate_audio(text_input, selected_voice_id, speed))
                
                # Read file for Streamlit
                with open(audio_path, "rb") as f:
                    audio_bytes = f.read()
                
                # Display Audio Player
                st.audio(audio_bytes, format="audio/mp3")
                
                # Download Button
                st.download_button(
                    label="Download MP3 📥",
                    data=audio_bytes,
                    file_name="tts_audio.mp3",
                    mime="audio/mp3"
                )
                
                # Clean up temp file
                os.remove(audio_path)
                
            except Exception as e:
                st.error(f"Error: {e}")

# Footer
st.markdown("---")
st.caption("Powered by Microsoft Edge TTS")
