import logging
from dataclasses import dataclass


@dataclass
class Config:
    connection_limit: int = 100
    connection_limit_per_host: int = 1
    connection_timeout: int = 30
    """in seconds"""
    connection_retry_count: int = 3
    """Count attempts before backoff"""
    refresh_period: int = 600
    """A period before check news"""
    relative_path: str = 'ycombinator'
    """Path to out folder. May be relative to the script path."""
    absolute_path: str = None
    out_folder: str = None
    existed_ids: set = None
    debug_level: int = logging.DEBUG
    asyncio_debug: bool = False

    # ######################### NAMES
    prefix_comment_folder: str = 'comment_'
    name_comments_page_file: str = 'comments.html'
    name_main_page_file: str = 'main.html'
    name_news_page_file: str = 'page.html'
    allowed_suffixs: frozenset = frozenset(('.html', '.pdf', '.htm'))

    # ######################### URLS
    url_start_page: str = 'https://news.ycombinator.com'
    url_comments_page_template: str = f'{url_start_page}/item?id='

    # ######################### XPATHs
    TR_PATH = '//tr[@class="athing"]'
    # использую union для поиска обоих элементов на странице
    xpath_start_page_trs: str = f'{TR_PATH} | {TR_PATH}/following::tr[1]'
    xpath_start_page_news_id: str = '@id'
    xpath_start_page_news_href: str = '(*//a)[2]/@href'
    xpath_start_page_news_name: str = '(*//a)[2]/text()'
    xpath_start_page_news_comments: str = '(*//a)[4][contains(text(),\'comments\')]'
    xpath_comments_page_link: str = '//table[@class="comment-tree"]//tr[@class="athing comtr "]//a[@rel="nofollow"]'
    xpath_comments_page_comment_id: str = 'ancestor::tr[@class="athing comtr "]/@id'
    xpath_comments_page_link_href: str = '@href'
