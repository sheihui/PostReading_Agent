#!/usr/bin/env python3
"""
微信读书 Agent Gateway 数据获取
Gateway → 存缓存 JSON → 返回数据
"""

import json
import os
import requests

GATEWAY = "https://i.weread.qq.com/api/agent/gateway"


def _call_gateway(api_name: str, api_key: str, **params) -> dict:
    body = {"api_name": api_name, "skill_version": "1.0.3", **params}
    resp = requests.post(
        GATEWAY,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=body,
    )
    data = resp.json()
    if data.get("errcode") and data["errcode"] != 0:
        raise Exception(f"Gateway error: {data}")
    return data


def title_to_bookId(title: str, api_key: str) -> str:
    data = _call_gateway("/store/search", api_key, keyword=title, scope=10, count=5)
    for group in data.get("results", []):
        for book in group.get("books", []):
            if book["bookInfo"]["title"] == title:
                return book["bookInfo"]["bookId"]
    return ""


def fetch_book_data(book_id: str, api_key: str) -> dict:
    return {
        "info": _call_gateway("/book/info", api_key, bookId=book_id),
        "chapters": _call_gateway("/book/chapterinfo", api_key, bookId=book_id),
        "highlights": _call_gateway("/book/bookmarklist", api_key, bookId=book_id),
        "reviews": _call_gateway("/review/list/mine", api_key, bookid=book_id),
        "bestbookmarks": _call_gateway("/book/bestbookmarks", api_key, bookId=book_id),
        "publicReviews": _call_gateway("/review/list", api_key, bookId=book_id, reviewListType=1, count=5),
    }


def get_book_info(title: str, api_key: str):
    if os.path.exists(f"data/books/{title}.json"):
        return json.load(open(f"data/books/{title}.json", encoding="utf-8")), True

    book_id = title_to_bookId(title, api_key)
    if not book_id:
        print(f"[get_book_info] 找不到书籍: {title}")
        return None, False

    data = fetch_book_data(book_id, api_key)
    return data, False


def save_json_file(data, title: str):
    os.makedirs("data/books", exist_ok=True)
    with open(f"data/books/{title}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[save_json_file] 已保存: data/books/{title}.json")
