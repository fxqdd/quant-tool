"""
四层噪声过滤器
用于过滤文本和信号中的噪声
"""

import re
import time
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class Signal:
    """信号数据结构"""
    source: str
    content: str
    sentiment: float  # -1 ~ 1
    confidence: float  # 0 ~ 1
    timestamp: str
    signal_type: str  # "news", "post", "comment"


class TextNoiseFilter:
    """第一层：文本噪声过滤器"""
    
    NOISE_PATTERNS = [
        (r"开户|荐股|微信\d+|QQ\d+|股票交流", "广告推销"),
        (r"哈哈{3,}|呵呵{3,}|卧槽{2,}", "无意义重复"),
        (r"如图|如图所示|见下图|见图片", "无内容引用"),
        (r"本文不代表|不构成投资|风险自担", "免责声明"),
        (r"^\d{6}$", "纯代码"),
        (r"^\s*$", "空白"),
        (r"转发|分享|收藏", "无效动作"),
    ]
    
    MIN_TEXT_LENGTH = 10
    MAX_TEXT_LENGTH = 5000
    
    def filter(self, text: str) -> Tuple[bool, str]:
        """
        判断文本是否为噪声
        Returns: (is_noise, reason)
        """
        if not text or len(text.strip()) < self.MIN_TEXT_LENGTH:
            return True, "文本过短"
        
        if len(text) > self.MAX_TEXT_LENGTH:
            return True, "文本过长"
        
        for pattern, reason in self.NOISE_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True, f"匹配噪声模式: {reason}"
        
        return False, ""
    
    def filter_batch(self, texts: List[str]) -> List[str]:
        """批量过滤"""
        return [t for t in texts if not self.filter(t)[0]]


class SentimentNoiseFilter:
    """第二层：情感信号噪声过滤器"""
    
    MIN_CONFIDENCE = 0.5
    
    TIME_DECAY_RATE = 0.05  # 每天衰减5%
    
    SOURCE_WEIGHTS = {
        "官方公告": 1.0,
        "券商研报": 0.9,
        "财经媒体": 0.7,
        "雪球精选": 0.6,
        "股吧热帖": 0.4,
        "散户评论": 0.3,
    }
    
    def filter_signals(self, signals: List[Signal]) -> List[Signal]:
        """
        过滤不可靠的情感信号
        """
        filtered = []
        
        for sig in signals:
            # 1. 置信度过滤
            if sig.confidence < self.MIN_CONFIDENCE:
                continue
            
            # 2. 来源权重过滤
            weight = self.SOURCE_WEIGHTS.get(sig.source, 0.3)
            if weight * sig.confidence < 0.3:
                continue
            
            # 3. 时间衰减
            days_old = self._calc_days_old(sig.timestamp)
            decay = 1.0 - (days_old * self.TIME_DECAY_RATE)
            effective_confidence = sig.confidence * max(decay, 0.5)
            
            sig.confidence = effective_confidence
            filtered.append(sig)
        
        # 4. 交叉验证：多个独立来源的一致信号
        filtered = self._cross_validate(filtered)
        
        return filtered
    
    def _calc_days_old(self, timestamp: str) -> float:
        """计算时间戳距离现在多少天"""
        try:
            from datetime import datetime
            dt = datetime.strptime(timestamp, "%Y-%m-%d")
            now = datetime.now()
            return (now - dt).days
        except:
            return 30  # 默认30天
    
    def _cross_validate(self, signals: List[Signal]) -> List[Signal]:
        """
        交叉验证：只有多个独立来源的一致信号才可信
        """
        if len(signals) < 2:
            return signals
        
        positive = sum(1 for s in signals if s.sentiment > 0.2)
        negative = sum(1 for s in signals if s.sentiment < -0.2)
        neutral = sum(1 for s in signals if -0.2 <= s.sentiment <= 0.2)
        
        total = len(signals)
        
        if positive / total >= 0.6 or negative / total >= 0.6:
            return signals
        
        if neutral / total > 0.5:
            for sig in signals:
                sig.confidence *= 0.5
        
        return signals


class OutlierFilter:
    """第三层：统计异常值过滤器"""
    
    def remove_outliers_iqr(self, values: List[float]) -> List[float]:
        """IQR法（四分位距）剔除异常值"""
        if len(values) < 4:
            return values
        
        sorted_vals = sorted(values)
        q1_idx = len(sorted_vals) // 4
        q3_idx = 3 * len(sorted_vals) // 4
        
        q1 = sorted_vals[q1_idx]
        q3 = sorted_vals[q3_idx]
        iqr = q3 - q1
        
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        
        return [v for v in values if lower <= v <= upper]
    
    def remove_outliers_zscore(self, values: List[float], threshold: float = 2.5) -> List[float]:
        """Z-score法（标准差）剔除异常值"""
        if len(values) < 3:
            return values
        
        import numpy as np
        mean = np.mean(values)
        std = np.std(values)
        
        if std == 0:
            return values
        
        return [v for v in values if abs((v - mean) / std) <= threshold]
    
    def filter_sentiments(self, sentiments: List[float]) -> List[float]:
        """过滤情感值中的异常值"""
        if len(sentiments) < 3:
            return sentiments
        
        result = self.remove_outliers_iqr(sentiments)
        result = self.remove_outliers_zscore(result)
        
        return result


