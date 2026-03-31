"""
纯交易数据分析器
基于量价关系和技术指标分析价格走势
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from data.processors.indicator import IndicatorCalculator


class TechnicalAnalyzer:
    """
    纯交易数据分析器
    不依赖外部新闻/财报，仅通过K线数据和技术指标分析走势
    """

    def __init__(self):
        self.calculator = IndicatorCalculator()

    def analyze(self, df: pd.DataFrame) -> Dict:
        """
        综合技术分析
        """
        if df is None or len(df) < 20:
            return {"error": "数据不足，无法分析"}
        
        df_with_indicators = IndicatorCalculator.calculate_all(df)
        
        result = {
            "trend": self._analyze_trend(df_with_indicators),
            "momentum": self._analyze_momentum(df_with_indicators),
            "volume": self._analyze_volume(df_with_indicators),
            "volatility": self._analyze_volatility(df_with_indicators),
            "signals": self._generate_signals(df_with_indicators),
            "summary": ""
        }
        
        result["summary"] = self._generate_summary(result)
        
        return result

    def _analyze_trend(self, df: pd.DataFrame) -> Dict:
        """
        趋势分析：判断当前是上涨/下跌/震荡
        """
        close_col = "收盘" if "收盘" in df.columns else "close"
        
        close = df[close_col]
        sma5 = df["sma5"] if "sma5" in df.columns else close
        sma20 = df["sma20"] if "sma20" in df.columns else close
        sma60 = df["sma60"] if "sma60" in df.columns else close
        
        current_price = close.iloc[-1]
        current_sma5 = sma5.iloc[-1]
        current_sma20 = sma20.iloc[-1]
        current_sma60 = sma60.iloc[-1]
        
        trend_score = 0
        
        if current_price > current_sma5:
            trend_score += 1
        if current_sma5 > current_sma20:
            trend_score += 1
        if current_sma20 > current_sma60:
            trend_score += 1
        
        if trend_score >= 2:
            trend = "上涨"
        elif trend_score <= -2:
            trend = "下跌"
        else:
            trend = "震荡"
        
        recent_returns = close.pct_change().tail(5)
        avg_return = recent_returns.mean()
        max_drawdown = ((close / close.cummax()) - 1).min()
        
        return {
            "trend": trend,
            "trend_score": trend_score,
            "avg_return_5d": avg_return * 100,
            "max_drawdown_5d": max_drawdown * 100,
            "price_vs_sma20": ((current_price / current_sma20) - 1) * 100
        }

    def _analyze_momentum(self, df: pd.DataFrame) -> Dict:
        """
        动量分析：RSI、MACD、KDJ
        """
        close_col = "收盘" if "收盘" in df.columns else "close"
        high_col = "最高" if "最高" in df.columns else "high"
        low_col = "最低" if "最低" in df.columns else "low"
        
        result = {}
        
        if "rsi" in df.columns:
            rsi = df["rsi"].iloc[-1]
            if rsi > 70:
                rsi_signal = "超买"
            elif rsi < 30:
                rsi_signal = "超卖"
            else:
                rsi_signal = "中性"
            result["rsi"] = {"value": round(rsi, 2), "signal": rsi_signal}
        
        if "macd_dif" in df.columns and "macd_dea" in df.columns:
            dif = df["macd_dif"].iloc[-1]
            dea = df["macd_dea"].iloc[-1]
            
            if dif > dea and dif > 0:
                macd_signal = "多头"
            elif dif < dea and dif < 0:
                macd_signal = "空头"
            else:
                macd_signal = "中性"
            
            result["macd"] = {
                "dif": round(dif, 4),
                "dea": round(dea, 4),
                "signal": macd_signal
            }
        
        if "kdj_k" in df.columns and "kdj_d" in df.columns and "kdj_j" in df.columns:
            k = df["kdj_k"].iloc[-1]
            d = df["kdj_d"].iloc[-1]
            j = df["kdj_j"].iloc[-1]
            
            if k > 80 or j > 100:
                kdj_signal = "超买"
            elif k < 20 or j < 0:
                kdj_signal = "超卖"
            elif k > d:
                kdj_signal = "金叉"
            else:
                kdj_signal = "死叉"
            
            result["kdj"] = {
                "k": round(k, 2),
                "d": round(d, 2),
                "j": round(j, 2),
                "signal": kdj_signal
            }
        
        return result

    def _analyze_volume(self, df: pd.DataFrame) -> Dict:
        """
        量价分析：缩量/放量、量比、OBV
        """
        close_col = "收盘" if "收盘" in df.columns else "close"
        volume_col = "成交量" if "成交量" in df.columns else "volume"
        
        result = {}
        
        if "volume_ratio" in df.columns:
            vr = df["volume_ratio"].iloc[-1]
            if vr > 2:
                vr_signal = "异常放量"
            elif vr < 0.5:
                vr_signal = "缩量"
            else:
                vr_signal = "正常"
            result["volume_ratio"] = {"value": round(vr, 2), "signal": vr_signal}
        
        if "obv" in df.columns:
            obv = df["obv"].iloc[-1]
            obv_ma5 = df["obv"].tail(5).mean()
            if obv > obv_ma5:
                obv_signal = "OBV上升"
            else:
                obv_signal = "OBV下降"
            result["obv"] = {"value": round(obv, 2), "signal": obv_signal}
        
        price_change = df[close_col].pct_change().iloc[-1] * 100
        volume_change = df[volume_col].pct_change().iloc[-1] * 100
        
        if price_change > 0 and volume_change > 0:
            result["price_volume"] = "价涨量增 - 强势"
        elif price_change > 0 and volume_change < 0:
            result["price_volume"] = "价涨量缩 - 潜在背离"
        elif price_change < 0 and volume_change > 0:
            result["price_volume"] = "价跌量增 - 弱势"
        else:
            result["price_volume"] = "价跌量缩 - 底部可能"
        
        return result

    def _analyze_volatility(self, df: pd.DataFrame) -> Dict:
        """
        波动性分析：布林带、ATR
        """
        close_col = "收盘" if "收盘" in df.columns else "close"
        
        result = {}
        
        if all(col in df.columns for col in ["bb_upper", "bb_middle", "bb_lower"]):
            upper = df["bb_upper"].iloc[-1]
            middle = df["bb_middle"].iloc[-1]
            lower = df["bb_lower"].iloc[-1]
            current_price = df[close_col].iloc[-1]
            
            position = (current_price - lower) / (upper - lower) * 100
            
            if position > 80:
                bb_signal = "接近上轨 - 超买"
            elif position < 20:
                bb_signal = "接近下轨 - 超卖"
            else:
                bb_signal = "中轨附近"
            
            result["bollinger"] = {
                "position": round(position, 2),
                "upper": round(upper, 2),
                "lower": round(lower, 2),
                "signal": bb_signal
            }
        
        if "atr" in df.columns:
            atr = df["atr"].iloc[-1]
            current_price = df[close_col].iloc[-1]
            atr_ratio = atr / current_price * 100
            result["atr"] = {"value": round(atr, 2), "atr_percent": round(atr_ratio, 2)}
        
        return result

    def _generate_signals(self, df: pd.DataFrame) -> List[Dict]:
        """
        生成交易信号
        """
        signals = []
        close_col = "收盘" if "收盘" in df.columns else "close"
        high_col = "最高" if "最高" in df.columns else "high"
        low_col = "最低" if "最低" in df.columns else "low"
        
        if "rsi" in df.columns:
            rsi = df["rsi"].iloc[-1]
            if rsi < 30:
                signals.append({"type": "买入", "reason": f"RSI超卖({rsi:.1f})", "strength": "强"})
            elif rsi > 70:
                signals.append({"type": "卖出", "reason": f"RSI超买({rsi:.1f})", "strength": "强"})
        
        if all(col in df.columns for col in ["macd_dif", "macd_dea"]):
            dif = df["macd_dif"].iloc[-1]
            dea = df["macd_dea"].iloc[-1]
            dif_prev = df["macd_dif"].iloc[-2]
            
            if dif > dea and dif_prev <= dea:
                signals.append({"type": "买入", "reason": "MACD金叉", "strength": "中"})
            elif dif < dea and dif_prev >= dea:
                signals.append({"type": "卖出", "reason": "MACD死叉", "strength": "中"})
        
        if "kdj_k" in df.columns and "kdj_d" in df.columns:
            k = df["kdj_k"].iloc[-1]
            d = df["kdj_d"].iloc[-1]
            k_prev = df["kdj_k"].iloc[-2]
            d_prev = df["kdj_d"].iloc[-2]
            
            if k > d and k_prev <= d_prev and k < 30:
                signals.append({"type": "买入", "reason": "KDJ低位金叉", "strength": "强"})
            elif k < d and k_prev >= d_prev and k > 70:
                signals.append({"type": "卖出", "reason": "KDJ高位死叉", "strength": "强"})
        
        price = df[close_col]
        if "bb_lower" in df.columns and "bb_upper" in df.columns:
            if price.iloc[-1] < df["bb_lower"].iloc[-1]:
                signals.append({"type": "买入", "reason": "价格跌破布林下轨", "strength": "强"})
            elif price.iloc[-1] > df["bb_upper"].iloc[-1]:
                signals.append({"type": "卖出", "reason": "价格突破布林上轨", "strength": "强"})
        
        divergence = IndicatorCalculator.detect_divergence(
            df[close_col],
            df["rsi"] if "rsi" in df.columns else df[close_col]
        )
        if divergence["signal"] == "bullish":
            signals.append({"type": "买入", "reason": "底背离", "strength": "强"})
        elif divergence["signal"] == "bearish":
            signals.append({"type": "卖出", "reason": "顶背离", "strength": "强"})
        
        return signals

    def _generate_summary(self, analysis: Dict) -> str:
        """
        生成分析总结
        """
        parts = []
        
        trend = analysis.get("trend", {})
        parts.append(f"趋势:{trend.get('trend', '未知')}")
        
        momentum = analysis.get("momentum", {})
        if "rsi" in momentum:
            parts.append(f"RSI:{momentum['rsi']['value']:.0f}")
        
        signals = analysis.get("signals", [])
        buy_signals = [s for s in signals if s["type"] == "买入"]
        sell_signals = [s for s in signals if s["type"] == "卖出"]
        
        if buy_signals:
            parts.append(f"买入信号:{len(buy_signals)}个")
        if sell_signals:
            parts.append(f"卖出信号:{len(sell_signals)}个")
        
        return " | ".join(parts)


if __name__ == "__main__":
    import akshare as ak
    
    collector = ak
    df = ak.stock_zh_a_hist(symbol="000001", period="daily", start_date="20240101", end_date="20260331")
    
    analyzer = TechnicalAnalyzer()
    result = analyzer.analyze(df)
    
    print("=" * 60)
    print("技术分析报告")
    print("=" * 60)
    print(f"\n趋势: {result['trend']}")
    print(f"动量: {result['momentum']}")
    print(f"量价: {result['volume']}")
    print(f"信号: {result['signals']}")
    print(f"\n总结: {result['summary']}")
