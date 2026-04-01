"""
Streamlit Web界面
A股量化分析系统 v2.0
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))

from data.collectors.akshare_collector import AkShareCollector
from data.processors.indicator import IndicatorCalculator
from analyzers.technical_analyzer import TechnicalAnalyzer
from analyzers.fundamental_analyzer import FundamentalAnalyzer, get_mock_financial_data
from analyzers.multi_factor_engine import MultiFactorEngine
from analyzers.noise_filter import NoiseFilterPipeline
from backtest.time_locked_backtest import TimeLockedBacktest, MockDataProvider


MOCK_KLINE_DATA = {
    "000001": {
        "name": "平安银行",
        "base_price": 8.96,
        "volatility": 0.02
    },
    "600519": {
        "name": "贵州茅台",
        "base_price": 1680.0,
        "volatility": 0.015
    },
    "000858": {
        "name": "五粮液",
        "base_price": 145.0,
        "volatility": 0.018
    }
}


def generate_mock_kline(stock_code: str, days: int = 100) -> pd.DataFrame:
    """生成模拟K线数据用于演示"""
    np.random.seed(hash(stock_code) % 2**32)
    
    if stock_code in MOCK_KLINE_DATA:
        config = MOCK_KLINE_DATA[stock_code]
        base_price = config["base_price"]
        volatility = config["volatility"]
    else:
        base_price = 20.0 + np.random.rand() * 80
        volatility = 0.02 + np.random.rand() * 0.02
    
    dates = pd.date_range(end=datetime.now(), periods=days, freq="D")
    dates = [d for d in dates if d.weekday() < 5][:days]
    
    trend = np.cumsum(np.random.randn(len(dates)) * volatility * base_price)
    close = base_price + trend * 0.3
    close = np.maximum(close, base_price * 0.5)
    
    df = pd.DataFrame({
        "日期": [d.strftime("%Y-%m-%d") for d in dates],
        "开盘": close * (1 + np.random.randn(len(dates)) * 0.005),
        "最高": close * (1 + np.abs(np.random.randn(len(dates)) * 0.01)),
        "最低": close * (1 - np.abs(np.random.randn(len(dates)) * 0.01)),
        "收盘": close,
        "成交量": np.random.randint(5000000, 50000000, len(dates))
    })
    
    df["开盘"] = df["开盘"].clip(lower=df["最低"] * 0.99, upper=df["最高"] * 1.01)
    df["收盘"] = df["收盘"].clip(lower=df["最低"] * 0.99, upper=df["最高"] * 1.01)
    
    return df


def convert_technical_signals(tech_result: dict) -> dict:
    """
    将 TechnicalAnalyzer 返回的结果转换为 MultiFactorEngine 期望的格式
    
    转换逻辑：
    - direction: 从 trend 获取（上涨/下跌/震荡 -> 偏多/偏空/中性）
    - score: 综合计算（基于买卖信号数量和强弱）
    """
    trend = tech_result.get("trend", {})
    signals = tech_result.get("signals", [])
    
    trend_direction = trend.get("trend", "震荡")
    if trend_direction == "上涨":
        direction = "偏多"
    elif trend_direction == "下跌":
        direction = "偏空"
    else:
        direction = "中性"
    
    buy_signals = [s for s in signals if s.get("type") == "买入"]
    sell_signals = [s for s in signals if s.get("type") == "卖出"]
    
    strength_map = {"强": 1.0, "中": 0.5, "弱": 0.25}
    
    buy_score = sum(strength_map.get(s.get("strength", "弱"), 0.25) for s in buy_signals)
    sell_score = sum(strength_map.get(s.get("strength", "弱"), 0.25) for s in sell_signals)
    
    score = buy_score - sell_score
    
    score = max(-3, min(3, score))
    
    return {
        "direction": direction,
        "score": score,
        "signals": signals
    }


INDICATOR_GUIDE = {
    "RSI": {
        "name": "RSI 相对强弱指数",
        "description": "衡量股价涨跌动力的指标，像速度表。数值越高说明涨得越猛，越低说明跌得越凶。",
        "ranges": {
            (70, 100): ("超买区", "危险", "涨太多，可能要跌，风险较高"),
            (30, 70): ("中性区", "正常", "正常波动范围，可继续观察"),
            (0, 30): ("超卖区", "机会", "跌太多，可能反弹，关注买入机会"),
        },
        "interpretation": "RSI > 70 超买，可能回调；RSI < 30 超卖，可能反弹"
    },
    "MACD": {
        "name": "MACD 指数平滑异同",
        "description": "判断趋势方向的指标，像方向盘。金叉往上开=看涨，死叉往下开=看跌。",
        "signals": {
            "多头": ("上涨趋势", " DIF > DEA 且 DIF > 0"),
            "空头": ("下跌趋势", " DIF < DEA 且 DIF < 0"),
            "中性": ("盘整", " DIF 接近 DEA"),
        },
        "interpretation": "MACD金叉买入，死叉卖出"
    },
    "KDJ": {
        "name": "KDJ 随机指标",
        "description": "判断超买超卖的指标，像油表。J值 > 100 = 没油了要跌，J值 < 0 = 快没油了要涨。",
        "ranges": {
            (80, 100): ("超买区", "危险", "K>80或J>100，涨过头了，注意风险"),
            (20, 80): ("中性区", "正常", "K在20-80之间，正常范围"),
            (0, 20): ("超卖区", "机会", "K<20或J<0，跌过头了，可能反弹"),
        },
        "interpretation": "KDJ低位金叉买入，高位死叉卖出"
    },
    "布林带": {
        "name": "布林带 (Bollinger Bands)",
        "description": "像股票的高速公路。上轨=超速要跌，下轨=慢速要涨，中轨=正常行驶。",
        "ranges": {
            (80, 100): ("上轨附近", "偏高", "价格触及上轨，可能回调"),
            (20, 80): ("中轨附近", "正常", "价格在通道内正常波动"),
            (0, 20): ("下轨附近", "偏低", "价格触及下轨，可能反弹"),
        },
        "interpretation": "价格突破上轨卖出，跌破下轨买入"
    },
    "量比": {
        "name": "量比 (Volume Ratio)",
        "description": "今天的成交量和平时比，像热闹程度。",
        "ranges": {
            (2, 100): ("异常放量", "关注", "突然放量，通常有大事发生"),
            (0.5, 2): ("正常范围", "正常", "正常交易活动"),
            (0, 0.5): ("缩量", "观望", "交易冷清，可能横盘"),
        },
        "interpretation": "量比 > 2 关注放量；量比 < 0.5 观望"
    },
    "OBV": {
        "name": "OBV 能量潮",
        "description": "累积成交量变化的指标，OBV上升=资金流入，下降=资金流出。",
        "interpretation": "OBV上升且价格上升=确认上涨；OBV下降且价格上升=顶背离（危险）"
    },
    "ATR": {
        "name": "ATR 平均真实波幅",
        "description": "衡量股价波动程度的指标，ATR越高=波动越剧烈。用于设置止损。",
        "interpretation": "ATR用于计算止损幅度，一般设置为止损1-2倍ATR"
    }
}


def show_indicator_guide():
    """显示指标解释指南"""
    st.sidebar.divider()
    st.sidebar.header("📖 指标解释")
    
    with st.sidebar.expander("RSI 相对强弱指数", expanded=False):
        info = INDICATOR_GUIDE["RSI"]
        st.write(f"**{info['name']}**")
        st.write(info['description'])
        st.write("---")
        st.write("**参考区间：**")
        for (low, high), (zone, status, meaning) in info['ranges'].items():
            icon = "🔴" if status == "危险" else ("🟢" if status == "机会" else "🟡")
            st.write(f"{icon} **{low}-{high}** {zone}: {meaning}")
        st.write("---")
        st.write(f"📌 *{info['interpretation']}*")
    
    with st.sidebar.expander("MACD 指数平滑异同", expanded=False):
        info = INDICATOR_GUIDE["MACD"]
        st.write(f"**{info['name']}**")
        st.write(info['description'])
        st.write("---")
        st.write("**信号解读：**")
        for signal, (trend, condition) in info['signals'].items():
            icon = "🟢" if signal == "多头" else ("🔴" if signal == "空头" else "🟡")
            st.write(f"{icon} **{signal}**: {trend} ({condition})")
        st.write("---")
        st.write(f"📌 *{info['interpretation']}*")
    
    with st.sidebar.expander("KDJ 随机指标", expanded=False):
        info = INDICATOR_GUIDE["KDJ"]
        st.write(f"**{info['name']}**")
        st.write(info['description'])
        st.write("---")
        st.write("**参考区间：**")
        for (low, high), (zone, status, meaning) in info['ranges'].items():
            icon = "🔴" if status == "危险" else ("🟢" if status == "机会" else "🟡")
            st.write(f"{icon} **{low}-{high}** {zone}: {meaning}")
        st.write("---")
        st.write(f"📌 *{info['interpretation']}*")
    
    with st.sidebar.expander("布林带", expanded=False):
        info = INDICATOR_GUIDE["布林带"]
        st.write(f"**{info['name']}**")
        st.write(info['description'])
        st.write("---")
        st.write("**价格位置：**")
        for (low, high), (zone, status, meaning) in info['ranges'].items():
            icon = "🔴" if status == "偏高" else ("🟢" if status == "偏低" else "🟡")
            st.write(f"{icon} **{low}-{high}%** {zone}: {meaning}")
        st.write("---")
        st.write(f"📌 *{info['interpretation']}*")
    
    with st.sidebar.expander("量比", expanded=False):
        info = INDICATOR_GUIDE["量比"]
        st.write(f"**{info['name']}**")
        st.write(info['description'])
        st.write("---")
        st.write("**参考区间：**")
        for (low, high), (zone, status, meaning) in info['ranges'].items():
            icon = "🟡" if status == "正常" else ("🟠" if status == "关注" else "🔵")
            st.write(f"{icon} **{low}-{high}** {zone}: {meaning}")
        st.write("---")
        st.write(f"📌 *{info['interpretation']}*")
    
    with st.sidebar.expander("OBV 能量潮", expanded=False):
        info = INDICATOR_GUIDE["OBV"]
        st.write(f"**{info['name']}**")
        st.write(info['description'])
        st.write("---")
        st.write(f"📌 *{info['interpretation']}*")
    
    with st.sidebar.expander("ATR 平均真实波幅", expanded=False):
        info = INDICATOR_GUIDE["ATR"]
        st.write(f"**{info['name']}**")
        st.write(info['description'])
        st.write("---")
        st.write(f"📌 *{info['interpretation']}*")


def show_data_source_info(use_cache: bool = False, is_mock: bool = False):
    """显示数据来源信息"""
    if is_mock:
        st.info("当前使用模拟数据（网络不可用）")
    elif use_cache:
        st.success("数据来源：缓存数据")


st.set_page_config(
    page_title="A股量化分析系统",
    page_icon="📈",
    layout="wide"
)


def main():
    st.title("📈 A股量化分析系统 v2.0")
    st.markdown("**技术面 + 基本面 + 情绪面 三维度融合分析**")
    
    show_indicator_guide()
    
    with st.sidebar:
        st.header("设置")
        
        stock_code = st.text_input("股票代码", value="000001", help="如：000001, 600519")
        
        analyze_button = st.button("开始分析", type="primary", use_container_width=True)
        
        st.divider()
        
        with st.expander("高级设置"):
            use_llm = st.checkbox("使用LLM分析情绪", value=False)
            if use_llm:
                llm_base_url = st.text_input("LLM API URL", value="")
                llm_api_key = st.text_input("LLM API Key", type="password", value="")
                llm_model = st.selectbox("模型", ["gpt-3.5-turbo", "gpt-4", "deepseek-chat"])
        
        st.divider()
        
        with st.expander("回测设置"):
            run_backtest = st.checkbox("运行时间锁定回测", value=False)
            if run_backtest:
                start_date = st.date_input("回测开始日期", value=datetime.now() - timedelta(days=90))
                end_date = st.date_input("回测结束日期", value=datetime.now())
    
    if analyze_button or "analysis_result" in st.session_state:
        if not analyze_button and "analysis_result" in st.session_state:
            result = st.session_state.analysis_result
        else:
            with st.spinner("正在获取数据..."):
                collector = AkShareCollector()
                kline_df = None
                use_cache = False
                is_mock = False
                
                try:
                    kline_df = collector.get_historical_kline(stock_code, use_cache=True)
                except Exception as e:
                    error_msg = str(e)
                    if "RemoteDisconnected" in error_msg or "Connection" in error_msg:
                        st.warning("网络不可用，使用模拟数据进行演示")
                        is_mock = True
                    else:
                        st.warning(f"数据获取异常: {error_msg[:50]}... 使用模拟数据")
                        is_mock = True
                
                if kline_df is None or len(kline_df) < 20:
                    if stock_code in MOCK_KLINE_DATA:
                        stock_name = MOCK_KLINE_DATA[stock_code]["name"]
                        st.info(f"使用 {stock_name} 的模拟数据进行演示")
                    else:
                        st.info(f"使用通用模拟数据进行演示")
                    kline_df = generate_mock_kline(stock_code, days=100)
                    is_mock = True
                    use_cache = False
                
                if kline_df is not None and len(kline_df) > 0:
                    indicators = IndicatorCalculator.calculate_all(kline_df)
                    
                    tech_analyzer = TechnicalAnalyzer()
                    tech_result = tech_analyzer.analyze(kline_df)
                    
                    financial_data = get_mock_financial_data(stock_code)
                    fund_analyzer = FundamentalAnalyzer()
                    fund_result = fund_analyzer.analyze(financial_data)
                    
                    tech_signals = convert_technical_signals(tech_result)
                    sent_result = {"score": 0.2, "label": "轻度看多"}
                    
                    mf_engine = MultiFactorEngine()
                    mf_result = mf_engine.fuse(
                        tech_signals,
                        {"direction": fund_result.overall, "score": fund_result.score},
                        sent_result["score"]
                    )
                    
                    result = {
                        "stock_code": stock_code,
                        "kline": kline_df,
                        "indicators": indicators,
                        "technical": tech_result,
                        "fundamental": fund_result,
                        "sentiment": sent_result,
                        "multi_factor": mf_result
                    }
                    
                    st.session_state.analysis_result = result
                else:
                    st.error("无法获取数据，请检查股票代码")
                    return
        
        if result:
            mf = result["multi_factor"]
            tech_signals = convert_technical_signals(result["technical"])
            
            tech_score = mf.technical_score
            fund_score = mf.fundamental_score
            sent_score = mf.sentiment_score
            
            tech_direction = tech_signals.get("direction", "中性")
            buy_signals = [s for s in tech_signals.get("signals", []) if s.get("type") == "买入"]
            sell_signals = [s for s in tech_signals.get("signals", []) if s.get("type") == "卖出"]
            
            fund_direction = result["fundamental"].overall
            
            st.subheader("综合分析结果")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("推荐操作", mf.action)
            
            with col2:
                st.metric("置信度", f"{mf.confidence:.0%}")
            
            with col3:
                st.metric("综合评分", f"{mf.score:.3f}")
            
            with st.expander("📐 查看计算详情", expanded=True):
                st.markdown("### 计算公式")
                
                st.markdown("""
                **综合评分计算：**
                ```
                score = tech_score × 0.4 + fund_score × 0.3 + sent_score × 0.3
                      = ({:.3f}) × 0.4 + ({:.3f}) × 0.3 + ({:.3f}) × 0.3
                      = {:.3f}
                ```
                """.format(tech_score, fund_score, sent_score, mf.score))
                
                st.markdown("""
                | 维度 | 得分 | 权重 | 贡献 |
                |------|------|------|------|
                | 技术面 | {:.3f} | 40% | {:.3f} |
                | 基本面 | {:.3f} | 30% | {:.3f} |
                | 情绪面 | {:.3f} | 30% | {:.3f} |
                """.format(
                    tech_score, tech_score * 0.4,
                    fund_score, fund_score * 0.3,
                    sent_score, sent_score * 0.3
                ))
                
                st.markdown("### 判断逻辑")
                
                action_text = ""
                if mf.action == "可以考虑买入":
                    action_text = f"""
                    **买入条件：** score ≥ 0.3 且 信号一致
                    - 当前 score = {mf.score:.3f} {'≥' if mf.score >= 0.3 else '<'} 0.3 ✓
                    - 信号一致性：{'一致' if mf.is_consistent else '不一致'}
                    """
                elif mf.action == "建议回避":
                    action_text = f"""
                    **回避条件：** score ≤ -0.3 且 信号一致
                    - 当前 score = {mf.score:.3f} {'≤' if mf.score <= -0.3 else '>'} -0.3 ✓
                    - 信号一致性：{'一致' if mf.is_consistent else '不一致'}
                    """
                else:
                    action_text = f"""
                    **观望条件：** -0.3 < score < 0.3 或 信号不一致
                    - 当前 score = {mf.score:.3f} (在观望区间)
                    - 信号一致性：{'一致' if mf.is_consistent else '不一致'}
                    """
                st.markdown(action_text)
                
                st.markdown("### 详细原因")
                
                reason_parts = []
                
                reason_parts.append(f"**技术面 ({tech_direction})**：")
                reason_parts.append(f"  - 趋势方向: {result['technical'].get('trend', {}).get('trend', 'N/A')}")
                reason_parts.append(f"  - 买入信号: {len(buy_signals)} 个")
                for sig in buy_signals:
                    reason_parts.append(f"    + {sig['reason']} (强度:{sig['strength']})")
                reason_parts.append(f"  - 卖出信号: {len(sell_signals)} 个")
                for sig in sell_signals:
                    reason_parts.append(f"    + {sig['reason']} (强度:{sig['strength']})")
                
                reason_parts.append(f"\n**基本面 ({fund_direction})**：")
                fund = result["fundamental"]
                reason_parts.append(f"  - 综合评级: {fund.overall}")
                reason_parts.append(f"  - PE: {fund.details.get('pe', 'N/A')}, PB: {fund.details.get('pb', 'N/A')}")
                reason_parts.append(f"  - ROE: {fund.details.get('roe', 0):.1f}%")
                
                reason_parts.append(f"\n**情绪面**：")
                reason_parts.append(f"  - 情绪评分: {result['sentiment'].get('score', 0):.2f}")
                reason_parts.append(f"  - 情绪标签: {result['sentiment'].get('label', '中性')}")
                
                st.markdown("\n".join(reason_parts))
            
            st.divider()
            
            tab1, tab2, tab3, tab4 = st.tabs(["📊 技术分析", "📋 基本面", "💬 情绪面", "📈 图表"])
            
            with tab1:
                st.subheader("技术面分析")
                
                tech = result["technical"]
                
                col_a, col_b = st.columns(2)
                
                with col_a:
                    st.write("**趋势**")
                    trend = tech.get("trend", {})
                    st.write(f"- 方向: {trend.get('trend', 'N/A')}")
                    st.write(f"- 评分: {trend.get('trend_score', 0)}")
                    st.write(f"- 5日收益: {trend.get('avg_return_5d', 0):.2f}%")
                
                with col_b:
                    st.write("**动量指标**")
                    momentum = tech.get("momentum", {})
                    if "rsi" in momentum:
                        rsi = momentum["rsi"]
                        st.write(f"- RSI(14): {rsi['value']:.1f} ({rsi['signal']})")
                    if "macd" in momentum:
                        macd = momentum["macd"]
                        st.write(f"- MACD: {macd['signal']}")
                    if "kdj" in momentum:
                        kdj = momentum["kdj"]
                        st.write(f"- KDJ: {kdj['signal']}")
                
                signals = tech.get("signals", [])
                if signals:
                    st.write("**交易信号**")
                    for sig in signals:
                        emoji = "🟢" if sig["type"] == "买入" else "🔴"
                        st.write(f"{emoji} {sig['type']}: {sig['reason']} (强度:{sig['strength']})")
            
            with tab2:
                st.subheader("基本面分析")
                
                fund = result["fundamental"]
                details = fund.details
                
                col_c, col_d = st.columns(2)
                
                with col_c:
                    st.write("**估值指标**")
                    st.write(f"- 市盈率(PE): {details.get('pe', 'N/A')}")
                    st.write(f"- 市净率(PB): {details.get('pb', 'N/A')}")
                    st.write(f"- 行业: {details.get('industry', 'N/A')}")
                
                with col_d:
                    st.write("**盈利指标**")
                    st.write(f"- ROE: {details.get('roe', 0):.1f}%")
                    st.write(f"- 营收增长: {details.get('revenue_growth', 0):.1f}%")
                    st.write(f"- 利润增长: {details.get('profit_growth', 0):.1f}%")
                
                st.write("---")
                st.write(f"**综合评级**: {fund.overall}")
            
            with tab3:
                st.subheader("情绪面分析")
                
                sent = result["sentiment"]
                
                st.write(f"**情绪评分**: {sent.get('score', 0):.3f}")
                st.write(f"**情绪标签**: {sent.get('label', '中性')}")
                
                st.info("情绪数据来源：模拟数据（实际需要接入东方财富/雪球）")
            
            with tab4:
                st.subheader("价格走势图")
                
                df = result["indicators"]
                close_col = "收盘" if "收盘" in df.columns else "close"
                date_col = "日期" if "日期" in df.columns else "date"
                
                df_display = df.tail(60).copy()
                
                fig = go.Figure()
                
                fig.add_trace(go.Scatter(
                    x=df_display[date_col],
                    y=df_display[close_col],
                    mode='lines',
                    name='收盘价',
                    line=dict(color='cyan', width=2)
                ))
                
                if "sma5" in df_display.columns:
                    fig.add_trace(go.Scatter(
                        x=df_display[date_col],
                        y=df_display["sma5"],
                        mode='lines',
                        name='5日均线',
                        line=dict(color='yellow', width=1)
                    ))
                
                if "sma20" in df_display.columns:
                    fig.add_trace(go.Scatter(
                        x=df_display[date_col],
                        y=df_display["sma20"],
                        mode='lines',
                        name='20日均线',
                        line=dict(color='magenta', width=1)
                    ))
                
                fig.update_layout(
                    title=f"{stock_code} 价格走势",
                    xaxis_title="日期",
                    yaxis_title="价格",
                    template="plotly_dark",
                    height=400
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                st.subheader("成交量")
                
                vol_col = "成交量" if "成交量" in df.columns else "volume"
                
                fig_vol = px.bar(
                    df_display,
                    x=date_col,
                    y=vol_col,
                    color=df_display[close_col].pct_change().apply(lambda x: 'green' if x >= 0 else 'red'),
                    color_discrete_map={'green': '#00FF00', 'red': '#FF0000'}
                )
                
                fig_vol.update_layout(
                    title="成交量",
                    xaxis_title="日期",
                    yaxis_title="成交量",
                    template="plotly_dark",
                    height=300
                )
                
                st.plotly_chart(fig_vol, use_container_width=True)
            
            if run_backtest and analyze_button:
                st.divider()
                st.subheader("时间锁定回测")
                
                with st.spinner("正在运行回测..."):
                    provider = MockDataProvider()
                    backtest = TimeLockedBacktest()
                    
                    bt_result = backtest.run_continuous(
                        stock_code=stock_code,
                        start_date=start_date.strftime("%Y-%m-%d"),
                        end_date=end_date.strftime("%Y-%m-%d"),
                        data_provider=provider.provide
                    )
                
                col_e, col_f, col_g = st.columns(3)
                
                with col_e:
                    st.metric("总测试次数", bt_result.total_tests)
                    st.metric("命中次数", bt_result.hits)
                
                with col_f:
                    st.metric("命中率", f"{bt_result.hit_rate:.1%}")
                    st.metric("最长连续命中", bt_result.max_consecutive_hits)
                
                with col_g:
                    st.metric("连续5轮命中率", f"{bt_result.consecutive_5_rate:.1%}")
                    st.metric("连续10轮命中率", f"{bt_result.consecutive_10_rate:.1%}")
                
                if bt_result.hit_rate >= 0.6:
                    st.success(f"策略表现可接受！命中率 {bt_result.hit_rate:.1%}")
                else:
                    st.warning(f"策略表现需要优化。当前命中率 {bt_result.hit_rate:.1%}")
    
    st.divider()
    st.markdown("""
    **使用说明**：
    1. 输入股票代码
    2. 点击"开始分析"
    3. 查看技术面、基本面、情绪面三维度分析
    4. 启用回测验证策略有效性
    
    **免责声明**：本工具仅供参考，不构成投资建议！
    """)


if __name__ == "__main__":
    main()
