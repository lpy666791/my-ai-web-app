import streamlit as st
import google.generativeai as genai
from openai import OpenAI
from sentence_transformers import SentenceTransformer
import json
import os
from datetime import datetime
import supabase

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


# （上面是你截图里的 my_tools = [...]）

# ==========================================
# 第二部分：记忆外脑 (RAG) 初始化与核心函数
# ==========================================

# 1. 初始化本地向量模型 (第一次运行会自动下载)
# 💡建议加个 Streamlit 缓存装饰器，避免每次刷新网页都重新加载模型，导致卡顿
@st.cache_resource 
def load_embedder():
    return SentenceTransformer('all-MiniLM-L6-v2')

embedder = load_embedder()

# 2. 初始化 Supabase 数据库客户端
# 确保你的 st.secrets 里有这两个配置
db = supabase.create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# 3. 存储设定的函数
def add_lore_to_db(category: str, content: str):
    vector = embedder.encode(content).tolist()
    db.table("novel_lore").insert({
        "category": category,
        "content": content,
        "embedding": vector
    }).execute()

# 4. 检索设定的函数
def retrieve_relevant_lore(user_query: str):
    query_vector = embedder.encode(user_query).tolist()
    response = db.rpc("match_lore", {
        "query_embedding": query_vector,
        "match_threshold": 0.3, 
        "match_count": 1000
    }).execute()
    return "\n".join([item["content"] for item in response.data])



# ==========================================
# 第三部分：Streamlit UI 界面与交互逻辑
# ==========================================
# （下面紧接着写你的 st.title, st.sidebar, 还有聊天框的代码）


# ==========================================

# 第二部分：系统配置与【Supabase 云端】存储引擎
# ==========================================
from supabase import create_client, Client

st.set_page_config(page_title="多频道 AI 聚合助手", page_icon="🚀", layout="wide")
st.title("🚀 云端多频道 AI 聚合助手")

# 1. 连接 Supabase 云端数据库
@st.cache_resource
def init_connection():
    # .strip() 会帮你删掉不小心复制进去的空格或换行
    url = st.secrets["SUPABASE_URL"].strip()
    key = st.secrets["SUPABASE_KEY"].strip()
    return create_client(url, key)

supabase: Client = init_connection()

# 我们给你的专属存档起个唯一的 ID
USER_RECORD_ID = "master_admin_record"

# 2. 云端存盘函数 (替代原来的本地写文件)
def save_data():
    # 使用 upsert：如果存在就更新，如果不存在就插入
    data = {
        "id": USER_RECORD_ID, 
        "chat_data": st.session_state.sessions
    }
    supabase.table("ai_sessions").upsert(data).execute()

# 3. 初始化云端读取记忆 (替代原来的本地读文件)
if "sessions" not in st.session_state:
    try:
        # 尝试从云端拉取你的数据
        response = supabase.table("ai_sessions").select("chat_data").eq("id", USER_RECORD_ID).execute()
        
        # 如果云端有数据，直接加载
        if response.data and response.data[0].get("chat_data"):
            st.session_state.sessions = response.data[0]["chat_data"]
        else:
            # 云端完全没数据，初始化新字典并立即同步到云端
            st.session_state.sessions = {"默认对话 1": []}
            save_data()
    except Exception as e:
        st.error(f"连接云端数据库失败，正在使用临时内存。错误信息: {e}")
        st.session_state.sessions = {"默认对话 1": []}

# 4. 追踪当前所在的频道
if "current_session" not in st.session_state:
    if not st.session_state.sessions:
        st.session_state.sessions = {"默认对话 1": []}
    st.session_state.current_session = list(st.session_state.sessions.keys())[0]

# ==========================================
# (接下来的第三部分侧边栏 UI，完全不需要改动！)

