"""
微信读书 API - 获取划线和笔记
参考 obsidian-weread-plugin 实现
"""

import json
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional
from pathlib import Path
# from config import WEREAD_COOKIE

import requests


@dataclass
class Book:
    """书籍基本信息"""
    book_id: str
    title: str
    author: str
    # cover: str
    intro: str = ""
    # publisher: str = ""
    category: str = ""
    # publish_time: str = ""
    # total_words: int = 0
    
    
@dataclass
class Chapter:
    """章节信息"""
    chapter_uid: int
    chapter_idx: int
    title: str
    level: int = 0
    # is_mp_chapter: int = 0
    
    
@dataclass
class Highlight:
    """划线/高亮"""
    bookmark_id: str
    chapter_uid: int
    chapter_idx: int
    chapter_title: str
    mark_text: str
    # style: int
    # color_style: int
    create_time: int
    # range: str
    review_content: str = ""  # 笔记内容（如果有）
    
    
@dataclass
class Review:
    """笔记/书评"""
    review_id: str
    chapter_uid: int
    chapter_title: str
    content: str  # 笔记内容
    create_time: int
    chapter_idx: int = 0
    abstract: str = ""
    range: str = ""
    
    
@dataclass
class BookNotes:
    """一本书的笔记汇总"""
    book: Book
    chapters: list[Chapter] = field(default_factory=list)
    highlights: list[Highlight] = field(default_factory=list)
    reviews: list[Review] = field(default_factory=list)


class WeReadAPI:
    """微信读书 API"""
    
    BASE_URL = "https://weread.qq.com"
    
    def __init__(self, cookies: dict):
        """
        初始化 API
        Args:
            cookies: 微信读书的 cookie 字典
        """
        self.session = requests.Session()
        self.session.cookies.update(cookies)
        self._update_headers()
        
    def _update_headers(self):
        """更新请求头"""
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json',
        })
    
    def _get_cookie_string(self) -> str:
        """获取 cookie 字符串"""
        return "; ".join([f"{k}={v}" for k, v in self.session.cookies.get_dict().items()])
    
    def _headers(self) -> dict:
        """获取带 cookie 的请求头"""
        headers = dict(self.session.headers)
        headers['Cookie'] = self._get_cookie_string()
        return headers
    
    def get_notebooks(self) -> list[dict]:
        """
        获取用户的书架/书籍列表
        Returns:
            书籍列表
        """
        url = f"{self.BASE_URL}/api/user/notebook"
        resp = self.session.get(url, headers=self._headers())
        data = resp.json()
        
        if data.get('errcode') == -2012:
            raise Exception("Cookie 已过期，请重新登录")
        
        return data.get('books', [])
    
    def get_book_detail(self, book_id: str) -> dict:
        """
        获取书籍详情
        Args:
            book_id: 书籍 ID
        Returns:
            书籍详情
        """
        url = f"{self.BASE_URL}/web/book/info?bookId={book_id}"
        resp = self.session.get(url, headers=self._headers())
        return resp.json()
    
    def get_bookmarks(self, book_id: str) -> dict:
        """
        获取书籍的划线列表
        Args:
            book_id: 书籍 ID
        Returns:
            划线数据
        """
        url = f"{self.BASE_URL}/web/book/bookmarklist?bookId={book_id}"
        resp = self.session.get(url, headers=self._headers())
        return resp.json()
    
    def get_reviews(self, book_id: str, list_type: int = 11, mine: int = 1, synckey: int = 0) -> dict:
        """
        获取书籍的笔记/书评列表
        Args:
            book_id: 书籍 ID
            list_type: 列表类型 (11 = 我的笔记)
            mine: 是否只获取我的笔记 (1 = 只获取我的)
            synckey: 同步键
        Returns:
            笔记数据
        """
        url = f"{self.BASE_URL}/web/review/list?bookId={book_id}&listType={list_type}&mine={mine}&synckey={synckey}"
        resp = self.session.get(url, headers=self._headers())
        return resp.json()
    
    def get_chapters(self, book_id: str) -> dict:
        """
        获取书籍章节信息
        Args:
            book_id: 书籍 ID
        Returns:
            章节数据
        """
        url = f"{self.BASE_URL}/web/book/chapterInfos"
        body = {"bookIds": [book_id]}
        resp = self.session.post(url, json=body, headers=self._headers())
        return resp.json()


