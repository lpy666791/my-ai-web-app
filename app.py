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
    # 这里是模拟数据，未来可以换成真实的 API 调用
    return f"{location} 在 {date} 的天气是：多云，7~13°C"

# 函数映射表，让程序知道 AI 说的名字对应哪个真函数
TOOL_CALL_MAP = {
    "get_date": get_date_mock,
    "get_weather": get_weather_mock
}

# 给 AI 看的工具说明书
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
# 第二部分：系统配置与本地记忆自动存档
# ==========================================
st.set_page_config(page_title="我的 AI 聚合助手", page_icon="🚀", layout="wide")

st.title("🚀 我的 AI 聚合助手")

# --- 升级后的多会话存储 ---
# 换一个新文件名，防止跟以前的旧格式冲突报错
DB_FILE = "chat_sessions.json" 

def save_data():
    with open(DB_FILE, "w", encoding="utf-8") as f:
        # 现在存的是整个 sessions 字典
        json.dump(st.session_state.sessions, f, ensure_ascii=False, indent=2)

# 1. 初始化对话字典
if "sessions" not in st.session_state:
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            st.session_state.sessions = json.load(f)
    else:
        st.session_state.sessions = {"默认对话 1": []}

# 2. 记录当前处于哪个对话窗口
if "current_session" not in st.session_state:
    st.session_state.current_session = list(st.session_state.sessions.keys())[0]

# ==========================================
# 第三部分：侧边栏 UI (门禁、切模型、导入导出)
# ==========================================
with st.sidebar:
    st.header("⚙️ 配置中心")
    
    # 1. 访问码门禁
    user_access_code = st.text_input("🔑 输入访问码激活内置 Key", type="password")
    st.divider()
    
    # 2. 模型选择与防串戏机制
    old_model = st.session_state.get("current_model", "DeepSeek V4 Pro")
    model_choice = st.selectbox("选择当前大脑：", ["DeepSeek V4 Pro", "Gemini 2.5 Flash"])
    
    # 如果切换了模型，自动清空记忆防串戏
    if old_model != model_choice:
        st.session_state.messages = []
        st.session_state.current_model = model_choice
        save_data()
        st.rerun()
    st.session_state.current_model = model_choice

    # 3. 密钥获取逻辑
    if user_access_code == st.secrets.get("ACCESS_CODE", "") and user_access_code != "":
        st.success("✅ 访问码正确，内置密钥已激活")
        ds_key = st.secrets.get("DEEPSEEK_API_KEY", "")
        gm_key = st.secrets.get("GEMINI_API_KEY", "")
        ds_base = st.secrets.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    else:
        if user_access_code != "":
            st.error("❌ 访问码错误，请自备 Key")
        ds_key = st.text_input("填入 DeepSeek 密钥 (sk-...)", type="password")
        gm_key = st.text_input("填入 Gemini 密钥", type="password")
        ds_base = "https://api.deepseek.com/v1"

    st.divider()
    
    # 4. 记忆导入与清空
    st.subheader("📂 记忆管理")
    # --- 新增：记忆容量监控表盘 ---
    msg_count = len(st.session_state.messages)
    st.metric(label="🧠 当前记忆负载", value=f"{msg_count} 条交互")
    
    if msg_count > 30:
        st.warning("⚠️ 记忆包有点沉了！为节省 Token 并保持 AI 反应速度，建议点击下方按钮清空不必要的对话。")

    st.divider()
    st.subheader("💬 会话频道管理")
    
    # 1. 新建对话按钮
    if st.button("➕ 新建独立对话"):
        # 自动生成新名字，比如 "对话 2"
        new_session_name = f"对话 {len(st.session_state.sessions) + 1}"
        st.session_state.sessions[new_session_name] = []
        st.session_state.current_session = new_session_name
        save_data()
        st.rerun()

    # 2. 切换频道菜单
    session_list = list(st.session_state.sessions.keys())
    selected_session = st.radio(
        "选择频道：", 
        session_list, 
        index=session_list.index(st.session_state.current_session)
    )
    
    # 如果用户点选了别的频道，立即切换并刷新
    if selected_session != st.session_state.current_session:
        st.session_state.current_session = selected_session
        st.rerun()
        
    # 3. 删除当前频道
    if st.button("🗑️ 删除当前对话"):
        if len(st.session_state.sessions) > 1:
            del st.session_state.sessions[st.session_state.current_session]
            # 删除后自动跳到第一个频道
            st.session_state.current_session = list(st.session_state.sessions.keys())[0]
        else:
            # 如果只剩最后一个了，就只清空内容，不删频道
            st.session_state.sessions[st.session_state.current_session] = []
        save_data()
        st.rerun()
   

    # --- 新增：角色设定区（放在侧边栏最底部） ---
    st.divider()
    st.subheader("🎭 角色设定 (System)")
    system_prompt = st.text_area(
        "告诉 AI 它是谁：", 
        value="你是一个精通全栈开发、熟练使用 Unity 引擎的资深架构师，你的回答要求严谨、专业且直接。",
        height=100
    )

# ==========================================
# 第四部分：主界面对话展示
# ==========================================
# 渲染历史记录（跳过隐藏的工具调用记录）
for msg in st.session_state.messages:
    if msg["role"] == "tool": 
        continue # 不单独显示工具返回的枯燥数据
    
    with st.chat_message(msg["role"]):
        # 如果包含思维链，用折叠面板显示
        if msg.get("reasoning_content"):
            with st.expander("🤔 查看思考过程"):
                st.markdown(msg["reasoning_content"])
        # 显示正文
        if msg.get("content"):
            st.markdown(msg["content"])
        # 如果调用了工具，显示一个小提示
        if msg.get("tool_calls"):
            for t in msg["tool_calls"]:
                st.info(f"🔧 AI 调用了系统工具：{t['function']['name']}")

