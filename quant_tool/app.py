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

sys.path.insert(0, os.path.dirname(__file__))

from data.collectors.akshare_collector import AkShareCollector
from data.processors.indicator import IndicatorCalculator
from analyzers.technical_analyzer import TechnicalAnalyzer
from analyzers.fundamental_analyzer import FundamentalAnalyzer, get_mock_financial_data
from analyzers.multi_factor_engine import MultiFactorEngine
from analyzers.noise_filter import NoiseFilterPipeline
from backtest.time_locked_backtest import TimeLockedBacktest, MockDataProvider


st.set_page_config(
    page_title="A股量化分析系统",
    page_icon="📈",
    layout="wide"
)


def main():
    st.title("📈 A股量化分析系统 v2.0")
    st.markdown("**技术面 + 基本面 + 情绪面 三维度融合分析**")
    
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
                
                try:
                    kline_df = collector.get_historical_kline(stock_code, use_cache=True)
                except Exception as e:
                    st.error(f"数据获取失败: {e}")
                    kline_df = None
                
                if kline_df is not None and len(kline_df) > 0:
                    indicators = IndicatorCalculator.calculate_all(kline_df)
                    
                    tech_analyzer = TechnicalAnalyzer()
                    tech_result = tech_analyzer.analyze(kline_df)
                    
                    financial_data = get_mock_financial_data(stock_code)
                    fund_analyzer = FundamentalAnalyzer()
                    fund_result = fund_analyzer.analyze(financial_data)
                    
                    sent_result = {"score": 0.2, "label": "轻度看多"}
                    
                    mf_engine = MultiFactorEngine()
                    mf_result = mf_engine.fuse(
                        tech_result,
                        {"direction": fund_result.overall, "score": fund_result.score},
                        sent_result
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
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("推荐操作", result["multi_factor"].action)
            
            with col2:
                confidence = result["multi_factor"].confidence
                st.metric("置信度", f"{confidence:.0%}")
            
            with col3:
                score = result["multi_factor"].score
                st.metric("综合评分", f"{score:.3f}")
            
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
