import streamlit as st
import edge_tts
import asyncio
import tempfile
import os

# Web App ခေါင်းစဉ်
st.set_page_config(page_title="Myanmar TTS", page_icon="🇲🇲", layout="centered")
st.title("🇲🇲 Myanmar Text-to-Speech")

# --- Session State (မှတ်ဉာဏ်) ---
if 'audio_data' not in st.session_state:
    st.session_state['audio_data'] = None

# --- Settings (Main Column တွင်ထားမည်) ---
# ကြည့်ကောင်းအောင် Expander သို့မဟုတ် Columns မသုံးဘဲ 
# ရိုးရိုးရှင်းရှင်း အပေါ်ကနေ အောက်စီပေးထားပါတယ်

st.subheader("Settings")

# ၁. အသံရွေးချယ်ရန်
voice_options = {
    "Male (Thiha)": "my-MM-ThihaNeural",
    "Female (Nilar)": "my-MM-NilarNeural" # Corrected Voice Name
}
selected_voice_label = st.selectbox("အသံ ရွေးချယ်ပါ (Select Voice)", list(voice_options.keys()))
selected_voice = voice_options[selected_voice_label]

# ၂. အမြန်နှုန်းချိန်ရန်
speed = st.slider("အမြန်နှုန်း (Speaking Speed)", 0.5, 2.0, 1.0, 0.1)

# Speed 计算
def get_rate_string(speed_val):
    if speed_val == 1.0:
        return "+0%"
    percentage = int((speed_val - 1) * 100)
    if percentage >= 0:
        return f"+{percentage}%"
    else:
        return f"{percentage}%"

rate_str = get_rate_string(speed)

st.markdown("---") # မျဉ်းတစ်ကြောင်းခြားမယ်

# --- Input Section ---
text_input = st.text_area("စာရိုက်ထည့်ပါ (Enter Text):", height=150, placeholder="မင်္ဂလာပါ...")

async def generate_tts(text, voice, rate):
    if rate == "+0%":
        communicate = edge_tts.Communicate(text, voice)
    else:
        communicate = edge_tts.Communicate(text, voice, rate=rate)
        
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
        await communicate.save(tmp_file.name)
        return tmp_file.name

# Button
if st.button("Generate Audio (အသံပြောင်းမည်)", type="primary"):
    if text_input.strip() == "":
        st.warning("စာရိုက်ထည့်ပေးပါ (Please enter text).")
    else:
        with st.spinner("လုပ်ဆောင်နေပါတယ်..."):
            try:
                temp_path = asyncio.run(generate_tts(text_input, selected_voice, rate_str))
                
                with open(temp_path, "rb") as f:
                    audio_bytes = f.read()
                
                st.session_state['audio_data'] = audio_bytes
                
                # Temp file cleanup
                os.remove(temp_path)
                
            except Exception as e:
                st.error(f"Error ဖြစ်သွားပါတယ်: {e}")

# --- Result Section ---
if st.session_state['audio_data'] is not None:
    st.success("အောင်မြင်ပါတယ်!")
    st.audio(st.session_state['audio_data'], format="audio/mp3")
    
    st.download_button(
        label="Download MP3",
        data=st.session_state['audio_data'],
        file_name="myanmar_tts.mp3",
        mime="audio/mp3"
    )