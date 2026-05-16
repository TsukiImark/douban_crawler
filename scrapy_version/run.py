"""
Scrapy爬虫独立运行入口
用法: python run.py
"""
import os
import sys
import time

# 将项目根目录加入sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings


def run_scrapy_spider():
    """运行Scrapy爬虫"""
    print("=" * 60)
    print("  豆瓣电影Top250 Scrapy爬虫")
    print("=" * 60)

    start_time = time.time()

    # 获取设置
    settings = get_project_settings()

    # 创建进程
    process = CrawlerProcess(settings)

    # 启动爬虫
    process.crawl("douban_top250")
    process.start()

    elapsed = time.time() - start_time
    print(f"\n爬取完成! 耗时: {elapsed:.1f}秒")


if __name__ == "__main__":
    # 切换到scrapy_version目录
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    run_scrapy_spider()
