"""
Scrapy Spider - 豆瓣电影Top250爬虫（完整Scrapy框架实现）
包含：列表页 → 详情页 的逐级爬取逻辑
"""
import re
import scrapy
from scrapy_version.douban_scrapy.items import DoubanMovieItem, CommentItem


class DoubanTop250Spider(scrapy.Spider):
    """豆瓣电影Top250 Scrapy Spider"""

    name = "douban_top250"
    allowed_domains = ["movie.douban.com", "douban.com"]
    start_urls = ["https://movie.douban.com/top250"]

    custom_settings = {
        "CONCURRENT_REQUESTS": 2,
        "DOWNLOAD_DELAY": 2,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.movie_count = 0
        self.comment_count = 0

    def start_requests(self):
        """生成10页列表请求"""
        for page in range(10):
            start = page * 25
            url = f"https://movie.douban.com/top250?start={start}&filter="
            yield scrapy.Request(
                url,
                callback=self.parse_list,
                meta={"page": page + 1},
                dont_filter=True,
            )

    def parse_list(self, response):
        """解析列表页"""
        page = response.meta.get("page", 1)
        self.logger.info(f"正在解析第{page}页: {response.url}")

        items = response.css("div.item")

        for item in items:
            movie = DoubanMovieItem()

            # 排名
            rank_text = item.css("em::text").get()
            movie["rank"] = int(rank_text) if rank_text else 0

            # 标题
            titles = item.css("span.title::text").getall()
            movie["title_cn"] = titles[0].strip() if len(titles) > 0 else ""
            movie["title_en"] = titles[1].strip("/ ").strip() if len(titles) > 1 else ""

            # 评分
            rating_text = item.css("span.rating_num::text").get()
            try:
                movie["rating"] = float(rating_text.strip()) if rating_text else 0.0
            except ValueError:
                movie["rating"] = 0.0

            # 评价人数
            count_text = item.css("div.star span:last-child::text").get()
            if count_text:
                count_text = count_text.replace("人评价", "").strip()
                if "万" in count_text:
                    movie["rating_count"] = int(float(count_text.replace("万", "")) * 10000)
                else:
                    try:
                        movie["rating_count"] = int(count_text)
                    except ValueError:
                        movie["rating_count"] = 0

            # 导演 & 主演
            p_text = item.css("div.bd p::text").get()
            if p_text:
                lines = [l.strip() for l in p_text.split("\n") if l.strip()]
                for line in lines:
                    if "导演" in line:
                        movie["director"] = re.sub(r'导演[:\s]*', '', line).strip()
                    if "主演" in line:
                        movie["actors"] = re.sub(r'主演[:\s]*', '', line).strip()

            # 简介
            movie["summary"] = item.css("span.inq::text").get("").strip()

            # 详情链接
            detail_url = item.css("a::attr(href)").get()
            movie["detail_url"] = detail_url or ""

            self.movie_count += 1

            # 请求详情页（获取年份/片长/类型/IMDb/海报）
            if detail_url:
                yield scrapy.Request(
                    detail_url,
                    callback=self.parse_detail,
                    meta={"movie": movie},
                    dont_filter=True,
                )
            else:
                yield movie

        self.logger.info(f"第{page}页解析完成")

    def parse_detail(self, response):
        """解析详情页 - 获取额外信息"""
        movie = response.meta["movie"]

        # info区域文本
        info_text = response.css("#info::text").getall()
        info_str = " ".join([t.strip() for t in info_text if t.strip()])
        # 同时获取链接文本
        for attr in response.css("#info span.attrs"):
            info_str += " " + attr.css("::text").getall()[0] if attr.css("::text").getall() else ""

        # 完整info
        full_info = response.css("#info").get() or ""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(full_info, "lxml")
        clean_info = soup.get_text("\n", strip=False)

        # 提取年份
        year_match = re.search(r'(\d{4})', clean_info)
        if year_match:
            movie["release_year"] = int(year_match.group(1))

        # 片长
        runtime_match = re.search(r'片长[:\s]*([^\n]+)', clean_info)
        if runtime_match:
            movie["runtime"] = runtime_match.group(1).strip()

        # 类型
        genre_spans = response.css("#info span[property='v:genre']::text").getall()
        if genre_spans:
            movie["genre"] = " / ".join(genre_spans)

        # IMDb
        imdb_match = re.search(r'IMDb[:\s]*([\d.]+)', clean_info)
        if imdb_match:
            try:
                movie["imdb_rating"] = float(imdb_match.group(1))
            except ValueError:
                movie["imdb_rating"] = 0.0

        # 海报URL
        poster_url = response.css("#mainpic img::attr(src)").get()
        if poster_url:
            movie["poster_url"] = poster_url

        yield movie

        # 生成短评页面请求
        rank = movie.get("rank", 0)
        comments_url = response.url.rstrip("/") + "comments?status=P"
        yield scrapy.Request(
            comments_url,
            callback=self.parse_comments,
            meta={"movie_rank": rank},
            dont_filter=True,
        )

    def parse_comments(self, response):
        """解析短评页"""
        movie_rank = response.meta["movie_rank"]

        comment_items = response.css(".comment-item")
        for item in comment_items[:20]:  # 每页取20条
            comment = CommentItem()
            comment["movie_rank"] = movie_rank
            comment["commenter"] = item.css(".comment-info a::text").get("").strip()
            comment["content"] = item.css(".comment-content span::text").get("").strip()
            comment["comment_time"] = item.css(".comment-time::text").get("").strip()

            # 评分 (通过class解析)
            rating_class = item.css(".comment-info .rating::attr(class)").get() or ""
            rating_map = {
                "allstar50": "5星", "allstar45": "4.5星", "allstar40": "4星",
                "allstar35": "3.5星", "allstar30": "3星", "allstar25": "2.5星",
                "allstar20": "2星", "allstar15": "1.5星", "allstar10": "1星",
                "allstar05": "0.5星",
            }
            stars = "未评分"
            for cls, star_text in rating_map.items():
                if cls in rating_class:
                    stars = star_text
                    break
            comment["rating"] = stars

            if comment.get("content"):
                self.comment_count += 1
                yield comment

    def closed(self, reason):
        """爬虫关闭时输出统计"""
        self.logger.info("=" * 50)
        self.logger.info(f"Scrapy爬虫关闭: {reason}")
        self.logger.info(f"共爬取电影: {self.movie_count} 部")
        self.logger.info(f"共爬取短评: {self.comment_count} 条")
        self.logger.info("=" * 50)
