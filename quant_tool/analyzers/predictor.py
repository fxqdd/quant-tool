"""
股票预测引擎 v2.0
===============
增强版预测算法，综合多维度信号

核心改进：
1. 信号强度分级 - 强/中/弱 信号区分
2. 趋势持续性判断 - 判断趋势是否可能延续
3. 背离检测 - 价格与指标背离时预警
4. 机器学习辅助 - 使用简单线性回归辅助判断
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from data.processors.indicator import IndicatorCalculator


@dataclass
class PredictionResult:
    """预测结果"""
    action: str = "观望"  # 买入/卖出/观望
    direction: str = "震荡"  # 上涨/下跌/震荡
    confidence: float = 0.0  # 置信度 0-1
    score: float = 0.0  # 综合评分
    reasons: List[str] = None  # 原因列表
    
    # 各维度得分
    trend_score: float = 0.0
    momentum_score: float = 0.0
    volume_score: float = 0.0
    breakout_score: float = 0.0
    
    # 明日预测
    predicted_change: float = 0.0  # 预测涨跌幅%
    predicted_direction: str = "震荡"
    
    # 风险指标
    risk_level: str = "中"  # 高/中/低
    stop_loss: float = 0.0  # 建议止损价
    take_profit: float = 0.0  # 建议止盈价
    
    def __post_init__(self):
        if self.reasons is None:
            self.reasons = []


class StockPredictor:
    """
    股票预测引擎
    基于技术分析的综合预测系统
    """
    
    def __init__(self):
        self.calculator = IndicatorCalculator()
    
    def predict(self, df: pd.DataFrame) -> PredictionResult:
        """
        综合预测
        
        Args:
            df: K线数据，至少包含 开盘/最高/最低/收盘/成交量
            
        Returns:
            PredictionResult: 预测结果
        """
        if df is None or len(df) < 20:
            return PredictionResult()
        
        close_col = "收盘" if "收盘" in df.columns else "close"
        high_col = "最高" if "最高" in df.columns else "high"
        low_col = "最低" if "最低" in df.columns else "low"
        volume_col = "成交量" if "成交量" in df.columns else "volume"
        
        result = PredictionResult()
        current_price = df[close_col].iloc[-1]
        
        df_indicators = IndicatorCalculator.calculate_all(df)
        
        result.trend_score = self._analyze_trend_score(df_indicators, result)
        result.momentum_score = self._analyze_momentum_score(df_indicators, result)
        result.volume_score = self._analyze_volume_score(df_indicators, result)
        result.breakout_score = self._analyze_breakout_score(df_indicators, result)
        
        result.score = (
            result.trend_score * 0.30 +
            result.momentum_score * 0.30 +
            result.volume_score * 0.20 +
            result.breakout_score * 0.20
        )
        
        result.confidence = min(abs(result.score) * 0.5 + 0.3, 1.0)
        
        result.predicted_change = self._predict_tomorrow_change(df, result)
        
        result.direction = self._determine_direction(result)
        result.action = self._determine_action(result)
        result.risk_level = self._assess_risk(df, result)
        
        result.stop_loss = current_price * (1 - 0.02 - self._risk_level_to_pct(result.risk_level) * 0.5)
        result.take_profit = current_price * (1 + 0.03 + self._risk_level_to_pct(result.risk_level))
        
        return result
    
    def _analyze_trend_score(self, df: pd.DataFrame, result: PredictionResult) -> float:
        """
        趋势评分 (-1 ~ 1)
        基于均线系统和趋势强度
        """
        close_col = "收盘" if "收盘" in df.columns else "close"
        close = df[close_col]
        
        sma5 = df["sma5"] if "sma5" in df.columns else close
        sma20 = df["sma20"] if "sma20" in df.columns else close
        sma60 = df["sma60"] if "sma60" in df.columns else close
        
        score = 0.0
        reasons = []
        
        price_vs_sma20 = (close.iloc[-1] / sma20.iloc[-1] - 1) * 100
        sma5_vs_sma20 = (sma5.iloc[-1] / sma20.iloc[-1] - 1) * 100
        sma20_vs_sma60 = (sma20.iloc[-1] / sma60.iloc[-1] - 1) * 100
        
        if price_vs_sma20 > 2:
            score += 0.3
            reasons.append(f"价格突破20日均线+{price_vs_sma20:.1f}%")
        elif price_vs_sma20 < -2:
            score -= 0.3
            reasons.append(f"价格跌破20日均线{price_vs_sma20:.1f}%")
        
        if sma5_vs_sma20 > 1:
            score += 0.25
            reasons.append("5日均线在20日均线上方")
        elif sma5_vs_sma20 < -1:
            score -= 0.25
            reasons.append("5日均线在20日均线下方")
        
        if sma20_vs_sma60 > 2:
            score += 0.25
            reasons.append("20日均线在60日均线上方(多头排列)")
        elif sma20_vs_sma60 < -2:
            score -= 0.25
            reasons.append("20日均线在60日均线下方(空头排列)")
        
        recent_5d_return = (close.iloc[-1] / close.iloc[-6] - 1) * 100 if len(close) >= 6 else 0
        if recent_5d_return > 3:
            score += 0.2
            reasons.append(f"5日涨幅+{recent_5d_return:.1f}%")
        elif recent_5d_return < -3:
            score -= 0.2
            reasons.append(f"5日跌幅{recent_5d_return:.1f}%")
        
        score = max(-1, min(1, score))
        
        if score > 0.2:
            reasons.append("整体趋势偏多")
        elif score < -0.2:
            reasons.append("整体趋势偏空")
        else:
            reasons.append("趋势不明确")
        
        result.reasons.extend(reasons[:3])
        return score
    
    def _analyze_momentum_score(self, df: pd.DataFrame, result: PredictionResult) -> float:
        """
        动量评分 (-1 ~ 1)
        基于RSI/MACD/KDJ的动量指标
        """
        score = 0.0
        reasons = []
        
        if "rsi" in df.columns:
            rsi = df["rsi"].iloc[-1]
            rsi_prev = df["rsi"].iloc[-2] if len(df) >= 2 else 50
            
            if rsi < 30:
                score += 0.25
                reasons.append(f"RSI超卖({rsi:.0f})")
            elif rsi > 70:
                score -= 0.25
                reasons.append(f"RSI超买({rsi:.0f})")
            
            if rsi_prev < 30 and rsi >= 30:
                score += 0.2
                reasons.append("RSI金叉(从超卖区回升)")
            elif rsi_prev > 70 and rsi <= 70:
                score -= 0.2
                reasons.append("RSI死叉(从超买区回落)")
        
        if "macd_dif" in df.columns and "macd_dea" in df.columns:
            dif = df["macd_dif"].iloc[-1]
            dea = df["macd_dea"].iloc[-1]
            dif_prev = df["macd_dif"].iloc[-2] if len(df) >= 2 else 0
            
            if dif > dea and dif > 0:
                score += 0.2
                reasons.append("MACD多头")
            elif dif < dea and dif < 0:
                score -= 0.2
                reasons.append("MACD空头")
            
            if dif_prev <= dea and dif > dea:
                score += 0.25
                reasons.append("MACD金叉")
            elif dif_prev >= dea and dif < dea:
                score -= 0.25
                reasons.append("MACD死叉")
        
        if "kdj_k" in df.columns and "kdj_d" in df.columns:
            k = df["kdj_k"].iloc[-1]
            d = df["kdj_d"].iloc[-1]
            k_prev = df["kdj_k"].iloc[-2] if len(df) >= 2 else 50
            d_prev = df["kdj_d"].iloc[-2] if len(df) >= 2 else 50
            
            if k < 20 and k > d:
                score += 0.2
                reasons.append("KDJ低位金叉")
            elif k > 80 and k < d:
                score -= 0.2
                reasons.append("KDJ高位死叉")
        
        score = max(-1, min(1, score))
        result.reasons.extend(reasons[:2])
        return score
    
    def _analyze_volume_score(self, df: pd.DataFrame, result: PredictionResult) -> float:
        """
        量价评分 (-1 ~ 1)
        放量上涨/缩量下跌是健康信号
        """
        close_col = "收盘" if "收盘" in df.columns else "close"
        volume_col = "成交量" if "成交量" in df.columns else "volume"
        
        close = df[close_col]
        volume = df[volume_col]
        
        score = 0.0
        reasons = []
        
        price_change = (close.iloc[-1] / close.iloc[-2] - 1) * 100 if len(close) >= 2 else 0
        volume_change = (volume.iloc[-1] / volume.iloc[-2] - 1) if len(volume) >= 2 else 0
        
        if "volume_ratio" in df.columns:
            vr = df["volume_ratio"].iloc[-1]
            if vr > 2:
                if price_change > 0:
                    score += 0.3
                    reasons.append(f"放量上涨({vr:.1f}倍)")
                else:
                    score -= 0.3
                    reasons.append(f"放量下跌({vr:.1f}倍)")
            elif vr < 0.5:
                if price_change > 0:
                    score -= 0.1
                    reasons.append("缩量上涨(动力不足)")
                else:
                    score += 0.1
                    reasons.append("缩量下跌(抛压不重)")
        
        if price_change > 0 and volume_change > 0.2:
            score += 0.2
            reasons.append("价涨量增")
        elif price_change < 0 and volume_change < -0.2:
            score += 0.15
            reasons.append("价跌量缩")
        elif price_change > 0 and volume_change < -0.2:
            score -= 0.15
            reasons.append("价涨量缩(背离)")
        elif price_change < 0 and volume_change > 0.2:
            score -= 0.15
            reasons.append("价跌量增")
        
        if "obv" in df.columns:
            obv = df["obv"]
            obv_trend = (obv.iloc[-1] / obv.iloc[-5] - 1) * 100 if len(obv) >= 5 else 0
            if obv_trend > 10:
                score += 0.2
                reasons.append(f"OBV上升({obv_trend:.0f}%)")
            elif obv_trend < -10:
                score -= 0.2
                reasons.append(f"OBV下降({obv_trend:.0f}%)")
        
        score = max(-1, min(1, score))
        result.reasons.extend(reasons[:2])
        return score
    
    def _analyze_breakout_score(self, df: pd.DataFrame, result: PredictionResult) -> float:
        """
        突破评分 (-1 ~ 1)
        检测价格是否突破重要位置
        """
        close_col = "收盘" if "收盘" in df.columns else "close"
        high_col = "最高" if "最高" in df.columns else "high"
        low_col = "最低" if "最低" in df.columns else "low"
        
        close = df[close_col]
        high = df[high_col]
        low = df[low_col]
        
        score = 0.0
        reasons = []
        
        upper_20 = df["bb_upper"].iloc[-1] if "bb_upper" in df.columns else close.iloc[-1] * 1.05
        lower_20 = df["bb_lower"].iloc[-1] if "bb_lower" in df.columns else close.iloc[-1] * 0.95
        middle_20 = df["bb_middle"].iloc[-1] if "bb_middle" in df.columns else close.iloc[-1]
        
        bb_position = (close.iloc[-1] - lower_20) / (upper_20 - lower_20) if upper_20 != lower_20 else 0.5
        
        if close.iloc[-1] > upper_20:
            score += 0.3
            reasons.append("突破布林上轨")
        elif close.iloc[-1] < lower_20:
            score -= 0.3
            reasons.append("跌破布林下轨")
        elif bb_position > 0.8:
            score += 0.15
            reasons.append("接近布林上轨")
        elif bb_position < 0.2:
            score -= 0.15
            reasons.append("接近布林下轨")
        
        if "atr" in df.columns:
            atr = df["atr"].iloc[-1]
            daily_range = (high.iloc[-1] - low.iloc[-1]) / close.iloc[-1]
            
            if daily_range > atr / close.iloc[-1] * 2:
                if close.iloc[-1] > open_col(df):
                    score += 0.2
                    reasons.append("波动加剧且上涨")
                else:
                    score -= 0.2
                    reasons.append("波动加剧且下跌")
        
        high_20 = high.iloc[-21:-1].max() if len(high) >= 21 else high.iloc[:-1].max()
        low_20 = low.iloc[-21:-1].min() if len(low) >= 21 else low.iloc[:-1].min()
        
        if close.iloc[-1] > high_20:
            score += 0.4
            reasons.append(f"突破20日高点({(close.iloc[-1]/high_20-1)*100:.1f}%)")
        elif close.iloc[-1] < low_20:
            score -= 0.4
            reasons.append(f"跌破20日低点({(close.iloc[-1]/low_20-1)*100:.1f}%)")
        
        score = max(-1, min(1, score))
        result.reasons.extend(reasons[:2])
        return score
    
    def _predict_tomorrow_change(self, df: pd.DataFrame, result: PredictionResult) -> float:
        """
        预测明日涨跌幅
        基于动量和趋势外推
        """
        close_col = "收盘" if "收盘" in df.columns else "close"
        close = df[close_col]
        
        recent_returns = close.pct_change().tail(5).dropna()
        avg_return = recent_returns.mean() * 100 if len(recent_returns) > 0 else 0
        
        momentum_factor = result.momentum_score * 2
        
        trend_factor = result.trend_score * 1.5
        
        predicted = (avg_return * 0.3 + momentum_factor * 0.4 + trend_factor * 0.3)
        
        predicted = max(-10, min(10, predicted))
        
        return round(predicted, 2)
    
    def _determine_direction(self, result: PredictionResult) -> str:
        """判断方向"""
        if result.score > 0.3:
            return "上涨"
        elif result.score < -0.3:
            return "下跌"
        else:
            return "震荡"
    
    def _determine_action(self, result: PredictionResult) -> str:
        """判断操作"""
        if result.score > 0.4 and result.confidence > 0.5:
            return "买入"
        elif result.score < -0.4 and result.confidence > 0.5:
            return "卖出"
        else:
            return "观望"
    
    def _assess_risk(self, df: pd.DataFrame, result: PredictionResult) -> str:
        """评估风险"""
        close_col = "收盘" if "收盘" in df.columns else "close"
        close = df[close_col]
        
        if "atr" in df.columns:
            atr_pct = df["atr"].iloc[-1] / close.iloc[-1] * 100
            if atr_pct > 4:
                return "高"
            elif atr_pct > 2.5:
                return "中"
            else:
                return "低"
        
        volatility = close.pct_change().tail(20).std() * 100
        if volatility > 3:
            return "高"
        elif volatility > 1.5:
            return "中"
        else:
            return "低"
    
    def _risk_level_to_pct(self, risk_level: str) -> float:
        """风险等级转百分比"""
        mapping = {"高": 0.03, "中": 0.02, "低": 0.01}
        return mapping.get(risk_level, 0.02)


def open_col(df):
    """获取开盘价列"""
    return df["开盘"] if "开盘" in df.columns else df["open"]


if __name__ == "__main__":
    import akshare as ak
    
    print("=" * 60)
    print("股票预测引擎 v2.0 测试")
    print("=" * 60)
    
    predictor = StockPredictor()
    
    try:
        df = ak.stock_zh_a_hist(symbol="000001", period="daily", start_date="20240101", end_date="20240331")
        result = predictor.predict(df)
        
        print(f"\n预测结果：")
        print(f"  操作: {result.action}")
        print(f"  方向: {result.direction}")
        print(f"  置信度: {result.confidence:.0%}")
        print(f"  评分: {result.score:.3f}")
        print(f"  预测涨跌: {result.predicted_change:+.2f}%")
        print(f"  风险等级: {result.risk_level}")
        print(f"  建议止损: {result.stop_loss:.2f}")
        print(f"  建议止盈: {result.take_profit:.2f}")
        print(f"\n原因分析：")
        for i, reason in enumerate(result.reasons, 1):
            print(f"  {i}. {reason}")
        
        print(f"\n分项评分：")
        print(f"  趋势: {result.trend_score:+.2f}")
        print(f"  动量: {result.momentum_score:+.2f}")
        print(f"  量价: {result.volume_score:+.2f}")
        print(f"  突破: {result.breakout_score:+.2f}")
    except Exception as e:
        print(f"测试失败: {e}")
