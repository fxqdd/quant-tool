"""
回测引擎
基于历史数据进行策略回测
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Callable
from enum import Enum


class Position(Enum):
    """持仓状态"""
    EMPTY = 0
    LONG = 1


class BacktestEngine:
    """
    简单回测引擎
    支持：买入/卖出信号、止损/止盈、风控统计
    """

    def __init__(
        self,
        initial_capital: float = 1000000,
        commission: float = 0.0003,
        slippage: float = 0.0001,
        stop_loss: float = 0.05,
        take_profit: float = 0.10
    ):
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        
        self.reset()

    def reset(self):
        """重置回测状态"""
        self.cash = self.initial_capital
        self.position = Position.EMPTY
        self.shares = 0
        self.entry_price = 0
        
        self.trades = []
        self.equity_curve = []
        
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        
        self.max_drawdown = 0
        self.peak_equity = self.initial_capital

    def _get_price_with_slippage(self, price: float, side: str = "buy") -> float:
        """计算滑点后的价格"""
        if side == "buy":
            return price * (1 + self.slippage)
        else:
            return price * (1 - self.slippage)

    def _calculate_commission(self, amount: float) -> float:
        """计算手续费"""
        return amount * self.commission

    def buy(self, date: str, price: float, shares: int = 0, percent: float = 1.0):
        """
        买入
        
        Args:
            date: 交易日期
            price: 当前价格
            shares: 买入股数（0表示按percent比例买入）
            percent: 买入比例（当shares=0时使用）
        """
        if self.position == Position.LONG:
            return
        
        actual_shares = shares
        if shares == 0:
            available_capital = self.cash * percent
            actual_shares = int(available_capital / (price * (1 + self.slippage)) / 100) * 100
        
        cost = actual_shares * self._get_price_with_slippage(price, "buy")
        commission = self._calculate_commission(cost)
        total_cost = cost + commission
        
        if total_cost > self.cash:
            actual_shares = int(self.cash / (price * (1 + self.slippage) * (1 + self.commission)) / 100) * 100
            cost = actual_shares * self._get_price_with_slippage(price, "buy")
            commission = self._calculate_commission(cost)
            total_cost = cost + commission
        
        if actual_shares < 100:
            return
        
        self.cash -= total_cost
        self.shares = actual_shares
        self.entry_price = price
        self.position = Position.LONG
        
        self.trades.append({
            "date": date,
            "action": "BUY",
            "price": price,
            "shares": actual_shares,
            "amount": cost,
            "commission": commission
        })
        
        self.total_trades += 1

    def sell(self, date: str, price: float, reason: str = ""):
        """卖出"""
        if self.position == Position.EMPTY or self.shares == 0:
            return
        
        sell_price = self._get_price_with_slippage(price, "sell")
        amount = self.shares * sell_price
        commission = self._calculate_commission(amount)
        net_amount = amount - commission
        
        profit_per_share = sell_price - self.entry_price
        profit_pct = profit_per_share / self.entry_price
        
        self.trades.append({
            "date": date,
            "action": "SELL",
            "price": price,
            "shares": self.shares,
            "amount": amount,
            "commission": commission,
            "profit_pct": profit_pct * 100,
            "reason": reason
        })
        
        if profit_pct > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
        
        self.cash += net_amount
        self.position = Position.EMPTY
        self.shares = 0
        self.entry_price = 0

    def update_equity(self, date: str, current_price: float):
        """更新权益曲线"""
        if self.position == Position.LONG:
            equity = self.cash + self.shares * current_price
        else:
            equity = self.cash
        
        if equity > self.peak_equity:
            self.peak_equity = equity
        
        drawdown = (self.peak_equity - equity) / self.peak_equity
        if drawdown > self.max_drawdown:
            self.max_drawdown = drawdown
        
        self.equity_curve.append({
            "date": date,
            "equity": equity,
            "drawdown": drawdown
        })

    def check_stop_loss(self, date: str, price: float) -> bool:
        """检查是否触发止损"""
        if self.position == Position.EMPTY:
            return False
        
        loss_pct = (self.entry_price - price) / self.entry_price
        
        if loss_pct >= self.stop_loss:
            self.sell(date, price, reason=f"止损(-{loss_pct*100:.1f}%)")
            return True
        return False

    def check_take_profit(self, date: str, price: float) -> bool:
        """检查是否触发止盈"""
        if self.position == Position.EMPTY:
            return False
        
        profit_pct = (price - self.entry_price) / self.entry_price
        
        if profit_pct >= self.take_profit:
            self.sell(date, price, reason=f"止盈(+{profit_pct*100:.1f}%)")
            return True
        return False

    def run(
        self,
        df: pd.DataFrame,
        strategy_func: Callable,
        show_progress: bool = True
    ) -> Dict:
        """
        运行回测
        
        Args:
            df: K线数据
            strategy_func: 策略函数，输入df和当前索引，输出"buy"/"sell"/"hold"
        """
        self.reset()
        
        close_col = "收盘" if "收盘" in df.columns else "close"
        date_col = "日期" if "日期" in df.columns else "date"
        
        df = df.copy()
        df = df.reset_index(drop=True)
        
        for i in range(len(df)):
            date = df.iloc[i][date_col]
            price = df.iloc[i][close_col]
            
            self.update_equity(date, price)
            
            if self.position == Position.LONG:
                if self.check_stop_loss(date, price):
                    if show_progress:
                        print(f"[{date}] 触发止损")
                    continue
                if self.check_take_profit(date, price):
                    if show_progress:
                        print(f"[{date}] 触发止盈")
                    continue
            
            signal = strategy_func(df, i)
            
            if signal == "buy" and self.position == Position.EMPTY:
                self.buy(date, price)
                if show_progress:
                    print(f"[{date}] 买入 @ {price:.2f}")
            elif signal == "sell" and self.position == Position.LONG:
                self.sell(date, price, reason="策略信号")
                if show_progress:
                    print(f"[{date}] 卖出 @ {price:.2f}")
        
        if self.position == Position.LONG:
            final_price = df.iloc[-1][close_col]
            self.sell(df.iloc[-1][date_col], final_price, reason="回测结束")
        
        return self.get_results()

    def get_results(self) -> Dict:
        """获取回测结果"""
        final_equity = self.equity_curve[-1]["equity"] if self.equity_curve else self.initial_capital
        total_return = (final_equity - self.initial_capital) / self.initial_capital * 100
        
        win_rate = 0
        if self.total_trades > 0:
            win_rate = self.winning_trades / self.total_trades * 100
        
        avg_win = 0
        avg_loss = 0
        for trade in self.trades:
            if trade["action"] == "SELL" and "profit_pct" in trade:
                if trade["profit_pct"] > 0:
                    avg_win += trade["profit_pct"]
                else:
                    avg_loss += abs(trade["profit_pct"])
        
        if self.winning_trades > 0:
            avg_win /= self.winning_trades
        if self.losing_trades > 0:
            avg_loss /= self.losing_trades
        
        sharpe_ratio = 0
        if len(self.equity_curve) > 1:
            returns = pd.Series([e["equity"] for e in self.equity_curve]).pct_change().dropna()
            if returns.std() != 0:
                sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252)
        
        return {
            "initial_capital": self.initial_capital,
            "final_equity": round(final_equity, 2),
            "total_return": round(total_return, 2),
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": round(win_rate, 2),
            "avg_win": round(avg_win, 2) if avg_win > 0 else 0,
            "avg_loss": round(avg_loss, 2) if avg_loss > 0 else 0,
            "max_drawdown": round(self.max_drawdown * 100, 2),
            "sharpe_ratio": round(sharpe_ratio, 2),
            "trades": self.trades,
            "equity_curve": self.equity_curve
        }

    def print_summary(self, results: Dict):
        """打印回测报告"""
        print("\n" + "=" * 60)
        print("回测报告")
        print("=" * 60)
        print(f"初始资金: {results['initial_capital']:,.2f}")
        print(f"最终权益: {results['final_equity']:,.2f}")
        print(f"总收益率: {results['total_return']:.2f}%")
        print("-" * 40)
        print(f"总交易次数: {results['total_trades']}")
        print(f"盈利次数: {results['winning_trades']}")
        print(f"亏损次数: {results['losing_trades']}")
        print(f"胜率: {results['win_rate']:.2f}%")
        print(f"平均盈利: {results['avg_win']:.2f}%")
        print(f"平均亏损: {results['avg_loss']:.2f}%")
        print("-" * 40)
        print(f"最大回撤: {results['max_drawdown']:.2f}%")
        print(f"夏普比率: {results['sharpe_ratio']:.2f}")
        print("=" * 60)


if __name__ == "__main__":
    import akshare as ak
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from analyzers.technical_analyzer import TechnicalAnalyzer
    
    df = ak.stock_zh_a_hist(symbol="000001", period="daily", start_date="20240101", end_date="20260331")
    
    def simple_strategy(df: pd.DataFrame, i: int) -> str:
        """简单RSI策略"""
        if i < 20:
            return "hold"
        
        close_col = "收盘" if "收盘" in df.columns else "close"
        rsi = TechnicalAnalyzer().calculator.calculate_rsi(df[close_col], 14)
        
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
        initial_capital=1000000,
        stop_loss=0.05,
        take_profit=0.10
    )
    
    results = engine.run(df, simple_strategy)
    engine.print_summary(results)
