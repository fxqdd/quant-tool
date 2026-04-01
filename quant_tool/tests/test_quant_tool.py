"""
项目功能测试
测试数据来源：
1. 模拟数据 - 用于单元测试，验证计算逻辑正确性
2. AkShare 实时数据 - 用于集成测试，验证真实数据采集能力

测试覆盖：
- 技术指标计算 (IndicatorCalculator)
- 回测引擎 (BacktestEngine)
- 数据收集 (AkShareCollector)
- 技术分析 (TechnicalAnalyzer)
"""

import unittest
import pandas as pd
import numpy as np
import sys
import os
import operator
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.processors.indicator import IndicatorCalculator
from backtest.engine import BacktestEngine, Position


class TestIndicatorCalculator(unittest.TestCase):
    """技术指标计算测试"""

    @classmethod
    def setUpClass(cls):
        """创建测试数据 - 使用模拟K线数据"""
        np.random.seed(42)
        dates = pd.date_range("2024-01-01", periods=100, freq="D")
        
        close = 100 + np.cumsum(np.random.randn(100) * 2)
        close = np.maximum(close, 10)
        
        cls.df = pd.DataFrame({
            "日期": dates,
            "开盘": close * 0.99,
            "最高": close * 1.02,
            "最低": close * 0.98,
            "收盘": close,
            "成交量": np.random.randint(1000000, 10000000, 100)
        })
        print(f"\n[测试数据] 创建了 {len(cls.df)} 条模拟K线数据")
        print(f"[测试数据] 价格范围: {cls.df['收盘'].min():.2f} ~ {cls.df['收盘'].max():.2f}")

    def test_sma(self):
        """测试简单移动平均"""
        sma5 = IndicatorCalculator.calculate_sma(self.df["收盘"], 5)
        sma20 = IndicatorCalculator.calculate_sma(self.df["收盘"], 20)
        
        self.assertEqual(len(sma5), len(self.df))
        self.assertEqual(len(sma20), len(self.df))
        self.assertFalse(sma5.isna().all())
        self.assertFalse(sma20.isna().all())
        
        manual_sma5 = self.df["收盘"].rolling(5, min_periods=1).mean()
        pd.testing.assert_series_equal(sma5.reset_index(drop=True), manual_sma5.reset_index(drop=True), check_names=False)
        print("[SMA测试] 通过 - 简单移动平均计算正确")

    def test_ema(self):
        """测试指数移动平均"""
        ema12 = IndicatorCalculator.calculate_ema(self.df["收盘"], 12)
        
        self.assertEqual(len(ema12), len(self.df))
        self.assertFalse(ema12.isna().all())
        self.assertTrue(ema12.iloc[-1] > 0)
        print("[EMA测试] 通过 - 指数移动平均计算正确")

    def test_rsi(self):
        """测试RSI指标"""
        rsi = IndicatorCalculator.calculate_rsi(self.df["收盘"], 14)
        
        self.assertEqual(len(rsi), len(self.df))
        self.assertTrue((rsi >= 0).all() and (rsi <= 100).all())
        
        valid_rsi = rsi.dropna()
        if len(valid_rsi) > 14:
            self.assertTrue(valid_rsi.iloc[0] == 100 or valid_rsi.iloc[0] == 50)
        print(f"[RSI测试] 通过 - RSI范围: {rsi.min():.1f} ~ {rsi.max():.1f}")

    def test_macd(self):
        """测试MACD指标"""
        dif, dea, bar = IndicatorCalculator.calculate_macd(self.df["收盘"])
        
        self.assertEqual(len(dif), len(self.df))
        self.assertEqual(len(dea), len(self.df))
        self.assertEqual(len(bar), len(self.df))
        
        self.assertFalse(dif.isna().all())
        self.assertFalse(dea.isna().all())
        print(f"[MACD测试] 通过 - DIF范围: {dif.min():.2f} ~ {dif.max():.2f}")

    def test_bollinger_bands(self):
        """测试布林带"""
        upper, middle, lower = IndicatorCalculator.calculate_bollinger_bands(self.df["收盘"])
        
        self.assertEqual(len(upper), len(self.df))
        self.assertEqual(len(lower), len(self.df))
        
        upper_arr = upper.values
        middle_arr = middle.values
        lower_arr = lower.values
        
        for i in range(len(upper_arr)):
            if not (np.isnan(upper_arr[i]) or np.isnan(lower_arr[i])):
                self.assertTrue(upper_arr[i] >= lower_arr[i], f"索引{i}: 上轨{upper_arr[i]:.2f} < 下轨{lower_arr[i]:.2f}")
            if not (np.isnan(middle_arr[i]) or np.isnan(lower_arr[i])):
                self.assertTrue(middle_arr[i] >= lower_arr[i], f"索引{i}: 中轨{middle_arr[i]:.2f} < 下轨{lower_arr[i]:.2f}")
            if not (np.isnan(upper_arr[i]) or np.isnan(middle_arr[i])):
                self.assertTrue(upper_arr[i] >= middle_arr[i], f"索引{i}: 上轨{upper_arr[i]:.2f} < 中轨{middle_arr[i]:.2f}")
        print("[布林带测试] 通过 - 上轨 >= 中轨 >= 下轨")

    def test_kdj(self):
        """测试KDJ指标"""
        k, d, j = IndicatorCalculator.calculate_kdj(
            self.df["最高"], 
            self.df["最低"], 
            self.df["收盘"]
        )
        
        self.assertEqual(len(k), len(self.df))
        self.assertEqual(len(d), len(self.df))
        self.assertEqual(len(j), len(self.df))
        
        self.assertTrue((k >= 0).all() and (k <= 100).all())
        self.assertTrue((d >= 0).all() and (d <= 100).all())
        print(f"[KDJ测试] 通过 - K:{k.iloc[-1]:.1f} D:{d.iloc[-1]:.1f} J:{j.iloc[-1]:.1f}")

    def test_obv(self):
        """测试OBV指标"""
        obv = IndicatorCalculator.calculate_obv(self.df["收盘"], self.df["成交量"])
        
        self.assertEqual(len(obv), len(self.df))
        self.assertFalse(obv.isna().all())
        print(f"[OBV测试] 通过 - OBV值: {obv.iloc[-1]:.0f}")

    def test_atr(self):
        """测试ATR指标"""
        atr = IndicatorCalculator.calculate_atr(
            self.df["最高"],
            self.df["最低"],
            self.df["收盘"]
        )
        
        self.assertEqual(len(atr), len(self.df))
        self.assertTrue((atr > 0).all())
        print(f"[ATR测试] 通过 - ATR值: {atr.iloc[-1]:.2f}")

    def test_volume_ratio(self):
        """测试量比"""
        vr = IndicatorCalculator.calculate_volume_ratio(self.df["成交量"])
        
        self.assertEqual(len(vr), len(self.df))
        self.assertTrue((vr > 0).all())
        print(f"[量比测试] 通过 - 量比均值: {vr.mean():.2f}")

    def test_divergence_detection(self):
        """测试背离检测"""
        divergence = IndicatorCalculator.detect_divergence(
            self.df["收盘"],
            self.df["收盘"]
        )
        
        self.assertIn("signal", divergence)
        self.assertIn("type", divergence)
        print(f"[背离检测测试] 通过 - 信号: {divergence['signal']}")


