"""
Scrapy Downloader Middleware - UA轮换、代理、延时、重试
"""
import random
import time
import logging
from scrapy import signals
from scrapy.downloadermiddlewares.useragent import UserAgentMiddleware
from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.utils.response import response_status_message

logger = logging.getLogger(__name__)

# User-Agent池
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
]


class RandomUserAgentMiddleware(UserAgentMiddleware):
    """随机User-Agent中间件"""

    def __init__(self, user_agent=""):
        super().__init__(user_agent)
        self.user_agents = USER_AGENTS

    def process_request(self, request, spider):
        ua = random.choice(self.user_agents)
        if ua:
            request.headers.setdefault("User-Agent", ua)
            request.headers.setdefault("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8")
            spider.logger.debug(f"使用UA: {ua[:50]}...")


class RandomDelayMiddleware:
    """随机请求延时中间件"""

    def __init__(self, min_delay=1.0, max_delay=4.0):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.last_request_time = {}

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            min_delay=getattr(crawler.settings, "MIN_DELAY", 1.0),
            max_delay=getattr(crawler.settings, "MAX_DELAY", 4.0),
        )

    def process_request(self, request, spider):
        """请求前随机延时"""
        domain = "movie.douban.com"
        now = time.time()
        if domain in self.last_request_time:
            elapsed = now - self.last_request_time[domain]
            required = random.uniform(self.min_delay, self.max_delay)
            if elapsed < required:
                time.sleep(required - elapsed)
        self.last_request_time[domain] = time.time()


class CustomRetryMiddleware(RetryMiddleware):
    """自定义重试中间件"""

    def process_response(self, request, response, spider):
        if response.status in [403, 429, 500, 502, 503]:
            reason = response_status_message(response.status)
            spider.logger.warning(
                f"触发重试 {response.status} {reason}: {request.url}"
            )
            return self._retry(request, reason, spider) or response
        return response

    def process_exception(self, request, exception, spider):
        spider.logger.warning(f"请求异常: {type(exception).__name__}: {exception}")
        return self._retry(request, exception, spider)
