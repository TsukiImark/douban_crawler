-- ============================================================
-- 豆瓣电影Top250 数据库建表脚本 (MySQL)
-- ============================================================

CREATE DATABASE IF NOT EXISTS douban_movies
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE douban_movies;

-- 电影主表
CREATE TABLE IF NOT EXISTS movies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    `rank` INT NOT NULL,
    title_cn VARCHAR(255) NOT NULL,
    title_en VARCHAR(255),
    rating DECIMAL(3,1) DEFAULT 0.0,
    rating_count INT DEFAULT 0,
    director VARCHAR(255),
    actors TEXT,
    summary TEXT,
    detail_url VARCHAR(500),
    release_year INT,
    runtime VARCHAR(50),
    genre VARCHAR(255),
    imdb_rating DECIMAL(3,1) DEFAULT 0.0,
    poster_path VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 短评表
CREATE TABLE IF NOT EXISTS comments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    movie_id INT NOT NULL,
    commenter VARCHAR(255),
    rating VARCHAR(20),
    content TEXT,
    comment_time VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_movie_id (movie_id),
    CONSTRAINT fk_comments_movie
        FOREIGN KEY (movie_id) REFERENCES movies(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
