-- ============================================================
-- 豆瓣电影Top250 数据库建表脚本 (SQLite)
-- ============================================================

-- 电影主表
CREATE TABLE IF NOT EXISTS movies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rank INTEGER NOT NULL,
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

-- 短评表
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

-- 索引
CREATE INDEX IF NOT EXISTS idx_movies_rank ON movies(rank);
CREATE INDEX IF NOT EXISTS idx_movies_rating ON movies(rating);
CREATE INDEX IF NOT EXISTS idx_comments_movie_id ON comments(movie_id);
