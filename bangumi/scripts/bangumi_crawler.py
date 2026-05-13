"""Bangumi 番剧信息查询工具。

提供面向 skill 的稳定函数：搜索条目、获取条目详情、评分、短评与格式化输出。
实现尽量使用 Bangumi 公开 v0 API；搜索和短评在 API 不足时降级解析网页。
"""
from __future__ import annotations

import html
import re
import time
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

BASE = "https://bgm.tv"
API = "https://api.bgm.tv/v0"
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 GenericAgent/1.0"
)
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.7",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.7,ja;q=0.6",
    "Referer": BASE + "/",
}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def _sleep(delay: float = 0.6) -> None:
    if delay > 0:
        time.sleep(delay)


def _get(url: str, *, params: Optional[dict] = None, timeout: int = 15) -> requests.Response:
    _sleep()
    resp = SESSION.get(url, params=params, timeout=timeout)
    resp.raise_for_status()
    return resp


def _post(url: str, *, json_data: Optional[dict] = None, timeout: int = 15) -> requests.Response:
    _sleep()
    resp = SESSION.post(url, json=json_data, timeout=timeout, headers={**HEADERS, "Accept": "application/json"})
    resp.raise_for_status()
    return resp


def _strip(text: Any) -> str:
    return re.sub(r"\s+", " ", html.unescape(str(text or ""))).strip()


def _subject_from_api_item(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": item.get("id"),
        "name": item.get("name") or "",
        "name_cn": item.get("name_cn") or "",
        "summary": item.get("summary") or "",
        "date": item.get("date") or "",
        "rank": item.get("rank"),
        "score": (item.get("rating") or {}).get("score"),
        "total": (item.get("rating") or {}).get("total"),
        "tags": [t.get("name") for t in (item.get("tags") or [])[:8] if t.get("name")],
        "url": f"{BASE}/subject/{item.get('id')}" if item.get("id") else "",
    }


def search(keyword: str, limit: int = 5) -> List[Dict[str, Any]]:
    """搜索动画条目，返回列表。"""
    keyword = _strip(keyword)
    if not keyword:
        return []
    limit = max(1, min(int(limit or 5), 20))
    payload = {
        "keyword": keyword,
        "sort": "match",
        "filter": {"type": [2]},
    }
    try:
        data = _post(f"{API}/search/subjects", json_data=payload).json()
        items = data.get("data") or []
        return [_subject_from_api_item(x) for x in items[:limit]]
    except Exception:
        # HTML fallback: /subject_search/<kw>?cat=2
        resp = _get(f"{BASE}/subject_search/{quote_plus(keyword)}", params={"cat": 2})
        soup = BeautifulSoup(resp.text, "html.parser")
        out: List[Dict[str, Any]] = []
        for li in soup.select("#browserItemList li.item")[:limit]:
            a = li.select_one("h3 a[href*='/subject/']")
            if not a:
                continue
            m = re.search(r"/subject/(\d+)", a.get("href", ""))
            sid = int(m.group(1)) if m else None
            name_cn = _strip(a.select_one("span.tip") .get_text(" ") if a.select_one("span.tip") else "")
            title = _strip(a.get_text(" "))
            score_el = li.select_one("small.fade")
            out.append({
                "id": sid,
                "name": title,
                "name_cn": name_cn,
                "summary": _strip(li.select_one("p.info").get_text(" ") if li.select_one("p.info") else ""),
                "date": "",
                "rank": None,
                "score": _strip(score_el.get_text(" ") if score_el else ""),
                "total": None,
                "tags": [],
                "url": f"{BASE}/subject/{sid}" if sid else "",
            })
        return out


def get_subject(subject_id: int | str) -> Dict[str, Any]:
    """获取条目 API 原始详情。"""
    sid = str(subject_id).strip()
    data = _get(f"{API}/subjects/{sid}", timeout=20).json()
    data["url"] = f"{BASE}/subject/{sid}"
    return data


def get_rating(subject_id: int | str) -> Dict[str, Any]:
    """获取评分摘要。"""
    data = get_subject(subject_id)
    rating = data.get("rating") or {}
    return {
        "id": data.get("id") or int(subject_id),
        "name": data.get("name") or "",
        "name_cn": data.get("name_cn") or "",
        "score": rating.get("score"),
        "total": rating.get("total"),
        "rank": data.get("rank"),
        "count": rating.get("count") or {},
        "url": data.get("url") or f"{BASE}/subject/{subject_id}",
    }


