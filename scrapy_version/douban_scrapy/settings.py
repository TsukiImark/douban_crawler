"""
Scrapy settings for douban_scrapy project
"""
import os

BOT_NAME = "douban_scrapy"
SPIDER_MODULES = ["scrapy_version.douban_scrapy.spiders"]
NEWSPIDER_MODULE = "scrapy_version.douban_scrapy.spiders"

# ==================== 礼貌爬取设置 ====================
ROBOTSTXT_OBEY = True

# 并发请求数
CONCURRENT_REQUESTS = 2
CONCURRENT_REQUESTS_PER_DOMAIN = 1

# 下载延时
DOWNLOAD_DELAY = 2.0
RANDOMIZE_DOWNLOAD_DELAY = True

# 自动限速 (AutoThrottle)
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 2.0
AUTOTHROTTLE_MAX_DELAY = 10.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0

# ==================== 中间件 ====================
DOWNLOADER_MIDDLEWARES = {
    "scrapy_version.douban_scrapy.middlewares.RandomUserAgentMiddleware": 400,
    "scrapy_version.douban_scrapy.middlewares.RandomDelayMiddleware": 450,
    "scrapy_version.douban_scrapy.middlewares.CustomRetryMiddleware": 500,
    "scrapy.downloadermiddlewares.retry.RetryMiddleware": None,
}

# ==================== Pipeline ====================
ITEM_PIPELINES = {
    "scrapy_version.douban_scrapy.pipelines.SQLitePipeline": 300,
    "scrapy_version.douban_scrapy.pipelines.CsvPipeline": 500,
    "scrapy_version.douban_scrapy.pipelines.JsonPipeline": 600,
}

# ==================== 重试设置 ====================
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [403, 429, 500, 502, 503, 504, 408]

# ==================== 请求头 ====================
DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# ==================== 超时 ====================
DOWNLOAD_TIMEOUT = 15

# ==================== 日志 ====================
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"

# ==================== 数据库路径 ====================
SQLITE_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "douban_scrapy.db",
)
CSV_OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "output", "data",
)
JSON_OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "output", "data",
)

# ==================== 延时范围 ====================
MIN_DELAY = 1.0
MAX_DELAY = 4.0

# ==================== 其他 ====================
REDIRECT_ENABLED = True
COOKIES_ENABLED = True
TELNETCONSOLE_ENABLED = False