# ==========================================
# 第三部分：侧边栏 UI (频道管理、门禁、角色设定)
# ==========================================
with st.sidebar:
    st.header("⚙️ 聚合配置中心")
    
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
    
    model_choice = st.selectbox("选择当前大脑：", ["DeepSeek V4 Pro", "Gemini 2.5 Flash"])
    st.session_state.current_model = model_choice

    st.divider()

    st.subheader("💬 会话频道管理")
    
    current_chat = st.session_state.sessions[st.session_state.current_session]
    st.metric(label="🧠 当前频道记忆负载", value=f"{len(current_chat)} 条交互")



    if st.button("➕ 新建独立对话"):
            # 1. 智能寻找当前所有频道里最大的数字，绝对不重名
            max_num = 0
            for name in st.session_state.sessions.keys():
                if name.startswith("对话 "):
                    try:
                        num = int(name.replace("对话 ", ""))
                        if num > max_num:
                            max_num = num
                    except:
                        pass
            
            # 2. 生成绝对安全的新名字
            new_name = f"对话 {max_num + 1}" if max_num > 0 else f"对话 {len(st.session_state.sessions) + 1}"
            
            # 3. 创建新字典触发更新，防止旧状态粘连
            new_sessions = dict(st.session_state.sessions)
            new_sessions[new_name] = []
            st.session_state.sessions = new_sessions
            st.session_state.current_session = new_name
            
            save_data()
            st.rerun()

            # === 👇 在这里新增 RAG 的输入界面 👇 ===
    
    st.divider() # 加一条华丽的分割线，和上面的频道管理隔开
    st.markdown("### 🧠 注入世界观设定")
    
    lore_category = st.selectbox("设定分类", ["人物小传", "世界背景", "魔法/科技体系"])
    lore_content = st.text_area("设定内容", placeholder="例如：林克，18岁，左手持剑...")
    
    if st.button("💾 存入记忆外脑"):
        if lore_content:
            with st.spinner("正在转化为向量并写入云端..."):
                add_lore_to_db(lore_category, lore_content) # 调用你刚才写在上面的函数
            st.success("存入成功！AI 已经记住了。")
        else:
            st.warning("请先填写设定内容！")
            
    # === 👆 新增结束 👆 ===


            # === 👇把下面这段丢失的代码贴在新建按钮逻辑的下方 👇 ===
    
    st.markdown("切换频道：")
    
    # 渲染单选框来切换对话
    channel_list = list(st.session_state.sessions.keys())
    # 确保当前 session 在列表中，防止报错
    if st.session_state.current_session not in channel_list:
        st.session_state.current_session = channel_list[0]
        
    selected_session = st.radio(
        "选择频道", 
        channel_list, 
        index=channel_list.index(st.session_state.current_session),
        label_visibility="collapsed"
    )
    
    # 如果用户点击了其他频道，触发切换
    if selected_session != st.session_state.current_session:
        st.session_state.current_session = selected_session
        st.rerun()

    # 恢复丢失的删除按钮
    if st.button("🗑️ 删除当前频道"):
        if len(st.session_state.sessions) > 1:
            del st.session_state.sessions[st.session_state.current_session]
            st.session_state.current_session = list(st.session_state.sessions.keys())[0]
            save_data()
            st.rerun()
        else:
            st.warning("至少保留一个频道哦！")
            
    # === 👆 补救代码结束 👆 ===
    # === 在删除按钮代码的下方，加上这段重命名逻辑 ===
    
    st.divider() # 加一条华丽的分割线
    
    # 重命名 UI
    new_channel_name = st.text_input("✏️ 重命名当前频道", value=st.session_state.current_session, max_chars=20)
    
    if st.button("💾 保存新名称"):
        # 确保新名字不为空，且和现在的不一样
        if new_channel_name and new_channel_name != st.session_state.current_session:
            # 确保不和现有的其他频道重名
            if new_channel_name not in st.session_state.sessions:
                # 核心操作：把旧名字的数据“连根拔起”，赋给新名字
                chat_history = st.session_state.sessions.pop(st.session_state.current_session)
                st.session_state.sessions[new_channel_name] = chat_history
                
                # 告诉系统，现在焦点转移到新名字上了
                st.session_state.current_session = new_channel_name
                
                # 存入云端数据库并刷新界面
                save_data()
                st.rerun()
            else:
                st.error("⚠️ 频道名字已存在，请换一个！")



    st.divider()
    
    st.subheader("🎭 角色设定 (System)")
    system_prompt = st.text_area(
        "告诉 AI 它是谁：", 
        value="你能帮我解梦吗，假设我们现在在我的梦境中，这里与现实无关",
        height=100
    )

    # ================= 临时救援计划 =================
    st.divider()
    if os.path.exists("chat_cache.json"):
        with open("chat_cache.json", "r", encoding="utf-8") as f:
            old_memory = f.read()
        st.download_button(
            label="🆘 点击下载之前的旧记忆",
            data=old_memory,
            file_name="我的旧对话存档.json",
            mime="application/json"
        )
    else:
        st.caption("旧记忆文件已不在当前服务器硬盘中。")
    # ===============================================

