"""
数据清洗模块 - 使用pandas进行缺失值处理、类型转换、去重
"""
import pandas as pd
import numpy as np
import re
from utils.logger import get_logger

logger = get_logger("data_cleaner")


class DataCleaner:
    """数据清洗器"""

    def __init__(self, movies, comments):
        """
        movies: list[dict] 电影数据列表
        comments: list[dict] 短评数据列表
        """
        self.movies_raw = movies
        self.comments_raw = comments
        self.movies_df = None
        self.comments_df = None
        self.cleaning_log = []

    def load_to_dataframe(self):
        """将原始数据转换为DataFrame"""
        self.movies_df = pd.DataFrame(self.movies_raw)
        self.comments_df = pd.DataFrame(self.comments_raw)
        logger.info(f"已加载 {len(self.movies_df)} 部电影, {len(self.comments_df)} 条短评")

    def clean_movies(self):
        """清洗电影数据"""
        if self.movies_df is None:
            self.load_to_dataframe()

        df = self.movies_df.copy()
        initial_count = len(df)

        # 1. 类型转换
        df["rank"] = pd.to_numeric(df["rank"], errors="coerce")
        df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
        df["rating_count"] = pd.to_numeric(df["rating_count"], errors="coerce")
        df["imdb_rating"] = pd.to_numeric(df["imdb_rating"], errors="coerce")
        df["release_year"] = pd.to_numeric(df["release_year"], errors="coerce")

        # 2. 处理缺失值
        df["title_cn"] = df["title_cn"].fillna("未知").str.strip()
        df["title_en"] = df["title_en"].fillna("")
        df["director"] = df["director"].fillna("未知")
        df["actors"] = df["actors"].fillna("")
        df["summary"] = df["summary"].fillna("")
        df["genre"] = df["genre"].fillna("未知")
        df["runtime"] = df["runtime"].fillna("")
        df["rating"] = df["rating"].fillna(0.0)
        df["rating_count"] = df["rating_count"].fillna(0).astype(int)
        df["imdb_rating"] = df["imdb_rating"].fillna(0.0)
        df["release_year"] = df["release_year"].fillna(0).astype(int)

        # 3. 清理文本字段
        for col in ["title_cn", "title_en", "director", "actors"]:
            if col in df.columns:
                df[col] = df[col].str.strip()

        # 4. 去重 (按rank)
        if "rank" in df.columns:
            df = df.drop_duplicates(subset=["rank"], keep="first")

        # 5. 排序
        df = df.sort_values("rank").reset_index(drop=True)

        # 6. 清理异常值 - 评分范围
        mask = (df["rating"] >= 0) & (df["rating"] <= 10)
        df = df[mask]

        self.movies_df = df

        # 记录清洗日志
        self.cleaning_log.append(f"电影数据: {initial_count} -> {len(df)} 条 (去重取值后)")
        logger.info(f"电影数据清洗完成: {len(df)} 条有效记录")
        return df

    def clean_comments(self):
        """清洗短评数据"""
        if self.comments_df is None:
            self.load_to_dataframe()

        df = self.comments_df.copy()
        initial_count = len(df)

        # 1. 填充缺失值
        df["commenter"] = df["commenter"].fillna("匿名")
        df["content"] = df["content"].fillna("")
        df["rating"] = df["rating"].fillna("未评分")
        df["comment_time"] = df["comment_time"].fillna("")

        # 2. 去除空内容的短评
        df = df[df["content"].str.strip() != ""]

        # 3. 去重 (按content去重)
        if "content" in df.columns:
            df = df.drop_duplicates(subset=["content"], keep="first")

        self.comments_df = df

        self.cleaning_log.append(f"短评数据: {initial_count} -> {len(df)} 条")
        logger.info(f"短评数据清洗完成: {len(df)} 条有效记录")
        return df

    def get_cleaning_report(self):
        """获取数据清洗报告"""
        report = {
            "movies_count": len(self.movies_df) if self.movies_df is not None else 0,
            "comments_count": len(self.comments_df) if self.comments_df is not None else 0,
            "movies_missing": {},
            "comments_missing": {},
        }

        if self.movies_df is not None:
            report["movies_missing"] = self.movies_df.isnull().sum().to_dict()

        if self.comments_df is not None:
            report["comments_missing"] = self.comments_df.isnull().sum().to_dict()

        return report

    def get_cleaned_data(self):
        """获取清洗后的数据"""
        return self.movies_df, self.comments_df
