"""
千问模型客户端（OpenAI 兼容模式）
模型: qwen3.7-max（对话）、text-embedding-v3（嵌入）
环境变量: QWEN_API_KEY

优化: 流式输出、输入长度截断
"""
import os
from openai import OpenAI

QWEN_API_KEY = os.environ.get("QWEN_API_KEY", "")
QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
CHAT_MODEL = "qwen3.7-max"
EMBED_MODEL = "text-embedding-v3"
MAX_INPUT_CHARS = 3000  # 输入总字符上限


def get_client():
    if not QWEN_API_KEY:
        return None
    return OpenAI(api_key=QWEN_API_KEY, base_url=QWEN_BASE_URL)


def chat(messages, temperature=0.5, max_tokens=800, stream=False):
    """调用千问对话模型"""
    client = get_client()
    if not client:
        return "【错误】QWEN_API_KEY 未配置", ""
    # 截断输入
    for m in messages:
        if len(m.get("content", "")) > MAX_INPUT_CHARS:
            m["content"] = m["content"][:MAX_INPUT_CHARS]

    try:
        if stream:
            resp = client.chat.completions.create(
                model=CHAT_MODEL, messages=messages,
                temperature=temperature, max_tokens=max_tokens, stream=True
            )
            # 收集流式输出
            result = []
            for chunk in resp:
                if chunk.choices[0].delta.content:
                    result.append(chunk.choices[0].delta.content)
            return "".join(result).strip(), ""
        else:
            resp = client.chat.completions.create(
                model=CHAT_MODEL, messages=messages,
                temperature=temperature, max_tokens=max_tokens
            )
            usage = resp.usage
            tokens = f"本次消耗：{usage.prompt_tokens}输入 + {usage.completion_tokens}输出" if usage else ""
            return resp.choices[0].message.content.strip(), tokens
    except Exception as e:
        return f"【错误】{str(e)[:100]}", ""


def embed(texts):
    """文本嵌入"""
    client = get_client()
    if not client:
        return None
    if isinstance(texts, str):
        texts = [texts]
    try:
        resp = client.embeddings.create(model=EMBED_MODEL, input=texts)
        return [d.embedding for d in resp.data]
    except Exception as e:
        print(f"[Embedding] Error: {e}")
        return None
