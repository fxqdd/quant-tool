"""
情绪分析器
基于新闻、社交媒体等文本数据进行情感分析
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import re


class SentimentAnalyzer:
    """
    情绪分析器
    利用规则-based方法进行简单的情绪打分
    (可扩展接入LLM API)
    """

    POSITIVE_WORDS = [
        "涨", "大涨", "涨停", "突破", "创新高", "增长", "盈利", "超预期",
        "买入", "增持", "推荐", "看好", "机会", "上升", "走强", "拉升",
        "利好", "业绩", "订单", "合作", "中标", "签约"
    ]

    NEGATIVE_WORDS = [
        "跌", "大跌", "跌停", "破位", "创新低", "亏损", "不及预期",
        "卖出", "减持", "下调", "看空", "风险", "下降", "走弱", "砸盘",
        "利空", "业绩", "裁员", "诉讼", "处罚", "违约"
    ]

    NEUTRAL_WORDS = [
        "公告", "会议", "报告", "数据", "统计", "发布", "表示", "称"
    ]

    def __init__(self):
        self.positive_pattern = self._build_pattern(self.POSITIVE_WORDS)
        self.negative_pattern = self._build_pattern(self.NEGATIVE_WORDS)
        self.neutral_pattern = self._build_pattern(self.NEUTRAL_WORDS)

    def _build_pattern(self, words: List[str]) -> re.Pattern:
        """构建正则匹配模式"""
        pattern = "|".join([re.escape(w) for w in words])
        return re.compile(pattern)

    def analyze_text(self, text: str) -> Dict:
        """
        分析单条文本的情绪
        """
        if not text or not isinstance(text, str):
            return {"score": 0, "label": "中性", "confidence": 0}

        pos_matches = len(self.positive_pattern.findall(text))
        neg_matches = len(self.negative_pattern.findall(text))
        
        total = pos_matches + neg_matches
        
        if total == 0:
            score = 0
            label = "中性"
            confidence = 0.3
        else:
            score = (pos_matches - neg_matches) / total
            
            if score > 0.3:
                label = "看多"
            elif score < -0.3:
                label = "看空"
            else:
                label = "中性"
            
            confidence = min(abs(score) * 0.8 + 0.2, 1.0)
        
        return {
            "score": round(score, 3),
            "label": label,
            "confidence": round(confidence, 3),
            "pos_count": pos_matches,
            "neg_count": neg_matches
        }

    def analyze_batch(self, texts: List[Dict]) -> Dict:
        """
        批量分析文本
        
        texts: List[{"title": str, "content": str, "date": str, "source": str}]
        """
        if not texts:
            return {
                "avg_score": 0,
                "label": "中性",
                "total": 0,
                "positive": 0,
                "negative": 0,
                "neutral": 0,
                "details": []
            }
        
        results = []
        for item in texts:
            title = item.get("title", "")
            content = item.get("content", "")
            full_text = f"{title} {content}"
            
            result = self.analyze_text(full_text)
            result["date"] = item.get("date", "")
            result["source"] = item.get("source", "")
            results.append(result)
        
        avg_score = np.mean([r["score"] for r in results])
        
        positive = len([r for r in results if r["label"] == "看多"])
        negative = len([r for r in results if r["label"] == "看空"])
        neutral = len([r for r in results if r["label"] == "中性"])
        
        if avg_score > 0.2:
            label = "看多"
        elif avg_score < -0.2:
            label = "看空"
        else:
            label = "中性"
        
        return {
            "avg_score": round(avg_score, 3),
            "label": label,
            "total": len(results),
            "positive": positive,
            "negative": negative,
            "neutral": neutral,
            "details": results
        }

    def compare_price_sentiment(
        self,
        price_change: float,
        sentiment_score: float
    ) -> Dict:
        """
        对比价格走势与情绪
        用于检测背离
        """
        result = {
            "price_change": price_change,
            "sentiment_score": sentiment_score,
            "divergence": None,
            "signal": "一致"
        }
        
        if price_change > 2 and sentiment_score < -0.2:
            result["divergence"] = "顶背离"
            result["signal"] = "看跌"
        elif price_change < -2 and sentiment_score > 0.2:
            result["divergence"] = "底背离"
            result["signal"] = "看涨"
        
        return result


if __name__ == "__main__":
    analyzer = SentimentAnalyzer()
    
    test_texts = [
        {"title": "某公司业绩大涨", "content": "公司发布财报显示营收同比增长50%，超出市场预期", "date": "2026-03-30"},
        {"title": "股价跌停", "content": "受利空消息影响，公司股价今日跌停", "date": "2026-03-29"},
        {"title": "发布公告", "content": "公司今日召开临时股东大会", "date": "2026-03-28"},
    ]
    
    result = analyzer.analyze_batch(test_texts)
    print("情绪分析结果:")
    print(f"平均得分: {result['avg_score']}")
    print(f"情绪标签: {result['label']}")
    print(f"看多/看空/中性: {result['positive']}/{result['negative']}/{result['neutral']}")