class SignalConsistencyChecker:
    """第四层：信号一致性检验"""
    
    def __init__(self):
        self.required_agreement = 2  # 至少需要2个维度一致
    
    def check(self, signals: Dict[str, any]) -> Tuple[bool, str]:
        """
        检查各维度信号是否一致
        signals: {
            "technical": {"direction": "偏多/偏空/中性", "score": float},
            "fundamental": {"direction": "良好/一般/较差", "score": float},
            "sentiment": float  # -1 ~ 1
        }
        """
        tech_dir = signals.get("technical", {}).get("direction", "中性")
        fund_dir = signals.get("fundamental", {}).get("direction", "一般")
        sent_dir = "偏多" if signals.get("sentiment", 0) > 0.2 else ("偏空" if signals.get("sentiment", 0) < -0.2 else "中性")
        
        votes = {"偏多": 0, "偏空": 0, "中性": 0}
        
        if tech_dir == "偏多":
            votes["偏多"] += 1
        elif tech_dir == "偏空":
            votes["偏空"] += 1
        else:
            votes["中性"] += 1
        
        if fund_dir == "良好":
            votes["偏多"] += 1
        elif fund_dir == "较差":
            votes["偏空"] += 1
        
        if sent_dir == "偏多":
            votes["偏多"] += 1
        elif sent_dir == "偏空":
            votes["偏空"] += 1
        
        max_vote = max(votes.values())
        direction = max(votes, key=votes.get)
        
        if max_vote >= self.required_agreement:
            confidence = max_vote / 3.0
            return True, f"{direction}（置信度{confidence:.0%}）"
        else:
            return False, "多空分歧严重，建议观望"
    
    def get_final_action(self, score: float, is_consistent: bool) -> Tuple[str, float]:
        """
        根据综合得分和一致性决定最终操作
        Returns: (action, confidence)
        """
        if not is_consistent:
            return "观望", 0.0
        
        confidence = min(abs(score), 1.0)
        
        if score >= 0.3:
            return "可以考虑买入", confidence
        elif score <= -0.3:
            return "建议回避", confidence
        else:
            return "轻度观望", confidence * 0.5


class NoiseFilterPipeline:
    """噪声过滤管道（串联四层过滤器）"""
    
    def __init__(self):
        self.text_filter = TextNoiseFilter()
        self.sentiment_filter = SentimentNoiseFilter()
        self.outlier_filter = OutlierFilter()
        self.consistency_checker = SignalConsistencyChecker()
    
    def filter_texts(self, texts: List[str]) -> List[str]:
        """过滤文本噪声"""
        return self.text_filter.filter_batch(texts)
    
    def filter_signals(self, signals: List[Signal]) -> List[Signal]:
        """过滤信号噪声"""
        return self.sentiment_filter.filter_signals(signals)
    
    def filter_sentiments(self, sentiments: List[float]) -> List[float]:
        """过滤情感值噪声"""
        return self.outlier_filter.filter_sentiments(sentiments)
    
    def check_consistency(self, signals: Dict[str, any]) -> Tuple[bool, str]:
        """检查信号一致性"""
        return self.consistency_checker.check(signals)
    
    def get_final_action(self, score: float, signals: Dict[str, any]) -> Dict:
        """获取最终操作建议"""
        is_consistent, reason = self.check_consistency(signals)
        action, confidence = self.consistency_checker.get_final_action(score, is_consistent)
        
        return {
            "action": action,
            "confidence": confidence,
            "reason": reason,
            "is_consistent": is_consistent
        }


if __name__ == "__main__":
    pipeline = NoiseFilterPipeline()
    
    texts = [
        "这家公司业绩大涨50%，超出市场预期",
        "开户找我，微信123456",
        "哈哈哈太好了",
        "如图所示，股价将上涨",
        "利润同比增长30%，持续看好",
    ]
    
    print("文本过滤测试:")
    for t in texts:
        is_noise, reason = pipeline.text_filter.filter(t)
        print(f"  {'[噪声]' if is_noise else '[有效]'} {t[:30]}... - {reason}")
    
    signals = [
        Signal("官方公告", "业绩大涨", 0.8, 0.9, "2026-03-28", "news"),
        Signal("散户评论", "跌死了", -0.3, 0.4, "2026-03-29", "comment"),
        Signal("财经媒体", "持续看好", 0.6, 0.7, "2026-03-27", "news"),
    ]
    
    print("\n信号过滤测试:")
    filtered = pipeline.filter_signals(signals)
    for s in filtered:
        print(f"  {s.source}: {s.sentiment} (置信度:{s.confidence:.2f})")
