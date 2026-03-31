"""
数据清洗模块
"""

import pandas as pd
import numpy as np
from typing import List, Optional


class DataCleaner:
    """数据清洗工具"""

    @staticmethod
    def remove_duplicates(df: pd.DataFrame, subset: Optional[List[str]] = None) -> pd.DataFrame:
        """
        删除重复行
        """
        before = len(df)
        df = df.drop_duplicates(subset=subset, keep="first")
        after = len(df)
        if before > after:
            print(f"[Cleaner] 删除 {before - after} 条重复记录")
        return df

    @staticmethod
    def handle_missing_values(
        df: pd.DataFrame,
        method: str = "ffill",
        columns: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        处理缺失值
        
        Args:
            method: "ffill"(前向填充), "bfill"(后向填充), "drop", "zero"
        """
        if columns:
            df_subset = df[columns]
        else:
            df_subset = df
        
        before = df_subset.isnull().sum().sum()
        
        if method == "ffill":
            df = df.fillna(method="ffill")
        elif method == "bfill":
            df = df.fillna(method="bfill")
        elif method == "zero":
            df = df.fillna(0)
        elif method == "drop":
            df = df.dropna()
        
        after = df.isnull().sum().sum()
        if before > after:
            print(f"[Cleaner] 填充 {before - after} 个缺失值 (method={method})")
        
        return df

    @staticmethod
    def standardize_column_names(df: pd.DataFrame) -> pd.DataFrame:
        """
        标准化列名
        """
        df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
        return df

    @staticmethod
    def remove_outliers(
        df: pd.DataFrame,
        column: str,
        n_std: float = 3.0
    ) -> pd.DataFrame:
        """
        移除异常值（基于标准差）
        """
        if column not in df.columns:
            return df
        
        mean = df[column].mean()
        std = df[column].std()
        
        lower = mean - n_std * std
        upper = mean + n_std * std
        
        before = len(df)
        df = df[(df[column] >= lower) & (df[column] <= upper)]
        after = len(df)
        
        if before > after:
            print(f"[Cleaner] 移除 {before - after} 个异常值 ({column})")
        
        return df

    @staticmethod
    def convert_date_format(
        df: pd.DataFrame,
        date_column: str,
        input_format: str = "%Y-%m-%d",
        output_format: str = "%Y%m%d"
    ) -> pd.DataFrame:
        """
        转换日期格式
        """
        if date_column in df.columns:
            df[date_column] = pd.to_datetime(df[date_column], format=input_format)
            df[date_column] = df[date_column].dt.strftime(output_format)
        return df

    @staticmethod
    def filter_by_date_range(
        df: pd.DataFrame,
        date_column: str,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """
        按日期范围筛选
        """
        if date_column not in df.columns:
            return df
        
        df = df[(df[date_column] >= start_date) & (df[date_column] <= end_date)]
        print(f"[Cleaner] 日期筛选: {start_date} ~ {end_date}, 剩余 {len(df)} 条记录")
        return df

    @staticmethod
    def clean_kline_data(df: pd.DataFrame) -> pd.DataFrame:
        """
        清洗K线数据
        """
        df = DataCleaner.standardize_column_names(df)
        
        date_col = "日期" if "日期" in df.columns else "date"
        if date_col in df.columns:
            df = DataCleaner.convert_date_format(df, date_col)
        
        if "代码" in df.columns:
            df["代码"] = df["代码"].astype(str).str.zfill(6)
        
        numeric_cols = ["开盘", "收盘", "最高", "最低", "成交量", "成交额"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        
        df = DataCleaner.handle_missing_values(df, method="ffill")
        
        return df

    @staticmethod
    def deduplicate_news(news_list: List[dict], text_key: str = "title") -> List[dict]:
        """
        去重新闻列表（基于标题）
        """
        seen = set()
        unique = []
        
        for item in news_list:
            text = item.get(text_key, "")
            if text and text not in seen:
                seen.add(text)
                unique.append(item)
        
        if len(news_list) > len(unique):
            print(f"[Cleaner] 新闻去重: {len(news_list)} -> {len(unique)}")
        
        return unique
