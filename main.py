"""
豆瓣电影Top250 爬虫数据分析系统 - 一键运行入口
用法:
  python main.py                  # 完整流程
  python main.py --crawl-only     # 仅爬取
  python main.py --analyze-only   # 仅分析
  python main.py --use-scrapy     # 使用Scrapy版本爬取
  python main.py --no-selenium    # 跳过Selenium（仅requests爬取）
"""
import os
import sys
import time
import argparse
from datetime import datetime

import config
from utils.logger import setup_logger, get_logger

logger = None  # 延迟初始化


def init_logger():
    """初始化日志"""
    global logger
    logger = setup_logger(
        name="douban_main",
        log_level=config.LOG_LEVEL,
        log_dir=config.LOGS_DIR,
        log_file=f"main_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
    )
    return logger


def print_banner():
    """打印程序横幅"""
    print("\n" + "=" * 60)
    print("  豆瓣电影Top250 爬虫数据分析系统")
    print("  Douban Movie Top250 Crawler & Analysis Platform")
    print("=" * 60)
    print(f"  开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  输出目录: {config.OUTPUT_DIR}")
    print(f"  数据库:   {config.SQLITE_PATH} (SQLite)")
    print("=" * 60 + "\n")


def crawl_all_with_selenium():
    """使用Selenium完整爬取：列表页 + 详情页 + 短评 + 海报（支持断点续传）"""
    logger.info(">>> Selenium完整爬取开始 <<<")

    # 先尝试从数据库加载已有数据
    existing_movies = []
    try:
        from database.db_manager import DatabaseManager
        db = DatabaseManager(db_type=config.DB_TYPE)
        existing_movies = db.get_all_movies()
        db.close()
        if existing_movies:
            logger.info(f"从数据库加载了 {len(existing_movies)} 部已有电影（跳过列表页和详情页）")
    except Exception:
        pass

    try:
        from crawlers.selenium_crawler import DoubanSeleniumCrawler

        sel_crawler = DoubanSeleniumCrawler(headless=False)
        all_movies = []

        try:
            all_movies = sel_crawler.crawl_all(
                pages=config.TOTAL_PAGES,
                with_comments=True,
                with_details=True,
                existing_movies=existing_movies,
            )
        finally:
            sel_crawler.quit()

        # 中间保存：列表+详情完成后立即存数据库
        if all_movies and not existing_movies:
            logger.info("中间保存: 列表页+详情页数据写入数据库...")
            store_to_database(all_movies)

        logger.info(f"Selenium爬取完成: {len(all_movies)} 部电影")
        return all_movies

    except Exception as e:
        logger.error(f"Selenium爬取异常: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return []


def download_posters(all_movies):
    """下载电影海报 - 优先Selenium，回退requests"""
    logger.info(">>> 阶段3: 海报下载开始 <<<")

    # 先检查已下载的
    import os as _os
    already = sum(1 for m in all_movies if m.get("poster_path") and _os.path.exists(m["poster_path"]))
    if already > 200:
        logger.info(f"已有 {already} 张海报，跳过")
        return {"downloaded": 0, "skipped": already, "failed": 0}

    # 用Selenium下载（doubanio.com封了requests）
    try:
        from crawlers.selenium_crawler import DoubanSeleniumCrawler
        import time as _time, os as _os

        sel = DoubanSeleniumCrawler(headless=True)
        sel._inject_cookies()
        _time.sleep(2)

        downloaded = skipped = failed = 0
        for i, m in enumerate(all_movies):
            rank = m.get("rank", 0)
            title = m.get("title_cn", f"movie_{rank}")
            safe = title.replace('/', '_').replace('\\', '_').replace(':', '_')[:40]
            filepath = _os.path.join(config.POSTERS_DIR, f"{rank:03d}_{safe}.jpg")

            if _os.path.exists(filepath) and _os.path.getsize(filepath) > 0:
                skipped += 1
                m["poster_path"] = filepath
                if i % 25 == 0:
                    logger.info(f"海报进度: {i+1}/250, 下载{downloaded} 跳过{skipped} 失败{failed}")
                continue

            detail_url = m.get("detail_url", "")
            if not detail_url:
                failed += 1
                continue

            try:
                # 从详情页截取海报（带Referer，CDN不会拦）
                sel.driver.get(detail_url)
                _time.sleep(1)
                poster_img_el = sel.driver.find_element("css selector", "#mainpic img")
                poster_img_el.screenshot(filepath)
                if _os.path.getsize(filepath) > 5000:
                    m["poster_path"] = filepath
                    downloaded += 1
                else:
                    _os.remove(filepath)
                    failed += 1
                _time.sleep(0.3)
            except Exception:
                failed += 1

            if i % 25 == 0:
                logger.info(f"海报进度: {i+1}/250, 下载{downloaded} 跳过{skipped} 失败{failed}")

        sel.quit()
        logger.info(f"海报完成: 下载{downloaded}, 跳过{skipped}, 失败{failed}")

        # 更新数据库
        from database.db_manager import DatabaseManager
        db = DatabaseManager(db_type=config.DB_TYPE)
        for m in all_movies:
            if m.get("poster_path"):
                db.conn.execute("UPDATE movies SET poster_path = ? WHERE rank = ?",
                              (m["poster_path"], m["rank"]))
        db.conn.commit()
        db.close()

        return {"downloaded": downloaded, "skipped": skipped, "failed": failed}
    except Exception as e:
        logger.error(f"Selenium海报下载异常: {e}")
        return {"downloaded": 0, "skipped": 0, "failed": 0}


def store_to_database(all_movies):
    """存储到数据库并导出"""
    logger.info(">>> 阶段4: 数据存储开始 <<<")

    try:
        from database.db_manager import DatabaseManager

        db = DatabaseManager(db_type=config.DB_TYPE)

        # 插入电影（跳过已存在的, 不覆盖已有数据）
        existing_ranks = set()
        for row in db.conn.execute("SELECT rank FROM movies"):
            existing_ranks.add(row[0])

        new_count = 0
        for movie in all_movies:
            if movie.get("rank") not in existing_ranks:
                db.insert_movie(movie)
                new_count += 1
        logger.info(f"新增电影: {new_count}, 跳过已有: {len(all_movies) - new_count}")

        # 插入短评
        total_comments = 0
        for movie in all_movies:
            comments = movie.get("comments", [])
            if comments:
                movie_rank = movie.get("rank")
                cursor = db.conn.execute("SELECT id FROM movies WHERE rank = ?", (movie_rank,))
                row = cursor.fetchone()
                if row:
                    movie_id = row[0]
                    db.insert_comments_batch(movie_id, comments)
                    total_comments += len(comments)

        # 导出
        db.export_to_csv(config.DATA_DIR)
        db.export_to_json(config.DATA_DIR)

        stats = db.get_stats()
        logger.info(f"数据存储完成: {stats}")
        db.close()

        return stats

    except Exception as e:
        logger.error(f"数据存储异常: {type(e).__name__}: {e}")
        return {"total_movies": 0, "total_comments": 0}


def clean_and_analyze():
    """数据清洗、分析与可视化"""
    logger.info(">>> 阶段5: 数据清洗与分析开始 <<<")

    try:
        from database.db_manager import DatabaseManager
        from data_processing.cleaner import DataCleaner
        from data_processing.exporter import DataExporter
        from analysis.analyzer import DataAnalyzer
        from analysis.visualizer import Visualizer
        from analysis.sentiment import SentimentAnalyzer

        # 从数据库加载
        db = DatabaseManager(db_type=config.DB_TYPE)
        movies_list = db.get_all_movies()
        comments_list = db.get_all_comments()
        db.close()

        logger.info(f"从数据库加载: {len(movies_list)} 部电影, {len(comments_list)} 条短评")

        # 数据清洗
        cleaner = DataCleaner(movies_list, comments_list)
        cleaner.load_to_dataframe()
        movies_df = cleaner.clean_movies()
        comments_df = cleaner.clean_comments()

        # 导出清洗后的数据
        exporter = DataExporter(config.DATA_DIR)
        exporter.export_all(movies_df, comments_df)

        # 数据分析
        analyzer = DataAnalyzer(movies_df, comments_df)
        report = analyzer.generate_analysis_report()

        # 打印基本统计
        stats = report["basic_stats"]
        print("\n" + "=" * 40)
        print("  数据分析结果")
        print("=" * 40)
        print(f"  电影总数:     {stats['movie_count']}")
        print(f"  短评总数:     {stats['comment_count']}")
        print(f"  平均评分:     {stats['avg_rating']}")
        print(f"  最高评分:     {stats['max_rating']}")
        print(f"  最低评分:     {stats['min_rating']}")
        print(f"  总评价人数:   {stats['total_rating_count']:,}")
        print(f"  评分-人数相关: {report['rating_count_correlation']}")
        print("-" * 40)

        # Top10
        print("\n  Top10 高分电影:")
        for i, m in enumerate(report["top10_movies"][:10], 1):
            print(f"  {i}. {m['title_cn']} - {m['rating']}分 ({m['rating_count']}人评价)")
        print("=" * 40 + "\n")

        # 可视化
        visualizer = Visualizer(movies_df, comments_df)
        chart_paths = visualizer.generate_all_charts()

        # 情感分析
        sentiment = SentimentAnalyzer(comments_df)
        sentiment_report = sentiment.generate_full_report()

        sent_stats = sentiment_report["sentiment_stats"]
        if sent_stats["total"] > 0:
            print("=" * 40)
            print("  情感分析结果")
            print("=" * 40)
            print(f"  正面: {sent_stats['positive']} 条 ({sent_stats['positive_pct']}%)")
            print(f"  中性: {sent_stats['neutral']} 条 ({sent_stats['neutral_pct']}%)")
            print(f"  负面: {sent_stats['negative']} 条 ({sent_stats['negative_pct']}%)")
            print(f"  平均情感得分: {sent_stats['avg_score']:.4f}")
            print(f"  词云已生成:   {sentiment_report.get('wordcloud_path', 'N/A')}")
            print("=" * 40 + "\n")

        # 输出图表列表
        print(f"已生成 {len(chart_paths)} 张图表:")
        for p in chart_paths:
            print(f"  - {p}")

        return True

    except Exception as e:
        logger.error(f"分析异常: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def crawl_with_scrapy():
    """使用Scrapy框架爬取"""
    logger.info(">>> Scrapy框架爬取开始 <<<")
    print("提示: 使用Scrapy框架重新爬取豆瓣Top250...")

    try:
        import subprocess
        scrapy_dir = os.path.join(os.path.dirname(__file__), "scrapy_version")
        result = subprocess.run(
            [sys.executable, "run.py"],
            cwd=scrapy_dir,
            capture_output=False,
        )
        if result.returncode == 0:
            logger.info("Scrapy爬取完成")
            print("Scrapy爬取完成! 数据已保存到 douban_scrapy.db")
        else:
            logger.error(f"Scrapy爬取失败，返回码: {result.returncode}")
            print(f"Scrapy爬取失败，返回码: {result.returncode}")
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Scrapy执行异常: {e}")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="豆瓣电影Top250 爬虫数据分析系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py                    # 完整流程
  python main.py --crawl-only       # 仅爬取
  python main.py --analyze-only     # 仅分析
  python main.py --use-scrapy       # Scrapy版本
  python main.py --no-selenium      # 跳过Selenium
        """,
    )
    parser.add_argument("--crawl-only", action="store_true", help="仅执行爬取")
    parser.add_argument("--analyze-only", action="store_true", help="仅执行数据分析和可视化")
    parser.add_argument("--no-comments", action="store_true", help="跳过短评爬取（加速）")
    parser.add_argument("--no-posters", action="store_true", help="跳过海报下载")
    parser.add_argument("--headless", action="store_true", help="Chrome无头模式")

    args = parser.parse_args()

    init_logger()
    print_banner()

    start_time = time.time()

    if args.analyze_only:
        clean_and_analyze()
    else:
        # 使用Selenium完整爬取 (列表页 + 详情页 + 短评 + 海报)
        logger.info("使用Selenium模式 (真实Chrome浏览器)")
        logger.info("提示: 请确保Chrome已登录豆瓣，如出现验证页面请手动完成")
        all_movies = crawl_all_with_selenium()

        if not args.no_posters and all_movies:
            download_posters(all_movies)

        if all_movies:
            store_to_database(all_movies)

        if not args.crawl_only:
            clean_and_analyze()

    elapsed = time.time() - start_time
    minutes, seconds = divmod(elapsed, 60)
    print(f"\n总耗时: {int(minutes)}分{seconds:.1f}秒")
    print("程序执行完成!\n")


if __name__ == "__main__":
    main()