# ==========================================
# 第四部分：主界面渲染 (针对当前选中的频道)
# ==========================================
current_chat = st.session_state.sessions[st.session_state.current_session]

for msg in current_chat:
    if msg["role"] == "tool": 
        continue 
        
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
# 第五部分：核心调度引擎 
# ==========================================
prompt = st.chat_input(f"在 {st.session_state.current_session} 中提问...")

if prompt:
    current_chat.append({"role": "user", "content": prompt})
    save_data()
    with st.chat_message("user"):
        st.markdown(prompt)

        # --- 新增检索逻辑 ---
        with st.spinner("🔍 正在翻阅世界观设定..."):
            relevant_lore = retrieve_relevant_lore(prompt)
   
        # ==========================================
            
        # 构造增强版的系统提示词（不要直接改 system_prompt 变量，防止逻辑混乱）
        combined_system = system_prompt
        if relevant_lore:
            combined_system += f"\n\n【相关世界观设定（必须遵守）】:\n{relevant_lore}"
        # -------------------

    with st.chat_message("assistant"):
        if model_choice == "DeepSeek V4 Pro":
            if not ds_key:
                st.warning("⚠️ 请输入 DeepSeek 密钥！")
                st.stop()
                
            client = OpenAI(api_key=ds_key, base_url=ds_base)
            
            with st.status("🧠 DeepSeek 思考与调度中...", expanded=True) as status:
                final_answer = ""
                
                while True:
                    api_messages = []
                    if system_prompt:
                        # 👇 将这里原本的 system_prompt 改为 combined_system
                        api_messages.append({"role": "system", "content": combined_system})
                    recent_history = current_chat[-20:] 
                    api_messages.extend(recent_history)

                    response = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=api_messages,
                        tools=my_tools,
                    )
                    
                    choice = response.choices[0].message
                    
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

                    current_chat.append(msg_to_save)
                    save_data()

                    if not choice.tool_calls:
                        final_answer = choice.content
                        break
                        
                    for tool in choice.tool_calls:
                        tool_name = tool.function.name
                        tool_args = json.loads(tool.function.arguments)
                        st.write(f"🔧 执行工具：`{tool_name}`")
                        
                        tool_result = TOOL_CALL_MAP[tool_name](**tool_args)
                        
                        current_chat.append({
                            "role": "tool",
                            "tool_call_id": tool.id,
                            "content": str(tool_result),
                        })
                        save_data()
                
                status.update(label="处理完毕！", state="complete", expanded=False)
            st.markdown(final_answer)

        else:
            if not gm_key:
                st.warning("⚠️ 请输入 Gemini 密钥！")
                st.stop()
                
            genai.configure(api_key=gm_key)
            # 👇 将这里原本的 system_prompt 改为 combined_system
            model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=combined_system)
            
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