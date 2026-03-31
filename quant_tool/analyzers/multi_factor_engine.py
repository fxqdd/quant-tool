"""
多因子融合引擎
综合技术面、基本面、情绪面三个维度
"""

from typing import Dict, Tuple
from dataclasses import dataclass
from .noise_filter import NoiseFilterPipeline


@dataclass
class MultiFactorResult:
    """多因子融合结果"""
    action: str = "观望"
    score: float = 0
    confidence: float = 0
    reason: str = ""
    technical_score: float = 0
    fundamental_score: float = 0
    sentiment_score: float = 0
    is_consistent: bool = False
    signals: Dict = None
    
    def __post_init__(self):
        if self.signals is None:
            self.signals = {}


class MultiFactorEngine:
    """
    多因子融合引擎
    
    综合三个维度的信号，通过加权融合得出最终结论
    """
    
    DEFAULT_WEIGHTS = {
        "technical": 0.40,
        "fundamental": 0.30,
        "sentiment": 0.30
    }
    
    def __init__(self, weights: Dict[str, float] = None):
        self.weights = weights or self.DEFAULT_WEIGHTS
        self.noise_filter = NoiseFilterPipeline()
    
    def fuse(
        self,
        technical_signals: Dict,
        fundamental_signals: Dict,
        sentiment_signals: Dict
    ) -> MultiFactorResult:
        """
        融合多因子信号
        
        Args:
            technical_signals: 技术面信号
                {
                    "direction": "偏多/偏空/中性",
                    "score": -3 ~ +3,
                    "signals": [...]
                }
            fundamental_signals: 基本面信号
                {
                    "direction": "良好/一般/较差",
                    "score": -1 ~ +1
                }
            sentiment_signals: 情绪面信号
                -1 ~ +1 (负数=看空, 正数=看多)
        
        Returns:
            MultiFactorResult
        """
        result = MultiFactorResult()
        
        tech_score = self._normalize_technical(technical_signals)
        fund_score = self._normalize_fundamental(fundamental_signals)
        sent_score = self._normalize_sentiment(sentiment_signals)
        
        result.technical_score = tech_score
        result.fundamental_score = fund_score
        result.sentiment_score = sent_score
        
        result.score = (
            tech_score * self.weights["technical"] +
            fund_score * self.weights["fundamental"] +
            sent_score * self.weights["sentiment"]
        )
        
        signals_for_check = {
            "technical": technical_signals,
            "fundamental": fundamental_signals,
            "sentiment": sentiment_signals
        }
        
        result.is_consistent, result.reason = self.noise_filter.check_consistency(signals_for_check)
        
        final_action = self.noise_filter.get_final_action(result.score, signals_for_check)
        result.action = final_action["action"]
        result.confidence = final_action["confidence"]
        
        result.signals = {
            "technical": technical_signals,
            "fundamental": fundamental_signals,
            "sentiment": sentiment_signals
        }
        
        return result
    
    def _normalize_technical(self, signals: Dict) -> float:
        """标准化技术面得分到 -1 ~ 1"""
        score = signals.get("score", 0)
        direction = signals.get("direction", "中性")
        
        if direction == "上涨" or direction == "偏多":
            base = 0.5
        elif direction == "下跌" or direction == "偏空":
            base = -0.5
        else:
            base = 0
        
        normalized = (score / 3) * 0.5 + base
        
        return max(-1, min(1, normalized))
    
    def _normalize_fundamental(self, signals: Dict) -> float:
        """标准化基本面积分到 -1 ~ 1"""
        direction = signals.get("direction", "一般")
        
        if direction == "优秀" or direction == "良好":
            return 0.5
        elif direction == "较差":
            return -0.5
        else:
            return 0
    
    def _normalize_sentiment(self, signals) -> float:
        """标准化情绪面积分到 -1 ~ 1"""
        if isinstance(signals, dict):
            return max(-1, min(1, signals.get("score", 0)))
        elif isinstance(signals, (int, float)):
            return max(-1, min(1, signals))
        else:
            return 0
    
    def get_weighted_explanation(self, result: MultiFactorResult) -> str:
        """生成加权解释"""
        explanations = []
        
        if result.technical_score > 0.2:
            explanations.append("技术面偏好")
        elif result.technical_score < -0.2:
            explanations.append("技术面偏空")
        
        if result.fundamental_score > 0.2:
            explanations.append("基本面良好")
        elif result.fundamental_score < -0.2:
            explanations.append("基本面偏差")
        
        if result.sentiment_score > 0.2:
            explanations.append("市场情绪向好")
        elif result.sentiment_score < -0.2:
            explanations.append("市场情绪谨慎")
        
        return "，".join(explanations) if explanations else "多空信号均衡"


class AdaptiveMultiFactorEngine(MultiFactorEngine):
    """
    自适应多因子引擎
    根据不同市场状态调整因子权重
    """
    
    MARKET_STATES = {
        "bull": {  # 牛市
            "technical": 0.30,
            "fundamental": 0.30,
            "sentiment": 0.40
        },
        "bear": {  # 熊市
            "technical": 0.50,
            "fundamental": 0.30,
            "sentiment": 0.20
        },
        "volatile": {  # 震荡市
            "technical": 0.40,
            "fundamental": 0.30,
            "sentiment": 0.30
        },
        "default": {  # 默认
            "technical": 0.40,
            "fundamental": 0.30,
            "sentiment": 0.30
        }
    }
    
    def detect_market_state(self, technical_signals: Dict) -> str:
        """检测市场状态"""
        trend = technical_signals.get("trend", "")
        
        if "上涨" in trend:
            return "bull"
        elif "下跌" in trend:
            return "bear"
        else:
            return "volatile"
    
    def fuse_adaptive(
        self,
        technical_signals: Dict,
        fundamental_signals: Dict,
        sentiment_signals: Dict
    ) -> MultiFactorResult:
        """自适应融合"""
        state = self.detect_market_state(technical_signals)
        self.weights = self.MARKET_STATES.get(state, self.MARKET_STATES["default"])
        
        return self.fuse(technical_signals, fundamental_signals, sentiment_signals)


if __name__ == "__main__":
    engine = MultiFactorEngine()
    
    tech_signals = {
        "direction": "上涨",
        "score": 2,
        "signals": ["MACD金叉", "均线多头"]
    }
    
    fund_signals = {
        "direction": "良好",
        "score": 0.5
    }
    
    sent_signals = {
        "score": 0.3
    }
    
    result = engine.fuse(tech_signals, fund_signals, sent_signals)
    
    print("=" * 50)
    print("多因子融合结果")
    print("=" * 50)
    print(f"最终操作: {result.action}")
    print(f"综合得分: {result.score:.3f}")
    print(f"置信度: {result.confidence:.1%}")
    print(f"一致性: {result.is_consistent}")
    print(f"原因: {result.reason}")
    print(f"技术面: {result.technical_score:.3f}")
    print(f"基本面: {result.fundamental_score:.3f}")
    print(f"情绪面: {result.sentiment_score:.3f}")
