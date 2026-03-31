"""
AkShare 数据收集器
收集A股行情、财务、资金流等数据
"""

import akshare as ak
import pandas as pd
from typing import Optional, List, Dict
from datetime import datetime
import sys
sys.path.insert(0, str(__file__).rsplit("/", 2)[0])
from config import CACHE_DIR


class AkShareCollector:
    """AkShare数据收集器"""

    def __init__(self, cache_dir=CACHE_DIR):
        self.cache_dir = cache_dir

    def get_realtime_quotes(self, stock_codes: Optional[List[str]] = None) -> pd.DataFrame:
        """
        获取实时行情（全市场或指定股票）
        """
        print("[Collector] 获取实时行情数据...")
        df = ak.stock_zh_a_spot_em()
        
        if stock_codes:
            df = df[df["代码"].isin(stock_codes)]
        
        print(f"[Collector] 获取到 {len(df)} 条记录")
        return df

    def get_historical_kline(
        self,
        stock_code: str,
        start_date: str = "20240101",
        end_date: str = "20260331",
        period: str = "daily",
        adjust: str = "qfq"
    ) -> pd.DataFrame:
        """
        获取历史K线数据
        
        Args:
            stock_code: 股票代码，如 "000001"
            start_date: 开始日期 "YYYYMMDD"
            end_date: 结束日期 "YYYYMMDD"
            period: K线周期 "daily"/"weekly"/"monthly"
            adjust: 复权类型 "qfq"/"hfq"/""
        """
        print(f"[Collector] 获取K线数据: {stock_code} ({start_date} ~ {end_date})")
        df = ak.stock_zh_a_hist(
            symbol=stock_code,
            period=period,
            start_date=start_date,
            end_date=end_date,
            adjust=adjust
        )
        print(f"[Collector] 获取到 {len(df)} 条K线记录")
        return df

    def get_market_index(
        self,
        index_code: str = "000001",
        start_date: str = "20240101",
        end_date: str = "20260331"
    ) -> pd.DataFrame:
        """
        获取指数K线
        """
        print(f"[Collector] 获取指数数据: {index_code}")
        df = ak.stock_zh_index_daily(symbol=f"sh{index_code}")
        df = df[(df["date"] >= start_date) & (df["date"] <= end_date)]
        print(f"[Collector] 获取到 {len(df)} 条指数记录")
        return df

    def get_individual_fund_flow(
        self,
        stock_code: str,
        market: str = "A股"
    ) -> Dict[str, pd.DataFrame]:
        """
        获取个股资金流向
        """
        print(f"[Collector] 获取资金流向: {stock_code}")
        df = ak.stock_individual_fund_flow(stock_code=stock_code, market=market)
        
        result = {
            "today": df[df["日期"].str.contains(datetime.now().strftime("%Y-%m-%d")[:10])],
            "recent5": df.tail(5),
            "recent20": df.tail(20)
        }
        print(f"[Collector] 资金流向数据获取成功")
        return result

    def get_stock_financial_analysis(
        self,
        stock_code: str,
        start_date: str = "20230101",
        end_date: str = "20260331"
    ) -> Dict[str, pd.DataFrame]:
        """
        获取个股财务数据
        """
        print(f"[Collector] 获取财务数据: {stock_code}")
        
        try:
            df_pl = ak.stock_financial_analysis_indicator(
                symbol=stock_code,
                start_date=start_date,
                end_date=end_date
            )
        except Exception as e:
            print(f"[Collector] 财务数据获取失败: {e}")
            df_pl = pd.DataFrame()
        
        return {"financial": df_pl}

    def get_stocks_by_plate(
        self,
        plate_code: str = "BK0001"
    ) -> pd.DataFrame:
        """
        获取板块成分股
        """
        print(f"[Collector] 获取板块成分股: {plate_code}")
        try:
            df = ak.stock_board_constituent(symbol=plate_code)
            print(f"[Collector] 获取到 {len(df)} 只成分股")
            return df
        except Exception as e:
            print(f"[Collector] 板块数据获取失败: {e}")
            return pd.DataFrame()

    def get_money_flow(
        self,
        start_date: str = "20240101",
        end_date: str = "20260331"
    ) -> pd.DataFrame:
        """
        获取市场资金流向（南向/北向）
        """
        print("[Collector] 获取北向资金数据...")
        try:
            df_north = ak.stock_em_hsgt_north_net_flow_in(indicator="沪深港通北向资金")
            df_north = df_north[(df_north["日期"] >= start_date) & (df_north["日期"] <= end_date)]
            print(f"[Collector] 获取到 {len(df_north)} 条北向资金记录")
            return df_north
        except Exception as e:
            print(f"[Collector] 北向资金获取失败: {e}")
            return pd.DataFrame()

    def get_tick_data(
        self,
        stock_code: str,
        trade_date: str
    ) -> pd.DataFrame:
        """
        获取分笔数据（当日逐笔）
        """
        print(f"[Collector] 获取分笔数据: {stock_code} @ {trade_date}")
        try:
            date_fmt = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:8]}"
            df = ak.stock_zh_a_tick(symbol=stock_code, trade_date=date_fmt)
            print(f"[Collector] 获取到 {len(df)} 条分笔记录")
            return df
        except Exception as e:
            print(f"[Collector] 分笔数据获取失败: {e}")
            return pd.DataFrame()

    def batch_collect(
        self,
        stock_codes: List[str],
        start_date: str = "20240101",
        end_date: str = "20260331"
    ) -> Dict[str, pd.DataFrame]:
        """
        批量收集多只股票数据
        """
        results = {}
        for code in stock_codes:
            try:
                kline = self.get_historical_kline(code, start_date, end_date)
                fund_flow = self.get_individual_fund_flow(code)
                results[code] = {
                    "kline": kline,
                    "fund_flow": fund_flow
                }
                print(f"[Collector] {code} 数据收集完成")
            except Exception as e:
                print(f"[Collector] {code} 数据收集失败: {e}")
                results[code] = {"kline": pd.DataFrame(), "fund_flow": {}}
        return results


if __name__ == "__main__":
    collector = AkShareCollector()
    
    test_code = "000001"
    
    print("=" * 60)
    print(f"测试收集: {test_code}")
    print("=" * 60)
    
    kline = collector.get_historical_kline(test_code)
    print("\nK线数据预览:")
    print(kline.tail())
    
    fund_flow = collector.get_individual_fund_flow(test_code)
    print("\n近期资金流向:")
    print(fund_flow["recent5"].tail() if not fund_flow["recent5"].empty else "无数据")
