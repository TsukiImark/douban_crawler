"""
Selenium爬虫模块 - 完整爬取豆瓣Top250（列表页+详情页+短评+海报）
使用真实Chrome浏览器绕过WAF验证
"""
import time
import random
import re
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException,
)
from config import (
    SELENIUM_HEADLESS, SELENIUM_TIMEOUT, SELENIUM_IMPLICIT_WAIT,
    CHROMEDRIVER_PATH, MIN_COMMENTS_PER_MOVIE, COMMENT_LOAD_MORE_CLICKS,
    USER_AGENTS, TOTAL_PAGES,
    LIST_PAGE_LOAD_WAIT, BETWEEN_LIST_PAGES,
    DETAIL_PAGE_LOAD_WAIT, BETWEEN_DETAIL_PAGES,
    COMMENTS_PAGE_LOAD_WAIT, BETWEEN_COMMENTS,
)
from utils.helpers import sanitize_filename
from utils.logger import get_logger

logger = get_logger("selenium_crawler")


class DoubanSeleniumCrawler:
    """Selenium完整爬虫 - 替代requests版本"""

    BASE_URL = "https://movie.douban.com/top250"

    def __init__(self, headless=None):
        self.headless = headless if headless is not None else SELENIUM_HEADLESS
        self.driver = None
        self._init_driver()

    def _init_driver(self):
        """初始化Chrome浏览器，通过Cookie文件注入登录状态"""
        chrome_options = Options()

        if self.headless:
            chrome_options.add_argument("--headless=new")

        # 使用临时用户数据目录（不影响正在运行的Chrome）
        import tempfile
        temp_dir = os.path.join(tempfile.gettempdir(), "chrome_selenium_douban")
        os.makedirs(temp_dir, exist_ok=True)
        chrome_options.add_argument(f"--user-data-dir={temp_dir}")
        logger.info(f"Chrome临时数据目录: {temp_dir}")

        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

        # 随机UA
        ua = random.choice(USER_AGENTS)
        chrome_options.add_argument(f"user-agent={ua}")

        try:
            if CHROMEDRIVER_PATH and os.path.exists(CHROMEDRIVER_PATH):
                service = Service(CHROMEDRIVER_PATH)
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                self.driver = webdriver.Chrome(options=chrome_options)
        except Exception as e:
            logger.error(f"ChromeDriver初始化失败: {e}")
            logger.error("可能原因:")
            logger.error("  1. ChromeDriver版本与Chrome浏览器不匹配")
            logger.error("  2. Chrome浏览器未安装")
            logger.error("  3. Chrome正在运行中(请先关闭Chrome)")
            logger.error("     Chrome用户数据被锁 -> 关闭所有Chrome窗口后重试")
            raise

        self.driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        self.driver.implicitly_wait(SELENIUM_IMPLICIT_WAIT)

    def _is_verification_page(self):
        """检测当前页面是否是验证页面"""
        try:
            title = self.driver.title
            if "禁止访问" in title or "验证" in title:
                return True
            page_text = self.driver.find_element(By.TAG_NAME, "body").text[:500]
            if "检测到有异常请求" in page_text or "请输入验证码" in page_text:
                return True
        except Exception:
            pass
        return False

    def crawl_list_page(self, start):
        """爬取单页列表，返回电影数据列表"""
        url = f"{self.BASE_URL}?start={start}&filter="
        movies = []

        try:
            self.driver.get(url)
            time.sleep(random.uniform(*LIST_PAGE_LOAD_WAIT))

            # 如果触发验证，等待用户手动通过
            if self._is_verification_page():
                logger.info("验证页面，请在Chrome窗口完成验证...")
                while self._is_verification_page():
                    time.sleep(2)
                self.driver.get(url)
                time.sleep(2)

            # 直接查找电影条目，用多种选择器尝试
            items = []
            selectors = [
                "ol.grid_view > li",
                "ol.grid_view > div.item",
                ".grid_view > li",
                ".grid_view .item",
                ".article ol li",
                ".item",
            ]
            for sel in selectors:
                items = self.driver.find_elements(By.CSS_SELECTOR, sel)
                if items:
                    logger.info(f"  选择器: {sel}, 找到 {len(items)} 个")
                    break

            if not items:
                logger.error(f"未找到电影条目! 页面title: {self.driver.title}")
                return movies

            # 解析时关闭隐式等待——找不到就立即返回，不等
            self.driver.implicitly_wait(0)

            for item in items:
                try:
                    movie = self._parse_list_item(item)
                    if movie:
                        movies.append(movie)
                except Exception as e:
                    pass

            # 恢复隐式等待
            self.driver.implicitly_wait(SELENIUM_IMPLICIT_WAIT)

        except Exception as e:
            logger.error(f"列表页爬取异常: start={start}, {type(e).__name__}: {e}")

        logger.info(f"列表页 start={start} 完成, 获得 {len(movies)} 部")
        return movies

    def _parse_list_item(self, item):
        """解析单个列表项（Selenium版本）"""
        movie = {}

        # 排名
        try:
            em = item.find_element(By.TAG_NAME, "em")
            movie["rank"] = int(em.text.strip())
        except NoSuchElementException:
            return None

        # 标题
        try:
            titles = item.find_elements(By.CSS_SELECTOR, ".title")
            movie["title_cn"] = titles[0].text.strip() if len(titles) > 0 else ""
            movie["title_en"] = titles[1].text.strip("/ ").strip() if len(titles) > 1 else ""
        except NoSuchElementException:
            movie["title_cn"] = ""
            movie["title_en"] = ""

        # 评分
        try:
            rating_el = item.find_element(By.CSS_SELECTOR, ".rating_num")
            movie["rating"] = float(rating_el.text.strip())
        except (NoSuchElementException, ValueError):
            movie["rating"] = 0.0

        # 评价人数 — rating_num的父元素里有"XXXX人评价"
        try:
            rating_el = item.find_element(By.CSS_SELECTOR, ".rating_num")
            parent_text = rating_el.find_element(By.XPATH, "..").text
            import re as _re
            match = _re.search(r'(\d+)\s*人评价', parent_text)
            if match:
                count_text = match.group(1)
                movie["rating_count"] = int(count_text)
            else:
                movie["rating_count"] = 0
        except (NoSuchElementException, ValueError):
            movie["rating_count"] = 0

        # 导演和主演
        movie["director"] = ""
        movie["actors"] = ""
        try:
            p_text = item.find_element(By.CSS_SELECTOR, ".bd p").text
            lines = p_text.strip().split("\n")
            for line in lines:
                line = line.strip()
                if "导演" in line:
                    movie["director"] = re.sub(r'导演[:\s]*', '', line).strip()
                if "主演" in line:
                    movie["actors"] = re.sub(r'主演[:\s]*', '', line).strip()
        except NoSuchElementException:
            pass

        # 简介
        try:
            quote = item.find_element(By.CSS_SELECTOR, ".quote")
            movie["summary"] = quote.text.strip()
        except NoSuchElementException:
            try:
                quote = item.find_element(By.CSS_SELECTOR, ".inq")
                movie["summary"] = quote.text.strip()
            except NoSuchElementException:
                movie["summary"] = ""

        # 详情链接
        try:
            link = item.find_element(By.CSS_SELECTOR, "a")
            movie["detail_url"] = link.get_attribute("href") or ""
        except NoSuchElementException:
            movie["detail_url"] = ""

        # 海报URL（直接从列表页取）
        try:
            poster_img = item.find_element(By.CSS_SELECTOR, "img")
            src = poster_img.get_attribute("src") or ""
            movie["poster_url"] = src
            movie["poster_path"] = src  # 存库前先用URL占位，下载后替换为本地路径
        except NoSuchElementException:
            movie["poster_url"] = ""
            movie["poster_path"] = ""

        # 初始化详情字段
        movie["release_year"] = None
        movie["runtime"] = ""
        movie["genre"] = ""
        movie["imdb_rating"] = 0.0
        movie["poster_path"] = ""
        movie["comments"] = []

        return movie

    def get_detail_info(self, detail_url):
        """获取详情页补充信息"""
        if not detail_url:
            return {}

        info = {}
        try:
            self.driver.get(detail_url)
            time.sleep(random.uniform(*DETAIL_PAGE_LOAD_WAIT))

            if self._is_verification_page():
                while self._is_verification_page():
                    time.sleep(2)
                self.driver.get(detail_url)
                time.sleep(2)

            try:
                info_box = WebDriverWait(self.driver, SELENIUM_TIMEOUT).until(
                    EC.presence_of_element_located((By.ID, "info"))
                )
                info_text = info_box.text

                year_match = re.search(r'(\d{4})', info_text)
                if year_match:
                    info["release_year"] = int(year_match.group(1))

                runtime_match = re.search(r'片长[:\s]*([^\n]+)', info_text)
                if runtime_match:
                    info["runtime"] = runtime_match.group(1).strip().split("/")[0].strip()

                genre_match = re.search(r'类型[:\s]*([^\n]+)', info_text)
                if genre_match:
                    info["genre"] = genre_match.group(1).strip()

                imdb_match = re.search(r'IMDb[:\s]*([\d.]+)', info_text)
                if imdb_match:
                    try:
                        info["imdb_rating"] = float(imdb_match.group(1))
                    except ValueError:
                        pass
            except TimeoutException:
                pass

            # 海报（列表页已有则不需要重新获取）
            if not info.get("poster_url"):
                try:
                    poster = self.driver.find_element(By.CSS_SELECTOR, "#mainpic img")
                    info["poster_url"] = poster.get_attribute("src") or ""
                except NoSuchElementException:
                    pass

        except Exception as e:
            logger.error(f"详情信息异常: {detail_url}, {e}")

        return info

    def get_comments(self, detail_url, max_clicks=None):
        """获取短评 - 先到详情页，再找短评入口"""
        if max_clicks is None:
            max_clicks = COMMENT_LOAD_MORE_CLICKS

        comments = []
        try:
            # 直接拼接comments URL，跳过详情页
            comments_url = detail_url.rstrip("/") + "/comments?status=P"

            # 确保URL格式正确 (处理可能的?from=xxx参数)
            if "?" in detail_url:
                base = detail_url.split("?")[0].rstrip("/")
                comments_url = base + "/comments?status=P"

            self.driver.get(comments_url)
            time.sleep(random.uniform(*COMMENTS_PAGE_LOAD_WAIT))

            # 等评论元素真正出现
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".comment-item"))
                )
            except TimeoutException:
                pass

            if self._is_verification_page():
                while self._is_verification_page():
                    time.sleep(2)
                self.driver.get(comments_url)
                time.sleep(2)

            # 检查是否被重定向到首页(URL不符)
            current = self.driver.current_url
            if "comments" not in current:
                return comments

            # 点击加载更多
            for click_count in range(max_clicks):
                try:
                    load_more_btn = WebDriverWait(self.driver, 2).until(
                        EC.element_to_be_clickable((By.ID, "loadmore"))
                    )
                    self.driver.execute_script("arguments[0].scrollIntoView();", load_more_btn)
                    time.sleep(0.3)
                    load_more_btn.click()
                    time.sleep(random.uniform(0.8, 1.5))
                except (TimeoutException, ElementClickInterceptedException, NoSuchElementException):
                    break

            # 解析短评
            comment_items = self.driver.find_elements(By.CSS_SELECTOR, ".comment-item")
            self.driver.implicitly_wait(0)
            for item in comment_items[:50]:
                try:
                    c = {}
                    try:
                        c["commenter"] = item.find_element(By.CSS_SELECTOR, ".comment-info a").text.strip()
                    except NoSuchElementException:
                        c["commenter"] = "匿名"

                    try:
                        rating_span = item.find_element(By.CSS_SELECTOR, ".comment-info .rating")
                        rating_class = rating_span.get_attribute("class")
                        rating_map = {
                            "allstar50": "5星", "allstar45": "4.5星", "allstar40": "4星",
                            "allstar35": "3.5星", "allstar30": "3星", "allstar25": "2.5星",
                            "allstar20": "2星", "allstar15": "1.5星", "allstar10": "1星",
                            "allstar05": "0.5星",
                        }
                        stars = "未评分"
                        for cls, star_text in rating_map.items():
                            if cls in rating_class:
                                stars = star_text
                                break
                        c["rating"] = stars
                    except NoSuchElementException:
                        c["rating"] = "未评分"

                    try:
                        c["content"] = item.find_element(By.CSS_SELECTOR, ".comment-content").text.strip()
                    except NoSuchElementException:
                        c["content"] = ""

                    try:
                        c["comment_time"] = item.find_element(By.CSS_SELECTOR, ".comment-time").text.strip()
                    except NoSuchElementException:
                        c["comment_time"] = ""

                    if c.get("content"):
                        comments.append(c)
                except Exception:
                    pass
            self.driver.implicitly_wait(SELENIUM_IMPLICIT_WAIT)

        except Exception as e:
            logger.error(f"短评异常: {detail_url}, {e}")
            self.driver.implicitly_wait(SELENIUM_IMPLICIT_WAIT)

        return comments[:50]

    def _inject_cookies(self):
        """从douban_cookies.json注入Cookie到Selenium浏览器"""
        cookie_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "douban_cookies.json"
        )
        if not os.path.exists(cookie_file):
            logger.warning("Cookie文件不存在，跳过注入")
            return False

        import json
        with open(cookie_file, "r", encoding="utf-8") as f:
            cookies = json.load(f)

        # 先访问豆瓣域名（Cookie注入需要该域名的页面已加载）
        self.driver.get("https://movie.douban.com/")
        time.sleep(2)

        success = 0
        for c in cookies:
            try:
                cookie_dict = {
                    "name": c["name"],
                    "value": c["value"],
                    "domain": c.get("domain", ".douban.com"),
                    "path": "/",
                }
                # 去掉可能导致问题的字段
                if "domain" in cookie_dict and not cookie_dict["domain"].startswith("."):
                    cookie_dict["domain"] = "." + cookie_dict["domain"]
                self.driver.add_cookie(cookie_dict)
                success += 1
            except Exception:
                pass

        logger.info(f"已注入 {success}/{len(cookies)} 条Cookie到浏览器")
        return success > 0

    def crawl_all(self, pages=None, with_comments=True, with_details=True,
                  existing_movies=None):
        """
        完整爬取流程（支持断点续传）
        pages: 爬取页数（默认10页=250部）
        with_comments: 是否爬取短评
        with_details: 是否爬取详情页补充信息
        existing_movies: 已有电影数据列表（用于跳过已爬取的）
        """
        if pages is None:
            pages = TOTAL_PAGES

        # 从已有数据中提取已爬取的rank集合
        existing_ranks = set()
        if existing_movies:
            for m in existing_movies:
                if m.get("rank"):
                    existing_ranks.add(m["rank"])
            logger.info(f"已有 {len(existing_ranks)} 部电影数据，将跳过列表页和详情页")

        all_movies = list(existing_movies) if existing_movies else []
        logger.info("=" * 50)
        logger.info("Selenium爬虫开始 (使用Chrome浏览器)")
        logger.info(f"已有={len(existing_ranks)}, 需爬列表={not existing_ranks}, "
                    f"详情={with_details}, 短评={with_comments}")
        logger.info("=" * 50)

        # 注入Cookie
        if not existing_ranks:
            self._inject_cookies()
            time.sleep(2)

        # 等待用户完成人机验证
        if self._is_verification_page():
            logger.info("=== 检测到验证页面，请在Chrome窗口手动完成验证 ===")
            while self._is_verification_page():
                time.sleep(2)
            logger.info("=== 验证通过，开始爬取 ===")

        # 列表页（跳过已有的）
        if not existing_ranks:
            for page in range(pages):
                start = page * 25
                logger.info(f"--- 列表页 {page+1}/{pages} (start={start}) ---")
                movies = self.crawl_list_page(start)
                all_movies.extend(movies)
                if page < pages - 1:
                    time.sleep(random.uniform(*BETWEEN_LIST_PAGES))
            logger.info(f"列表页完成: {len(all_movies)} 部")
        else:
            # 重新注入Cookie（可能过期）
            self._inject_cookies()
            time.sleep(2)

        # 详情页（只爬取没有release_year的）
        if with_details:
            need_details = [m for m in all_movies if not m.get("release_year")]
            if need_details:
                logger.info(f"--- 详情页: {len(need_details)} 部待爬 ---")
                for i, movie in enumerate(need_details):
                    if i % 10 == 0:
                        logger.info(f"详情进度: {i+1}/{len(need_details)}")
                    detail_url = movie.get("detail_url", "")
                    if detail_url:
                        info = self.get_detail_info(detail_url)
                        movie.update({k: v for k, v in info.items() if v})
                        time.sleep(random.uniform(*BETWEEN_DETAIL_PAGES))
            else:
                logger.info("详情页: 全部已有，跳过")

        # 中间保存：详情完成后立即存库，防止短评阶段出问题白爬
        if with_details and need_details:
            self._save_movies_intermediate(all_movies)

        # 短评（跳过数据库里已有短评的电影）
        if with_comments:
            existing_comment_ranks = self._get_existing_comment_ranks()
            need_comments = [m for m in all_movies
                           if m.get("rank") not in existing_comment_ranks]
            if need_comments:
                logger.info(f"--- 短评: {len(need_comments)} 部待爬 (每50部自动保存) ---")
                total_comments = 0
                for i, movie in enumerate(need_comments):
                    if i % 5 == 0:
                        logger.info(f"短评进度: {i+1}/{len(need_comments)}, 已获{total_comments}条")
                    detail_url = movie.get("detail_url", "")
                    if detail_url:
                        comments = self.get_comments(detail_url)
                        movie["comments"] = comments
                        total_comments += len(comments)
                        time.sleep(random.uniform(*BETWEEN_COMMENTS))

                    # 每50部保存一次短评
                    if (i + 1) % 50 == 0:
                        self._save_comments_batch(need_comments[:i+1])
                        logger.info(f">>> 短评已保存 ({i+1}部, {total_comments}条) <<<")

                # 最后一批保存
                self._save_comments_batch(need_comments)
                logger.info(f"短评完成: {total_comments} 条，已全部入库")
            else:
                logger.info("短评: 全部已有，跳过")

        return all_movies

    def _get_existing_comment_ranks(self):
        """查询数据库，返回已有短评的电影rank集合"""
        try:
            from database.db_manager import DatabaseManager
            import config as cfg
            db = DatabaseManager(db_type=cfg.DB_TYPE)
            cursor = db.conn.execute(
                "SELECT DISTINCT m.rank FROM movies m INNER JOIN comments c ON m.id = c.movie_id"
            )
            ranks = set(row[0] for row in cursor.fetchall())
            db.close()
            logger.info(f"数据库中已有短评的电影: {len(ranks)} 部")
            return ranks
        except Exception as e:
            logger.warning(f"查询已有短评失败: {e}")
            return set()

    def _save_comments_batch(self, movies):
        """批量保存短评到数据库"""
        try:
            from database.db_manager import DatabaseManager
            import config as cfg
            db = DatabaseManager(db_type=cfg.DB_TYPE)
            saved = 0
            for m in movies:
                comments = m.get("comments", [])
                if comments:
                    db_movie_id = None
                    cursor = db.conn.execute(
                        "SELECT id FROM movies WHERE rank = ?", (m.get("rank"),)
                    )
                    row = cursor.fetchone()
                    if row:
                        db_movie_id = row[0]
                        # 只插入新短评
                        existing = db.conn.execute(
                            "SELECT COUNT(*) FROM comments WHERE movie_id = ?",
                            (db_movie_id,)
                        ).fetchone()[0]
                        if existing == 0:
                            for c in comments:
                                db.conn.execute(
                                    "INSERT INTO comments (movie_id, commenter, rating, content, comment_time) VALUES (?, ?, ?, ?, ?)",
                                    (db_movie_id, c.get("commenter", ""), c.get("rating", ""),
                                     c.get("content", ""), c.get("comment_time", ""))
                                )
                                saved += 1
                    db.conn.commit()
            db.close()
        except Exception as e:
            logger.error(f"短评保存失败: {e}")

    def _save_movies_intermediate(self, movies):
        """中间保存电影数据到数据库（不包含短评）"""
        try:
            from database.db_manager import DatabaseManager
            import config as cfg
            db = DatabaseManager(db_type=cfg.DB_TYPE)
            for m in movies:
                db.insert_movie(m)
            stats = db.get_stats()
            logger.info(f"中间保存完成: {stats['total_movies']} 部电影已写入数据库")
            db.close()
        except Exception as e:
            logger.error(f"中间保存失败: {e}")

    def quit(self):
        """关闭浏览器"""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
