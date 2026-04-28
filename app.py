import streamlit as st
from openai import OpenAI
import google.generativeai as genai

# 1. 网页配置
st.set_page_config(page_title="AI 聚合实验室", page_icon="🚀", layout="wide")
st.title("🚀 我的 AI 聚合助手")

# --- 侧边栏：门禁与配置 ---
with st.sidebar:
    st.header("⚙️ 配置中心")
    
    # 1. 门禁系统：询问访问码
    user_access_code = st.text_input("🔑 输入访问码以激活内置 Key", type="password")
    
    st.divider()
    model_choice = st.selectbox("选择当前大脑：", ["DeepSeek V4 Pro", "Gemini 1.5 Flash"])
    
    # 2. 逻辑判断：
    # 如果用户输入的访问码对上了，就偷偷从保险柜拿 Key
    # 如果没对上，就依然让用户自己填他自己的 Key
    if user_access_code == st.secrets.get("ACCESS_CODE"):
        st.success("✅ 访问码正确，已激活内置密钥")
        if model_choice == "DeepSeek V4 Pro":
            api_key = st.secrets.get("DEEPSEEK_API_KEY")
        else:
            api_key = st.secrets.get("GEMINI_API_KEY")
    else:
        # 没暗号？那就得自备 Key
        if user_access_code != "":
            st.error("❌ 访问码错误")
        api_key = st.text_input(f"填入个人 {model_choice} 密钥", type="password")

    # --- 这里就是新增的“永久保存”功能区 ---
    st.divider()
    st.subheader("💾 对话管理")
    if "messages" in st.session_state and st.session_state.messages:
        # 转换对话格式为 Markdown
        chat_text = "# AI 聚合助手对话记录\n\n"
        for m in st.session_state.messages:
            role = "用户" if m["role"] == "user" else "AI"
            chat_text += f"### {role}:\n{m['content']}\n\n---\n\n"
        
        st.download_button(label="📥 导出对话记录", data=chat_text, file_name="chat_history.md")
        if st.button("🗑️ 清空当前对话"):
            st.session_state.messages = []
            st.rerun()

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