"""
数据分析模块 - 统计分析：Top10、导演/类型分布、评分相关性
"""
import pandas as pd
import numpy as np
from collections import Counter
from utils.logger import get_logger

logger = get_logger("data_analyzer")


class DataAnalyzer:
    """数据分析器"""

    def __init__(self, movies_df, comments_df):
        self.movies_df = movies_df
        self.comments_df = comments_df

    def get_basic_stats(self):
        """获取基本统计信息"""
        stats = {
            "movie_count": len(self.movies_df),
            "comment_count": len(self.comments_df),
            "avg_rating": round(self.movies_df["rating"].mean(), 2),
            "max_rating": self.movies_df["rating"].max(),
            "min_rating": self.movies_df["rating"].min(),
            "median_rating": round(self.movies_df["rating"].median(), 2),
            "avg_rating_count": int(self.movies_df["rating_count"].mean()),
            "total_rating_count": int(self.movies_df["rating_count"].sum()),
            "avg_imdb": round(self.movies_df[self.movies_df["imdb_rating"] > 0]["imdb_rating"].mean(), 2)
            if "imdb_rating" in self.movies_df.columns else 0,
        }
        return stats

    def get_top10_movies(self):
        """获取评分最高的10部电影"""
        top10 = self.movies_df.nlargest(10, "rating")[
            ["rank", "title_cn", "rating", "rating_count", "director"]
        ].copy()
        top10["rating"] = top10["rating"].apply(lambda x: f"{x:.1f}")
        top10["rating_count"] = top10["rating_count"].apply(lambda x: f"{x:,}")
        return top10.to_dict(orient="records")

    def get_rating_distribution(self):
        """评分分布统计"""
        bins = [0, 6.0, 7.0, 7.5, 8.0, 8.5, 9.0, 9.5, 10.0]
        labels = ["<6.0", "6.0-7.0", "7.0-7.5", "7.5-8.0", "8.0-8.5", "8.5-9.0", "9.0-9.5", "9.5-10"]
        self.movies_df["rating_bin"] = pd.cut(self.movies_df["rating"], bins=bins, labels=labels)
        dist = self.movies_df["rating_bin"].value_counts().sort_index()
        return dict(dist)

    def get_genre_distribution(self):
        """类型分布统计"""
        genres = []
        for g in self.movies_df["genre"].dropna():
            for genre in str(g).split("/"):
                genre = genre.strip()
                if genre and genre != "未知":
                    genres.append(genre)
        counter = Counter(genres)
        return dict(counter.most_common(15))

    def get_director_distribution(self):
        """导演作品数量分布"""
        directors = self.movies_df["director"].dropna().str.strip()
        counter = Counter(directors[directors != "未知"])
        return dict(counter.most_common(15))

    def get_year_distribution(self):
        """上映年份分布"""
        valid_years = self.movies_df[self.movies_df["release_year"] > 0]
        year_counts = valid_years["release_year"].value_counts().sort_index()
        return dict(year_counts)

    def get_rating_count_correlation(self):
        """评分与评价人数的相关性"""
        correlation = self.movies_df["rating"].corr(self.movies_df["rating_count"])
        return round(correlation, 4)

    def get_year_avg_rating(self):
        """每年平均评分趋势"""
        valid = self.movies_df[(self.movies_df["release_year"] > 0)]
        yearly = valid.groupby("release_year")["rating"].agg(["mean", "count"]).round(2)
        yearly = yearly[yearly["count"] >= 2]  # 至少2部电影
        return yearly.reset_index().to_dict(orient="records")

    def get_comments_star_distribution(self):
        """短评星级分布"""
        if self.comments_df is None or "rating" not in self.comments_df.columns:
            return {}
        stars = self.comments_df["rating"].value_counts()
        return dict(stars)

    def generate_analysis_report(self):
        """生成完整分析报告"""
        report = {
            "basic_stats": self.get_basic_stats(),
            "top10_movies": self.get_top10_movies(),
            "rating_distribution": self.get_rating_distribution(),
            "genre_distribution": self.get_genre_distribution(),
            "director_distribution": self.get_director_distribution(),
            "year_distribution": self.get_year_distribution(),
            "rating_count_correlation": self.get_rating_count_correlation(),
            "year_avg_rating": self.get_year_avg_rating(),
            "comment_stars": self.get_comments_star_distribution(),
        }
        return report
