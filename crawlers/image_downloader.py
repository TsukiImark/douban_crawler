"""
图片下载模块 - 下载电影海报图片，支持断点续传
"""
import os
import requests
import time
import random
from tqdm import tqdm
from config import POSTERS_DIR, REQUEST_TIMEOUT, USER_AGENTS
from utils.helpers import sanitize_filename
from utils.logger import get_logger

logger = get_logger("image_downloader")


class ImageDownloader:
    """电影海报下载器"""

    def __init__(self, output_dir=None):
        self.output_dir = output_dir or POSTERS_DIR
        os.makedirs(self.output_dir, exist_ok=True)
        self.session = requests.Session()
        self._load_cookies()
        self.downloaded_count = 0
        self.skipped_count = 0
        self.failed_count = 0

    def _load_cookies(self):
        """加载Cookie到Session"""
        import json
        cookie_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "douban_cookies.json"
        )
        if not os.path.exists(cookie_file):
            return
        try:
            # 兼容各种编码
            for enc in ["utf-8", "utf-8-sig", "gbk"]:
                try:
                    with open(cookie_file, "r", encoding=enc) as f:
                        cookies = json.load(f)
                    break
                except (UnicodeDecodeError, json.JSONDecodeError):
                    continue
            for c in cookies:
                self.session.cookies.set(
                    c["name"], str(c.get("value", "")),
                    domain=c.get("domain", ".douban.com"))
            logger.info(f"图片下载器已加载 {len(cookies)} 条Cookie")
        except Exception as e:
            logger.warning(f"Cookie加载失败: {e}")

    def get_filename(self, rank, title_cn):
        """生成规范的文件名: {rank}_{title}.jpg"""
        safe_title = sanitize_filename(title_cn)
        filename = f"{rank:03d}_{safe_title}.jpg"
        return os.path.join(self.output_dir, filename)

    def check_exists(self, filepath):
        """检查文件是否已存在（断点续传）"""
        return os.path.exists(filepath) and os.path.getsize(filepath) > 0

    def download_poster(self, url, filepath, max_retries=3):
        """
        下载单张海报
        返回: True=成功/已存在, False=失败
        """
        if not url:
            logger.warning(f"海报URL为空，跳过: {filepath}")
            self.skipped_count += 1
            return False

        if self.check_exists(filepath):
            logger.debug(f"海报已存在，跳过: {os.path.basename(filepath)}")
            self.skipped_count += 1
            return True

        for attempt in range(max_retries):
            try:
                headers = {"User-Agent": random.choice(USER_AGENTS)}
                response = self.session.get(url, headers=headers, timeout=REQUEST_TIMEOUT, stream=True)

                if response.status_code == 200:
                    with open(filepath, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    self.downloaded_count += 1
                    logger.debug(f"下载完成: {os.path.basename(filepath)}")
                    return True
                elif response.status_code == 404:
                    logger.warning(f"海报404: {url}")
                    self.failed_count += 1
                    return False
                else:
                    logger.warning(f"海报下载失败 ({response.status_code}) 尝试 {attempt+1}/{max_retries}: {url}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
            except requests.exceptions.Timeout:
                logger.warning(f"海报下载超时 尝试 {attempt+1}/{max_retries}: {url}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
            except Exception as e:
                logger.error(f"海报下载异常: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)

        self.failed_count += 1
        logger.error(f"海报下载最终失败: {url}")
        return False

    def download_all(self, movies, show_progress=True):
        """
        批量下载所有电影海报
        movies: list[dict] 包含 rank, title_cn, poster_url
        """
        logger.info(f"开始下载海报，共 {len(movies)} 部电影...")
        self.downloaded_count = 0
        self.skipped_count = 0
        self.failed_count = 0

        iterator = tqdm(movies, desc="下载海报") if show_progress else movies

        for movie in iterator:
            poster_url = movie.get("poster_url", "")
            if not poster_url:
                poster_url = movie.get("poster_path", "")

            rank = movie.get("rank", 0)
            title = movie.get("title_cn", f"movie_{rank}")

            filepath = self.get_filename(rank, title)
            success = self.download_poster(poster_url, filepath)

            if success and not self.check_exists(filepath):
                movie["poster_path"] = filepath

            time.sleep(random.uniform(0.3, 1.0))

        logger.info(
            f"海报下载完成: 下载={self.downloaded_count}, "
            f"跳过={self.skipped_count}, 失败={self.failed_count}"
        )
        return {
            "downloaded": self.downloaded_count,
            "skipped": self.skipped_count,
            "failed": self.failed_count,
        }

    def get_poster_path(self, rank, title_cn):
        """根据排名和标题获取海报路径（用于断点续传检查）"""
        filepath = self.get_filename(rank, title_cn)
        if self.check_exists(filepath):
            return filepath
        return None

    def close(self):
        """关闭session"""
        self.session.close()
