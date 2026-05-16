"""
数据库管理器 - 支持SQLite和MySQL，提供统一接口
"""
import sqlite3
import os
import json
import csv
from datetime import datetime


class DatabaseManager:
    """数据库管理器，封装SQLite操作"""

    def __init__(self, db_path=None, db_type="sqlite", mysql_config=None):
        self.db_type = db_type

        if db_type == "sqlite":
            if db_path is None:
                from config import SQLITE_PATH

                db_path = SQLITE_PATH
            self.db_path = db_path
            self.conn = sqlite3.connect(db_path)
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA foreign_keys=ON")
            self._init_sqlite_schema()
        elif db_type == "mysql":
            import pymysql

            if mysql_config is None:
                from config import MYSQL_CONFIG

                mysql_config = MYSQL_CONFIG
            self.conn = pymysql.connect(**mysql_config)
            self._init_mysql_schema()
        else:
            raise ValueError(f"Unsupported db_type: {db_type}")

    def _init_sqlite_schema(self):
        """初始化SQLite表结构"""
        schema_path = os.path.join(
            os.path.dirname(__file__), "schema_sqlite.sql"
        )
        with open(schema_path, "r", encoding="utf-8") as f:
            sql = f.read()
        self.conn.executescript(sql)
        self.conn.commit()

    def _init_mysql_schema(self):
        """初始化MySQL表结构"""
        import pymysql

        schema_path = os.path.join(
            os.path.dirname(__file__), "schema_mysql.sql"
        )
        with open(schema_path, "r", encoding="utf-8") as f:
            sql = f.read()
        with self.conn.cursor() as cursor:
            for statement in sql.split(";"):
                stmt = statement.strip()
                if stmt and not stmt.startswith("--"):
                    cursor.execute(stmt)
        self.conn.commit()

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()

    def insert_movie(self, movie_data):
        """
        插入电影记录，若已存在(同rank)则只更新非空字段，不覆盖已有数据
        返回 movie_id
        """
        if self.db_type == "sqlite":
            sql = """
            INSERT OR REPLACE INTO movies
                (id, rank, title_cn, title_en, rating, rating_count,
                 director, actors, summary, detail_url, release_year,
                 runtime, genre, imdb_rating, poster_path)
            VALUES (
                (SELECT id FROM movies WHERE rank = ?),
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """
        else:
            sql = """
            INSERT INTO movies
                (rank, title_cn, title_en, rating, rating_count,
                 director, actors, summary, detail_url, release_year,
                 runtime, genre, imdb_rating, poster_path)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                title_cn=VALUES(title_cn), rating=VALUES(rating),
                rating_count=VALUES(rating_count), summary=VALUES(summary)
            """
        values = [
            movie_data.get("rank"),  # 子查询WHERE用的rank
            movie_data.get("rank"),  # 列值rank
            movie_data.get("title_cn", ""),
            movie_data.get("title_en", ""),
            movie_data.get("rating", 0.0),
            movie_data.get("rating_count", 0),
            movie_data.get("director", ""),
            movie_data.get("actors", ""),
            movie_data.get("summary", ""),
            movie_data.get("detail_url", ""),
            movie_data.get("release_year"),
            movie_data.get("runtime", ""),
            movie_data.get("genre", ""),
            movie_data.get("imdb_rating", 0.0),
            movie_data.get("poster_path", ""),
        ]
        self.conn.execute(sql, values)
        self.conn.commit()

        cursor = self.conn.execute("SELECT id FROM movies WHERE rank = ?", (movie_data.get("rank"),))
        row = cursor.fetchone()
        return row[0] if row else None

    def insert_comment(self, movie_id, comment_data):
        """插入短评记录"""
        if self.db_type == "sqlite":
            sql = """
            INSERT INTO comments (movie_id, commenter, rating, content, comment_time)
            VALUES (?, ?, ?, ?, ?)
            """
        else:
            sql = """
            INSERT INTO comments (movie_id, commenter, rating, content, comment_time)
            VALUES (%s, %s, %s, %s, %s)
            """
        values = [
            movie_id,
            comment_data.get("commenter", ""),
            comment_data.get("rating", ""),
            comment_data.get("content", ""),
            comment_data.get("comment_time", ""),
        ]
        self.conn.execute(sql, values)
        self.conn.commit()
        return self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    def insert_comments_batch(self, movie_id, comments):
        """批量插入短评"""
        for c in comments:
            self.insert_comment(movie_id, c)

    def get_all_movies(self):
        """获取所有电影记录"""
        cursor = self.conn.execute("SELECT * FROM movies ORDER BY rank")
        columns = [d[0] for d in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_comments_for_movie(self, movie_id):
        """获取某部电影的所有短评"""
        cursor = self.conn.execute(
            "SELECT * FROM comments WHERE movie_id = ?", (movie_id,)
        )
        columns = [d[0] for d in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_all_comments(self):
        """获取所有短评"""
        cursor = self.conn.execute("SELECT * FROM comments")
        columns = [d[0] for d in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_stats(self):
        """获取爬取统计信息"""
        movie_count = self.conn.execute(
            "SELECT COUNT(*) FROM movies"
        ).fetchone()[0]
        comment_count = self.conn.execute(
            "SELECT COUNT(*) FROM comments"
        ).fetchone()[0]
        return {
            "total_movies": movie_count,
            "total_comments": comment_count,
        }

    def clear_all(self):
        """清空所有数据"""
        self.conn.execute("DELETE FROM comments")
        self.conn.execute("DELETE FROM movies")
        self.conn.commit()

    def export_to_csv(self, output_dir):
        """导出为CSV文件"""
        import pandas as pd

        movies = self.get_all_movies()
        comments = self.get_all_comments()

        movies_df = pd.DataFrame(movies)
        comments_df = pd.DataFrame(comments)

        movies_path = os.path.join(output_dir, "movies.csv")
        comments_path = os.path.join(output_dir, "comments.csv")

        movies_df.to_csv(movies_path, index=False, encoding="utf-8-sig")
        comments_df.to_csv(comments_path, index=False, encoding="utf-8-sig")

        return movies_path, comments_path

    def export_to_json(self, output_dir):
        """导出为JSON文件"""
        movies = self.get_all_movies()
        comments = self.get_all_comments()

        movies_path = os.path.join(output_dir, "movies.json")
        comments_path = os.path.join(output_dir, "comments.json")

        with open(movies_path, "w", encoding="utf-8") as f:
            json.dump(movies, f, ensure_ascii=False, indent=2)
        with open(comments_path, "w", encoding="utf-8") as f:
            json.dump(comments, f, ensure_ascii=False, indent=2)

        return movies_path, comments_path
