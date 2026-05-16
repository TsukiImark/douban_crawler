"""
requests爬虫模块 - 基于requests + BeautifulSoup的列表页+详情页爬虫
负责：排名、标题（中英）、评分、评价人数、导演/主演、简介、详情链接、详情页信息
"""
import re
import time
from bs4 import BeautifulSoup
from tqdm import tqdm
from crawlers.anti_spider import AntiSpiderManager
from utils.helpers import clean_text, parse_count, parse_rating
from utils.logger import get_logger

logger = get_logger("request_crawler")


class DoubanRequestsCrawler:
    """豆瓣电影Top250 requests爬虫"""

    BASE_URL = "https://movie.douban.com/top250"

    def __init__(self):
        self.anti_spider = AntiSpiderManager()
        self.anti_spider.check_robots()

    def crawl_list_page(self, start):
        """
        爬取单页列表
        start: 起始序号 (0, 25, 50, ...)
        返回: list[dict] 该页所有电影基本数据，以及列表页URL
        """
        url = f"{self.BASE_URL}?start={start}&filter="
        logger.info(f"爬取列表页: start={start}")

        response = self.anti_spider.request_with_retry(url)
        if not response:
            logger.error(f"列表页爬取失败: start={start}")
            return [], url

        soup = BeautifulSoup(response.text, "lxml")
        items = soup.find_all("div", class_="item")
        movies = []

        for item in items:
            try:
                movie = self._parse_list_item(item)
                if movie:
                    movies.append(movie)
            except Exception as e:
                logger.warning(f"解析列表项异常: {e}")

        logger.info(f"列表页 start={start} 解析完成，获得 {len(movies)} 部电影")
        return movies, url

    def _parse_list_item(self, item):
        """解析单个列表项"""
        movie = {}

        # 排名
        em = item.find("em")
        if em:
            movie["rank"] = int(em.text.strip())

        # 标题 (中文 + 英文)
        title_spans = item.find_all("span", class_="title")
        movie["title_cn"] = title_spans[0].text.strip() if len(title_spans) > 0 else ""
        movie["title_en"] = ""
        if len(title_spans) > 1:
            en_title = title_spans[1].text.strip()
            movie["title_en"] = en_title.strip("/ ")

        # 其他名称
        other = item.find("span", class_="other")
        if other and not movie["title_en"]:
            movie["title_en"] = other.text.strip("/ ")

        # 评分
        rating_span = item.find("span", class_="rating_num")
        movie["rating"] = parse_rating(rating_span.text) if rating_span else 0.0

        # 评价人数
        rating_people = item.find("div", class_="star")
        if rating_people:
            count_text = rating_people.find_all("span")[-1].text if rating_people.find_all("span") else ""
            movie["rating_count"] = parse_count(count_text)
        else:
            movie["rating_count"] = 0

        # 导演 & 主演
        bd = item.find("div", class_="bd")
        p_tag = bd.find("p", class_="") if bd else None
        movie["director"] = ""
        movie["actors"] = ""
        if p_tag:
            text = p_tag.get_text(strip=True)
            # 解析 "导演: xxx 主演: xxx"
            parts = re.split(r'[一-龥]{2,}:\s*', text)
            lines = p_tag.get_text("\n", strip=False).split("\n")
            for line in lines:
                line = line.strip()
                if "导演" in line:
                    movie["director"] = re.sub(r'导演[:\s]*', '', line).strip()
                if "主演" in line:
                    movie["actors"] = re.sub(r'主演[:\s]*', '', line).strip()

        # 简介
        quote = item.find("span", class_="inq")
        movie["summary"] = quote.text.strip() if quote else ""

        # 详情链接
        link = item.find("a")
        movie["detail_url"] = link["href"] if link and link.get("href") else ""

        # 初始化详情页字段
        movie["release_year"] = None
        movie["runtime"] = ""
        movie["genre"] = ""
        movie["imdb_rating"] = 0.0
        movie["poster_path"] = ""

        return movie

    def crawl_detail_page(self, detail_url, referer=None):
        """
        爬取电影详情页，提取：
        上映年份、片长、类型、IMDb评分
        """
        if not detail_url:
            return {}

        logger.debug(f"爬取详情页: {detail_url}")
        headers = self.anti_spider.get_random_headers(referer=referer or "https://movie.douban.com/top250")
        response = self.anti_spider.request_with_retry(detail_url, headers=headers)
        if not response:
            logger.warning(f"详情页爬取失败: {detail_url}")
            return {}

        soup = BeautifulSoup(response.text, "lxml")
        info = {}
        raw_html_snippet = response.text[:500]

        # 检测是否是验证页面
        if "验证" in response.text and len(response.text) < 2000:
            logger.warning(f"详情页疑似验证页面: {detail_url}")
            return info

        # 方案1: 使用CSS选择器精确提取（优先）
        # 年份
        year_el = soup.select_one('span[property="v:initialReleaseDate"]')
        if year_el:
            year_match = re.search(r'(\d{4})', year_el.get("content", ""))
            if year_match:
                info["release_year"] = int(year_match.group(1))

        # 片长
        runtime_el = soup.select_one('span[property="v:runtime"]')
        if runtime_el:
            info["runtime"] = runtime_el.get("content", "").strip()

        # 类型 (使用property标签)
        genre_els = soup.select('span[property="v:genre"]')
        if genre_els:
            info["genre"] = " / ".join([g.text.strip() for g in genre_els])

        # 方案2: 如果CSS选择器没提取到，回退到info区域文本解析
        info_box = soup.find("div", id="info")
        if info_box:
            info_text = info_box.get_text("\n", strip=False)

            if not info.get("release_year"):
                date_match = re.search(r'上映日期[:\s]*(.+)', info_text)
                if date_match:
                    year_match = re.search(r'(\d{4})', date_match.group(1))
                    if year_match:
                        info["release_year"] = int(year_match.group(1))

            if not info.get("runtime"):
                runtime_match = re.search(r'片长[:\s]*([^\n]+)', info_text)
                if runtime_match:
                    info["runtime"] = runtime_match.group(1).strip().split("\n")[0].strip()

            if not info.get("genre"):
                genre_match = re.search(r'类型[:\s]*([^\n]+)', info_text)
                if genre_match:
                    info["genre"] = genre_match.group(1).strip().split("\n")[0].strip()

            # IMDb评分 (仅在info区域中)
            imdb_match = re.search(r'IMDb[:\s]*([\d.]+)', info_text)
            if imdb_match:
                try:
                    info["imdb_rating"] = float(imdb_match.group(1))
                except ValueError:
                    pass

        # 海报URL (多种方式查找)
        poster_img = soup.select_one("#mainpic img")
        if poster_img:
            info["poster_url"] = poster_img.get("src") or poster_img.get("data-src") or ""

        return info

    def crawl_all(self, pages=10):
        """
        爬取全部10页（250部电影）基本信息和详情
        返回: list[dict]
        """
        all_movies = []
        page_urls = {}  # 记录每部电影来自哪个列表页（用作referer）
        logger.info("=" * 50)
        logger.info("开始爬取豆瓣电影Top250 (requests版本)")
        logger.info("=" * 50)

        for page in tqdm(range(pages), desc="爬取列表页"):
            start = page * 25
            movies, list_url = self.crawl_list_page(start)
            for m in movies:
                page_urls[m.get("rank")] = list_url
            all_movies.extend(movies)
            if page < pages - 1:
                self.anti_spider.random_delay()

        logger.info(f"列表页爬取完成，共 {len(all_movies)} 部电影")

        # 爬取详情页（带referer防盗链）
        logger.info("开始爬取详情页...")
        for i, movie in enumerate(tqdm(all_movies, desc="爬取详情页")):
            if movie.get("detail_url"):
                referer = page_urls.get(movie.get("rank"), "https://movie.douban.com/top250")
                detail_info = self.crawl_detail_page(movie["detail_url"], referer=referer)
                movie.update(detail_info)
                if detail_info:
                    logger.debug(f"详情页成功: {movie.get('title_cn', '')} -> "
                                f"年份={detail_info.get('release_year')}, "
                                f"类型={detail_info.get('genre')}, "
                                f"IMDb={detail_info.get('imdb_rating')}")
            if i < len(all_movies) - 1:
                self.anti_spider.random_delay()

        success_count = sum(1 for m in all_movies if m.get("release_year"))
        logger.info(f"详情页爬取完成: {success_count}/{len(all_movies)} 成功")
        return all_movies

    def close(self):
        """关闭session"""
        self.anti_spider.close()
