import streamlit as st
from openai import OpenAI
import google.generativeai as genai

# 1. 网页配置
st.set_page_config(page_title="AI 聚合实验室", page_icon="🚀", layout="wide")
st.title("🚀 我的 AI 聚合助手")

# 2. 侧边栏：配置中心
with st.sidebar:
    st.header("⚙️ 配置中心")
    
    # 模型选择开关
    model_choice = st.selectbox(
        "选择当前大脑：",
        ["DeepSeek V4 Pro", "Gemini 1.5 Flash"]
    )
    
    st.divider()
    
    # 根据选择显示对应的 Key 输入框
    if model_choice == "DeepSeek V4 Pro":
        api_key = st.text_input("sk-64966fb1158541b6a85f3fd3f954fc93", type="password")
        st.info("当前模式：逻辑深度推理专家")
    else:
        api_key = st.text_input("AIzaSyDmksXP5lkkJYgKSKw-7VnaOvmRQQa4-Jw", type="password")
        st.info("当前模式：创意、超长上下文专家")

# 3. 初始化记忆
if "messages" not in st.session_state:
    st.session_state.messages = []

# 4. 展示历史对话
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 5. 聊天逻辑
if prompt := st.chat_input("向选中的 AI 提问..."):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    if not api_key:
        st.warning(f"请先在左侧输入 {model_choice} 的 API Key！")
    else:
        try:
            with st.chat_message("assistant"):
                # --- 分支处理：DeepSeek ---
                if model_choice == "DeepSeek V4 Pro":
                    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
                    with st.status("DeepSeek 正在思考逻辑..."):
                        response = client.chat.completions.create(
                            model="deepseek-v4-pro",
                            messages=st.session_state.messages,
                            reasoning_effort="high",
                            extra_body={"thinking": {"type": "enabled"}}
                        )
                        answer = response.choices[0].message.content
                    st.markdown(answer)
                
                # --- 分支处理：Gemini ---
                else:
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    # 转换格式以适配 Gemini
                    history = [{"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]} for m in st.session_state.messages[:-1]]
                    chat = model.start_chat(history=history)
                    
                    with st.spinner("Gemini 正在迸发灵感..."):
                        response = chat.send_message(prompt)
                        answer = response.text
                    st.markdown(answer)

            st.session_state.messages.append({"role": "assistant", "content": answer})
            
        except Exception as e:
            st.error(f"调用出错：{e}")