"""
可视化模块 - 生成5+张图表：评分分布直方图、类型饼图、散点图、词云、时间趋势线图
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
from collections import Counter
from config import CHARTS_DIR, MATPLOTLIB_FONT, WORDCLOUD_FONT_PATH, WORDCLOUD_WIDTH, WORDCLOUD_HEIGHT, WORDCLOUD_MAX_WORDS
from utils.logger import get_logger

logger = get_logger("visualizer")

# 设置中文字体
try:
    plt.rcParams["font.sans-serif"] = [MATPLOTLIB_FONT, "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
except Exception:
    pass


class Visualizer:
    """图表生成器 - 生成至少5张可视化图表"""

    def __init__(self, movies_df, comments_df, output_dir=None):
        self.movies_df = movies_df
        self.comments_df = comments_df
        self.output_dir = output_dir or CHARTS_DIR
        os.makedirs(self.output_dir, exist_ok=True)
        self.chart_paths = []

        # 设置seaborn风格
        sns.set_style("whitegrid")

    def chart_rating_histogram(self):
        """图1: 评分分布直方图"""
        fig, ax = plt.subplots(figsize=(10, 6))
        ratings = self.movies_df["rating"].dropna()

        ax.hist(ratings, bins=20, edgecolor="white", color=sns.color_palette("viridis", 1), alpha=0.8)
        ax.axvline(ratings.mean(), color="red", linestyle="--", linewidth=2, label=f'平均分: {ratings.mean():.2f}')
        ax.axvline(ratings.median(), color="orange", linestyle="--", linewidth=2, label=f'中位数: {ratings.median():.2f}')

        ax.set_xlabel("豆瓣评分", fontsize=12)
        ax.set_ylabel("电影数量", fontsize=12)
        ax.set_title("豆瓣电影Top250 评分分布直方图", fontsize=14, fontweight="bold")
        ax.legend()
        ax.grid(True, alpha=0.3)

        path = os.path.join(self.output_dir, "01_rating_histogram.png")
        fig.tight_layout()
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        self.chart_paths.append(path)
        logger.info(f"图表已生成: 评分分布直方图")
        return path

    def chart_genre_pie(self):
        """图2: 电影类型饼图"""
        fig, ax = plt.subplots(figsize=(12, 8))

        genres = []
        for g in self.movies_df["genre"].dropna():
            for genre in str(g).split("/"):
                genre = genre.strip()
                if genre and genre != "未知":
                    genres.append(genre)
        counter = Counter(genres)
        top_genres = counter.most_common(10)

        labels = [g[0] for g in top_genres]
        sizes = [g[1] for g in top_genres]
        colors = sns.color_palette("Set3", len(labels))

        wedges, texts, autotexts = ax.pie(
            sizes, labels=None, autopct="%1.1f%%",
            colors=colors, startangle=90, pctdistance=0.85
        )
        for t in autotexts:
            t.set_fontsize(9)

        ax.legend(wedges, labels, title="电影类型", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))
        ax.set_title("豆瓣电影Top250 类型分布饼图", fontsize=14, fontweight="bold")

        path = os.path.join(self.output_dir, "02_genre_pie.png")
        fig.tight_layout()
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        self.chart_paths.append(path)
        logger.info(f"图表已生成: 类型分布饼图")
        return path

    def chart_rating_vs_count_scatter(self):
        """图3: 评分与评价人数散点图"""
        fig, ax = plt.subplots(figsize=(10, 6))

        df = self.movies_df.dropna(subset=["rating", "rating_count"])
        correlation = df["rating"].corr(df["rating_count"])

        scatter = ax.scatter(
            df["rating_count"] / 10000, df["rating"],
            c=df["rating"], cmap="viridis", alpha=0.6,
            s=df["rating_count"] / 10000, edgecolors="gray", linewidth=0.3
        )
        plt.colorbar(scatter, ax=ax, label="评分")

        # 趋势线
        # 去除异常值防止SVD不收敛
        x = df["rating_count"] / 10000
        y = df["rating"]
        mask = (x > 0) & np.isfinite(x) & np.isfinite(y)
        x, y = x[mask], y[mask]
        if len(x) < 2:
            path = os.path.join(self.output_dir, "03_rating_vs_count.png")
            fig.savefig(path, dpi=150, bbox_inches="tight")
            plt.close(fig)
            return path
        z = np.polyfit(x, y, 1)
        p = np.poly1d(z)
        x_line = np.linspace(df["rating_count"].min() / 10000, df["rating_count"].max() / 10000, 100)
        ax.plot(x_line, p(x_line), "r--", linewidth=2, label=f"趋势线 (r={correlation:.3f})")

        ax.set_xlabel("评价人数 (万)", fontsize=12)
        ax.set_ylabel("豆瓣评分", fontsize=12)
        ax.set_title(f"评分 vs 评价人数 散点图 (相关系数: {correlation:.3f})", fontsize=14, fontweight="bold")
        ax.legend()
        ax.grid(True, alpha=0.3)

        path = os.path.join(self.output_dir, "03_rating_vs_count.png")
        fig.tight_layout()
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        self.chart_paths.append(path)
        logger.info(f"图表已生成: 评分与人数散点图")
        return path

    def chart_director_bar(self):
        """图4: 导演作品数量柱状图"""
        fig, ax = plt.subplots(figsize=(12, 6))

        directors = self.movies_df["director"].dropna().str.strip()
        directors = directors[directors != "未知"]
        top_directors = Counter(directors).most_common(12)

        names = [d[0][:8] for d in top_directors]
        counts = [d[1] for d in top_directors]

        bars = ax.barh(range(len(names)), counts, color=sns.color_palette("viridis", len(names)))
        ax.set_yticks(range(len(names)))
        ax.set_yticklabels(names)
        ax.invert_yaxis()
        ax.set_xlabel("入选Top250作品数", fontsize=12)
        ax.set_title("豆瓣电影Top250 导演分布 (Top12)", fontsize=14, fontweight="bold")
        ax.grid(True, alpha=0.3, axis="x")

        for i, (bar, count) in enumerate(zip(bars, counts)):
            ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height() / 2, str(count), va="center")

        path = os.path.join(self.output_dir, "04_director_bar.png")
        fig.tight_layout()
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        self.chart_paths.append(path)
        logger.info(f"图表已生成: 导演分布柱状图")
        return path

    def chart_year_trend(self):
        """图5: 上映年份与平均评分趋势线图"""
        fig, ax1 = plt.subplots(figsize=(12, 6))

        valid = self.movies_df[self.movies_df["release_year"] > 0].copy()
        yearly = valid.groupby("release_year").agg(
            avg_rating=("rating", "mean"),
            count=("rating", "count")
        ).reset_index()
        yearly = yearly[yearly["count"] >= 2]

        ax1.plot(yearly["release_year"], yearly["avg_rating"], "o-", color="#2E86AB", linewidth=2, label="平均评分")
        ax1.fill_between(yearly["release_year"], yearly["avg_rating"], alpha=0.2, color="#2E86AB")
        ax1.set_xlabel("上映年份", fontsize=12)
        ax1.set_ylabel("平均评分", fontsize=12, color="#2E86AB")
        ax1.tick_params(axis="y", labelcolor="#2E86AB")

        ax2 = ax1.twinx()
        ax2.bar(yearly["release_year"], yearly["count"], alpha=0.3, color="#A23B72", label="电影数量")
        ax2.set_ylabel("电影数量", fontsize=12, color="#A23B72")
        ax2.tick_params(axis="y", labelcolor="#A23B72")

        ax1.set_title("豆瓣电影Top250 上映年份趋势 (评分 & 数量)", fontsize=14, fontweight="bold")
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")
        ax1.grid(True, alpha=0.3)

        path = os.path.join(self.output_dir, "05_year_trend.png")
        fig.tight_layout()
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        self.chart_paths.append(path)
        logger.info(f"图表已生成: 时间趋势线图")
        return path

    def chart_comment_stars_pie(self):
        """图6 (加分): 短评星级分布饼图"""
        if self.comments_df is None or "rating" not in self.comments_df.columns:
            logger.warning("无法生成短评星级图: 数据不足")
            return None

        fig, ax = plt.subplots(figsize=(10, 8))
        stars = self.comments_df["rating"].value_counts()

        colors = sns.color_palette("RdYlGn", len(stars))[::-1]
        wedges, texts, autotexts = ax.pie(
            stars.values, labels=stars.index, autopct="%1.1f%%",
            colors=colors, startangle=90
        )
        for t in autotexts:
            t.set_fontsize(10)
        ax.set_title("短评星级分布", fontsize=14, fontweight="bold")

        path = os.path.join(self.output_dir, "06_comment_stars.png")
        fig.tight_layout()
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        self.chart_paths.append(path)
        logger.info(f"图表已生成: 短评星级分布")
        return path

    def generate_all_charts(self):
        """生成所有图表"""
        logger.info("开始生成可视化图表...")
        self.chart_paths = []

        charts = [
            self.chart_rating_histogram(),
            self.chart_genre_pie(),
            self.chart_rating_vs_count_scatter(),
            self.chart_director_bar(),
            self.chart_year_trend(),
        ]

        # 短评星级（如果有数据）
        if self.comments_df is not None and len(self.comments_df) > 0:
            charts.append(self.chart_comment_stars_pie())

        valid_charts = [c for c in charts if c is not None]
        logger.info(f"可视化完成，共生成 {len(valid_charts)} 张图表")
        return valid_charts
