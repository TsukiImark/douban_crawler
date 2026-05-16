"""
反爬虫策略模块 - UA池、代理池、Cookie管理、robots.txt检查、重试机制
"""
import time
import random
import re
import json
import os
import requests
from urllib.robotparser import RobotFileParser
from config import (
    USER_AGENTS, PROXY_POOL, USE_PROXY,
    MIN_DELAY, MAX_DELAY, MAX_RETRIES, RETRY_BACKOFF, REQUEST_TIMEOUT,
    DOUBAN_TOP250
)
from utils.logger import get_logger

logger = get_logger("anti_spider")


class AntiSpiderManager:
    """反爬虫策略管理器"""

    def __init__(self):
        self.ua_pool = USER_AGENTS
        self.proxy_pool = PROXY_POOL
        self.proxy_index = 0
        self.session = requests.Session()
        self.robots_checked = False
        self.robots_allowed = True
        self.crawl_delay = 3.0
        self._warmed_up = False
        # 尝试加载浏览器Cookie
        self.load_cookies_from_file()

    # ==================== Session预热 (获取Cookie) ====================
    def load_cookies_from_file(self, filepath=None):
        """从JSON文件加载浏览器导出的Cookie到Session"""
        if filepath is None:
            filepath = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "douban_cookies.json"
            )

        if not os.path.exists(filepath):
            logger.info(f"Cookie文件不存在: {filepath}，将使用无Cookie模式")
            return False

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                cookies = json.load(f)

            for cookie in cookies:
                self.session.cookies.set(
                    cookie["name"],
                    cookie.get("value", ""),
                    domain=cookie.get("domain", ".douban.com"),
                )

            self._warmed_up = True
            logger.info(f"成功加载 {len(cookies)} 条Cookie: {[c['name'] for c in cookies]}")
            return True
        except Exception as e:
            logger.error(f"Cookie文件加载失败: {e}")
            return False

    def warmup_session(self):
        """首次访问豆瓣首页，获取必需的Cookie（如bid）"""
        if self._warmed_up:
            return True

        logger.info("正在预热Session，获取初始Cookie...")
        try:
            headers = self.get_random_headers(referer="https://www.douban.com/")
            resp = self.session.get(
                "https://www.douban.com/",
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
            logger.info(f"首页预热完成，状态码: {resp.status_code}, "
                        f"获得Cookie: {dict(self.session.cookies)}")

            resp2 = self.session.get(
                "https://movie.douban.com/",
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
            logger.info(f"电影首页预热完成，状态码: {resp2.status_code}")

            self._warmed_up = True
            return True
        except Exception as e:
            logger.warning(f"Session预热失败: {e}")
            self._warmed_up = True  # 继续尝试
            return False

    def _is_blocked(self, response):
        """检测是否被反爬拦截（返回了验证页面而非正常内容）"""
        if response.status_code != 200:
            return True
        text = response.text.lower()
        block_indicators = [
            "检测到有异常请求",
            "请验证以下问题",
            "请输入验证码",
            "access denied",
            "permission denied",
        ]
        for indicator in block_indicators:
            if indicator in text:
                logger.warning(f"检测到反爬拦截: 页面包含 '{indicator}'")
                return True
        if len(response.text) < 500:
            logger.warning(f"检测到异常短页面: {len(response.text)} 字符")
            return True
        return False

    # ==================== User-Agent管理 ====================
    def get_random_ua(self):
        """获取随机User-Agent"""
        return random.choice(self.ua_pool)

    def get_random_headers(self, referer=None):
        """生成随机请求头"""
        if referer is None:
            referer = "https://movie.douban.com/"
        headers = {
            "User-Agent": self.get_random_ua(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Referer": referer,
            "Cache-Control": "max-age=0",
        }
        return headers

    # ==================== 代理IP管理 ====================
    def get_proxy(self):
        """轮询获取代理IP"""
        if not USE_PROXY or not self.proxy_pool:
            return None
        proxy = self.proxy_pool[self.proxy_index % len(self.proxy_pool)]
        self.proxy_index += 1
        return {"http": proxy, "https": proxy}

    def fetch_free_proxies(self, count=10):
        """从免费代理API获取代理IP列表"""
        proxy_apis = [
            "https://proxylist.geonode.com/api/proxy-list?limit=20&page=1&sort_by=lastChecked&sort_type=desc",
        ]
        new_proxies = []
        for api_url in proxy_apis:
            try:
                resp = requests.get(api_url, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("data", [])[:count]:
                        ip = item.get("ip")
                        port = item.get("port")
                        if ip and port:
                            proxy_url = f"http://{ip}:{port}"
                            new_proxies.append(proxy_url)
                if len(new_proxies) >= count:
                    break
            except Exception as e:
                logger.debug(f"获取代理失败: {api_url}, {e}")

        if new_proxies:
            self.proxy_pool.extend(new_proxies)
            logger.info(f"成功获取 {len(new_proxies)} 个免费代理IP")
        return new_proxies

    # ==================== Robots.txt检查 ====================
    def check_robots(self, url=DOUBAN_TOP250):
        """检查robots.txt规则，记录允许/禁止的路径"""
        try:
            rp = RobotFileParser()
            rp.set_url("https://movie.douban.com/robots.txt")
            rp.read()
            self.robots_checked = True
            self.robots_allowed = rp.can_fetch("*", url)
            if rp.crawl_delay("*"):
                self.crawl_delay = max(self.crawl_delay, rp.crawl_delay("*"))

            logger.info(f"robots.txt检查完成: 允许爬取={self.robots_allowed}, "
                        f"爬取延时={self.crawl_delay}s")

            # 记录详细信息到日志文件
            logger.info("=== Robots.txt 遵守情况 ===")
            logger.info(f"站点: movie.douban.com")
            logger.info(f"User-Agent: *")
            logger.info(f"允许爬取 Top250: {self.robots_allowed}")
            logger.info(f"建议延时: {self.crawl_delay}s")
            logger.info("实际遵守: 延时1-4s随机, 仅爬取公开数据, 不登录, 不过度请求")
            logger.info("=========================")
        except Exception as e:
            logger.warning(f"无法获取robots.txt: {e}")
            self.robots_allowed = True

        return self.robots_allowed

    # ==================== 请求重试机制 ====================
    def request_with_retry(self, url, headers=None, timeout=None, max_retries=None):
        """
        带重试机制的HTTP GET请求
        支持指数退避，针对403/429/5xx自动重试
        """
        if max_retries is None:
            max_retries = MAX_RETRIES
        if timeout is None:
            timeout = REQUEST_TIMEOUT

        # 首次请求前预热Session获取Cookie
        if not self._warmed_up:
            self.warmup_session()

        for attempt in range(max_retries + 1):
            try:
                if headers is None:
                    headers = self.get_random_headers()

                proxies = self.get_proxy()

                response = self.session.get(
                    url,
                    headers=headers,
                    timeout=timeout,
                    proxies=proxies,
                )

                # 检查状态码
                if response.status_code == 200:
                    # 进一步检查是否被反爬拦截（返回验证页面）
                    if self._is_blocked(response):
                        logger.warning(f"页面被反爬拦截 (尝试 {attempt+1}/{max_retries+1}): {url}")
                        if attempt < max_retries:
                            headers = self.get_random_headers()
                            wait = RETRY_BACKOFF ** (attempt + 2) + random.uniform(3, 6)
                            logger.info(f"拦截重试等待 {wait:.1f}s")
                            time.sleep(wait)
                            self.warmup_session()  # 重新获取Cookie
                            continue
                    return response

                elif response.status_code == 403:
                    logger.warning(f"403 Forbidden (尝试 {attempt+1}/{max_retries+1}): {url}")
                    if attempt < max_retries:
                        # 换UA，换代理，增加等待
                        headers = self.get_random_headers()
                        wait = RETRY_BACKOFF ** (attempt + 1) + random.uniform(1, 3)
                        logger.info(f"403重试等待 {wait:.1f}s")
                        time.sleep(wait)

                elif response.status_code == 429:
                    logger.warning(f"429 Too Many Requests (尝试 {attempt+1}/{max_retries+1})")
                    if attempt < max_retries:
                        wait = RETRY_BACKOFF ** (attempt + 2) + random.uniform(2, 5)
                        logger.info(f"429重试等待 {wait:.1f}s")
                        time.sleep(wait)
                        headers = self.get_random_headers()

                elif response.status_code >= 500:
                    logger.warning(f"{response.status_code} Server Error (尝试 {attempt+1}/{max_retries+1})")
                    if attempt < max_retries:
                        wait = RETRY_BACKOFF ** (attempt + 1) + random.uniform(1, 3)
                        logger.info(f"5xx重试等待 {wait:.1f}s")
                        time.sleep(wait)

                else:
                    logger.warning(f"未预期的状态码 {response.status_code}: {url}")

            except requests.exceptions.Timeout:
                logger.warning(f"请求超时 (尝试 {attempt+1}/{max_retries+1}): {url}")
                if attempt < max_retries:
                    time.sleep(RETRY_BACKOFF ** (attempt + 1))

            except requests.exceptions.ConnectionError as e:
                logger.warning(f"连接错误 (尝试 {attempt+1}/{max_retries+1}): {e}")
                if attempt < max_retries:
                    time.sleep(RETRY_BACKOFF ** (attempt + 1))

            except Exception as e:
                logger.error(f"请求异常 (尝试 {attempt+1}/{max_retries+1}): {type(e).__name__}: {e}")
                if attempt < max_retries:
                    time.sleep(RETRY_BACKOFF ** (attempt + 1))

        logger.error(f"请求最终失败 ({max_retries+1}次尝试): {url}")
        return None

    def random_delay(self):
        """随机延时（遵守robots.txt）"""
        delay = random.uniform(MIN_DELAY, MAX_DELAY)
        # 确保不低于robots.txt要求的延时
        if hasattr(self, "crawl_delay"):
            delay = max(delay, self.crawl_delay)
        time.sleep(delay)

    def close(self):
        """关闭session"""
        self.session.close()
