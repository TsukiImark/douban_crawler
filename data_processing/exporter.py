"""
数据导出模块 - CSV/JSON格式备份
"""
import os
import json
import csv
import pandas as pd
from config import DATA_DIR
from utils.logger import get_logger

logger = get_logger("data_exporter")


class DataExporter:
    """数据导出器"""

    def __init__(self, output_dir=None):
        self.output_dir = output_dir or DATA_DIR
        os.makedirs(self.output_dir, exist_ok=True)

    def export_movies_csv(self, movies_df, filename="movies.csv"):
        """导出电影数据为CSV"""
        path = os.path.join(self.output_dir, filename)
        movies_df.to_csv(path, index=False, encoding="utf-8-sig")
        logger.info(f"电影数据已导出CSV: {path} ({len(movies_df)}条)")
        return path

    def export_comments_csv(self, comments_df, filename="comments.csv"):
        """导出短评数据为CSV"""
        path = os.path.join(self.output_dir, filename)
        comments_df.to_csv(path, index=False, encoding="utf-8-sig")
        logger.info(f"短评数据已导出CSV: {path} ({len(comments_df)}条)")
        return path

    def export_movies_json(self, movies, filename="movies.json"):
        """导出电影数据为JSON"""
        path = os.path.join(self.output_dir, filename)
        if isinstance(movies, pd.DataFrame):
            movies = movies.to_dict(orient="records")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(movies, f, ensure_ascii=False, indent=2)
        logger.info(f"电影数据已导出JSON: {path}")
        return path

    def export_comments_json(self, comments, filename="comments.json"):
        """导出短评数据为JSON"""
        path = os.path.join(self.output_dir, filename)
        if isinstance(comments, pd.DataFrame):
            comments = comments.to_dict(orient="records")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(comments, f, ensure_ascii=False, indent=2)
        logger.info(f"短评数据已导出JSON: {path}")
        return path

    def export_all(self, movies, comments):
        """一次性导出所有格式"""
        results = {}
        results["movies_csv"] = self.export_movies_csv(movies)
        results["comments_csv"] = self.export_comments_csv(comments)
        results["movies_json"] = self.export_movies_json(movies)
        results["comments_json"] = self.export_comments_json(comments)
        return results
