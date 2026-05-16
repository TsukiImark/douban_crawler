"""
全局配置文件 - 豆瓣电影Top250爬虫系统
"""
import os
import logging

# ==================== 项目路径 ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
DATA_DIR = os.path.join(OUTPUT_DIR, "data")
CHARTS_DIR = os.path.join(OUTPUT_DIR, "charts")
LOGS_DIR = os.path.join(OUTPUT_DIR, "logs")
POSTERS_DIR = os.path.join(BASE_DIR, "posters")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CHARTS_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(POSTERS_DIR, exist_ok=True)

# ==================== 数据库配置 ====================
# SQLite (默认)
SQLITE_PATH = os.path.join(BASE_DIR, "douban_movies.db")

# MySQL (可选 - 需要先创建数据库)
MYSQL_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "88888888",
    "database": "douban_movies",
    "charset": "utf8mb4",
}

# 当前使用数据库类型: "sqlite" 或 "mysql"
DB_TYPE = "sqlite"

# ==================== 豆瓣电影URL ====================
DOUBAN_TOP250 = "https://movie.douban.com/top250"
DOUBAN_TOP250_PATTERN = "https://movie.douban.com/top250?start={start}&filter="

# ==================== 请求配置 ====================
# 请求延时范围 (秒)
MIN_DELAY = 1.0
MAX_DELAY = 4.0

# Selenium 爬取速度 (秒) — 弹验证去Chrome窗口手动过
LIST_PAGE_LOAD_WAIT = (1.0, 1.5)      # 列表页加载后等待
BETWEEN_LIST_PAGES = (1.0, 2.0)       # 列表页之间等待
DETAIL_PAGE_LOAD_WAIT = (0.5, 1.0)    # 详情页加载后等待
BETWEEN_DETAIL_PAGES = (0.5, 1.0)     # 详情页之间等待
COMMENTS_PAGE_LOAD_WAIT = (1.5, 2.5)  # 短评页加载后等待（需要等页面渲染）
BETWEEN_COMMENTS = (0.3, 0.6)         # 短评之间等待

# 最大重试次数
MAX_RETRIES = 3

# 重试退避基数 (秒)
RETRY_BACKOFF = 2.0

# 请求超时 (秒)
REQUEST_TIMEOUT = 15

# 每页电影数量
PER_PAGE = 25
TOTAL_PAGES = 10

# ==================== User-Agent池 ====================
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OPR/106.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
]

# ==================== 代理IP池 ====================
# 免费代理IP（可从 https://www.zdaye.com/ 等获取，需要定期更新）
# 格式: "http://ip:port"
PROXY_POOL = [
    # 以下为示例，实际使用时需要替换为有效代理
    # "http://127.0.0.1:8080",
]

# 是否启用代理
USE_PROXY = False

# ==================== Selenium配置 ====================
SELENIUM_HEADLESS = True
SELENIUM_TIMEOUT = 15
SELENIUM_IMPLICIT_WAIT = 10
# ChromeDriver路径 (None = 自动检测PATH)
import os as _os
CHROMEDRIVER_PATH = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "chromedriver.exe")

# ==================== 短评爬取配置 ====================
MIN_COMMENTS_PER_MOVIE = 15
MAX_COMMENTS_PER_MOVIE = 50
COMMENT_LOAD_MORE_CLICKS = 2

# ==================== 日志配置 ====================
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE = os.path.join(LOGS_DIR, "crawler.log")
LOG_FILE_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5

# ==================== 数据分析配置 ====================
# matplotlib中文字体
MATPLOTLIB_FONT = "SimHei"  # Windows: SimHei, macOS: Arial Unicode MS, Linux: WenQuanYi Micro Hei

# 词云配置
WORDCLOUD_FONT_PATH = None  # None = 使用系统默认
WORDCLOUD_WIDTH = 800
WORDCLOUD_HEIGHT = 500
WORDCLOUD_MAX_WORDS = 100