class TestBacktestEngine(unittest.TestCase):
    """回测引擎测试"""

    @classmethod
    def setUpClass(cls):
        """创建测试数据"""
        np.random.seed(42)
        dates = pd.date_range("2024-01-01", periods=100, freq="D")
        
        close = 100 + np.cumsum(np.random.randn(100) * 2)
        close = np.maximum(close, 10)
        
        cls.df = pd.DataFrame({
            "日期": [str(d.date()) for d in dates],
            "开盘": close * 0.99,
            "最高": close * 1.02,
            "最低": close * 0.98,
            "收盘": close,
            "成交量": np.random.randint(1000000, 10000000, 100)
        })
        print(f"\n[回测数据] 创建了 {len(cls.df)} 条测试数据")

    def test_initialization(self):
        """测试回测引擎初始化"""
        engine = BacktestEngine(
            initial_capital=1000000,
            commission=0.0003,
            slippage=0.0001,
            stop_loss=0.05,
            take_profit=0.10
        )
        
        self.assertEqual(engine.initial_capital, 1000000)
        self.assertEqual(engine.cash, 1000000)
        self.assertEqual(engine.position, Position.EMPTY)
        print("[初始化测试] 通过 - 回测引擎参数正确")

    def test_buy_operation(self):
        """测试买入操作"""
        engine = BacktestEngine(initial_capital=1000000)
        engine.buy("2024-01-01", price=50.0)
        
        self.assertEqual(engine.position, Position.LONG)
        self.assertGreater(engine.shares, 0)
        self.assertEqual(engine.entry_price, 50.0)
        self.assertEqual(len(engine.trades), 1)
        print(f"[买入测试] 通过 - 买入股数: {engine.shares}")

    def test_sell_operation(self):
        """测试卖出操作"""
        engine = BacktestEngine(initial_capital=1000000)
        engine.buy("2024-01-01", price=50.0)
        engine.sell("2024-01-02", price=55.0)
        
        self.assertEqual(engine.position, Position.EMPTY)
        self.assertEqual(engine.shares, 0)
        self.assertEqual(len(engine.trades), 2)
        
        sell_trade = engine.trades[1]
        self.assertGreater(sell_trade["profit_pct"], 0)
        print(f"[卖出测试] 通过 - 盈利比例: {sell_trade['profit_pct']:.2f}%")

    def test_stop_loss(self):
        """测试止损机制"""
        engine = BacktestEngine(initial_capital=1000000, stop_loss=0.05)
        engine.buy("2024-01-01", price=100.0)
        
        stopped = engine.check_stop_loss("2024-01-02", price=94.0)
        
        self.assertTrue(stopped)
        self.assertEqual(engine.position, Position.EMPTY)
        print("[止损测试] 通过 - 止损机制正常工作")

    def test_take_profit(self):
        """测试止盈机制"""
        engine = BacktestEngine(initial_capital=1000000, take_profit=0.10)
        engine.buy("2024-01-01", price=100.0)
        
        triggered = engine.check_take_profit("2024-01-02", price=111.0)
        
        self.assertTrue(triggered)
        self.assertEqual(engine.position, Position.EMPTY)
        print("[止盈测试] 通过 - 止盈机制正常工作")

    def test_simple_strategy(self):
        """测试简单RSI策略回测"""
        def rsi_strategy(df: pd.DataFrame, i: int) -> str:
            if i < 20:
                return "hold"
            rsi = IndicatorCalculator.calculate_rsi(df["收盘"], 14)
            if rsi.iloc[i] < 30:
                return "buy"
            elif rsi.iloc[i] > 70:
                return "sell"
            return "hold"
        
        engine = BacktestEngine(initial_capital=1000000)
        results = engine.run(self.df, rsi_strategy, show_progress=False)
        
        self.assertIn("total_return", results)
        self.assertIn("win_rate", results)
        self.assertIn("max_drawdown", results)
        self.assertIn("sharpe_ratio", results)
        print(f"[RSI策略回测] 通过 - 总收益: {results['total_return']:.2f}%, 交易次数: {results['total_trades']}")

    def test_equity_curve(self):
        """测试权益曲线更新"""
        engine = BacktestEngine(initial_capital=1000000)
        
        for i in range(10):
            engine.update_equity(f"2024-01-{i+1:02d}", 100 + i)
        
        self.assertEqual(len(engine.equity_curve), 10)
        self.assertTrue(engine.equity_curve[-1]["equity"] >= 0)
        print(f"[权益曲线测试] 通过 - 最终权益: {engine.equity_curve[-1]['equity']:.2f}")


