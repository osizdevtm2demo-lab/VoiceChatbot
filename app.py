import streamlit as st
import ollama as ol
from voice import record_voice  # your custom voice recording module
from gtts import gTTS
import tempfile
import base64
import os
import threading

st.set_page_config(page_title="🎙️ Voice Bot", layout="wide")
st.title("🎙️ Osiz Technologies Speech Bot")
st.sidebar.title("`Speak with LLMs` \n`in any language`")


# 🌍 Language Selector
def language_selector():
    lang_options = [
        "Arabic", "German", "English", "Spanish", "French",
        "Italian", "Japanese", "Dutch", "Polish",
        "Portuguese", "Russian", "Chinese (Mandarin)", "Tamil"
    ]
    return st.selectbox("Speech Language", lang_options, index=2)  # Default English


# 🔤 Language → Code
def get_lang_code(lang):
    mapping = {
        "English": "en",
        "Arabic": "ar",
        "German": "de",
        "Spanish": "es",
        "French": "fr",
        "Italian": "it",
        "Japanese": "ja",
        "Dutch": "nl",
        "Polish": "pl",
        "Portuguese": "pt",
        "Russian": "ru",
        "Chinese (Mandarin)": "zh-cn",
        "Tamil": "ta"
    }
    return mapping.get(lang, "en")


# 🦙 LLM Selector
def llm_selector():
    try:
        response = ol.list()
        models = response.get("models", [])
        if not models:
            st.sidebar.error("No Ollama models found. Run: ollama pull llama3.2")
            return None

        ollama_models = []
        for m in models:
            if isinstance(m, dict):
                model_name = m.get("name") or m.get("model")
                if model_name:
                    ollama_models.append(model_name)
            else:
                try:
                    data = m.model_dump() if hasattr(m, 'model_dump') else m
                    model_name = data.get("name") or data.get("model")
                    if model_name:
                        ollama_models.append(model_name)
                except:
                    continue

        if not ollama_models:
            st.sidebar.error("No valid models found")
            return None

        return st.selectbox("LLM", ollama_models)
    
    except Exception as e:
        st.sidebar.error(f"Error connecting to Ollama: {str(e)}")
        return None


# 🖨️ Print text (RTL support)
def print_txt(text):
    if any("\u0600" <= c <= "\u06FF" for c in text):  # Arabic check
        text = f"<p style='direction: rtl; text-align: right; font-size: 16px;'>{text}</p>"
    st.markdown(text, unsafe_allow_html=True)


# 💬 Chat UI
def print_chat_message(message):
    text = message["content"]
    if message["role"] == "user":
        with st.chat_message("user", avatar="🎙️"):
            print_txt(text)
    else:
        with st.chat_message("assistant", avatar="🦙"):
            print_txt(text)


# 🔊 Auto-play TTS
def speak_text_auto(text, lang="en"):
    try:
        # Clean up old temp files
        temp_files = [f for f in os.listdir(tempfile.gettempdir()) if f.startswith('tmp') and f.endswith('.mp3')]
        for temp_file in temp_files[-10:]:
            try:
                os.remove(os.path.join(tempfile.gettempdir(), temp_file))
            except:
                pass
        
        tts = gTTS(text=text, lang=lang)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            tts.save(fp.name)
            with open(fp.name, "rb") as audio_file:
                audio_bytes = audio_file.read()
            
            b64 = base64.b64encode(audio_bytes).decode()
            
            audio_html = f"""
                <audio autoplay style="display: none;">
                    <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
                </audio>
                <script>
                    var audio = document.querySelector('audio');
                    audio.play().catch(function(error) {{
                        console.log("Auto-play failed:", error);
                    }});
                </script>
            """
            st.markdown(audio_html, unsafe_allow_html=True)
            
            # Cleanup temp file after 2 seconds
            def cleanup():
                try:
                    os.unlink(fp.name)
                except:
                    pass
            threading.Timer(2.0, cleanup).start()
            
    except Exception as e:
        st.error(f"TTS Error: {str(e)}")


# 🚀 Main App
def main():
    if "last_spoken" not in st.session_state:
        st.session_state.last_spoken = ""
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = {}
    
    # Sidebar
    with st.sidebar:
        selected_lang = language_selector()
        model = llm_selector()
        st.markdown("---")
        st.subheader("🎤 Voice Input")
        question = record_voice(language=selected_lang)
    
    if not model:
        st.warning("⚠️ Please select an LLM model from the sidebar.")
        return
    
    # Initialize chat history for model
    if model not in st.session_state.chat_history:
        st.session_state.chat_history[model] = []
    
    chat_history = st.session_state.chat_history[model]
    
    # Display chat history
    for message in chat_history:
        print_chat_message(message)
    
    if not chat_history:
        st.info("👈 Select a model and language, then click the microphone button to start speaking!")
    
    # Process voice input
    if question and question.strip():
        if not chat_history or (chat_history[-1].get("content") != question):
            user_message = {"role": "user", "content": question}
            print_chat_message(user_message)
            chat_history.append(user_message)
            
            with st.spinner("🦙 Osiz AI Thinking..."):
                try:
                    response = ol.chat(model=model, messages=chat_history)
                    answer = response["message"]["content"] if isinstance(response, dict) else response.message.content
                    
                    ai_message = {"role": "assistant", "content": answer}
                    print_chat_message(ai_message)
                    chat_history.append(ai_message)
                    
                    # 🔊 Convert AI response to speech
                    lang_code = get_lang_code(selected_lang)
                    speak_text_auto(answer, lang_code)
                    st.session_state.last_spoken = answer
                    
                    # Limit history
                    if len(chat_history) > 20:
                        chat_history = chat_history[-20:]
                        st.session_state.chat_history[model] = chat_history
                    
                except Exception as e:
                    st.error(f"Error getting response from LLM: {str(e)}")
                    error_message = {"role": "assistant", "content": f"Sorry, I encountered an error: {str(e)}"}
                    print_chat_message(error_message)
                    chat_history.append(error_message)
        
        st.rerun()


if __name__ == "__main__":
    main()
