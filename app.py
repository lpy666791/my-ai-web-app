import streamlit as st
from openai import OpenAI
import google.generativeai as genai

# 1. 网页配置
st.set_page_config(page_title="AI 聚合实验室", page_icon="🚀", layout="wide")
st.title("🚀 我的 AI 聚合助手")

# 2. 侧边栏：配置中心
with st.sidebar:
    st.header("⚙️ 配置中心")
    # --- 永久保存对话的功能区 ---
    st.divider()
    st.subheader("💾 对话管理")
    
    if st.session_state.messages:
        # 1. 转换对话格式为 Markdown 文本
        chat_text = "# AI 聚合助手对话记录\n\n"
        for m in st.session_state.messages:
            role = "用户" if m["role"] == "user" else "AI"
            chat_text += f"### {role}:\n{m['content']}\n\n---\n\n"
        
        # 2. 导出按钮：点击后会将文件下载到你的电脑里
        st.download_button(
            label="📥 导出对话记录 (Markdown)",
            data=chat_text,
            file_name="ai_chat_history.md",
            mime="text/markdown"
        )
        
        # 3. 清空对话按钮
        if st.button("🗑️ 清空当前对话"):
            st.session_state.messages = []
            st.rerun()
    model_choice = st.selectbox(
        "选择当前大脑：",
        ["DeepSeek V4 Pro", "Gemini 1.5 Flash"]
    )
    
    st.divider()
    
    # --- 关键：在这里安全地获取 API Key ---
    if model_choice == "DeepSeek V4 Pro":
        api_key = st.text_input("sk-cb075231f2964b5bb3fe46c0b35e18e9", type="password", key="ds_key")
        st.info("模式：逻辑深度推理专家")
    else:
        api_key = st.text_input("AIzaSyDmksXP5lkkJYgKSKw-7VnaOvmRQQa4-Jw", type="password", key="gm_key")
        st.info("模式：创意与超长上下文专家")

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
                if model_choice == "DeepSeek V4 Pro":
                    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
                    
                    # 开启流式输出，解决“思考后消失”的问题
                    with st.status("DeepSeek 正在深度思考...", expanded=True) as status:
                        response = client.chat.completions.create(
                            model="deepseek-v4-pro",
                            messages=st.session_state.messages,
                            stream=True,
                            reasoning_effort="high",
                            extra_body={"thinking": {"type": "enabled"}}
                        )
                        
                        placeholder = st.empty()
                        full_response = ""
                        for chunk in response:
                            if chunk.choices[0].delta.content:
                                full_response += chunk.choices[0].delta.content
                                placeholder.markdown(full_response)
                        status.update(label="思考完毕！", state="complete", expanded=False)
                    answer = full_response
                
                else:
                    # Gemini 的调用逻辑（保持不变）
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    history = [{"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]} for m in st.session_state.messages[:-1]]
                    chat = model.start_chat(history=history)
                    with st.spinner("Gemini 正在响应..."):
                        response = chat.send_message(prompt)
                        answer = response.text
                    st.markdown(answer)

            st.session_state.messages.append({"role": "assistant", "content": answer})
            
        except Exception as e:
            st.error(f"调用出错：{e}")