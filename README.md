# 豆瓣电影Top250 爬虫数据分析系统

## 项目简介

完整的Python网络爬虫数据采集与分析系统，以豆瓣电影Top250为基础，实现列表页+详情页+短评的多层级爬虫，包含数据存储、清洗、分析与可视化。

## 环境配置

### 1. Python 3.8+
```bash
pip install -r requirements.txt
```

### 2. ChromeDriver (Selenium 需要)
- 确认已安装 Chrome 浏览器
- 下载匹配版本的 [ChromeDriver](https://chromedriver.chromium.org/)
- 将 `chromedriver.exe` 放到项目根目录

### 3. Cookie 配置（豆瓣需要登录）
豆瓣 `movie.douban.com` 要求登录态。按以下步骤导出浏览器 Cookie：

1. Chrome 登录豆瓣，打开 `https://movie.douban.com/top250`
2. `F12` → **Console**，粘贴执行：
```javascript
JSON.stringify(document.cookie.split('; ').map(c => {
    var p = c.split('=');
    return {name: p[0], value: decodeURIComponent(p.slice(1).join('='))};
}), null, 2)
```
3. 复制输出的 JSON，在项目根目录新建 `douban_cookies.json` 并粘贴
4. `F12` → **Application** → Cookies → `movie.douban.com`，找到 `dbcl2`，将其 `name` 和 `value` 手动追加到 JSON 文件

### 4. 数据库
默认 SQLite，零配置。MySQL 可选：修改 `config.py` 中 `DB_TYPE = "mysql"` 及连接信息，执行 `database/schema_mysql.sql`。

## 快速开始

```bash
python main.py                 # 完整流程
python main.py --no-comments   # 跳过短评（加速）
python main.py --no-posters    # 跳过海报
python main.py --analyze-only  # 仅分析已有数据
```

> **注意**：首次运行前确保 Chrome 浏览器已登录豆瓣且 Cookie 文件已配置。`Ctrl+C` 可随时停止，数据会自动保存。

## 项目结构

```
douban-movie-crawler-250/
├── main.py                     # 一键运行入口
├── config.py                   # 全局配置（速度/数据库/反爬参数）
├── requirements.txt            # 依赖清单
│
├── crawlers/                   # 爬虫模块
│   ├── request_crawler.py      #   requests+BS4 列表页+详情页
│   ├── selenium_crawler.py     #   Selenium 完整爬虫（列表+详情+短评+海报）
│   ├── image_downloader.py     #   requests海报下载（断点续传）
│   └── anti_spider.py          #   反爬：UA池/代理/延时/重试/robots/Cookie
│
├── scrapy_version/             # Scrapy完整重构
│   ├── scrapy.cfg / run.py
│   └── douban_scrapy/
│       ├── items.py            #   Item定义
│       ├── settings.py         #   并发/延时/Middleware配置
│       ├── pipelines.py        #   SQLite + CSV + JSON 三Pipeline
│       ├── middlewares.py      #   UA轮换/延时/重试中间件
│       └── spiders/douban_spider.py
│
├── database/                   # 数据库
│   ├── db_manager.py           #   统一接口（SQLite/MySQL）
│   ├── schema_sqlite.sql / schema_mysql.sql
│
├── data_processing/            # 数据清洗
│   ├── cleaner.py              #   pandas缺失值/类型转换/去重
│   └── exporter.py             #   CSV + JSON导出
│
├── analysis/                   # 分析与可视化
│   ├── analyzer.py             #   统计分析（Top10/分布/相关性）
│   ├── visualizer.py           #   7张图表生成
│   └── sentiment.py            #   jieba分词 + SnowNLP情感分析 + 词云
│
├── utils/                      # 工具
│   ├── logger.py               #   logging日志管理
│   └── helpers.py              #   通用工具函数
│
├── output/
│   ├── data/                   #   CSV/JSON备份
│   ├── charts/                 #   7张可视化图表
│   └── logs/                   #   运行日志
│
└── posters/                    # 电影海报（250张）
```

## 数据库设计

### movies 主表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| rank | INTEGER | 排名(1-250) |
| title_cn | TEXT | 中文片名 |
| title_en | TEXT | 英文片名 |
| rating | REAL | 豆瓣评分 |
| rating_count | INTEGER | 评价人数 |
| director | TEXT | 导演 |
| actors | TEXT | 主演 |
| summary | TEXT | 简介 |
| detail_url | TEXT | 详情链接 |
| release_year | INTEGER | 上映年份 |
| runtime | TEXT | 片长 |
| genre | TEXT | 类型 |
| imdb_rating | REAL | IMDb评分 |
| poster_path | TEXT | 海报本地路径 |

### comments 短评表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| movie_id | INTEGER FK | 关联 movies.id |
| commenter | TEXT | 评论者 |
| rating | TEXT | 评分（星级） |
| content | TEXT | 评论内容 |
| comment_time | TEXT | 评论时间 |

## 输出说明

### 数据文件 (output/data/)
- `movies.csv/json` — 250部电影完整数据
- `comments.csv/json` — 5000条短评

### 可视化图表 (output/charts/)
- `01_rating_histogram.png` — 评分分布直方图
- `02_genre_pie.png` — 类型分布饼图
- `03_rating_vs_count.png` — 评分 vs 评价人数散点图
- `04_director_bar.png` — 导演分布柱状图
- `05_year_trend.png` — 上映年份趋势线图
- `06_comment_stars.png` — 短评星级分布
- `07_wordcloud.png` — 短评词云

### 日志 (output/logs/)
- 爬虫运行日志，含 robots.txt 遵守情况、请求重试记录等

## 功能特性

| 功能 | 实现 |
|------|------|
| requests+BS4 列表页爬取 | `crawlers/request_crawler.py` |
| Selenium 动态短评+详情 | `crawlers/selenium_crawler.py` |
| 海报下载 + 断点续传 | `crawlers/image_downloader.py` |
| 反爬策略 | UA池(20+) / 延时1-4s / 403/429重试 / robots.txt / Cookie管理 |
| SQLite数据库 | movies + comments 2表外键关联 |
| CSV/JSON双格式导出 | `output/data/` |
| Scrapy完整重构 | Item/Spider/Pipeline/Middleware |
| pandas数据清洗 | 缺失值/类型转换/去重 |
| 统计分析 | Top10 / 导演/类型分布 / 评分相关性 |
| 可视化(7张图) | Matplotlib + Seaborn + Plotly |
| 情感分析 | jieba分词 + SnowNLP + wordcloud词云 |
| 日志 + 进度条 | logging + tqdm |
| 断点续传 | 电影/短评/海报均支持 |

## 注意事项

- 仅爬取公开页面，遵守 robots.txt，礼貌延时
- `douban_cookies.json` 包含登录凭证，已加入 `.gitignore`
- 仅供学习研究使用
- 如网站结构变化需调整 CSS 选择器

## 环境要求

- Python >= 3.8
- Chrome 浏览器 + 匹配版本的 ChromeDriver
- 豆瓣账号（用于登录态 Cookie）
