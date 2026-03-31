"""
时间锁定回测系统
模拟穿越到过去某一天，只使用该时间点之前的数据来判断应该买入还是卖出
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class BacktestResult:
    """单次回测结果"""
    target_date: str
    prediction: str
    actual_next_day: str
    actual_change_pct: float
    hit: bool
    confidence: float
    data_used: Dict


@dataclass
class ContinuousBacktestResult:
    """连续回测结果"""
    total_tests: int
    hits: int
    hit_rate: float
    max_consecutive_hits: int
    consecutive_5_rate: float
    consecutive_10_rate: float
    results: List[BacktestResult]


class TimeLockedBacktest:
    """
    时间锁定回测引擎
    
    核心思想：模拟"穿越到过去某一天"，只使用该时间点之前的数据
    来判断应该买入还是卖出，然后看后一天的实际情况是否正确。
    """
    
    def __init__(self, lookback_days: int = 60, news_lookback_days: int = 30):
        self.lookback_days = lookback_days
        self.news_lookback_days = news_lookback_days
    
    def run_single(
        self,
        stock_code: str,
        target_date: str,
        data_provider: callable
    ) -> BacktestResult:
        """
        执行单次时间锁定回测
        
        Args:
            stock_code: 股票代码
            target_date: 目标日期 "YYYY-MM-DD"
            data_provider: 数据提供者函数，接受(stock_code, cutoff_date)返回数据
        
        Returns:
            BacktestResult
        """
        cutoff_date = self._get_previous_trading_day(target_date)
        
        data = data_provider(stock_code, cutoff_date)
        
        kline_data = data.get("kline", pd.DataFrame())
        news_data = data.get("news", [])
        fundamentals = data.get("fundamentals", {})
        
        signals = {
            "technical": self._analyze_technical(kline_data),
            "fundamental": fundamentals,
            "sentiment": self._analyze_sentiment(news_data)
        }
        
        prediction = self._make_prediction(signals)
        
        next_day_data = data.get("next_day", {})
        actual = "涨" if next_day_data.get("change_pct", 0) > 0 else "跌"
        actual_change = next_day_data.get("change_pct", 0)
        
        hit = (
            (prediction["action"] == "买入" and actual == "涨") or
            (prediction["action"] == "建议回避" and actual == "跌") or
            (prediction["action"] == "观望" and abs(actual_change) < 1.0)
        )
        
        return BacktestResult(
            target_date=target_date,
            prediction=prediction["action"],
            actual_next_day=actual,
            actual_change_pct=actual_change,
            hit=hit,
            confidence=prediction["confidence"],
            data_used={
                "kline_days": min(len(kline_data), self.lookback_days),
                "news_count": len(news_data),
                "has_fundamentals": bool(fundamentals)
            }
        )
    
    def run_continuous(
        self,
        stock_code: str,
        start_date: str,
        end_date: str,
        data_provider: callable
    ) -> ContinuousBacktestResult:
        """
        连续多轮回测
        
        Args:
            stock_code: 股票代码
            start_date: 回测开始日期
            end_date: 回测结束日期
            data_provider: 数据提供者函数
        
        Returns:
            ContinuousBacktestResult
        """
        trading_days = self._get_trading_days(start_date, end_date)
        
        results = []
        for date in trading_days:
            try:
                result = self.run_single(stock_code, date, data_provider)
                results.append(result)
            except Exception as e:
                print(f"回测 {date} 失败: {e}")
                continue
        
        total = len(results)
        hits = sum(1 for r in results if r.hit)
        hit_rate = hits / total if total > 0 else 0
        
        consecutive = self._calc_consecutive_hits(results)
        max_consecutive = max(consecutive) if consecutive else 0
        
        consecutive_5 = sum(1 for c in consecutive if c >= 5)
        consecutive_10 = sum(1 for c in consecutive if c >= 10)
        
        return ContinuousBacktestResult(
            total_tests=total,
            hits=hits,
            hit_rate=hit_rate,
            max_consecutive_hits=max_consecutive,
            consecutive_5_rate=consecutive_5 / total if total > 0 else 0,
            consecutive_10_rate=consecutive_10 / total if total > 0 else 0,
            results=results
        )
    
    def _get_previous_trading_day(self, date_str: str) -> str:
        """获取前一个交易日"""
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        dt = dt - timedelta(days=1)
        return dt.strftime("%Y-%m-%d")
    
    def _get_next_trading_day(self, date_str: str) -> str:
        """获取后一个交易日"""
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        dt = dt + timedelta(days=1)
        return dt.strftime("%Y-%m-%d")
    
    def _get_trading_days(self, start_date: str, end_date: str) -> List[str]:
        """获取交易日列表（简化版，实际应从数据源获取）"""
        days = []
        dt_start = datetime.strptime(start_date, "%Y-%m-%d")
        dt_end = datetime.strptime(end_date, "%Y-%m-%d")
        
        current = dt_start
        while current <= dt_end:
            if current.weekday() < 5:
                days.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)
        
        return days
    
    def _calc_consecutive_hits(self, results: List[BacktestResult]) -> List[int]:
        """计算连续命中次数"""
        consecutive = []
        current = 0
        
        for r in results:
            if r.hit:
                current += 1
            else:
                if current > 0:
                    consecutive.append(current)
                current = 0
        
        if current > 0:
            consecutive.append(current)
        
        return consecutive
    
    def _analyze_technical(self, kline_data: pd.DataFrame) -> Dict:
        """技术面分析（简化版）"""
        if kline_data is None or len(kline_data) < 20:
            return {"direction": "中性", "score": 0}
        
        close_col = "收盘" if "收盘" in kline_data.columns else "close"
        
        if close_col not in kline_data.columns:
            return {"direction": "中性", "score": 0}
        
        recent = kline_data.tail(5)
        sma5 = recent[close_col].mean()
        sma20 = kline_data.tail(20)[close_col].mean() if len(kline_data) >= 20 else sma5
        current_price = recent[close_col].iloc[-1]
        
        if current_price > sma5 and sma5 > sma20:
            direction = "上涨"
            score = 2
        elif current_price < sma5 and sma5 < sma20:
            direction = "下跌"
            score = -2
        else:
            direction = "震荡"
            score = 0
        
        return {"direction": direction, "score": score}
    
    def _analyze_sentiment(self, news_data: List[Dict]) -> Dict:
        """情绪面分析（简化版）"""
        if not news_data:
            return {"score": 0}
        
        positive = sum(1 for n in news_data if n.get("sentiment", 0) > 0)
        negative = sum(1 for n in news_data if n.get("sentiment", 0) < 0)
        total = len(news_data)
        
        score = (positive - negative) / total if total > 0 else 0
        
        return {"score": score}
    
    def _make_prediction(self, signals: Dict) -> Dict:
        """根据信号做出预测"""
        tech_score = signals.get("technical", {}).get("score", 0)
        sent_score = signals.get("sentiment", {}).get("score", 0)
        fund_score = signals.get("fundamental", {}).get("score", 0)
        
        total_score = tech_score * 0.4 + sent_score * 0.3 + fund_score * 0.3
        
        if total_score >= 0.5:
            action = "买入"
            confidence = min(total_score, 1.0)
        elif total_score <= -0.5:
            action = "建议回避"
            confidence = min(abs(total_score), 1.0)
        else:
            action = "观望"
            confidence = 0.3
        
        return {"action": action, "confidence": confidence}


class MockDataProvider:
    """模拟数据提供者（用于测试）"""
    
    def __init__(self):
        self.data_cache = {}
    
    def provide(self, stock_code: str, cutoff_date: str) -> Dict:
        """提供模拟数据"""
        kline = self._generate_mock_kline(cutoff_date)
        news = self._generate_mock_news(10)
        fundamentals = self._generate_mock_fundamentals()
        next_day = self._generate_mock_next_day()
        
        return {
            "kline": kline,
            "news": news,
            "fundamentals": fundamentals,
            "next_day": next_day
        }
    
    def _generate_mock_kline(self, cutoff_date: str) -> pd.DataFrame:
        """生成模拟K线数据"""
        dates = pd.date_range(end=cutoff_date, periods=60, freq="D")
        np.random.seed(hash(cutoff_date) % 2**32)
        
        prices = 10 + np.cumsum(np.random.randn(60) * 0.5)
        
        return pd.DataFrame({
            "date": dates.strftime("%Y-%m-%d"),
            "open": prices * 0.99,
            "high": prices * 1.02,
            "low": prices * 0.98,
            "close": prices,
            "volume": np.random.randint(1000000, 10000000, 60)
        })
    
    def _generate_mock_news(self, count: int) -> List[Dict]:
        """生成模拟新闻数据"""
        sentiments = [0.5, -0.3, 0.8, -0.2, 0.3, 0.1, -0.4, 0.6, -0.1, 0.2]
        news = []
        for i in range(min(count, len(sentiments))):
            news.append({
                "title": f"新闻标题{i+1}",
                "sentiment": sentiments[i],
                "date": "2026-03-20"
            })
        return news
    
    def _generate_mock_fundamentals(self) -> Dict:
        """生成模拟基本面数据"""
        return {"direction": "良好", "score": 0.3}
    
    def _generate_mock_next_day(self) -> Dict:
        """生成模拟次日数据"""
        np.random.seed()
        change = np.random.randn() * 2
        return {"change_pct": change}


if __name__ == "__main__":
    provider = MockDataProvider()
    backtest = TimeLockedBacktest()
    
    result = backtest.run_continuous(
        stock_code="000001",
        start_date="2026-01-01",
        end_date="2026-03-28",
        data_provider=provider.provide
    )
    
    print("=" * 50)
    print("时间锁定回测结果")
    print("=" * 50)
    print(f"总测试次数: {result.total_tests}")
    print(f"命中次数: {result.hits}")
    print(f"命中率: {result.hit_rate:.1%}")
    print(f"最长连续命中: {result.max_consecutive_hits}")
    print(f"连续5轮命中次数: {result.consecutive_5_rate:.1%}")
    print(f"连续10轮命中次数: {result.consecutive_10_rate:.1%}")
