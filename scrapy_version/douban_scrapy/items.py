"""
Scrapy Item 定义 - 电影和短评数据结构
"""
import scrapy


class DoubanMovieItem(scrapy.Item):
    """电影基本信息Item"""
    rank = scrapy.Field()
    title_cn = scrapy.Field()
    title_en = scrapy.Field()
    rating = scrapy.Field()
    rating_count = scrapy.Field()
    director = scrapy.Field()
    actors = scrapy.Field()
    summary = scrapy.Field()
    detail_url = scrapy.Field()
    # 详情页额外字段
    release_year = scrapy.Field()
    runtime = scrapy.Field()
    genre = scrapy.Field()
    imdb_rating = scrapy.Field()
    poster_url = scrapy.Field()
    poster_path = scrapy.Field()


class CommentItem(scrapy.Item):
    """短评Item"""
    movie_rank = scrapy.Field()
    commenter = scrapy.Field()
    rating = scrapy.Field()
    content = scrapy.Field()
    comment_time = scrapy.Field()

    # 关联字段（Pipeline中通过movie_rank查找movie_id）
    movie_id = scrapy.Field()