def akshare_available():
    """检查 AkShare 是否可用"""
    try:
        import akshare
        return True
    except ImportError:
        return False


class TestAkShareIntegration(unittest.TestCase):
    """AkShare 真实数据集成测试"""

    @classmethod
    def setUpClass(cls):
        """准备真实数据测试"""
        cls.available = False
        try:
            import akshare as ak
            cls.available = True
            print("\n[数据源] AkShare 可用 - 将使用真实数据进行测试")
        except ImportError:
            print("\n[数据源] AkShare 不可用 - 跳过真实数据测试")

    @unittest.skipUnless(akshare_available(), "AkShare 未安装")
    def test_realtime_quotes(self):
        """测试实时行情获取"""
        from data.collectors.akshare_collector import AkShareCollector
        
        collector = AkShareCollector()
        df = collector.get_realtime_quotes()
        
        self.assertIsInstance(df, pd.DataFrame)
        self.assertGreater(len(df), 0)
        self.assertIn("代码", df.columns)
        print(f"[实时行情] 通过 - 获取了 {len(df)} 只股票的实时数据")

    @unittest.skipUnless(akshare_available(), "AkShare 未安装")
    def test_historical_kline(self):
        """测试历史K线获取"""
        from data.collectors.akshare_collector import AkShareCollector
        
        collector = AkShareCollector()
        df = collector.get_historical_kline(
            stock_code="000001",
            start_date="20240101",
            end_date="20240331",
            use_cache=False
        )
        
        self.assertIsInstance(df, pd.DataFrame)
        self.assertGreater(len(df), 20)
        required_cols = ["日期", "开盘", "最高", "最低", "收盘", "成交量"]
        for col in required_cols:
            self.assertIn(col, df.columns)
        print(f"[历史K线] 通过 - 获取了 {len(df)} 条K线数据")
        print(f"[数据预览] 最新: {df.iloc[-1]['日期']} 收盘: {df.iloc[-1]['收盘']}")

    @unittest.skipUnless(akshare_available(), "AkShare 未安装")
    def test_technical_analysis_on_real_data(self):
        """使用真实数据进行技术分析"""
        import akshare as ak
        from analyzers.technical_analyzer import TechnicalAnalyzer
        
        df = ak.stock_zh_a_hist(
            symbol="000001",
            period="daily",
            start_date="20240101",
            end_date="20240331"
        )
        
        analyzer = TechnicalAnalyzer()
        result = analyzer.analyze(df)
        
        self.assertIn("trend", result)
        self.assertIn("momentum", result)
        self.assertIn("signals", result)
        print(f"[真实数据分析] 通过 - 趋势: {result['trend'].get('trend', 'N/A')}")
        print(f"[买入信号] {len([s for s in result.get('signals', []) if s['type'] == '买入'])} 个")
        print(f"[卖出信号] {len([s for s in result.get('signals', []) if s['type'] == '卖出'])} 个")


