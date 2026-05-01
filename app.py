import streamlit as st
import google.generativeai as genai
from openai import OpenAI
import json
import os
from datetime import datetime

# ==========================================
# 第一部分：定义 AI 工具箱 (Function Calling)
# ==========================================
def get_date_mock():
    return datetime.now().strftime("%Y-%m-%d")

def get_weather_mock(location, date):
    return f"{location} 在 {date} 的天气是：多云，7~13°C"

TOOL_CALL_MAP = {
    "get_date": get_date_mock,
    "get_weather": get_weather_mock
}

my_tools = [
    {
        "type": "function",
        "function": {
            "name": "get_date",
            "description": "获取当前的系统日期",
            "parameters": { "type": "object", "properties": {} },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取指定地点的天气，需要提供城市和日期。",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": { "type": "string", "description": "城市名称，例如：杭州" },
                    "date": { "type": "string", "description": "日期，格式：YYYY-mm-dd" },
                },
                "required": ["location", "date"]
            },
        }
    },
]

# ==========================================
# 第二部分：系统配置与【多会话】本地存储引擎
# ==========================================
st.set_page_config(page_title="多频道 AI 聚合助手", page_icon="🚀", layout="wide")
st.title("🚀 多频道 AI 聚合助手")

# 升级后的数据库文件名
DB_FILE = "chat_sessions.json"

def save_data():
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(st.session_state.sessions, f, ensure_ascii=False, indent=2)

# 1. 初始化多频道数据结构
if "sessions" not in st.session_state:
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            st.session_state.sessions = json.load(f)
    else:
        st.session_state.sessions = {"默认对话 1": []}

# 2. 追踪当前所在的频道
if "current_session" not in st.session_state:
    st.session_state.current_session = list(st.session_state.sessions.keys())[0]

# ==========================================
# 第三部分：侧边栏 UI (频道管理、门禁、角色设定)
# ==========================================
with st.sidebar:
    st.header("⚙️ 聚合配置中心")
    
    # 门禁系统
    user_access_code = st.text_input("🔑 输入访问码激活内置 Key", type="password")
    
    if user_access_code == st.secrets.get("ACCESS_CODE", "") and user_access_code != "":
        st.success("✅ 内置密钥激活")
        ds_key = st.secrets.get("DEEPSEEK_API_KEY", "")
        gm_key = st.secrets.get("GEMINI_API_KEY", "")
        ds_base = st.secrets.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    else:
        ds_key = st.text_input("DeepSeek 密钥 (sk-...)", type="password")
        gm_key = st.text_input("Gemini 密钥", type="password")
        ds_base = "https://api.deepseek.com"

    st.divider()
    
    # 模型切换
    model_choice = st.selectbox("选择当前大脑：", ["DeepSeek V4 Pro", "Gemini 2.5 Flash"])
    st.session_state.current_model = model_choice

    st.divider()

    # --- 强大的多频道会话管理器 ---
    st.subheader("💬 会话频道管理")
    
    # 当前记忆容量监控
    current_chat = st.session_state.sessions[st.session_state.current_session]
    st.metric(label="🧠 当前频道记忆负载", value=f"{len(current_chat)} 条交互")

    if st.button("➕ 新建独立对话"):
        new_name = f"对话 {len(st.session_state.sessions) + 1}"
        st.session_state.sessions[new_name] = []
        st.session_state.current_session = new_name
        save_data()
        st.rerun()

    session_list = list(st.session_state.sessions.keys())
    selected_session = st.radio(
        "切换频道：", 
        session_list, 
        index=session_list.index(st.session_state.current_session)
    )
    if selected_session != st.session_state.current_session:
        st.session_state.current_session = selected_session
        st.rerun()

    if st.button("🗑️ 删除当前频道"):
        if len(st.session_state.sessions) > 1:
            del st.session_state.sessions[st.session_state.current_session]
            st.session_state.current_session = list(st.session_state.sessions.keys())[0]
        else:
            st.session_state.sessions[st.session_state.current_session] = []
        save_data()
        st.rerun()

    st.divider()
    
    # 动态系统提示词
    st.subheader("🎭 角色设定 (System)")
    system_prompt = st.text_area(
        "告诉 AI 它是谁：", 
        value="你是一个精通全栈开发、熟练使用 Unity 引擎的资深架构师，回答要求严谨、专业。",
        height=100
    )

