#!/usr/bin/env python3
"""
A股量化分析工具 - 主入口
==================

功能：
1. 数据收集（AkShare/新浪财经）
2. 技术指标计算
3. 纯交易数据分析（量价关系/背离）
4. 情绪数据收集（爬虫）
5. 回测引擎

使用方式：
    python main.py --stock 000001 --mode analyze
    python main.py --stock 000001 --mode backtest
    python main.py --stocks 000001,600519,000858 --mode batch
"""

import sys
import argparse
from typing import List, Dict

from config import AKSHARE_CONFIG, BACKTEST_CONFIG
from data.collectors.akshare_collector import AkShareCollector
from data.collectors.sentiment_collector import SentimentCollector
from data.processors.indicator import IndicatorCalculator
from analyzers.technical_analyzer import TechnicalAnalyzer
from analyzers.sentiment_analyzer import SentimentAnalyzer
from backtest.engine import BacktestEngine


def print_banner():
    print("=" * 70)
    print("                    A股量化分析工具 v1.0")
    print("=" * 70)
    print()


def analyze_stock(stock_code: str, start_date: str = "20240101", end_date: str = "20260331"):
    """
    分析单只股票
    """
    print(f"\n[主程序] 开始分析: {stock_code}")
    print("-" * 50)
    
    collector = AkShareCollector()
    sentiment_collector = SentimentCollector()
    
    print("\n>>> 步骤1: 收集K线数据...")
    kline_df = collector.get_historical_kline(stock_code, start_date, end_date)
    if kline_df is None or len(kline_df) == 0:
        print(f"[错误] 无法获取 {stock_code} 的数据")
        return
    
    print(f"获取到 {len(kline_df)} 条K线记录")
    
    print("\n>>> 步骤2: 技术指标计算...")
    indicators = IndicatorCalculator.calculate_all(kline_df)
    print("技术指标计算完成")
    
    print("\n>>> 步骤3: 纯交易数据分析...")
    tech_analyzer = TechnicalAnalyzer()
    analysis = tech_analyzer.analyze(kline_df)
    
    print("\n" + "=" * 60)
    print(f"技术分析报告: {stock_code}")
    print("=" * 60)
    
    print(f"\n【趋势分析】")
    trend = analysis.get("trend", {})
    print(f"  趋势方向: {trend.get('trend', 'N/A')}")
    print(f"  趋势评分: {trend.get('trend_score', 0)}")
    print(f"  5日平均收益: {trend.get('avg_return_5d', 0):.2f}%")
    print(f"  5日最大回撤: {trend.get('max_drawdown_5d', 0):.2f}%")
    
    print(f"\n【动量分析】")
    momentum = analysis.get("momentum", {})
    if "rsi" in momentum:
        rsi = momentum["rsi"]
        print(f"  RSI(14): {rsi['value']:.2f} - {rsi['signal']}")
    if "macd" in momentum:
        macd = momentum["macd"]
        print(f"  MACD: DIF={macd['dif']:.4f}, DEA={macd['dea']:.4f} - {macd['signal']}")
    if "kdj" in momentum:
        kdj = momentum["kdj"]
        print(f"  KDJ: K={kdj['k']:.2f}, D={kdj['d']:.2f}, J={kdj['j']:.2f} - {kdj['signal']}")
    
    print(f"\n【量价分析】")
    volume = analysis.get("volume", {})
    if "volume_ratio" in volume:
        vr = volume["volume_ratio"]
        print(f"  量比: {vr['value']:.2f} - {vr['signal']}")
    if "price_volume" in volume:
        print(f"  量价关系: {volume['price_volume']}")
    
    print(f"\n【波动性分析】")
    volatility = analysis.get("volatility", {})
    if "bollinger" in volatility:
        bb = volatility["bollinger"]
        print(f"  布林带位置: {bb['position']:.2f}% - {bb['signal']}")
        print(f"  布林上轨: {bb['upper']:.2f}, 下轨: {bb['lower']:.2f}")
    if "atr" in volatility:
        atr = volatility["atr"]
        print(f"  ATR: {atr['value']:.2f} (波动率{atr['atr_percent']:.2f}%)")
    
    signals = analysis.get("signals", [])
    print(f"\n【交易信号】 ({len(signals)}个)")
    if signals:
        for i, sig in enumerate(signals, 1):
            print(f"  {i}. [{sig['type']}] {sig['reason']} (强度:{sig['strength']})")
    else:
        print("  暂无明确信号")
    
    print(f"\n【综合结论】")
    print(f"  {analysis.get('summary', 'N/A')}")
    
    print("\n>>> 步骤4: 情绪数据收集...")
    sentiment_result = sentiment_collector.get_market_sentiment_index()
    print(f"  市场情绪指数: {sentiment_result.get('sentiment_value', 'N/A')}")
    
    print("\n" + "=" * 60)
    print(f"分析完成: {stock_code}")
    print("=" * 60)


