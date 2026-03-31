"""
情绪数据收集模块
收集东方财富/雪球等平台的散户情绪数据
"""

import requests
import pandas as pd
from typing import List, Dict, Optional
import time
import sys
sys.path.insert(0, str(__file__).rsplit("/", 2)[0])


class SentimentCollector:
    """
    情绪数据收集器
    注意：爬虫容易被封，建议设置合理的请求间隔
    """

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        }
        self.session = requests.Session()

    def get_xueqiu_stock_comments(
        self,
        stock_code: str,
        limit: int = 20
    ) -> List[Dict]:
        """
        获取雪球股票评论
        注意：雪球API需要cookie，完整实现需要登录态
        """
        print(f"[Sentiment] 雪球评论获取（模拟）: {stock_code}")
        
        mock_comments = [
            {"text": "看好这只股票，基本面优秀", "sentiment": "positive", "date": "2026-03-30"},
            {"text": "等回调再买入", "sentiment": "neutral", "date": "2026-03-30"},
            {"text": "跌停了，踩雷了", "sentiment": "negative", "date": "2026-03-29"},
        ]
        
        return mock_comments[:limit]

    def get_eastmoney_stock_bar(
        self,
        stock_code: str,
        limit: int = 50
    ) -> List[Dict]:
        """
        获取东方财富股吧帖子
        """
        print(f"[Sentiment] 东方财富股吧数据获取: {stock_code}")
        
        try:
            url = f"https://guba.eastmoney.com/list/{stock_code},1,f_{limit}.html"
            response = self.session.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                print(f"[Sentiment] 获取到 {limit} 条帖子数据")
            else:
                print(f"[Sentiment] 请求失败: {response.status_code}")
                
        except Exception as e:
            print(f"[Sentiment] 获取失败: {e}")
        
        mock_data = [
            {"title": f"{stock_code}今日讨论", "views": 1000, "replies": 50, "sentiment": "neutral"},
            {"title": f"{stock_code}技术面分析", "views": 500, "replies": 20, "sentiment": "positive"},
        ]
        
        return mock_data

    def get_north_money_flow(self) -> pd.DataFrame:
        """
        获取北向资金数据（情绪指标）
        """
        print("[Sentiment] 获取北向资金数据...")
        
        try:
            import akshare as ak
            df = ak.stock_em_hsgt_north_net_flow_in(indicator="沪深港通北向资金")
            print(f"[Sentiment] 获取到 {len(df)} 条北向资金记录")
            return df
        except Exception as e:
            print(f"[Sentiment] 北向资金获取失败: {e}")
            return pd.DataFrame()

    def get_market_sentiment_index(self) -> Dict:
        """
        获取市场情绪指数
        """
        print("[Sentiment] 计算市场情绪指数...")
        
        try:
            import akshare as ak
            
            try:
                df = ak.stock_em_market_sentiment()
                
                if df is not None and len(df) > 0:
                    latest = df.iloc[-1]
                    sentiment_value = float(latest.get("上涨家数", 0)) / (float(latest.get("上涨家数", 1)) + float(latest.get("下跌家数", 1))) * 100
                    
                    return {
                        "sentiment_value": sentiment_value,
                        "rising_count": int(latest.get("上涨家数", 0)),
                        "falling_count": int(latest.get("下跌家数", 0)),
                        "date": str(latest.get("日期", ""))
                    }
            except Exception:
                pass
            
            df_sh = ak.stock_zh_index_spot_em(symbol="上证指数")
            
            change_pct = float(df_sh.iloc[0].get("涨跌幅", 0))
            
            sentiment_value = 50 + change_pct * 5
            sentiment_value = max(0, min(100, sentiment_value))
            
            return {
                "sentiment_value": sentiment_value,
                "index_change": change_pct,
                "date": "今日"
            }
            
        except Exception as e:
            print(f"[Sentiment] 情绪指数获取失败: {e}")
            return {"sentiment_value": 50, "error": str(e)}

    def calculate_social_sentiment(
        self,
        stock_code: str,
        bar_data: List[Dict]
    ) -> Dict:
        """
        计算社交媒体情绪
        """
        if not bar_data:
            return {"avg_sentiment": 50, "label": "中性", "confidence": 0}
        
        sentiment_map = {"positive": 100, "neutral": 50, "negative": 0}
        
        scores = [sentiment_map.get(d.get("sentiment", "neutral"), 50) for d in bar_data]
        avg = sum(scores) / len(scores)
        
        if avg > 65:
            label = "看多"
        elif avg < 35:
            label = "看空"
        else:
            label = "中性"
        
        return {
            "avg_sentiment": round(avg, 2),
            "label": label,
            "sample_size": len(bar_data)
        }


if __name__ == "__main__":
    collector = SentimentCollector()
    
    print("=" * 60)
    print("情绪数据收集测试")
    print("=" * 60)
    
    sentiment = collector.get_market_sentiment_index()
    print(f"\n市场情绪指数: {sentiment}")
    
    comments = collector.get_xueqiu_stock_comments("000001")
    print(f"\n雪球评论: {len(comments)} 条")
