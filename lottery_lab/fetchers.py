from __future__ import annotations

import gzip
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable

from .models import Draw, DrawPage
from .parsers import parse_dlt_page, parse_ssq_page


DLT_ENDPOINT = "https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry"
SSQ_ENDPOINT = "https://jc.zhcw.com/port/client_json.php"
DLT_REFERER = "https://static.sporttery.cn/"
SSQ_REFERER = "https://www.zhcw.com/kjxx/ssq/"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
)
TextGetter = Callable[[str, str], str]


def http_get_text(url: str, referer: str, *, timeout: float = 20.0) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json,text/plain,*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": referer,
            "User-Agent": USER_AGENT,
        },
    )
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read()
                if response.headers.get("Content-Encoding") == "gzip":
                    body = gzip.decompress(body)
                return body.decode("utf-8")
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(0.5 * (attempt + 1))
    raise RuntimeError(f"request failed after 3 attempts: {url}") from last_error


def fetch_dlt_history(*, get_text: TextGetter = http_get_text) -> list[Draw]:
    def fetch_page(page_no: int) -> DrawPage:
        query = urllib.parse.urlencode(
            {
                "gameNo": 85,
                "provinceId": 0,
                "pageSize": 100,
                "isVerify": 1,
                "pageNo": page_no,
            }
        )
        return parse_dlt_page(json.loads(get_text(f"{DLT_ENDPOINT}?{query}", DLT_REFERER)))

    return _fetch_all(fetch_page)


def fetch_ssq_history(*, get_text: TextGetter = http_get_text) -> list[Draw]:
    def fetch_page(page_no: int) -> DrawPage:
        query = urllib.parse.urlencode(
            {
                "callback": "lotteryLabCallback",
                "transactionType": "10001001",
                "lotteryId": 1,
                "issueCount": 10000,
                "startIssue": "",
                "endIssue": "",
                "startDate": "",
                "endDate": "",
                "type": 0,
                "pageNum": page_no,
                "pageSize": 300,
            }
        )
        return parse_ssq_page(get_text(f"{SSQ_ENDPOINT}?{query}", SSQ_REFERER))

    return _fetch_all(fetch_page)


def _fetch_all(fetch_page: Callable[[int], DrawPage]) -> list[Draw]:
    first = fetch_page(1)
    pages = [first]
    for page_no in range(2, first.total_pages + 1):
        page = fetch_page(page_no)
        if page.page_no != page_no:
            raise RuntimeError(f"expected page {page_no}, received page {page.page_no}")
        pages.append(page)
    unique = {draw.issue: draw for page in pages for draw in page.draws}
    if len(unique) != first.total_records:
        raise RuntimeError(
            f"incomplete history: expected {first.total_records} unique draws, got {len(unique)}"
        )
    return sorted(unique.values(), key=lambda draw: (draw.draw_date, draw.issue), reverse=True)