class WeReadParser:
    """微信读书数据解析器"""
    
    @staticmethod
    def parse_book(detail: dict) -> Book:
        """解析书籍详情"""
        return Book(
            book_id=detail.get('bookId', ''),
            title=detail.get('title', ''),
            author=detail.get('author', ''),
            # cover=detail.get('cover', ''),
            intro=detail.get('intro', ''),
            # publisher=detail.get('publisher', ''),
            category=detail.get('category', ''),
            # publish_time=detail.get('publishTime', ''),
            # total_words=detail.get('totalWords', 0),
        )
    
    @staticmethod
    def parse_chapters(data: dict, book_id: str) -> list[Chapter]:
        """解析章节列表"""
        chapters = []
        for book_data in data.get('data', []):
            if book_data.get('bookId') != book_id:
                continue
            for ch in book_data.get('updated', []):
                chapters.append(Chapter(
                    chapter_uid=ch.get('chapterUid', 0),
                    chapter_idx=ch.get('chapterIdx', 0),
                    title=ch.get('title', ''),
                    level=ch.get('level', 0),
                    # is_mp_chapter=ch.get('isMPChapter', 0),
                ))
        # 按章节顺序排序
        chapters.sort(key=lambda x: x.chapter_idx)
        return chapters
    
    @staticmethod
    def parse_highlights(data: dict) -> list[Highlight]:
        """解析划线列表"""
        highlights = []
        for h in data.get('updated', []):
            highlights.append(Highlight(
                bookmark_id=h.get('bookmarkId', ''),
                chapter_uid=h.get('chapterUid', 0),
                chapter_idx=h.get('chapterIdx', 0),
                chapter_title=h.get('chapterName', ''),
                mark_text=h.get('markText', ''),
                # style=h.get('style', 0),
                # color_style=h.get('colorStyle', 0),
                create_time=h.get('createTime', 0),
                # range=h.get('range', ''),
            ))
        # 按章节顺序+位置排序
        highlights.sort(key=lambda x: (x.chapter_idx, x.create_time))
        return highlights
    
    @staticmethod
    def parse_reviews(data: dict) -> list[Review]:
        """解析笔记列表"""
        reviews = []
        for item in data.get('reviews', []):
            review = item.get('review', {})
            reviews.append(Review(
                review_id=review.get('reviewId', ''),
                chapter_uid=review.get('chapterUid', 0),
                chapter_title=review.get('chapterName', ''),
                content=review.get('content', ''),
                create_time=review.get('createTime', 0),
                chapter_idx=review.get('chapterIdx', 0),
                abstract=review.get('abstract', ''),
                range=review.get('range', ''),
            ))
        # 按创建时间排序
        reviews.sort(key=lambda x: x.create_time, reverse=True)
        return reviews



def parse_cookies(content: str) -> dict:
    """从文件加载 cookies"""
    # 解析 cookie 字符串
    cookies = {}
    for part in content.split(';'):
        part = part.strip()
        if '=' in part:
            key, value = part.split('=', 1)
            cookies[key.strip()] = value.strip()
    return cookies


# 测试用
if __name__ == "__main__":
    print("微信读书 API")
    print("=" * 50)
    # org = ""
    # cookies = parse_cookies(org)
    # api = WeReadAPI(cookies)
    # books = api.get_notebooks()[0]
    # print(books['book'].get('title'))
    # book_detail = api.get_book_detail(3300148783)
    # book_detail = WeReadParser.parse_book(book_detail)
    # print(book_detail)
    # 获取章节
    # print("   获取章节...")
    # chapters_data = api.get_chapters(book_detail.book_id)
    # chapters = WeReadParser.parse_chapters(chapters_data, book_detail.book_id)
    # print(chapters)

    # book_marks = api.get_bookmarks(books.get('bookId'))
    # highlights = WeReadParser.parse_highlights(book_marks)
    # print(highlights)
    # reviews_data = api.get_reviews(books.get('bookId'), mine=1)
    # reviews = WeReadParser.parse_reviews(reviews_data)
    # print(reviews)
    # for i in range(30):
    #     print(books[i]['book'].get('title'))
    # print(books[0]['book'].get('title'))
    # res = get_all_books_notes(api, books, 1)
    

