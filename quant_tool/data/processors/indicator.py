"""
技术指标计算模块
包含常用的量价技术指标
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional


class IndicatorCalculator:
    """技术指标计算器"""

    @staticmethod
    def calculate_sma(series: pd.Series, window: int) -> pd.Series:
        """
        简单移动平均 (SMA)
        """
        return series.rolling(window=window, min_periods=1).mean()

    @staticmethod
    def calculate_ema(series: pd.Series, span: int) -> pd.Series:
        """
        指数移动平均 (EMA)
        """
        return series.ewm(span=span, adjust=False).mean()

    @staticmethod
    def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
        """
        相对强弱指数 (RSI)
        RSI = 100 - (100 / (1 + RS))
        RS = 平均涨幅 / 平均跌幅
        """
        delta = series.diff()
        
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=period, min_periods=1).mean()
        avg_loss = loss.rolling(window=period, min_periods=1).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi

    @staticmethod
    def calculate_macd(
        series: pd.Series,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        MACD指标
        DIF = EMA(fast) - EMA(slow)
        DEA = EMA(DIF, signal)
        BAR = 2 * (DIF - DEA)
        """
        ema_fast = IndicatorCalculator.calculate_ema(series, fast)
        ema_slow = IndicatorCalculator.calculate_ema(series, slow)
        
        dif = ema_fast - ema_slow
        dea = IndicatorCalculator.calculate_ema(dif, signal)
        bar = 2 * (dif - dea)
        
        return dif, dea, bar

    @staticmethod
    def calculate_bollinger_bands(
        series: pd.Series,
        window: int = 20,
        num_std: float = 2.0
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        布林带
        中轨 = SMA
        上轨 = 中轨 + 2 * STD
        下轨 = 中轨 - 2 * STD
        """
        sma = IndicatorCalculator.calculate_sma(series, window)
        std = series.rolling(window=window, min_periods=1).std()
        
        upper = sma + num_std * std
        lower = sma - num_std * std
        
        return upper, sma, lower

    @staticmethod
    def calculate_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
        """
        能量潮指标 (OBV)
        OBV = 昨日OBV + 今日成交量 * 符号
        符号: 收盘涨为正，跌为负
        """
        delta = close.diff()
        
        sign = delta.apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
        
        obv = (sign * volume).cumsum()
        
        return obv

    @staticmethod
    def calculate_kdj(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        n: int = 9,
        m1: int = 3,
        m2: int = 3
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        KDJ指标
        RSV = (Close - LLV(Low, N)) / (HHV(High, N) - LLV(Low, N)) * 100
        K = 2/3 * 昨日K + 1/3 * RSV
        D = 2/3 * 昨日D + 1/3 * K
        J = 3K - 2D
        """
        lowest_low = low.rolling(window=n, min_periods=1).min()
        highest_high = high.rolling(window=n, min_periods=1).max()
        
        rsv = ((close - lowest_low) / (highest_high - lowest_low)) * 100
        rsv = rsv.fillna(50)
        
        k = pd.Series(index=close.index, dtype=float)
        d = pd.Series(index=close.index, dtype=float)
        
        k.iloc[0] = 50
        d.iloc[0] = 50
        
        for i in range(1, len(close)):
            k.iloc[i] = 2/3 * k.iloc[i-1] + 1/3 * rsv.iloc[i]
            d.iloc[i] = 2/3 * d.iloc[i-1] + 1/3 * k.iloc[i]
        
        j = 3 * k - 2 * d
        
        return k, d, j

    @staticmethod
    def calculate_atr(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14
    ) -> pd.Series:
        """
        平均真实波幅 (ATR)
        """
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period, min_periods=1).mean()
        
        return atr

    @staticmethod
    def calculate_volume_ratio(volume: pd.Series, period: int = 5) -> pd.Series:
        """
        量比 (Volume Ratio)
        量比 = 当前成交量 / 过去N日平均成交量
        """
        avg_volume = volume.rolling(window=period, min_periods=1).mean()
        vr = volume / avg_volume
        return vr

    @staticmethod
    def detect_divergence(
        price: pd.Series,
        indicator: pd.Series,
        window: int = 20
    ) -> dict:
        """
        检测价格与指标的背离
        
        顶背离: 价格创新高, 指标未创新高 -> 看跌
        底背离: 价格创新低, 指标未创新低 -> 看涨
        """
        result = {
            "type": None,
            "price_pct_change": 0,
            "indicator_pct_change": 0,
            "signal": "none"
        }
        
        recent_price = price.tail(window)
        recent_indicator = indicator.tail(window)
        
        price_high = recent_price.max()
        price_low = recent_price.min()
        indicator_high = recent_indicator.max()
        indicator_low = recent_indicator.min()
        
        current_price = price.iloc[-1]
        current_indicator = indicator.iloc[-1]
        
        if current_price >= price_high * 0.98:
            if current_indicator < indicator_high * 0.95:
                result["type"] = "top"
                result["signal"] = "bearish"
                result["price_pct_change"] = (current_price - price_low) / price_low * 100
                result["indicator_pct_change"] = (current_indicator - indicator_low) / (indicator_low + 0.001) * 100
        
        elif current_price <= price_low * 1.02:
            if current_indicator > indicator_low * 1.05:
                result["type"] = "bottom"
                result["signal"] = "bullish"
                result["price_pct_change"] = (current_price - price_high) / price_high * 100
                result["indicator_pct_change"] = (current_indicator - indicator_high) / (indicator_high + 0.001) * 100
        
        return result

    @staticmethod
    def calculate_all(df: pd.DataFrame) -> pd.DataFrame:
        """
        计算所有基础技术指标
        """
        result = df.copy()
        
        close_col = "收盘" if "收盘" in df.columns else "close"
        open_col = "开盘" if "开盘" in df.columns else "open"
        high_col = "最高" if "最高" in df.columns else "high"
        low_col = "最低" if "最低" in df.columns else "low"
        volume_col = "成交量" if "成交量" in df.columns else "volume"
        
        if close_col in df.columns:
            result["sma5"] = IndicatorCalculator.calculate_sma(df[close_col], 5)
            result["sma10"] = IndicatorCalculator.calculate_sma(df[close_col], 10)
            result["sma20"] = IndicatorCalculator.calculate_sma(df[close_col], 20)
            result["sma60"] = IndicatorCalculator.calculate_sma(df[close_col], 60)
            
            result["ema12"] = IndicatorCalculator.calculate_ema(df[close_col], 12)
            result["ema26"] = IndicatorCalculator.calculate_ema(df[close_col], 26)
            
            result["rsi"] = IndicatorCalculator.calculate_rsi(df[close_col], 14)
            
            dif, dea, bar = IndicatorCalculator.calculate_macd(df[close_col])
            result["macd_dif"] = dif
            result["macd_dea"] = dea
            result["macd_bar"] = bar
            
            upper, middle, lower = IndicatorCalculator.calculate_bollinger_bands(df[close_col])
            result["bb_upper"] = upper
            result["bb_middle"] = middle
            result["bb_lower"] = lower
        
        if close_col in df.columns and volume_col in df.columns:
            result["obv"] = IndicatorCalculator.calculate_obv(df[close_col], df[volume_col])
        
        if all(col in df.columns for col in [high_col, low_col, close_col]):
            k, d, j = IndicatorCalculator.calculate_kdj(df[high_col], df[low_col], df[close_col])
            result["kdj_k"] = k
            result["kdj_d"] = d
            result["kdj_j"] = j
            
            result["atr"] = IndicatorCalculator.calculate_atr(df[high_col], df[low_col], df[close_col])
        
        if volume_col in df.columns:
            result["volume_ratio"] = IndicatorCalculator.calculate_volume_ratio(df[volume_col])
        
        return result


if __name__ == "__main__":
    import akshare as ak
    
    df = ak.stock_zh_a_hist(symbol="000001", period="daily", start_date="20240101", end_date="20260331")
    df.columns = df.columns.str.strip()
    
    result = IndicatorCalculator.calculate_all(df)
    
    print("技术指标计算完成:")
    print(result[["日期", "收盘", "rsi", "macd_dif", "macd_dea", "volume_ratio"]].tail(10))
