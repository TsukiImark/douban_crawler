"""
Scrapy Item Pipeline - 数据存储（SQLite/CSV/JSON）
"""
import sqlite3
import os
import csv
import json
import logging

logger = logging.getLogger(__name__)


class SQLitePipeline:
    """将Item存储到SQLite数据库"""

    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = None
        self.cursor = None

    @classmethod
    def from_crawler(cls, crawler):
        db_path = crawler.settings.get("SQLITE_DB_PATH", "douban_scrapy.db")
        return cls(db_path=db_path)

    def open_spider(self, spider):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.cursor = self.conn.cursor()
        self._create_tables()
        spider.logger.info(f"SQLite数据库已连接: {self.db_path}")

    def _create_tables(self):
        """创建表结构"""
        self.cursor.executescript("""
            CREATE TABLE IF NOT EXISTS movies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rank INTEGER NOT NULL UNIQUE,
                title_cn TEXT NOT NULL,
                title_en TEXT,
                rating REAL DEFAULT 0.0,
                rating_count INTEGER DEFAULT 0,
                director TEXT,
                actors TEXT,
                summary TEXT,
                detail_url TEXT,
                release_year INTEGER,
                runtime TEXT,
                genre TEXT,
                imdb_rating REAL DEFAULT 0.0,
                poster_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                movie_id INTEGER NOT NULL,
                commenter TEXT,
                rating TEXT,
                content TEXT,
                comment_time TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_movies_rank ON movies(rank);
            CREATE INDEX IF NOT EXISTS idx_comments_movie_id ON comments(movie_id);
        """)
        self.conn.commit()

    def process_item(self, item, spider):
        """处理Item"""
        from scrapy_version.douban_scrapy.items import DoubanMovieItem, CommentItem

        if isinstance(item, DoubanMovieItem):
            self._save_movie(item, spider)
        elif isinstance(item, CommentItem):
            self._save_comment(item, spider)
        return item

    def _save_movie(self, item, spider):
        """保存电影信息"""
        sql = """
        INSERT OR REPLACE INTO movies
            (rank, title_cn, title_en, rating, rating_count,
             director, actors, summary, detail_url, release_year,
             runtime, genre, imdb_rating, poster_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        values = (
            item.get("rank"),
            item.get("title_cn", ""),
            item.get("title_en", ""),
            item.get("rating", 0.0),
            item.get("rating_count", 0),
            item.get("director", ""),
            item.get("actors", ""),
            item.get("summary", ""),
            item.get("detail_url", ""),
            item.get("release_year"),
            item.get("runtime", ""),
            item.get("genre", ""),
            item.get("imdb_rating", 0.0),
            item.get("poster_path", ""),
        )
        self.cursor.execute(sql, values)
        self.conn.commit()
        spider.logger.debug(f"电影已保存: rank={item.get('rank')}, {item.get('title_cn')}")

    def _save_comment(self, item, spider):
        """保存短评"""
        # 通过movie_rank查找movie_id
        movie_rank = item.get("movie_rank")
        self.cursor.execute("SELECT id FROM movies WHERE rank = ?", (movie_rank,))
        row = self.cursor.fetchone()
        if not row:
            spider.logger.warning(f"未找到对应电影 rank={movie_rank}，短评跳过")
            return

        movie_id = row[0]
        sql = """
        INSERT INTO comments (movie_id, commenter, rating, content, comment_time)
        VALUES (?, ?, ?, ?, ?)
        """
        values = (
            movie_id,
            item.get("commenter", ""),
            item.get("rating", ""),
            item.get("content", ""),
            item.get("comment_time", ""),
        )
        self.cursor.execute(sql, values)
        self.conn.commit()

    def close_spider(self, spider):
        if self.conn:
            spider.logger.info("SQLite数据库连接已关闭")
            self.conn.close()


class CsvPipeline:
    """导出电影数据为CSV"""

    def __init__(self, output_dir):
        self.output_dir = output_dir
        self.movies = []
        self.comments = []

    @classmethod
    def from_crawler(cls, crawler):
        output_dir = crawler.settings.get("CSV_OUTPUT_DIR", "output/data")
        return cls(output_dir=output_dir)

    def process_item(self, item, spider):
        from scrapy_version.douban_scrapy.items import DoubanMovieItem, CommentItem

        if isinstance(item, DoubanMovieItem):
            self.movies.append(dict(item))
        elif isinstance(item, CommentItem):
            self.comments.append(dict(item))
        return item

    def close_spider(self, spider):
        os.makedirs(self.output_dir, exist_ok=True)
        if self.movies:
            self._write_csv(os.path.join(self.output_dir, "movies_scrapy.csv"), self.movies)
        if self.comments:
            self._write_csv(os.path.join(self.output_dir, "comments_scrapy.csv"), self.comments)
        spider.logger.info(f"CSV已导出到 {self.output_dir}")

    def _write_csv(self, filepath, data):
        if not data:
            return
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)


class JsonPipeline:
    """导出数据为JSON"""

    def __init__(self, output_dir):
        self.output_dir = output_dir
        self.movies = []
        self.comments = []

    @classmethod
    def from_crawler(cls, crawler):
        output_dir = crawler.settings.get("JSON_OUTPUT_DIR", "output/data")
        return cls(output_dir=output_dir)

    def process_item(self, item, spider):
        from scrapy_version.douban_scrapy.items import DoubanMovieItem, CommentItem

        if isinstance(item, DoubanMovieItem):
            self.movies.append(dict(item))
        elif isinstance(item, CommentItem):
            self.comments.append(dict(item))
        return item

    def close_spider(self, spider):
        os.makedirs(self.output_dir, exist_ok=True)
        if self.movies:
            with open(os.path.join(self.output_dir, "movies_scrapy.json"), "w", encoding="utf-8") as f:
                json.dump(self.movies, f, ensure_ascii=False, indent=2)
        if self.comments:
            with open(os.path.join(self.output_dir, "comments_scrapy.json"), "w", encoding="utf-8") as f:
                json.dump(self.comments, f, ensure_ascii=False, indent=2)
        spider.logger.info(f"JSON已导出到 {self.output_dir}")