def backtest_stock(stock_code: str, start_date: str = "20240101", end_date: str = "20260331"):
    """
    回测单只股票
    """
    print(f"\n[主程序] 开始回测: {stock_code}")
    print("-" * 50)
    
    collector = AkShareCollector()
    kline_df = collector.get_historical_kline(stock_code, start_date, end_date)
    
    if kline_df is None or len(kline_df) < 60:
        print(f"[错误] 数据不足，无法回测")
        return
    
    def rsi_strategy(df: Dict, i: int) -> str:
        """RSI均值回归策略"""
        if i < 20:
            return "hold"
        
        close_col = "收盘" if "收盘" in df.columns else "close"
        close = df[close_col]
        rsi = IndicatorCalculator.calculate_rsi(close, 14)
        
        if i >= len(rsi):
            return "hold"
        
        current_rsi = rsi.iloc[i]
        prev_rsi = rsi.iloc[i-1] if i > 0 else 50
        
        if prev_rsi < 30 and current_rsi >= 30:
            return "buy"
        elif prev_rsi > 70 and current_rsi <= 70:
            return "sell"
        
        return "hold"
    
    engine = BacktestEngine(
        initial_capital=BACKTEST_CONFIG["initial_capital"],
        commission=BACKTEST_CONFIG["commission"],
        stop_loss=BACKTEST_CONFIG["stop_loss"],
        take_profit=BACKTEST_CONFIG["take_profit"]
    )
    
    results = engine.run(kline_df, rsi_strategy)
    engine.print_summary(results)
    
    return results


def batch_analyze(stock_codes: List[str]):
    """
    批量分析多只股票
    """
    print(f"\n[主程序] 批量分析 {len(stock_codes)} 只股票")
    print("-" * 50)
    
    collector = AkShareCollector()
    analyzer = TechnicalAnalyzer()
    
    results = []
    for code in stock_codes:
        try:
            kline_df = collector.get_historical_kline(code)
            if kline_df is not None and len(kline_df) >= 20:
                analysis = analyzer.analyze(kline_df)
                results.append({
                    "code": code,
                    "trend": analysis.get("trend", {}).get("trend", "N/A"),
                    "signals": len(analysis.get("signals", [])),
                    "summary": analysis.get("summary", "")
                })
                print(f"[{code}] 分析完成")
            else:
                print(f"[{code}] 数据不足")
        except Exception as e:
            print(f"[{code}] 分析失败: {e}")
    
    print("\n" + "=" * 60)
    print("批量分析结果汇总")
    print("=" * 60)
    for r in results:
        print(f"\n{r['code']}:")
        print(f"  趋势: {r['trend']}")
        print(f"  信号数: {r['signals']}")
        print(f"  总结: {r['summary']}")


def main():
    parser = argparse.ArgumentParser(description="A股量化分析工具")
    
    parser.add_argument("--stock", type=str, default="000001",
                        help="股票代码 (默认: 000001)")
    parser.add_argument("--stocks", type=str, default="",
                        help="股票代码列表，逗号分隔")
    parser.add_argument("--mode", type=str, default="analyze",
                        choices=["analyze", "backtest", "batch"],
                        help="运行模式")
    parser.add_argument("--start", type=str, default="20240101",
                        help="开始日期 YYYYMMDD")
    parser.add_argument("--end", type=str, default="20260331",
                        help="结束日期 YYYYMMDD")
    
    args = parser.parse_args()
    
    print_banner()
    
    if args.stocks:
        stock_list = [s.strip() for s in args.stocks.split(",")]
        batch_analyze(stock_list)
    elif args.mode == "backtest":
        backtest_stock(args.stock, args.start, args.end)
    else:
        analyze_stock(args.stock, args.start, args.end)


if __name__ == "__main__":
    main()
