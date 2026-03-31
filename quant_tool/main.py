#!/usr/bin/env python3
"""
A股量化分析工具 - 小白友好版
========================

专门为新手设计的输出，带详细解释和建议

使用方式：
    python main.py --stock 000001
"""

import sys
import argparse

from config import AKSHARE_CONFIG, BACKTEST_CONFIG
from data.collectors.akshare_collector import AkShareCollector
from data.collectors.sentiment_collector import SentimentCollector
from data.processors.indicator import IndicatorCalculator
from analyzers.technical_analyzer import TechnicalAnalyzer
from analyzers.sentiment_analyzer import SentimentAnalyzer
from backtest.engine import BacktestEngine


TERMINOLOGY = {
    "RSI": {
        "name": "RSI 相对强弱指数",
        "explain": "衡量股票涨跌动力的指标，就像速度表。数值越高说明涨得越猛，越低说明跌得越凶",
        "区间": {
            "超买区(>70)": "涨太多了，可能要跌",
            "中性区(30-70)": "正常范围",
            "超卖区(<30)": "跌太多了，可能要涨"
        }
    },
    "MACD": {
        "name": "MACD 指数平滑异同",
        "explain": "判断趋势方向的指标，像汽车的方向盘。MACD金叉=往上开，死叉=往下开",
        "区间": {}
    },
    "KDJ": {
        "name": "KDJ 随机指标",
        "explain": "判断超买超卖的指标，像汽车的油表。J值>100=没油了要跌，J值<0=快没油了要涨",
        "区间": {
            "超买区(K>80,J>100)": "涨太多了，可能要跌",
            "中性区(K 20-80)": "正常范围",
            "超卖区(K<20,J<0)": "跌太多了，可能要涨"
        }
    },
    "布林带": {
        "name": "布林带",
        "explain": "像股票的高速公路。价格在上轨=超速要跌，下轨=慢速要涨，中轨=正常行驶",
        "区间": {
            "上轨附近(>80%)": "价格偏高，小心下跌",
            "下轨附近(<20%)": "价格偏低，可能反弹",
            "中轨附近": "正常范围"
        }
    },
    "量比": {
        "name": "量比",
        "explain": "今天的成交量和平时比，像热闹程度。>2=特别热闹，<0.5=冷清",
        "区间": {
            "异常放量(>2)": "有很多人突然买入，要关注",
            "正常(0.5-2)": "正常交易",
            "缩量(<0.5)": "交易冷清，可能横盘"
        }
    },
    "MACD金叉": "MACD的DIF线从下往上穿过DEA线，像汽车往上冲，看涨信号",
    "MACD死叉": "MACD的DIF线从上往下穿过DEA线，像汽车往下掉，看跌信号",
    "底背离": "价格创新低但指标没创新低，像物极必反，看涨信号",
    "顶背离": "价格创新高但指标没创新高，像强弩之末，看跌信号",
}


def print_banner():
    print("=" * 70)
    print("               A股量化分析工具 v2.0 (小白版)")
    print("=" * 70)
    print()


def explain_term(term):
    """打印术语解释"""
    if term in TERMINOLOGY:
        info = TERMINOLOGY[term]
        if isinstance(info, dict):
            print(f"\n📖 【{info['name']}】")
            print(f"   {info['explain']}")
            if info.get('区间'):
                print("   数值解读：")
                for k, v in info['区间'].items():
                    print(f"     • {k}：{v}")
        else:
            print(f"\n📖 【{term}】")
            print(f"   {info}")


def get_simple_verdict(analysis: dict) -> dict:
    """生成简化的投资建议"""
    result = {
        "action": "观望",
        "reason": [],
        "confidence": "低"
    }
    
    signals = analysis.get("signals", [])
    momentum = analysis.get("momentum", {})
    trend = analysis.get("trend", {})
    volume = analysis.get("volume", {})
    volatility = analysis.get("volatility", {})
    
    buy_signals = [s for s in signals if s["type"] == "买入"]
    sell_signals = [s for s in signals if s["type"] == "卖出"]
    
    score = 0
    reasons = []
    
    if momentum.get("rsi"):
        rsi = momentum["rsi"]["value"]
        if rsi < 30:
            score += 2
            reasons.append(f"RSI={rsi:.0f}，处于超卖区，可能反弹")
        elif rsi > 70:
            score -= 2
            reasons.append(f"RSI={rsi:.0f}，处于超买区，可能回调")
    
    if buy_signals:
        score += len(buy_signals)
        reasons.append(f"出现{len(buy_signals)}个买入信号")
    if sell_signals:
        score -= len(sell_signals)
        reasons.append(f"出现{len(sell_signals)}个卖出信号")
    
    if volatility.get("bollinger"):
        bb_pos = volatility["bollinger"]["position"]
        if bb_pos < 20:
            score += 1
            reasons.append(f"价格触及布林下轨，可能反弹")
        elif bb_pos > 80:
            score -= 1
            reasons.append(f"价格触及布林上轨，可能回调")
    
    if trend.get("trend") == "上涨":
        score += 1
    elif trend.get("trend") == "下跌":
        score -= 1
    
    if score >= 3:
        result = {"action": "可以考虑买入", "reason": reasons, "confidence": "较高"}
    elif score >= 1:
        result = {"action": "轻度看好", "reason": reasons, "confidence": "中"}
    elif score <= -3:
        result = {"action": "建议回避", "reason": reasons, "confidence": "较高"}
    elif score <= -1:
        result = {"action": "轻度看空", "reason": reasons, "confidence": "中"}
    else:
        reasons.append("多空信号均衡，建议观望等待更明确信号")
        result = {"action": "观望", "reason": reasons, "confidence": "低"}
    
    return result


