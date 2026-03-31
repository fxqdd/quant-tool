"""
基本面分析模块
分析股票的财务数据、估值、成长性等
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class FundamentalScore:
    """基本面评分结果"""
    valuation: float = 0      # -2 ~ +2
    growth: float = 0        # -2 ~ +2
    profitability: float = 0 # -2 ~ +2
    momentum: float = 0      # -2 ~ +2
    overall: str = "一般"     # 优秀/良好/一般/较差
    score: float = 0         # -1 ~ +1
    details: Dict = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}


class FundamentalAnalyzer:
    """基本面分析器"""
    
    INDUSTRY_PE_RANGES = {
        "银行": (4, 8),
        "证券": (10, 20),
        "保险": (8, 15),
        "房地产": (5, 12),
        "医药": (20, 40),
        "消费": (15, 30),
        "科技": (30, 60),
        "能源": (8, 15),
        "工业": (10, 20),
        "默认": (10, 30)
    }
    
    def __init__(self):
        self.industry_pe_ranges = self.INDUSTRY_PE_RANGES
    
    def analyze(self, financial_data: Dict, price_data: Dict = None) -> FundamentalScore:
        """
        综合基本面分析
        
        Args:
            financial_data: 财务数据字典
            price_data: 价格数据字典（用于计算实时PE等）
        """
        result = FundamentalScore()
        
        pe = financial_data.get("pe", 0)
        pb = financial_data.get("pb", 0)
        roe = financial_data.get("roe", 0)
        revenue_growth = financial_data.get("revenue_growth", 0)
        profit_growth = financial_data.get("profit_growth", 0)
        gross_margin = financial_data.get("gross_margin", 0)
        net_margin = financial_data.get("net_margin", 0)
        debt_ratio = financial_data.get("debt_ratio", 0)
        industry = financial_data.get("industry", "默认")
        
        result.valuation = self._calc_valuation_score(pe, pb, industry)
        result.growth = self._calc_growth_score(revenue_growth, profit_growth)
        result.profitability = self._calc_profitability_score(roe, gross_margin, net_margin, debt_ratio)
        
        result.score = (
            result.valuation * 0.3 +
            result.growth * 0.3 +
            result.profitability * 0.4
        )
        
        if result.score >= 0.5:
            result.overall = "优秀"
        elif result.score >= 0.2:
            result.overall = "良好"
        elif result.score >= -0.2:
            result.overall = "一般"
        else:
            result.overall = "较差"
        
        result.details = {
            "pe": pe,
            "pb": pb,
            "roe": roe,
            "revenue_growth": revenue_growth,
            "profit_growth": profit_growth,
            "gross_margin": gross_margin,
            "debt_ratio": debt_ratio,
            "industry": industry
        }
        
        return result
    
    def _calc_valuation_score(self, pe: float, pb: float, industry: str) -> float:
        """计算估值得分"""
        if pe <= 0 or pe > 200:
            pe_score = 0
        else:
            pe_range = self.industry_pe_ranges.get(industry, self.industry_pe_ranges["默认"])
            if pe < pe_range[0]:
                pe_score = 2
            elif pe > pe_range[1]:
                pe_score = -2
            else:
                pe_score = 1 - (pe - pe_range[0]) / (pe_range[1] - pe_range[0]) * 2
        
        if pb <= 0:
            pb_score = 0
        elif pb < 1:
            pb_score = 2
        elif pb > 5:
            pb_score = -2
        else:
            pb_score = 2 - pb
        
        return (pe_score * 0.6 + pb_score * 0.4) / 2
    
    def _calc_growth_score(self, revenue_growth: float, profit_growth: float) -> float:
        """计算成长性得分"""
        growth_score = 0
        
        if revenue_growth > 20:
            growth_score += 1
        elif revenue_growth > 10:
            growth_score += 0.5
        elif revenue_growth < 0:
            growth_score -= 1
        elif revenue_growth < 5:
            growth_score -= 0.5
        
        if profit_growth > 30:
            growth_score += 1
        elif profit_growth > 15:
            growth_score += 0.5
        elif profit_growth < 0:
            growth_score -= 1
        elif profit_growth < 5:
            growth_score -= 0.5
        
        return max(-2, min(2, growth_score))
    
    def _calc_profitability_score(
        self, 
        roe: float, 
        gross_margin: float, 
        net_margin: float,
        debt_ratio: float
    ) -> float:
        """计算盈利能力得分"""
        score = 0
        
        if roe > 15:
            score += 1
        elif roe > 10:
            score += 0.5
        elif roe < 5:
            score -= 1
        elif roe < 0:
            score -= 2
        
        if gross_margin > 40:
            score += 0.5
        elif gross_margin < 10:
            score -= 0.5
        
        if net_margin > 15:
            score += 0.5
        elif net_margin < 0:
            score -= 1
        
        if debt_ratio > 80:
            score -= 1
        elif debt_ratio > 60:
            score -= 0.5
        elif debt_ratio < 40:
            score += 0.5
        
        return max(-2, min(2, score))
    
    def get_direction(self, score: FundamentalScore) -> str:
        """将评分转换为方向描述"""
        if score.overall == "优秀":
            return "良好"
        elif score.overall == "良好":
            return "良好"
        elif score.overall == "一般":
            return "一般"
        else:
            return "较差"


def get_mock_financial_data(stock_code: str) -> Dict:
    """
    获取模拟财务数据（用于测试）
    实际使用时应该调用真实数据源
    """
    mock_data = {
        "000001": {
            "pe": 6.2,
            "pb": 0.7,
            "roe": 12.3,
            "revenue_growth": 8.5,
            "profit_growth": 12.1,
            "gross_margin": 32.5,
            "net_margin": 8.2,
            "debt_ratio": 45.0,
            "industry": "银行"
        },
        "600519": {
            "pe": 35.0,
            "pb": 12.0,
            "roe": 28.5,
            "revenue_growth": 15.2,
            "profit_growth": 18.3,
            "gross_margin": 75.0,
            "net_margin": 45.0,
            "debt_ratio": 25.0,
            "industry": "消费"
        }
    }
    
    return mock_data.get(stock_code, {
        "pe": 15.0,
        "pb": 2.0,
        "roe": 10.0,
        "revenue_growth": 5.0,
        "profit_growth": 5.0,
        "gross_margin": 20.0,
        "net_margin": 10.0,
        "debt_ratio": 50.0,
        "industry": "默认"
    })


if __name__ == "__main__":
    analyzer = FundamentalAnalyzer()
    
    for code in ["000001", "600519"]:
        data = get_mock_financial_data(code)
        result = analyzer.analyze(data)
        
        print(f"\n{'='*50}")
        print(f"股票 {code} 基本面分析")
        print(f"{'='*50}")
        print(f"估值得分: {result.valuation:.2f} ({result.details.get('industry', 'N/A')})")
        print(f"成长得分: {result.growth:.2f}")
        print(f"盈利得分: {result.profitability:.2f}")
        print(f"综合评分: {result.score:.2f}")
        print(f"综合评级: {result.overall}")
