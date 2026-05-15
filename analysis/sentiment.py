"""
情感分析模块 - jieba分词 + SnowNLP情感分析 + wordcloud词云
"""
import os
import re
import numpy as np
from collections import Counter
from config import CHARTS_DIR, WORDCLOUD_FONT_PATH, WORDCLOUD_WIDTH, WORDCLOUD_HEIGHT, WORDCLOUD_MAX_WORDS
from utils.logger import get_logger

logger = get_logger("sentiment_analyzer")


class SentimentAnalyzer:
    """短评情感分析器"""

    def __init__(self, comments_df):
        self.comments_df = comments_df
        self.sentiment_results = None
        self.word_freq = None

        # 延迟导入分词和情感分析库
        self._jieba = None
        self._SnowNLP = None

    @property
    def jieba(self):
        if self._jieba is None:
            try:
                import jieba
                self._jieba = jieba
            except ImportError:
                logger.error("jieba未安装，请运行: pip install jieba")
                raise
        return self._jieba

    @property
    def SnowNLP(self):
        if self._SnowNLP is None:
            try:
                from snownlp import SnowNLP as SNLP
                self._SnowNLP = SNLP
            except ImportError:
                logger.error("SnowNLP未安装，请运行: pip install snownlp")
                raise
        return self._SnowNLP

    def clean_text(self, text):
        """清洗评论文本"""
        if not text:
            return ""
        # 去除HTML标签
        text = re.sub(r"<[^>]+>", "", text)
        # 去除URL
        text = re.sub(r"http[s]?://\S+", "", text)
        # 去除特殊字符但保留中文、英文、数字
        text = re.sub(r"[^一-龥a-zA-Z0-9\s]", "", text)
        return text.strip()

    def analyze_sentiment(self):
        """
        对每条短评进行情感分析
        使用SnowNLP (0-1之间的值, >0.6为正面, 0.4-0.6中性, <0.4负面)
        """
        if self.comments_df is None or len(self.comments_df) == 0:
            logger.warning("无短评数据，跳过情感分析")
            return []

        logger.info("开始情感分析...")
        results = []
        contents = self.comments_df["content"].dropna().tolist()

        for text in contents:
            cleaned = self.clean_text(text)
            if len(cleaned) < 5:
                continue
            try:
                s = self.SnowNLP(cleaned)
                score = s.sentiments
                if score > 0.6:
                    sentiment = "正面"
                elif score < 0.4:
                    sentiment = "负面"
                else:
                    sentiment = "中性"
                results.append({
                    "content": cleaned,
                    "score": round(score, 4),
                    "sentiment": sentiment,
                })
            except Exception as e:
                logger.debug(f"情感分析异常: {e}")

        self.sentiment_results = results
        logger.info(f"情感分析完成: {len(results)} 条")
        return results

    def get_sentiment_stats(self):
        """获取情感分析统计"""
        if not self.sentiment_results:
            self.analyze_sentiment()

        total = len(self.sentiment_results)
        if total == 0:
            return {"positive": 0, "neutral": 0, "negative": 0, "total": 0}

        sentiments = [r["sentiment"] for r in self.sentiment_results]
        counter = Counter(sentiments)

        return {
            "positive": counter.get("正面", 0),
            "neutral": counter.get("中性", 0),
            "negative": counter.get("负面", 0),
            "total": total,
            "positive_pct": round(counter.get("正面", 0) / total * 100, 1),
            "neutral_pct": round(counter.get("中性", 0) / total * 100, 1),
            "negative_pct": round(counter.get("负面", 0) / total * 100, 1),
            "avg_score": round(np.mean([r["score"] for r in self.sentiment_results]), 4),
        }

    def extract_keywords(self, top_n=30):
        """使用jieba进行中文分词并提取关键词"""
        if self.comments_df is None or len(self.comments_df) == 0:
            return {}

        logger.info("开始分词提取关键词...")
        contents = self.comments_df["content"].dropna().tolist()
        all_text = " ".join([self.clean_text(t) for t in contents])

        # 添加自定义词典（电影相关词汇）
        for word in ["剧情", "演技", "特效", "导演", "演员", "配乐", "画面", "故事", "结局", "节奏"]:
            self.jieba.add_word(word)

        # 分词
        words = self.jieba.cut(all_text)

        # 停用词
        stopwords = set([
            "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一",
            "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着",
            "没有", "看", "好", "自己", "这", "他", "她", "它", "们", "那", "些",
            "但", "是", "之", "而", "或", "且", "与", "及", "被", "把", "让",
            "从", "为", "以", "对", "等", "个", "中", "里", "还", "这个",
            "太", "就", "也", "很", "非常", "比较", "那么", "可以", "所以",
            "这样", "那样", "怎么", "什么", "因为", "如果", "虽然", "但是",
            "然后", "最后", "开始", "已经", "正在", "将", "可以", "应该",
            "觉得", "感觉", "可能", "也许", "一定", "一部", "真的", "一部",
        ])

        # 过滤
        word_freq = Counter()
        for word in words:
            word = word.strip()
            if len(word) >= 2 and word not in stopwords and not word.isdigit():
                word_freq[word] += 1

        self.word_freq = dict(word_freq.most_common(top_n))
        logger.info(f"关键词提取完成: {len(self.word_freq)} 个")
        return self.word_freq

    def generate_wordcloud(self):
        """生成词云图"""
        if not self.word_freq:
            self.extract_keywords()

        if not self.word_freq:
            logger.warning("无词汇数据，无法生成词云")
            return None

        try:
            from wordcloud import WordCloud
            import matplotlib.pyplot as plt

            font_path = WORDCLOUD_FONT_PATH
            if font_path is None:
                # 尝试自动检测中文字体
                import matplotlib.font_manager as fm
                chinese_fonts = [f for f in fm.findSystemFonts() if "simhei" in f.lower() or "msyh" in f.lower()]
                if chinese_fonts:
                    font_path = chinese_fonts[0]
                else:
                    font_path = fm.findSystemFonts()[0]

            wc = WordCloud(
                font_path=font_path,
                width=WORDCLOUD_WIDTH,
                height=WORDCLOUD_HEIGHT,
                max_words=WORDCLOUD_MAX_WORDS,
                background_color="white",
                colormap="viridis",
                collocations=False,
            )
            wc.generate_from_frequencies(self.word_freq)

            fig, ax = plt.subplots(figsize=(12, 8))
            ax.imshow(wc, interpolation="bilinear")
            ax.axis("off")
            ax.set_title("豆瓣电影Top250 短评词云", fontsize=16, fontweight="bold")

            path = os.path.join(CHARTS_DIR, "07_wordcloud.png")
            fig.tight_layout()
            fig.savefig(path, dpi=150, bbox_inches="tight")
            plt.close(fig)
            logger.info(f"词云图已生成")
            return path
        except Exception as e:
            logger.error(f"词云生成失败: {e}")
            return None

    def generate_full_report(self):
        """生成完整情感分析报告"""
        sentiment_stats = self.get_sentiment_stats()
        keywords = self.extract_keywords()
        wordcloud_path = self.generate_wordcloud()

        return {
            "sentiment_stats": sentiment_stats,
            "top_keywords": keywords,
            "wordcloud_path": wordcloud_path,
        }