def analyze_stock(stock_code: str, start_date: str = "20240101", end_date: str = "20260331"):
    """分析单只股票（小白友好版）"""
    print(f"\n开始分析股票: {stock_code}")
    print("-" * 50)
    
    collector = AkShareCollector()
    
    print("\n正在获取数据...")
    kline_df = collector.get_historical_kline(stock_code, start_date, end_date)
    if kline_df is None or len(kline_df) == 0:
        print(f"[错误] 无法获取 {stock_code} 的数据")
        return
    
    print(f"获取到 {len(kline_df)} 条历史数据")
    
    print("正在计算指标...")
    indicators = IndicatorCalculator.calculate_all(kline_df)
    
    tech_analyzer = TechnicalAnalyzer()
    analysis = tech_analyzer.analyze(kline_df)
    
    print("\n" + "=" * 70)
    print(f"               分析报告: {stock_code}")
    print("=" * 70)
    
    print("\n" + "━" * 70)
    print("【最终结论】")
    print("━" * 70)
    
    verdict = get_simple_verdict(analysis)
    
    print(f"\n{'='*50}")
    if verdict["action"] in ["建议回避", "可以考虑买入"]:
        symbol = "🔴" if verdict["action"] == "建议回避" else "🟢"
        print(f"{symbol} 推荐操作: {verdict['action']}")
    else:
        symbol = "🟡"
        print(f"{symbol} 推荐操作: {verdict['action']}")
    print(f"{'='*50}")
    
    if verdict["reason"]:
        print("\n原因：")
        for i, r in enumerate(verdict["reason"], 1):
            print(f"  {i}. {r}")
    
    print(f"\n信号可信度: {verdict['confidence']}")
    
    print("\n" + "━" * 70)
    print("【详细解读】")
    print("━" * 70)
    
    trend = analysis.get("trend", {})
    print(f"\n📊 趋势判断：{trend.get('trend', 'N/A')}")
    print(f"   解释：股价目前整体走势是{trend.get('trend', '未知')}趋势")
    
    momentum = analysis.get("momentum", {})
    
    if "rsi" in momentum:
        rsi = momentum["rsi"]
        explain_term("RSI")
        print(f"\n   你看到的值: RSI={rsi['value']:.1f}，状态={rsi['signal']}")
        if rsi['value'] > 70:
            print(f"   ➜ 解读：涨太多了，继续追涨风险大！")
        elif rsi['value'] < 30:
            print(f"   ➜ 解读：跌过头了，可能有反弹机会")
        else:
            print(f"   ➜ 解读：正常范围，可以继续观察")
    
    if "macd" in momentum:
        macd = momentum["macd"]
        print(f"\n📊 MACD指标：")
        explain_term("MACD")
        print(f"\n   DIF线: {macd['dif']:.4f}")
        print(f"   DEA线: {macd['dea']:.4f}")
        print(f"   当前状态: {macd['signal']}")
        if macd['signal'] == '多头':
            print(f"   ➜ 解读：MACD显示上涨趋势")
        elif macd['signal'] == '空头':
            print(f"   ➜ 解读：MACD显示下跌趋势")
    
    if "kdj" in momentum:
        kdj = momentum["kdj"]
        explain_term("KDJ")
        print(f"\n   K={kdj['k']:.1f}, D={kdj['d']:.1f}, J={kdj['j']:.1f}")
        print(f"   状态: {kdj['signal']}")
        if kdj['signal'] == '超买':
            print(f"   ➜ 解读：KDJ显示涨过头了，注意风险")
        elif kdj['signal'] == '超卖':
            print(f"   ➜ 解读：KDJ显示跌过头了，可能反弹")
    
    print("\n" + "━" * 70)
    print("【成交量分析】")
    print("━" * 70)
    
    volume = analysis.get("volume", {})
    if "volume_ratio" in volume:
        vr = volume["volume_ratio"]
        explain_term("量比")
        print(f"\n   今日量比: {vr['value']:.2f} ({vr['signal']})")
        if vr['value'] > 2:
            print(f"   ➜ 解读：成交量突然放大，通常有大事发生，要密切关注")
        elif vr['value'] < 0.5:
            print(f"   ➜ 解读：成交量萎缩，观望情绪浓厚")
    
    if "price_volume" in volume:
        pv = volume['price_volume']
        print(f"\n   量价关系: {pv}")
        if "价涨量增" in pv:
            print(f"   ➜ 解读：价涨量增，健康的上涨走势")
        elif "价跌量增" in pv:
            print(f"   ➜ 解读：放量下跌，不太好，可能还要跌")
        elif "价涨量缩" in pv:
            print(f"   ➜ 解读：缩量上涨，上涨动力不足")
    
    print("\n" + "━" * 70)
    print("【波动性分析】")
    print("━" * 70)
    
    volatility = analysis.get("volatility", {})
    if "bollinger" in volatility:
        bb = volatility["bollinger"]
        explain_term("布林带")
        print(f"\n   价格位置: {bb['position']:.1f}% (0%=下轨，100%=上轨)")
        print(f"   ➜ 状态: {bb['signal']}")
        if bb['position'] > 80:
            print(f"   ➜ 解读：价格已经很高了，小心回调风险")
        elif bb['position'] < 20:
            print(f"   ➜ 解读：价格已经很低了，可能有反弹机会")
    
    signals = analysis.get("signals", [])
    if signals:
        print("\n" + "━" * 70)
        print("【交易信号】")
        print("━" * 70)
        print(f"\n发现 {len(signals)} 个信号：\n")
        for i, sig in enumerate(signals, 1):
            sig_type = sig["type"]
            reason = sig["reason"]
            strength = sig["strength"]
            
            if sig_type == "买入":
                symbol = "🟢"
            else:
                symbol = "🔴"
            
            print(f"{symbol} 信号{i}: {sig_type} - {reason}")
            print(f"   强度: {strength}")
            
            if reason in ["MACD金叉", "KDJ低位金叉"]:
                explain_term("MACD金叉" if "MACD" in reason else "底背离")
            elif reason in ["MACD死叉", "KDJ高位死叉"]:
                explain_term("MACD死叉" if "MACD" in reason else "顶背离")
            
            print()
    
    print("\n" + "=" * 70)
    print("【术语解释】")
    print("=" * 70)
    explain_term("MACD金叉")
    explain_term("MACD死叉")
    explain_term("底背离")
    explain_term("顶背离")
    
    print("\n" + "=" * 70)
    print("⚠️  免责声明")
    print("=" * 70)
    print("""
本工具仅供参考，不构成投资建议！
股市有风险，入市需谨慎。
建议结合多方信息做出决策。
""")
    print("=" * 70)


