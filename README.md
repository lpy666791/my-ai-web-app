# 多频道 AI 聚合助手

一个基于 Streamlit 的多模型对话应用，支持在 DeepSeek 与 Gemini 之间切换，具备工具调用（Function Calling）、向量检索（RAG）和云端会话持久化。

A multi-model chat application built with Streamlit, supporting DeepSeek and Gemini, with function calling, retrieval-augmented generation and cloud-side session persistence.

---

## 主要功能

**多模型切换** — 在同一界面内切换 DeepSeek 与 Gemini，两套 SDK 的消息格式差异在调度层统一处理，对话历史可跨模型延续。

**工具调用（Function Calling）** — 定义工具 schema 并实现调度循环：模型返回 `tool_calls` 后本地执行对应函数，将结果回填进消息序列并再次请求，直到模型给出最终回答。目前内置日期与天气两个示例工具，新增工具只需在 `my_tools` 与 `TOOL_CALL_MAP` 中登记。

**记忆外脑（RAG）** — 使用 `sentence-transformers` 的 all-MiniLM-L6-v2 在本地生成向量，存入 Supabase 的向量表，检索时通过 `match_lore` 相似度函数召回相关设定，拼接进 system prompt。模型本地运行，文本内容不经过第三方嵌入接口。

**多频道会话管理** — 支持新建、重命名、删除多个独立对话频道，各频道历史互相隔离。

**云端持久化** — 会话数据存储在 Supabase，而非本地文件，因此在 Streamlit Cloud 这类无持久磁盘的环境中重启不丢失。

**密钥管理** — 所有 API key 通过 `st.secrets` 注入，不进入代码库；也支持用户在侧边栏自带密钥运行。

---

## 技术栈

| 层 | 使用 |
|---|---|
| 前端 / 应用框架 | Streamlit |
| 大模型 | DeepSeek（OpenAI 兼容接口）、Google Gemini |
| 向量化 | sentence-transformers (all-MiniLM-L6-v2)，本地运行 |
| 数据库 / 向量检索 | Supabase (PostgreSQL + pgvector) |

---

## 本地运行

```bash
git clone https://github.com/lpy666791/my-ai-web-app.git
cd my-ai-web-app
pip install -r requirements.txt
```

在项目下创建 `.streamlit/secrets.toml`：

```toml
SUPABASE_URL = "你的 Supabase 项目地址"
SUPABASE_KEY = "你的 Supabase key"
DEEPSEEK_API_KEY = "sk-..."
GEMINI_API_KEY = "..."
ACCESS_CODE = "自定义访问码"
```

数据库需要两张表：`ai_sessions`（存对话存档）与 `novel_lore`（存设定及其向量），以及一个用于相似度检索的 `match_lore` 函数。

启动：

```bash
streamlit run app.py
```

首次运行会自动下载嵌入模型，需等待片刻。

---

## 项目说明

这是我在自学大模型应用开发过程中搭建的练习项目，重点想弄清楚三件事：工具调用的完整循环是怎么跑起来的、RAG 从向量化到召回的每一步在做什么、以及无状态的前端如何配合数据库做持久化。代码仍在迭代中。