def get_comments(subject_id: int | str, limit: int = 8) -> List[Dict[str, Any]]:
    """抓取网页短评，返回用户名、星级和文本。"""
    sid = str(subject_id).strip()
    limit = max(1, min(int(limit or 8), 30))
    resp = _get(f"{BASE}/subject/{sid}/comments")
    soup = BeautifulSoup(resp.text, "html.parser")
    comments: List[Dict[str, Any]] = []
    for item in soup.select("#comment_box .item, .commentsList .item, div[id^='post_']"):
        user_el = item.select_one("a.l, strong a, .inner strong")
        text_el = item.select_one("p, .text, .reply_content")
        star = None
        cls_text = " ".join(" ".join(x.get("class", [])) for x in item.select("span[class*='stars'], span[class*='starlight']"))
        m = re.search(r"stars?(\d+)|starlight\s*stars(\d+)", cls_text)
        if m:
            star = int(next(g for g in m.groups() if g))
        text = _strip(text_el.get_text(" ") if text_el else item.get_text(" "))
        if text:
            comments.append({"user": _strip(user_el.get_text(" ") if user_el else ""), "star": star, "text": text})
        if len(comments) >= limit:
            break
    return comments


def get_subject_detail(subject_id: int | str, comments_limit: int = 8) -> Dict[str, Any]:
    """获取条目详情 + 评分 + 短评。"""
    data = get_subject(subject_id)
    detail = _subject_from_api_item(data)
    detail.update({
        "infobox": data.get("infobox") or [],
        "platform": data.get("platform") or "",
        "eps": data.get("eps"),
        "volumes": data.get("volumes"),
        "comments": get_comments(subject_id, comments_limit),
    })
    return detail


def query_anime(keyword: str, *, comments_limit: int = 8) -> Dict[str, Any]:
    """按关键词查询最匹配动画的评分与风评。"""
    results = search(keyword, limit=5)
    if not results:
        return {"query": keyword, "results": [], "detail": None, "error": "未找到相关番剧"}
    best = results[0]
    sid = best.get("id")
    if not sid:
        return {"query": keyword, "results": results, "detail": None, "error": "搜索结果缺少条目ID"}
    detail = get_subject_detail(sid, comments_limit=comments_limit)
    return {"query": keyword, "results": results, "detail": detail, "error": None}


def format_search_results(results: List[Dict[str, Any]]) -> str:
    if not results:
        return "未找到相关番剧。"
    lines = ["Bangumi 搜索结果："]
    for i, r in enumerate(results, 1):
        title = r.get("name_cn") or r.get("name") or r.get("id")
        extra = []
        if r.get("score") not in (None, ""):
            extra.append(f"评分 {r.get('score')}")
        if r.get("total"):
            extra.append(f"{r.get('total')}人")
        if r.get("date"):
            extra.append(str(r.get("date")))
        lines.append(f"{i}. {title} (ID: {r.get('id')})" + (" — " + " / ".join(extra) if extra else ""))
    return "\n".join(lines)


def format_rating(rating: Dict[str, Any]) -> str:
    title = rating.get("name_cn") or rating.get("name") or rating.get("id")
    score = rating.get("score")
    total = rating.get("total")
    rank = rating.get("rank")
    return f"{title}: Bangumi 评分 {score if score is not None else '暂无'} / 10，{total or 0} 人评分" + (f"，排名 #{rank}" if rank else "")


def format_detail(detail: Dict[str, Any]) -> str:
    if not detail:
        return "未获取到详情。"
    title = detail.get("name_cn") or detail.get("name") or detail.get("id")
    lines = [f"# {title}", format_rating(detail)]
    if detail.get("date"):
        lines.append(f"放送日期：{detail['date']}")
    if detail.get("tags"):
        lines.append("标签：" + "、".join(detail["tags"][:8]))
    summary = _strip(detail.get("summary"))
    if summary:
        lines.append("简介：" + summary[:400])
    comments = detail.get("comments") or []
    if comments:
        lines.append("\n短评 / 风评摘录：")
        for c in comments[:8]:
            prefix = f"- {c.get('user') or '匿名'}"
            if c.get("star"):
                prefix += f"（{c['star']}星）"
            lines.append(prefix + "：" + c.get("text", "")[:220])
    if detail.get("url"):
        lines.append("链接：" + detail["url"])
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "葬送的芙莉莲"
    print(format_detail(query_anime(q)["detail"]))