# ==========================================
# 第五部分：核心对话与工具调度引擎
# ==========================================
prompt = st.chat_input("向选中的 AI 提问...")

if prompt:
    # 1. 存入用户消息
    st.session_state.messages.append({"role": "user", "content": prompt})
    save_data()
    
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. 呼叫 AI
    with st.chat_message("assistant"):
        # ------------ DeepSeek 引擎 (带工具调用和思维链) ------------
        if model_choice == "DeepSeek V4 Pro":
            if not ds_key:
                st.warning("⚠️ 请先在侧边栏输入 DeepSeek 密钥或访问码！")
                st.stop()
                
            client = OpenAI(api_key=ds_key, base_url=ds_base)
            
            # 使用状态面板展示处理过程
            with st.status("🧠 DeepSeek 正在思考并调度工具...", expanded=True) as status:
                final_answer = ""
                
                # 开始自动循环（处理多次工具调用）
                while True:
                    # --- 新增：动态拼装最终发送给 API 的消息数组 ---
                    api_messages = []
                    
                    # 1. 永远把 System 设定放在剧本的绝对第一行
                    if system_prompt:
                        api_messages.append({"role": "system", "content": system_prompt})
                        
                    # 2. 滑动窗口：只取最近的 20 条，防止撑爆
                    recent_history = st.session_state.messages[-20:]
                    api_messages.extend(recent_history)
                    
                    # 按照官方要求发送请求 (注意这里 messages 换成了 api_messages)
                    response = client.chat.completions.create(
                        model="deepseek-chat", 
                        messages=api_messages,  # 👈 核心修改：用拼装好的剧本
                        tools=my_tools,
                    )
                    # --- 新增：提取并展示缓存命中率（省钱雷达） ---
                    if hasattr(response, 'usage') and response.usage:
                        # 安全地获取这两个字段（如果库版本较旧，可能需要用 getattr）
                        hit_tokens = getattr(response.usage, 'prompt_cache_hit_tokens', 0)
                        miss_tokens = getattr(response.usage, 'prompt_cache_miss_tokens', 0)
                        
                        if hit_tokens > 0:
                            total = hit_tokens + miss_tokens
                            hit_rate = (hit_tokens / total) * 100 if total > 0 else 0
                            # 在网页右下角弹出一个不打扰的小提示
                            st.toast(f"⚡ 硬盘缓存命中: {hit_tokens} tokens (命中率 {hit_rate:.1f}%)", icon="🚀")
                    # --------------------------------------------

                    # ... 接下来的提取 tool_calls_data 和保存 msg_dict 的代码保持不变 ...
                    
                    # 提取并格式化工具调用信息，以确保 JSON 可以保存
                    tool_calls_data = None
                    if choice.tool_calls:
                        tool_calls_data = []
                        for t in choice.tool_calls:
                            tool_calls_data.append({
                                "id": t.id, 
                                "type": "function", 
                                "function": {"name": t.function.name, "arguments": t.function.arguments}
                            })

                    # 把 AI 的回复（包含可能存在的推理和工具调用）无损保存，避开 400 报错
                    msg_dict = {
                        "role": "assistant",
                        "content": choice.content,
                        "reasoning_content": getattr(choice, 'reasoning_content', None),
                        "tool_calls": tool_calls_data
                    }
                    st.session_state.messages.append(msg_dict)
                    save_data()
                    
                    # 在界面上展示实时推理过程
                    if msg_dict["reasoning_content"]:
                        st.write("💭 思考中：\n" + msg_dict["reasoning_content"])
                    
                    # 如果 AI 没有调用工具，说明拿到最终答案，跳出循环！
                    if not choice.tool_calls:
                        final_answer = choice.content
                        break
                        
                    # 如果 AI 决定调用工具，就在本地执行函数
                    for tool in choice.tool_calls:
                        tool_name = tool.function.name
                        tool_args = json.loads(tool.function.arguments)
                        
                        st.write(f"🔧 执行工具：`{tool_name}`，参数：`{tool_args}`")
                        
                        # 真正执行 Python 函数
                        tool_result = TOOL_CALL_MAP[tool_name](**tool_args)
                        
                        # 将工具执行结果喂给 AI
                        st.session_state.messages.append({
                            "role": "tool",
                            "tool_call_id": tool.id,
                            "content": str(tool_result),
                        })
                        save_data()
                
                status.update(label="处理完毕！", state="complete", expanded=False)
            
            # 显示最终答案
            st.markdown(final_answer)

        # ------------ Gemini 引擎 ------------
        else:
            if not gm_key:
                st.warning("⚠️ 请先在侧边栏输入 Gemini 密钥或访问码！")
                st.stop()
                
            genai.configure(api_key=gm_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            # 兼容性转换：Gemini 不需要复杂的 tool 角色，只需要纯文本记录
            gemini_history = []
            for m in st.session_state.messages[:-1]:
                if m["role"] in ["user", "assistant"] and m.get("content"):
                    gemini_history.append({
                        "role": "user" if m["role"] == "user" else "model",
                        "parts": [m["content"]]
                    })
                    
            chat = model.start_chat(history=gemini_history)
            with st.spinner("Gemini 2.5 正在响应..."):
                response = chat.send_message(prompt)
                answer = response.text
            
            st.markdown(answer)
            
            # 保存 Gemini 的回复
            st.session_state.messages.append({"role": "assistant", "content": answer})
            save_data()