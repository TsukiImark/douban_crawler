"""
通用工具函数
"""
import re
import time
import random
from config import USER_AGENTS, MIN_DELAY, MAX_DELAY


def clean_text(text):
    """清洗文本：去除多余空白和换行"""
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_count(text):
    """解析人数文本（如 '129.5万' -> 1295000）"""
    if not text:
        return 0
    text = text.strip()
    if "万" in text:
        num = float(text.replace("万", ""))
        return int(num * 10000)
    try:
        return int(text)
    except ValueError:
        return 0


def parse_rating(text):
    """解析评分，返回float"""
    if not text:
        return 0.0
    try:
        return float(text.strip())
    except ValueError:
        return 0.0


def random_delay(min_s=None, max_s=None):
    """随机延时"""
    if min_s is None:
        min_s = MIN_DELAY
    if max_s is None:
        max_s = MAX_DELAY
    delay = random.uniform(min_s, max_s)
    time.sleep(delay)


def get_random_ua():
    """获取随机User-Agent"""
    return random.choice(USER_AGENTS)


def get_random_referer():
    """获取随机Referer"""
    referers = [
        "https://www.google.com/",
        "https://www.baidu.com/",
        "https://movie.douban.com/",
        "https://www.bing.com/",
        "https://www.douban.com/",
    ]
    return random.choice(referers)


def sanitize_filename(name):
    """清理文件名中的非法字符"""
    return re.sub(r'[\\/:*?"<>|]', "_", name)
