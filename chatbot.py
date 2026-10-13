# 运行命令: streamlit run chatbot.py
import streamlit as st
from openai import OpenAI
import os
from dotenv import load_dotenv

# 加载 .env 文件里的环境变量（本地运行用；云端无 .env，靠 secrets.toml）
load_dotenv()

# 统一读取配置：云端优先用 Streamlit secrets（secrets.toml），本地回退到 .env
def get_config(key, default=None):
    if key in st.secrets:
        return st.secrets[key]
    return os.getenv(key, default)

# 初始化OpenAI客户端
# base_url 可以切换为任何OpenAI兼容API（DeepSeek、Moonshot、Qwen等）
client = OpenAI(
    api_key=get_config("API_KEY"),
    base_url=get_config("API_BASE_URL", "https://api.openai.com/v1")
)
MODEL = get_config("MODEL_NAME", "gpt-4o-mini")

# 页面配置（必须是第一个Streamlit命令，否则报错）
st.set_page_config(page_title="AI聊天助手", page_icon="🤖", layout="centered")
st.title("🤖 AI聊天助手")

# ===== System Prompt：AI的「角色设定」=====
# 这里定义AI的性格、能力边界、回答规则
# 修改这里，就能创造出不同专业方向的AI助手
SYSTEM_PROMPT = """你是一个专业、友好的AI助手。你的特点：
- 回答简洁准确，避免废话
- 必要时用具体例子说明
- 对于不确定的信息，主动说明不确定
- 默认用中文回答"""

# ===== 初始化对话历史 =====
# session_state 是 Streamlit 的「跨刷新状态存储」
# 没有它，每次重新渲染界面时变量都会重置（对话历史就丢了）
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": SYSTEM_PROMPT}  # 第0条：角色指令（用户不可见）
    ]

# ===== 侧边栏：用户可调节的参数 =====
with st.sidebar:
    st.header("⚙️ 对话设置")
    # Temperature：控制「创造力」
    # 0 = 严谨固定（适合代码生成、事实查询）
    # 1 = 发散创意（适合写作、头脑风暴）
    temperature = st.slider(
        "创造力 (Temperature)",
        min_value=0.0, max_value=1.0, value=0.7, step=0.1,
        help="值越高回答越有创意，值越低越保守稳定"
    )
    max_tokens = st.slider("最大回复长度", min_value=100, max_value=4000, value=1000, step=100)
    st.divider()
    msg_count = len([m for m in st.session_state.messages if m["role"] != "system"])
    st.metric("已对话轮数", msg_count // 2)
    if st.button("🗑️ 清除对话历史", use_container_width=True):
        st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        st.rerun()

# ===== 显示历史对话 =====
# 从 index=1 开始，跳过第0条 system 消息
for msg in st.session_state.messages[1:]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ===== 处理用户新输入 =====
if prompt := st.chat_input("输入你的问题，按 Enter 发送..."):
    # 1. 把用户消息加入历史
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. 调用API，开启流式输出
    with st.chat_message("assistant"):
        stream = client.chat.completions.create(
            model=MODEL,
            messages=st.session_state.messages,  # 发送完整历史，实现多轮对话
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True   # 关键！一个token一个token地流式返回
        )
        # st.write_stream 自动处理流式，显示打字机效果，返回完整文本
        response_text = st.write_stream(
            chunk.choices[0].delta.content or ""
            for chunk in stream
            if chunk.choices[0].delta.content
        )

    # 3. 把AI回复加入历史（下次请求时会带上，实现记忆）
    st.session_state.messages.append({"role": "assistant", "content": response_text})
