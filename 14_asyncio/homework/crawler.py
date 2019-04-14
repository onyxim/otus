import asyncio
import logging
import os
import re
import unicodedata
import urllib
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

import aiohttp
from lxml import html

from config import Config

DIR_NAME_PATTERN = r'^(\d+) .+$'
'''Regex для поиска id в спарсенной директории'''
dir_name_regex = re.compile(DIR_NAME_PATTERN)


@dataclass
class NewsData:
    id: str
    path: str
    url: str
    comments: bool


def sanitize_name(name, max_length=20):
    """Sanitize filename for saving on disk"""
    name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode()
    name = re.sub(r'[^\w\s-]', '', name).strip()
    # Replace more than two space characters after each other with one space.
    name = re.sub(r'\s{2,}', ' ', name)
    name = name[:max_length]
    return name


def prepare_file_path(url: str, path: str, default_name: str, allowed_suffix: frozenset) -> str:
    """Get file name for a page from url"""
    url_path = urlsplit(url)[2]
    url_path = Path(url_path)
    suffix = url_path.suffix
    if suffix and suffix in allowed_suffix:
        file_name = url_path.name
    else:
        file_name = default_name
    return os.path.join(path, file_name)


async def get_page(session: aiohttp.ClientSession, url: str, retry_count: int):
    """Actually get page either in an encoded text or in bytes"""
    logging.debug('Trying to get link: %s', url)
    n = 1
    while n <= retry_count:
        try:
            async with session.get(url) as response:
                return_value = await response.read()
        except Exception as e:
            if n == retry_count:
                raise e
            logging.exception('Can\'t get page, try again.')
            await asyncio.sleep(5 * n)
            n += 1
            continue
        break
    return return_value


async def get_lxml_document(session: aiohttp.ClientSession, url, c: Config):
    """Get page and parsing it to lxml document"""
    page = await get_page(session, url, c.connection_retry_count)
    return html.document_fromstring(page.decode()), page


def save_file(path, data: bytes):
    """Actually write file on a HDD"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, mode='wb') as file:
        file.write(data)


async def async_save_file(*args):
    return await asyncio.get_running_loop().run_in_executor(None, save_file, *args)


async def get_save_page(session, url, path, default_name: str, c: Config):
    """Get and save page"""
    data = await get_page(session, url, c.connection_retry_count)

    path = prepare_file_path(url, path, default_name, c.allowed_suffixs)
    await async_save_file(path, data)


async def set_path_save_file(path: str, name: str, data: bytes):
    """Save page asynchronously in different thread"""
    path = os.path.join(path, name)
    await async_save_file(path, data)


async def parse_news_comments_urls(session: aiohttp.ClientSession, c: Config, data: NewsData):
    """Parse links from comments and plan tasks for getting it"""
    url = f'{c.url_comments_page_template}{data.id}'
    document, page = await get_lxml_document(session, url, c)
    for link in document.xpath(c.xpath_comments_page_link):
        comment_id = link.xpath(c.xpath_comments_page_comment_id)[0]
        link_url = link.xpath(c.xpath_comments_page_link_href)[0]
        dir_name = f'{c.prefix_comment_folder}{comment_id}'
        path = os.path.join(data.path, dir_name)
        asyncio.create_task(get_save_page(session, link_url, path, c.name_news_page_file, c))

    await set_path_save_file(data.path, c.name_comments_page_file, page)


async def parse_main_page(session: aiohttp.ClientSession, c: Config):
    document, page = await get_lxml_document(session, c.url_start_page, c)

    # Итерируемся по обоим строчкам со страницы
    for name_element, comment_element in zip(*[iter(document.xpath(c.xpath_start_page_trs))] * 2):
        id_ = name_element.xpath(c.xpath_start_page_news_id)[0]
        if id_ in c.existed_ids:
            continue
        dir_name = f'{id_} {sanitize_name(name_element.xpath(c.xpath_start_page_news_name)[0])}'

        url = name_element.xpath(c.xpath_start_page_news_href)[0]
        ext_url = bool(urllib.parse.urlsplit(url).netloc)

        data = NewsData(
            id_,
            os.path.join(c.out_folder, dir_name),
            url,
            bool(comment_element.xpath(c.xpath_start_page_news_comments)),
        )
        if data.comments:
            asyncio.create_task(parse_news_comments_urls(session, c, data))

        # If url is not in ycombinator, get it
        if ext_url:
            asyncio.create_task(get_save_page(session, data.url, data.path, c.name_news_page_file, c))
    logging.info('All tasks for main page planned')
    await set_path_save_file(c.out_folder, c.name_main_page_file, page)


def create_folder(c: Config):
    """Create folder if necessary from config path"""
    if c.absolute_path:
        out_dir = c.absolute_path
    else:
        module_dir = os.path.dirname(__file__)
        out_dir = os.path.join(module_dir, c.relative_path)
    os.makedirs(out_dir, exist_ok=True)
    return out_dir


def get_existed_ids(out_folder, dir_name_regex=dir_name_regex):
    """Get all existed ids from output directory."""
    result = set()
    for dir_ in os.scandir(path=out_folder):
        if dir_.is_file():
            continue
        search_result = dir_name_regex.search(dir_.name)
        if not search_result:
            continue
        result.add(search_result.group(1))
    return result


async def main(c: Config):
    c.out_folder = create_folder(c)
    c.existed_ids = get_existed_ids(c.out_folder)

    timeout = aiohttp.ClientTimeout(total=c.connection_timeout)
    conn = aiohttp.TCPConnector(limit=c.connection_limit, enable_cleanup_closed=True, force_close=True,
                                limit_per_host=c.connection_limit_per_host)
    session = aiohttp.ClientSession(connector=conn, timeout=timeout)
    while True:
        await parse_main_page(session, c)

        await asyncio.sleep(c.refresh_period)


if __name__ == "__main__":
    c = Config()
    logging.basicConfig(level=c.debug_level)
    logging.captureWarnings(True)
    asyncio.run(main(c), debug=c.asyncio_debug)