def backtest_stock(stock_code: str, start_date: str = "20240101", end_date: str = "20260331"):
    """回测单只股票"""
    print(f"\n[回测模式] {stock_code}")
    print("-" * 50)
    
    collector = AkShareCollector()
    kline_df = collector.get_historical_kline(stock_code, start_date, end_date)
    
    if kline_df is None or len(kline_df) < 60:
        print(f"[错误] 数据不足，无法回测")
        return
    
    def rsi_strategy(df: dict, i: int) -> str:
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


def batch_analyze(stock_codes: list):
    """批量分析"""
    print(f"\n[批量分析] {len(stock_codes)} 只股票")
    print("-" * 50)
    
    collector = AkShareCollector()
    analyzer = TechnicalAnalyzer()
    
    results = []
    for code in stock_codes:
        try:
            kline_df = collector.get_historical_kline(code)
            if kline_df is not None and len(kline_df) >= 20:
                analysis = analyzer.analyze(kline_df)
                verdict = get_simple_verdict(analysis)
                results.append({
                    "code": code,
                    "action": verdict["action"],
                    "reason": verdict["reason"],
                    "signals": len(analysis.get("signals", []))
                })
                print(f"[{code}] {verdict['action']}")
        except Exception as e:
            print(f"[{code}] 分析失败: {e}")
    
    if results:
        print("\n" + "=" * 50)
        print("汇总结果")
        print("=" * 50)
        for r in results:
            print(f"\n{r['code']}: {r['action']}")


def main():
    parser = argparse.ArgumentParser(description="A股量化分析工具 v2.0 (小白版)")
    
    parser.add_argument("--stock", type=str, default="000001", help="股票代码")
    parser.add_argument("--stocks", type=str, default="", help="股票代码列表")
    parser.add_argument("--mode", type=str, default="analyze", choices=["analyze", "backtest", "batch"])
    parser.add_argument("--start", type=str, default="20240101", help="开始日期")
    parser.add_argument("--end", type=str, default="20260331", help="结束日期")
    
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
