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

# 本地数据库文件名
DB_FILE = "chat_cache.json"

# 自动存盘函数
def save_data():
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(st.session_state.messages, f, ensure_ascii=False, indent=2)

# 初始化读取记忆
if "messages" not in st.session_state:
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            st.session_state.messages = json.load(f)
    else:
        st.session_state.messages = []

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
    if st.button("🗑️ 清空当前对话"):
        st.session_state.messages = []
        save_data()
        st.rerun()

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
                    # 按照官方要求发送请求
                    response = client.chat.completions.create(
                        model="deepseek-chat", # 请根据实际权限确认模型名称是否为 deepseek-v4-pro
                        messages=st.session_state.messages,
                        tools=my_tools,
                        # reasoning_effort="high", # 如果报错不支持该参数，可将此行注释掉
                        # extra_body={"thinking": {"type": "enabled"}} # 如果使用非 r1/pro 模型，注释掉此行
                    )
                    
                    choice = response.choices[0].message
                    
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