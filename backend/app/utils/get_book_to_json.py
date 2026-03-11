#!/usr/bin/env python3
"""
将指定书籍内容导出：
    1、书籍信息
    2、章节信息
    3、划线信息
    4、笔记信息
    {"book_info": {
        "book_id": "string",
        "title": "string",
        "author": "string",
        "intro": "string",
        "category": "string",
    },
    "chapters": [
        {
            "chapter_uid": 0,
            "chapter_idx": 0,
            "title": "string"
        }
    ],
    "highlights": [
        {
            "bookmark_id": "string",
            "chapter_uid": 0,
            "chapter_idx": 0,
            "mark_text": "string",
            "create_time": 0
        }
    ],
    "reviews": [
        {
            "review_id": "string",
            "chapter_uid": 0,
            "chapter_title": "string",
            "content": "string",
            "create_time": 0
        }
    ]
    }
"""



import json
import os
import sys
from pathlib import Path

from app.utils.weread_api import WeReadAPI, WeReadParser, BookNotes, Book, parse_cookies


def title_to_bookId(api: WeReadAPI, title: str) -> str:
    """根据标题获取书籍 ID"""
    try:
        books = api.get_notebooks()
        for book in books[:100]:
            if book['book'].get('title') == title:
                print(f"[title_to_bookId]找到书籍 ID: {book.get('bookId')}")
                return book.get('bookId')
    except Exception as e:
        print(f"[title_to_bookId]获取书籍 ID 失败: {e}")
        return ""


def load_book_info(api: WeReadAPI, book_id: str) -> Book:
    """根据书籍 ID 获取书籍信息"""
    try:
        book_detail = api.get_book_detail(book_id)
        book_detail = WeReadParser.parse_book(book_detail)
        print(f"[load_book_info]获取书籍详情成功")
    except Exception as e:
        print(f"[load_book_info]获取书籍详情失败: {e}")
        return None

    chapters = api.get_chapters(book_id)
    chapters = WeReadParser.parse_chapters(chapters, book_id)
    print(f"[load_book_info]获取章节信息成功.")
    
    book_marks = api.get_bookmarks(book_id)
    book_marks = WeReadParser.parse_highlights(book_marks)
    print(f"[load_book_info]获取划线信息成功.")
    
    reviews = api.get_reviews(book_id, mine=1)
    reviews = WeReadParser.parse_reviews(reviews)
    print(f"[load_book_info]获取笔记信息成功.")    
    
    return [book_detail, chapters, book_marks, reviews]


def book_info_to_json(book_info: list) -> dict:
    """将书籍信息转换为 JSON 字符串"""
    if not book_info:
        print(f"[book_info_to_json]书籍信息为空")
        return None
    
    result = {"book_info": {},
              "chapters": [],
              "highlights": [],
              "reviews": [],
              }
    result["book_info"]["book_id"] = book_info[0].book_id
    result["book_info"]["title"] = book_info[0].title
    result["book_info"]["author"] = book_info[0].author
    result["book_info"]["intro"] = book_info[0].intro
    result["book_info"]["category"] = book_info[0].category

    for chapter in book_info[1]:
        result["chapters"].append({
            "chapter_uid": chapter.chapter_uid,
            "chapter_idx": chapter.chapter_idx,
            "title": chapter.title,
        })
    
    for highlight in book_info[2]:
        result["highlights"].append({
            "bookmark_id": highlight.bookmark_id,
            "chapter_uid": highlight.chapter_uid,
            "chapter_idx": highlight.chapter_idx,
            "mark_text": highlight.mark_text,
            "create_time": highlight.create_time,
        })
    
    for review in book_info[3]:
        result["reviews"].append({
            "review_id": review.review_id,
            "chapter_uid": review.chapter_uid,
            "chapter_title": review.chapter_title,
            "content": review.content,
            "create_time": review.create_time,
        })
    
    return result


def get_book_info(title: str) -> json:
    """根据标题获取书籍信息"""
    from backend.app.config import WEREAD_COOKIE
    cookies = parse_cookies(WEREAD_COOKIE)
    api = WeReadAPI(cookies)
    book_id = title_to_bookId(api, title)
    if not book_id:
        print(f"获取书籍 ID 失败: {title}")
        return None
    
    book_info = load_book_info(api, book_id)
    book_info_json = book_info_to_json(book_info)
    if not book_info_json:
        print(f"获取书籍信息失败: {title}")
        return None
    
    return book_info_json


def save_json_file(book_info_json: json, title: str) -> None:
    """将 JSON 字符串保存到文件"""
    with open(f"data/books/{title}.json", 'w', encoding='utf-8') as f:
        f.write(json.dumps(book_info_json, ensure_ascii=False, indent=4))
    print(f"书籍信息已保存到: data/books/{title}.json")



if __name__ == "__main__":
    # this is a test
    file_path = "data/books"


    book_info_json = get_book_info("巴比伦最富有的人")
    if book_info_json:
        print(book_info_json)
        # save_json_file(book_info_json, "巴比伦最富有的人", file_path)