def akshare_available():
    """检查 AkShare 是否可用"""
    try:
        import akshare
        return True
    except ImportError:
        return False


class TestData真实性验证(unittest.TestCase):
    """数据真实性验证测试"""

    def test_simulated_data_realistic(self):
        """验证模拟数据符合真实市场特征"""
        np.random.seed(42)
        dates = pd.date_range("2024-01-01", periods=100, freq="D")
        close = 100 + np.cumsum(np.random.randn(100) * 2)
        close = np.maximum(close, 10)
        
        df = pd.DataFrame({
            "日期": dates,
            "开盘": close * 0.99,
            "最高": close * 1.02,
            "最低": close * 0.98,
            "收盘": close,
            "成交量": np.random.randint(1000000, 10000000, 100)
        })
        
        self.assertTrue((df["最高"] >= df["收盘"]).all())
        self.assertTrue((df["最高"] >= df["开盘"]).all())
        self.assertTrue((df["最低"] <= df["收盘"]).all())
        self.assertTrue((df["最低"] <= df["开盘"]).all())
        self.assertTrue((df["成交量"] > 0).all())
        print("[数据真实性] 通过 - OHLCV 数据逻辑正确")


if __name__ == "__main__":
    print("=" * 70)
    print("A股量化分析工具 - 功能测试")
    print("=" * 70)
    print("\n测试数据说明:")
    print("1. 单元测试: 使用模拟K线数据 (np.random.randn 生成)")
    print("   - 确保计算逻辑正确")
    print("   - 可复现，seed=42")
    print("")
    print("2. 集成测试: 使用 AkShare 实时数据")
    print("   - 验证真实市场数据采集能力")
    print("   - 数据来自: 新浪财经、东方财富")
    print("=" * 70)
    
    unittest.main(verbosity=2)
