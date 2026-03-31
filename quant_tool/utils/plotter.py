"""
终端绘图模块
在命令行中绘制股票价格曲线
"""

import plotext as plt
import pandas as pd
from typing import Optional


class TerminalPlotter:
    """终端绘图器"""

    def __init__(self, width: int = 120, height: int = 30):
        self.width = width
        self.height = height

    def plot_stock_price(
        self,
        df: pd.DataFrame,
        stock_code: str,
        days: int = 30
    ) -> None:
        """
        绘制股票价格曲线

        Args:
            df: K线数据
            stock_code: 股票代码
            days: 显示最近N天数据
        """
        close_col = "收盘" if "收盘" in df.columns else "close"
        date_col = "日期" if "日期" in df.columns else "date"

        df = df.tail(days).copy()

        dates = df[date_col].tolist()
        prices = df[close_col].tolist()

        plt.clf()
        plt.plot(prices, label=stock_code, color="cyan")
        plt.title(f"{stock_code} 近{days}日收盘价")
        plt.xlabel("交易日")
        plt.ylabel("价格")
        plt.ticks(dtype="string", ticks=5)
        plt.show()

    def plot_stock_with_ma(
        self,
        df: pd.DataFrame,
        stock_code: str,
        days: int = 30
    ) -> None:
        """
        绘制带均线的股票价格曲线
        """
        close_col = "收盘" if "收盘" in df.columns else "close"
        date_col = "日期" if "日期" in df.columns else "date"

        df = df.tail(days).copy()

        prices = df[close_col].tolist()
        dates = df[date_col].tolist()

        sma5 = df["sma5"].tail(days).tolist() if "sma5" in df.columns else prices
        sma20 = df["sma20"].tail(days).tolist() if "sma20" in df.columns else prices

        plt.clf()

        plt.plot(prices, label="收盘价", color="cyan")
        plt.plot(sma5, label="5日均线", color="yellow")
        plt.plot(sma20, label="20日均线", color="magenta")

        plt.title(f"{stock_code} 价格与均线")
        plt.xlabel("交易日")
        plt.ylabel("价格")
        try:
            plt.legend()
        except:
            pass
        plt.ticks(dtype="string", ticks=5)
        plt.show()

    def plot_volume(
        self,
        df: pd.DataFrame,
        stock_code: str,
        days: int = 30
    ) -> None:
        """
        绘制成交量柱状图
        """
        close_col = "收盘" if "收盘" in df.columns else "close"
        date_col = "日期" if "日期" in df.columns else "date"
        vol_col = "成交量" if "成交量" in df.columns else "volume"

        df = df.tail(days).copy()

        volumes = df[vol_col].tolist()
        dates = df[date_col].tolist()
        prices = df[close_col].tolist()

        colors = ["green" if prices[i] >= prices[i-1] else "red" for i in range(1, len(prices))]
        colors.insert(0, "green" if prices[0] >= prices[0] else "red")

        plt.clf()
        plt.bar(dates, volumes, color=colors, label="成交量")
        plt.title(f"{stock_code} 成交量")
        plt.xlabel("交易日")
        plt.ylabel("成交量")
        plt.ticks(dtype="string", ticks=5)
        plt.show()

    def plot_candlestick(
        self,
        df: pd.DataFrame,
        stock_code: str,
        days: int = 20
    ) -> None:
        """
        绘制蜡烛图（简化版，用折线表示涨跌）
        """
        close_col = "收盘" if "收盘" in df.columns else "close"
        date_col = "日期" if "日期" in df.columns else "date"

        df = df.tail(days).copy()

        prices = df[close_col].tolist()
        dates = df[date_col].tolist()

        plt.clf()

        colors = []
        for i in range(len(prices)):
            if i == 0:
                colors.append("cyan")
            elif prices[i] >= prices[i-1]:
                colors.append("green")
            else:
                colors.append("red")

        plt.scatter(range(len(prices)), prices, color=colors, marker=".")
        plt.plot(prices, color="white", style="o")

        plt.title(f"{stock_code} 蜡烛图(简化版)")
        plt.xlabel("交易日")
        plt.ylabel("价格")
        plt.ticks(dtype="string", ticks=5)
        plt.show()

    def plot_all(
        self,
        df: pd.DataFrame,
        stock_code: str,
        days: int = 30
    ) -> None:
        """
        绘制所有图表
        """
        close_col = "收盘" if "收盘" in df.columns else "close"

        if close_col not in df.columns:
            print("[绘图] 数据中没有收盘价列")
            return

        print("\n" + "=" * 60)
        print("📈 价格走势图")
        print("=" * 60)
        self.plot_stock_with_ma(df, stock_code, days)

        print("\n" + "=" * 60)
        print("📊 成交量图")
        print("=" * 60)
        self.plot_volume(df, stock_code, days)


if __name__ == "__main__":
    import akshare as ak
    from data.processors.indicator import IndicatorCalculator

    df = ak.stock_zh_a_hist(symbol="000001", period="daily", start_date="20260201", end_date="20260331")
    df.columns = df.columns.str.strip()

    df = IndicatorCalculator.calculate_all(df)

    plotter = TerminalPlotter()
    plotter.plot_all(df, "000001", days=20)