# ==========================================
# 第四部分：主界面渲染 (针对当前选中的频道)
# ==========================================
current_chat = st.session_state.sessions[st.session_state.current_session]

for msg in current_chat:
    if msg["role"] == "tool": 
        continue # 隐藏枯燥的工具后台数据
        
    with st.chat_message(msg["role"]):
        if msg.get("reasoning_content"):
            with st.expander("🤔 展开思考过程"):
                st.markdown(msg["reasoning_content"])
        if msg.get("content"):
            st.markdown(msg["content"])
        if msg.get("tool_calls"):
            for t in msg["tool_calls"]:
                st.info(f"🔧 系统调用了工具：{t['function']['name']}")

# ==========================================
# 第五部分：核心调度引擎 (完美序列化防报错版)
# ==========================================
prompt = st.chat_input(f"在 {st.session_state.current_session} 中提问...")

if prompt:
    # 存入当前频道
    current_chat.append({"role": "user", "content": prompt})
    save_data()
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # ------------ DeepSeek 引擎 ------------
        if model_choice == "DeepSeek V4 Pro":
            if not ds_key:
                st.warning("⚠️ 请输入 DeepSeek 密钥！")
                st.stop()
                
            client = OpenAI(api_key=ds_key, base_url=ds_base)
            
            with st.status("🧠 DeepSeek 思考与调度中...", expanded=True) as status:
                final_answer = ""
                
                while True:
                    # 拼装带缓存滑动窗口的消息包
                    api_messages = []
                    if system_prompt:
                        api_messages.append({"role": "system", "content": system_prompt})
                    recent_history = current_chat[-20:] # 只发最近20条防撑爆
                    api_messages.extend(recent_history)

                    response = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=api_messages,
                        tools=my_tools,
                    )
                    
                    choice = response.choices[0].message
                    
                    # 💡 安全序列化字典 (彻底解决 JSON 报错)
                    msg_to_save = {
                        "role": "assistant",
                        "content": choice.content if choice.content else ""
                    }
                    if hasattr(choice, 'reasoning_content') and choice.reasoning_content:
                        msg_to_save["reasoning_content"] = choice.reasoning_content
                        st.write("💭 思考：\n" + choice.reasoning_content)
                        
                    if choice.tool_calls:
                        msg_to_save["tool_calls"] = []
                        for t in choice.tool_calls:
                            msg_to_save["tool_calls"].append({
                                "id": t.id,
                                "type": "function",
                                "function": {
                                    "name": t.function.name,
                                    "arguments": t.function.arguments
                                }
                            })

                    # 无损存入当前频道
                    current_chat.append(msg_to_save)
                    save_data()

                    # 处理工具调用循环
                    if not choice.tool_calls:
                        final_answer = choice.content
                        break
                        
                    for tool in choice.tool_calls:
                        tool_name = tool.function.name
                        tool_args = json.loads(tool.function.arguments)
                        st.write(f"🔧 执行工具：`{tool_name}`")
                        
                        tool_result = TOOL_CALL_MAP[tool_name](**tool_args)
                        
                        # 返回结果必须转为纯字符串
                        current_chat.append({
                            "role": "tool",
                            "tool_call_id": tool.id,
                            "content": str(tool_result),
                        })
                        save_data()
                
                status.update(label="处理完毕！", state="complete", expanded=False)
            st.markdown(final_answer)

        # ------------ Gemini 引擎 ------------
        else:
            if not gm_key:
                st.warning("⚠️ 请输入 Gemini 密钥！")
                st.stop()
                
            genai.configure(api_key=gm_key)
            model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=system_prompt)
            
            gemini_history = []
            for m in current_chat[:-1]:
                if m["role"] in ["user", "assistant"] and m.get("content"):
                    gemini_history.append({
                        "role": "user" if m["role"] == "user" else "model",
                        "parts": [m["content"]]
                    })
                    
            chat = model.start_chat(history=gemini_history)
            with st.spinner("Gemini 正在响应..."):
                response = chat.send_message(prompt)
                answer = response.text
            
            st.markdown(answer)
            current_chat.append({"role": "assistant", "content": answer})
            save_data()