import streamlit as st
import requests

st.set_page_config(page_title="Debug Mode", page_icon="🔧")

st.title("🔧 Error ရှာဖွေရေး (Debug Mode)")
st.info("မိတ်ဆွေ၏ Google Cloud Setting များ မှန်ကန်ပါသည်။ Code တွင်းရှိ Model Name ကို စစ်ဆေးနေပါသည်။")

# --- Check Key ---
if "gemini_api_key" in st.secrets:
    api_key = st.secrets["gemini_api_key"]
    st.success(f"✅ API Key တွေ့ရှိပါသည် (Key အစ: {api_key[:5]}...)")
else:
    st.error("❌ API Key မတွေ့ပါ။ secrets.toml ကို စစ်ဆေးပါ။")
    st.stop()

# --- Inputs ---
text = st.text_input("စမ်းသပ်ရန် စာရိုက်ပါ (English/Myanmar):", "Mingalarpar")

# Model နာမည်အမျိုးမျိုးကို စမ်းကြည့်ရန် Dropdown
# (တစ်ခုမရရင် နောက်တစ်ခု ပြောင်းရွေးပြီး Test နှိပ်ကြည့်ပါ)
model_options = [
    "gemini-2.0-flash",       # Stable
    "gemini-2.0-flash-exp",   # Experimental (AI Studio)
    "gemini-1.5-flash"        # Older version
]
model = st.selectbox("Model ရွေးပါ:", model_options)
voice = st.selectbox("Voice ရွေးပါ:", ["Puck", "Charon", "Zephyr", "Kore"])

if st.button("Test Connection"):
    # OpenAI-Compatible Endpoint for Audio
    url = "https://generativelanguage.googleapis.com/v1beta/openai/audio/speech"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": model,
        "input": text,
        "voice": voice
    }
    
    with st.spinner(f"Testing {model}..."):
        try:
            response = requests.post(url, headers=headers, json=data)
            
            # --- Result Analysis ---
            if response.status_code == 200:
                st.success(f"🎉 အောင်မြင်ပါတယ်! ({model} is working)")
                st.audio(response.content, format="audio/mp3")
            else:
                st.error(f"❌ Error: {response.status_code}")
                # Google က ပြန်ပို့လိုက်တဲ့ Error စာသားအပြည့်အစုံ
                st.json(response.json()) 
                
        except Exception as e:
            st.error(f"System Error: {str(e)}")
