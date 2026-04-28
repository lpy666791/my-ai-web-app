import streamlit as st
from openai import OpenAI

# 1. 网页配置：标题和图标
st.set_page_config(page_title="我的专属 AI 助手", page_icon="🤖")
st.title("🤖 DeepSeek V4 Pro 网页版")

# 2. 侧边栏：填写 API Key
with st.sidebar:
    st.header("配置中心")
    api_key = st.text_input("填入 DeepSeek API Key", type="password")
    st.info("Key 不会保存在服务器上，仅供当前会话使用。")

# 3. 初始化会话记忆 (st.session_state)
if "messages" not in st.session_state:
    st.session_state.messages = []

# 4. 在界面上展示历史对话
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 5. 用户输入
if prompt := st.chat_input("问我任何问题..."):
    # 先把用户说的话展示出来
    st.chat_message("user").markdown(prompt)
    # 存入历史记忆
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 如果没填 Key，提醒用户
    if not api_key:
        st.error("请先在左侧输入 API Key！")
    else:
        # 6. 调用 AI (DeepSeek V4 Pro)
        try:
            client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
            
            with st.chat_message("assistant"):
                # 展示一个“思考中”的状态
                with st.status("DeepSeek 正在进行深度思考...", expanded=True):
                    response = client.chat.completions.create(
                        model="deepseek-v4-pro",
                        messages=st.session_state.messages,
                        stream=False,
                        reasoning_effort="high",
                        extra_body={"thinking": {"type": "enabled"}}
                    )
                    full_response = response.choices[0].message.content
                
                # 正式打印回答
                st.markdown(full_response)
                
            # 将 AI 的回答也存入历史记忆
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            st.error(f"连接出错：{e}")