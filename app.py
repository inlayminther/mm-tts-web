import streamlit as st
import edge_tts
import asyncio
import os

# 1. Page Config
st.set_page_config(page_title="Secure Edge TTS", page_icon="🔒", layout="centered")

# ==========================================
# Authentication (Login System)
# ==========================================

# Login အခြေအနေကို စစ်ဆေးခြင်း
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

def check_login():
    user = st.session_state.get('input_username', '')
    pwd = st.session_state.get('input_password', '')
    
    # secrets.toml ထဲက credentials နဲ့ တိုက်စစ်ခြင်း
    try:
        if "credentials" in st.secrets and \
           user == st.secrets["credentials"]["username"] and \
           pwd == st.secrets["credentials"]["password"]:
            st.session_state['logged_in'] = True
            st.success("Login Success!")
        else:
            st.error("Username သို့မဟုတ် Password မှားနေပါသည်!")
    except Exception as e:
        st.error(f"Config Error: {e}")

# အကယ်၍ Login မဝင်ရသေးရင် ဒီမှာပဲ ရပ်မယ်
if not st.session_state['logged_in']:
    st.title("🔐 Login Required")
    st.caption("ကျေးဇူးပြု၍ လော့အင်ဝင်ပါ")
    
    st.text_input("Username", key="input_username")
    st.text_input("Password", type="password", key="input_password")
    st.button("Login", on_click=check_login)
    st.stop() # ဒီအောက်က ကုဒ်တွေကို ဆက်မလုပ်ခိုင်းဘူး

# ==========================================
# Main App (Login ဝင်ပြီးမှ မြင်ရမည့်အပိုင်း)
# ==========================================

st.title("🎵 Simple Edge TTS")
st.caption("Free & Unlimited (Myanmar + English)")

# Logout Button
if st.button("Log out 🔒"):
    st.session_state['logged_in'] = False
    st.rerun() # Refresh ပြန်လုပ်ပြီး Login စာမျက်နှာပြန်ပို့

# --- Session State for Audio & SRT ---
if 'audio_bytes' not in st.session_state:
    st.session_state['audio_bytes'] = None
# (NEW) SRT အတွက် Session State ထပ်ဖြည့်သည်
if 'srt_content' not in st.session_state:
    st.session_state['srt_content'] = None

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
    
    # (NEW) SubMaker ကို ခေါ်သုံးသည်
    submaker = edge_tts.SubMaker()
    
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
        # (NEW) WordBoundary (စကားလုံးဖြတ်ရာ) များကို ဖမ်းယူပြီး Subtitle တည်ဆောက်သည်
        elif chunk["type"] == "WordBoundary":
            submaker.feed(chunk)
            
    # (NEW) Audio နှင့် SRT ကို တွဲပြီး return ပြန်သည်
    return audio_data, submaker.generate_subs()

# Generate Button
if st.button("Generate Audio 🔊", type="primary"):
    if not text_input.strip():
        st.warning("စာရိုက်ထည့်ပါ...")
    else:
        with st.spinner("Generating..."):
            try:
                # (NEW) Return ၂ ခု ပြန်လက်ခံသည်
                audio_data, srt_content = asyncio.run(generate_audio(text_input, selected_voice_id, speed))
                st.session_state['audio_bytes'] = audio_data
                st.session_state['srt_content'] = srt_content
            except Exception as e:
                st.error(f"Error: {e}")

# --- Display Result ---
if st.session_state['audio_bytes']:
    st.markdown("---")
    st.success("Success! အသံဖိုင် နှင့် စာတန်းထိုး ရပါပြီ။")
    st.audio(st.session_state['audio_bytes'], format="audio/mp3")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.download_button(
            label="Download MP3 📥",
            data=st.session_state['audio_bytes'],
            file_name="tts_audio.mp3",
            mime="audio/mp3",
            key="download_btn_mp3"
        )
        
    with col2:
        # (NEW) SRT Download Button
        if st.session_state['srt_content']:
            st.download_button(
                label="Download SRT 📝",
                data=st.session_state['srt_content'],
                file_name="tts_subtitle.srt",
                mime="text/plain",
                key="download_btn_srt"
            )
