import streamlit as st
import edge_tts
import asyncio
import os

# 1. Page Config
st.set_page_config(page_title="Secure Edge TTS", page_icon="🔒", layout="centered")

# ==========================================
# Helper Class: Smart SRT Maker (Fixed)
# ==========================================
class CustomSubMaker:
    def __init__(self):
        self.events = []

    def feed(self, chunk):
        # WordBoundary data များကို လက်ခံသိမ်းဆည်းခြင်း
        self.events.append(chunk)

    def _format_time(self, total_seconds):
        # Seconds ကို SRT Time format (HH:MM:SS,mmm) သို့ ပြောင်းခြင်း
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        milliseconds = int((total_seconds - int(total_seconds)) * 1000)
        return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"

    def generate_srt(self, audio_len_bytes, original_text):
        # 1. အကယ်၍ Timing Data (Events) ပါလာလျှင် (English အတွက်)
        if self.events:
            srt_output = ""
            # --- ပြင်ဆင်လိုက်သော နေရာ (Space ခြားလိုက်ပါပြီ) ---
            for index, event in enumerate(self.events, 1):
                # EdgeTTS offset is in 100ns units (1e-7 seconds)
                start_seconds = event['offset'] / 10_000_000
                duration_seconds = event['duration'] / 10_000_000
                end_seconds = start_seconds + duration_seconds
                
                start_time = self._format_time(start_seconds)
                end_time = self._format_time(end_seconds)
                text = event['text']
                
                srt_output += f"{index}\n"
                srt_output += f"{start_time} --> {end_time}\n"
                srt_output += f"{text}\n\n"
            return srt_output
        
        # 2. အကယ်၍ Timing Data မပါလာလျှင် (မြန်မာ အတွက်)
        # အသံဖိုင် Size ပေါ်မူတည်ပြီး ကြာချိန်ကို ခန့်မှန်းတွက်ချက်သည်
        else:
            # EdgeTTS mp3 usually approx 16000 bytes per second (128kbps estimate)
            # ဒါက အတိအကျမဟုတ်ပေမယ့် SRT ထွက်ဖို့ လုံလောက်ပါတယ်
            if audio_len_bytes == 0:
                estimated_seconds = 5 # Default duration if audio is empty
            else:
                estimated_seconds = audio_len_bytes / 16000 
            
            start_time = self._format_time(0)
            end_time = self._format_time(estimated_seconds)
            
            # စာသားအကုန်လုံးကို တစ်ကွက်တည်း ပြမည်
            return f"1\n{start_time} --> {end_time}\n{original_text}\n"

# ==========================================
# Authentication (Login System)
# ==========================================

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
            st.success("Login Success!")
        else:
            st.error("Username သို့မဟုတ် Password မှားနေပါသည်!")
    except Exception as e:
        st.error(f"Config Error: {e}")

if not st.session_state['logged_in']:
    st.title("🔐 Login Required")
    st.text_input("Username", key="input_username")
    st.text_input("Password", type="password", key="input_password")
    st.button("Login", on_click=check_login)
    st.stop()

# ==========================================
# Main App
# ==========================================

st.title("🎵 Simple Edge TTS")
st.caption("SRT Fixed for Myanmar & English")

if st.button("Log out 🔒"):
    st.session_state['logged_in'] = False
    st.rerun()

# --- Session State ---
if 'audio_bytes' not in st.session_state:
    st.session_state['audio_bytes'] = None
if 'srt_content' not in st.session_state:
    st.session_state['srt_content'] = None

# --- Settings ---
language = st.radio("ဘာသာစကား:", ["မြန်မာ (Myanmar)", "အင်္ဂလိပ် (English)"], horizontal=True)

if language == "မြန်မာ (Myanmar)":
    voice_options = {
        "Thiha (Male)": "my-MM-ThihaNeural",
        "Nilar (Female)": "my-MM-NilarNeural"
    }
else:
    voice_options = {
        "Aria (Female)": "en-US-AriaNeural",
        "Christopher (Male)": "en-US-ChristopherNeural",
        "Guy (Male)": "en-US-GuyNeural",
        "Jenny (Female)": "en-US-JennyNeural"
    }

selected_voice_name = st.selectbox("Select Voice:", list(voice_options.keys()))
selected_voice_id = voice_options[selected_voice_name]
speed = st.slider("Speed:", 0.5, 2.0, 1.0, 0.1)
text_input = st.text_area("Enter Text:", height=200, placeholder="စာရိုက်ပါ...")

# --- Generator ---
async def generate_audio(text, voice, speed_val):
    percentage = int((speed_val - 1) * 100)
    rate_str = f"+{percentage}%" if percentage >= 0 else f"{percentage}%"
    
    communicate = edge_tts.Communicate(text, voice, rate=rate_str)
    submaker = CustomSubMaker() # Custom Class
    
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
        elif chunk["type"] == "WordBoundary":
            submaker.feed(chunk)
            
    # SRT ထုတ်တဲ့အခါ audio size နဲ့ မူရင်းစာသားကို ပို့ပေးရမယ်
    final_srt = submaker.generate_srt(len(audio_data), text)
    return audio_data, final_srt

if st.button("Generate Audio 🔊", type="primary"):
    if not text_input.strip():
        st.warning("စာရိုက်ထည့်ပါ...")
    else:
        with st.spinner("Generating..."):
            try:
                audio_data, srt_content = asyncio.run(generate_audio(text_input, selected_voice_id, speed))
                st.session_state['audio_bytes'] = audio_data
                st.session_state['srt_content'] = srt_content
            except Exception as e:
                st.error(f"Error: {e}")

# --- Result ---
if st.session_state['audio_bytes']:
    st.markdown("---")
    st.success("Success!")
    st.audio(st.session_state['audio_bytes'], format="audio/mp3")
    
    c1, c2 = st.columns(2)
    with c1:
        st.download_button("Download MP3 📥", st.session_state['audio_bytes'], "audio.mp3", "audio/mp3")
    with c2:
        if st.session_state['srt_content']:
            st.download_button("Download SRT 📝", st.session_state['srt_content'], "subtitle.srt", "text/plain")
        else:
            st.warning("No SRT available")
