"""
RAG 服务 — Chroma 向量数据库 + 千问嵌入
启动时自动从 policy_data.json 构建索引，后续检索 top-3 相关片段
"""
import os
import json

try:
    import chromadb
    from chromadb.config import Settings
    _HAS_CHROMA = True
except ImportError:
    _HAS_CHROMA = False
    print("[RAG] chromadb 未安装，RAG 检索功能禁用")

from qwen_client import embed

POLICY_PATH = os.environ.get("POLICY_DATA_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "silver_headlines_data.json"))
CHROMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".chroma_db")

_collection = None


def _load_policy_items():
    """从 policy JSON 中提取所有政策条目为文本片段"""
    if not os.path.exists(POLICY_PATH):
        print(f"[RAG] 政策文件不存在: {POLICY_PATH}")
        return []
    with open(POLICY_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = []
    for cat in data.get("categories", []):
        cat_title = cat.get("title", "")
        all_items = []
        if "sub_categories" in cat:
            for sub in cat["sub_categories"]:
                all_items.extend(sub.get("items", []))
        else:
            all_items = cat.get("items", [])
        for item in all_items:
            title = item.get("title", "")[:120]
            source = item.get("source", "")
            date = item.get("date", "")
            summary = item.get("summary", "")
            url = item.get("url", "")
            text = f"【{cat_title}】{title}\n来源：{source}（{date}）\n摘要：{summary}\n链接：{url}"
            items.append({"text": text, "title": title, "source": source, "url": url})
    return items


def init_rag():
    """初始化 Chroma 索引（启动时调用）"""
    global _collection
    if not _HAS_CHROMA:
        print("[RAG] chromadb 不可用，跳过索引构建")
        return
    os.makedirs(CHROMA_PATH, exist_ok=True)
    client = chromadb.PersistentClient(path=CHROMA_PATH, settings=Settings(anonymized_telemetry=False))
    collections = [c.name for c in client.list_collections()]
    if "policies" in collections:
        _collection = client.get_collection("policies")
        print(f"[RAG] 加载已有索引，共 {_collection.count()} 条")
    else:
        items = _load_policy_items()
        if not items:
            print("[RAG] 无政策数据，跳过索引构建")
            return
        texts = [it["text"] for it in items]
        print(f"[RAG] 正在构建嵌入向量 ({len(texts)} 条)...")
        vectors = embed(texts)
        if not vectors:
            print("[RAG] 嵌入失败，使用空索引")
            return
        _collection = client.create_collection("policies")
        ids = [f"p{i}" for i in range(len(texts))]
        metadatas = [{"title": it["title"], "source": it["source"], "url": it["url"]} for it in items]
        _collection.add(embeddings=vectors, documents=texts, metadatas=metadatas, ids=ids)
        print(f"[RAG] 索引构建完成，共 {_collection.count()} 条")


def retrieve(query, k=3):
    """检索 top-k 相关片段，返回 [{"content": "...", "title": "...", "source": "...", "url": "..."}]"""
    global _collection
    if _collection is None or _collection.count() == 0:
        return []
    qv = embed(query)
    if not qv:
        return []
    results = _collection.query(query_embeddings=qv, n_results=min(k, _collection.count()))
    items = []
    for i in range(len(results["ids"][0])):
        items.append({
            "content": results["documents"][0][i][:500],
            "title": results["metadatas"][0][i].get("title", ""),
            "source": results["metadatas"][0][i].get("source", ""),
            "url": results["metadatas"][0][i].get("url", ""),
        })
    return items
