#!/usr/bin/env python3
"""
A股自动化预测与报告系统
=======================
功能：
1. 每日自动收集A股数据
2. 基于技术分析预测次日涨跌
3. 与实际数据对比验证
4. 每5日生成统计报告

使用方法：
    python auto_predictor.py                    # 运行预测
    python auto_predictor.py --report          # 生成5日报告
    python auto_predictor.py --backtest 30     # 回测最近30天
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from analyzers.predictor import StockPredictor
from data.processors.indicator import IndicatorCalculator


DATA_DIR = Path(__file__).parent / "data" / "prediction_records"
REPORT_DIR = Path(__file__).parent / "reports"


class PredictionRecord:
    """预测记录"""
    
    def __init__(self, data_dir: Path = DATA_DIR):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.record_file = data_dir / "predictions.jsonl"
    
    def add(self, record: dict):
        """添加预测记录"""
        with open(self.record_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    def get_all(self) -> list:
        """获取所有记录"""
        if not self.record_file.exists():
            return []
        
        records = []
        with open(self.record_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records
    
    def get_recent(self, days: int = 5) -> list:
        """获取最近N天的预测记录"""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        return [r for r in self.get_all() if r.get("date", "") >= cutoff]
    
    def verify_prediction(self, record: dict, actual_change: float):
        """验证预测是否正确"""
        predicted_dir = record.get("predicted_direction", "震荡")
        
        if actual_change > 0.5:
            actual_dir = "上涨"
        elif actual_change < -0.5:
            actual_dir = "下跌"
        else:
            actual_dir = "震荡"
        
        correct = predicted_dir == actual_dir
        close_win = actual_change > 0 if record.get("action") == "买入" else False
        
        return {
            "correct": correct,
            "actual_direction": actual_dir,
            "actual_change": actual_change,
            "close_win": close_win
        }


class AutoPredictor:
    """自动化预测系统"""
    
    def __init__(self, stock_codes: list = None):
        self.predictor = StockPredictor()
        self.record = PredictionRecord()
        self.stock_codes = stock_codes or ["000001", "600519", "000858", "600036", "601318"]
    
    def predict_today(self, stock_code: str) -> dict:
        """
        预测今日（为明日做准备）
        
        流程：
        1. 获取历史数据（到昨天为止）
        2. 基于昨天数据预测今日涨跌
        3. 记录预测结果
        """
        try:
            import akshare as ak
            
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=120)).strftime("%Y%m%d")
            
            df = ak.stock_zh_a_hist(
                symbol=stock_code,
                period="daily",
                start_date=start_date,
                end_date=yesterday,
                adjust="qfq"
            )
            
            if df is None or len(df) < 20:
                return {"success": False, "error": "数据不足"}
            
            result = self.predictor.predict(df)
            
            record = {
                "stock_code": stock_code,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "predict_date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
                "close_price": df["收盘"].iloc[-1],
                "action": result.action,
                "direction": result.direction,
                "confidence": result.confidence,
                "score": result.score,
                "predicted_change": result.predicted_change,
                "risk_level": result.risk_level,
                "stop_loss": result.stop_loss,
                "take_profit": result.take_profit,
                "reasons": result.reasons[:5],
                "trend_score": result.trend_score,
                "momentum_score": result.momentum_score,
                "volume_score": result.volume_score,
                "breakout_score": result.breakout_score,
                "verified": False
            }
            
            self.record.add(record)
            
            return {"success": True, "record": record}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def verify_yesterday(self, stock_code: str) -> dict:
        """
        验证昨日预测
        对比昨日预测与今日实际数据
        """
        try:
            import akshare as ak
            
            today = datetime.now().strftime("%Y%m%d")
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=125)).strftime("%Y%m%d")
            
            df = ak.stock_zh_a_hist(
                symbol=stock_code,
                period="daily",
                start_date=start_date,
                end_date=today,
                adjust="qfq"
            )
            
            if df is None or len(df) < 2:
                return {"success": False, "error": "数据不足"}
            
            close_yesterday = df["收盘"].iloc[-2]
            close_today = df["收盘"].iloc[-1]
            actual_change = (close_today / close_yesterday - 1) * 100
            
            recent = self.record.get_recent(days=2)
            pred_record = None
            for r in recent:
                if r.get("stock_code") == stock_code and r.get("date") == yesterday:
                    pred_record = r
                    break
            
            if not pred_record:
                return {
                    "success": True,
                    "verified": False,
                    "actual_change": actual_change,
                    "message": "没有找到昨日预测记录"
                }
            
            verification = self.record.verify_prediction(pred_record, actual_change)
            
            for r in recent:
                if r.get("stock_code") == stock_code and r.get("date") == yesterday:
                    r["verified"] = True
                    r["actual_change"] = actual_change
                    r["actual_direction"] = verification["actual_direction"]
                    r["correct"] = verification["correct"]
            
            return {
                "success": True,
                "verified": True,
                "actual_change": actual_change,
                "pred_record": pred_record,
                "verification": verification
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def run_daily(self):
        """运行每日预测"""
        print("=" * 60)
        print(f"A股自动化预测 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("=" * 60)
        
        results = []
        for code in self.stock_codes:
            print(f"\n正在预测 {code}...")
            
            verify_result = self.verify_yesterday(code)
            if verify_result.get("success") and verify_result.get("verified"):
                v = verify_result["verification"]
                actual = verify_result["actual_change"]
                pred = verify_result["pred_record"]
                emoji = "✓" if v["correct"] else "✗"
                print(f"  {emoji} 昨日预测: {pred['direction']} | 实际: {v['actual_direction']} ({actual:+.2f}%)")
            
            pred_result = self.predict_today(code)
            if pred_result.get("success"):
                r = pred_result["record"]
                print(f"  → 明日预测: {r['direction']} ({r['predicted_change']:+.2f}%)")
                print(f"    操作: {r['action']} | 置信度: {r['confidence']:.0%}")
                print(f"    风险: {r['risk_level']} | 止损: {r['stop_loss']:.2f} | 止盈: {r['take_profit']:.2f}")
                results.append(r)
            else:
                print(f"  ✗ 预测失败: {pred_result.get('error', '未知错误')}")
        
        return results


class PredictionReport:
    """预测报告生成器"""
    
    def __init__(self, data_dir: Path = DATA_DIR, report_dir: Path = REPORT_DIR):
        self.record = PredictionRecord(data_dir)
        self.report_dir = report_dir
        self.report_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_5day_report(self) -> dict:
        """
        生成5日预测报告
        
        统计：
        1. 预测准确率（方向判断）
        2. 买入胜率（买入信号次日上涨比例）
        3. 盈亏统计（假设每次买入1000元）
        """
        records = self.record.get_recent(days=7)
        
        verified_records = [r for r in records if r.get("verified", False)]
        
        if len(verified_records) < 3:
            return {
                "success": False,
                "message": f"验证数据不足（仅{len(verified_records)}条），需要更多数据"
            }
        
        total_predictions = len(verified_records)
        correct_predictions = sum(1 for r in verified_records if r.get("correct", False))
        accuracy = correct_predictions / total_predictions * 100 if total_predictions > 0 else 0
        
        buy_signals = [r for r in verified_records if r.get("action") == "买入"]
        buy_wins = sum(1 for r in buy_signals if r.get("actual_change", 0) > 0)
        buy_win_rate = buy_wins / len(buy_signals) * 100 if buy_signals else 0
        
        INVESTMENT_PER_TRADE = 1000
        trading_count = len(buy_signals)
        
        total_investment = INVESTMENT_PER_TRADE * trading_count
        
        profits = []
        for r in buy_signals:
            change = r.get("actual_change", 0)
            profit = INVESTMENT_PER_TRADE * (change / 100)
            profits.append(profit)
        
        total_profit = sum(profits)
        avg_profit = total_profit / trading_count if trading_count > 0 else 0
        
        profit_rate = (total_profit / total_investment * 100) if total_investment > 0 else 0
        
        winning_trades = [p for p in profits if p > 0]
        losing_trades = [p for p in profits if p <= 0]
        
        avg_win = sum(winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(losing_trades) / len(losing_trades) if losing_trades else 0
        
        win_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        
        report = {
            "success": True,
            "report_date": datetime.now().strftime("%Y-%m-%d"),
            "period": f"最近{len(verified_records)}个交易日",
            "statistics": {
                "total_predictions": total_predictions,
                "correct_predictions": correct_predictions,
                "accuracy": round(accuracy, 2),
                "buy_signals": len(buy_signals),
                "buy_wins": buy_wins,
                "buy_win_rate": round(buy_win_rate, 2)
            },
            "profit_analysis": {
                "investment_per_trade": INVESTMENT_PER_TRADE,
                "total_trades": trading_count,
                "total_investment": round(total_investment, 2),
                "total_profit": round(total_profit, 2),
                "avg_profit": round(avg_profit, 2),
                "profit_rate": round(profit_rate, 2),
                "winning_trades": len(winning_trades),
                "losing_trades": len(losing_trades),
                "avg_win": round(avg_win, 2),
                "avg_loss": round(avg_loss, 2),
                "win_loss_ratio": round(win_loss_ratio, 2)
            },
            "records": verified_records[-10:]
            if verified_records else []
        }
        
        return report
    
    def print_report(self, report: dict):
        """打印报告"""
        if not report.get("success"):
            print(f"\n报告生成失败: {report.get('message', '未知错误')}")
            return
        
        stats = report["statistics"]
        profit = report["profit_analysis"]
        
        print("\n" + "=" * 70)
        print(f"               5日预测报告 - {report['report_date']}")
        print("=" * 70)
        
        print("\n【预测准确率统计】")
        print(f"  总预测次数: {stats['total_predictions']}")
        print(f"  正确次数: {stats['correct_predictions']}")
        print(f"  准确率: {stats['accuracy']:.1f}%")
        
        print("\n【买入信号统计】")
        print(f"  买入信号数: {stats['buy_signals']}")
        print(f"  盈利次数: {stats['buy_wins']}")
        print(f"  买入胜率: {stats['buy_win_rate']:.1f}%")
        
        print("\n【盈亏分析】（假设每次买入 1000 元）")
        print(f"  总交易次数: {profit['total_trades']}")
        print(f"  总投入: {profit['total_investment']:.2f} 元")
        print(f"  总盈亏: {profit['total_profit']:+.2f} 元")
        print(f"  收益率: {profit['profit_rate']:+.2f}%")
        
        print(f"\n  盈利交易: {profit['winning_trades']} 笔 (平均 +{profit['avg_win']:.2f} 元)")
        print(f"  亏损交易: {profit['losing_trades']} 笔 (平均 {profit['avg_loss']:.2f} 元)")
        print(f"  盈亏比: {profit['win_loss_ratio']:.2f}")
        
        print("\n【近期交易记录】")
        print("-" * 70)
        print(f"{'日期':<12} {'代码':<8} {'预测':<6} {'实际涨跌':<10} {'结果':<6} {'盈亏(元)':<10}")
        print("-" * 70)
        
        for r in report.get("records", [])[-5:]:
            date = r.get("date", "")[:10]
            code = r.get("stock_code", "")
            pred = r.get("direction", "")
            actual = r.get("actual_change", 0)
            correct = "✓" if r.get("correct") else "✗"
            
            investment = 1000
            pnl = investment * (actual / 100)
            
            print(f"{date:<12} {code:<8} {pred:<6} {actual:+.2f}%    {correct:<6} {pnl:+.2f}")
        
        print("-" * 70)
        
        if profit['profit_rate'] > 5:
            verdict = "策略表现优秀！"
        elif profit['profit_rate'] > 0:
            verdict = "策略略有盈利，可以继续观察"
        elif profit['profit_rate'] > -5:
            verdict = "策略表现一般，建议优化"
        else:
            verdict = "策略亏损严重，需要重新评估"
        
        print(f"\n【综合评价】{verdict}")
        print("=" * 70)
        
        return report
    
    def save_report(self, report: dict):
        """保存报告到文件"""
        if not report.get("success"):
            return
        
        date_str = report["report_date"]
        filename = self.report_dir / f"report_{date_str}.json"
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n报告已保存到: {filename}")
        
        md_filename = self.report_dir / f"report_{date_str}.md"
        self._save_markdown(report, md_filename)
        print(f"Markdown报告已保存到: {md_filename}")
    
    def _save_markdown(self, report: dict, filename: Path):
        """保存Markdown格式报告"""
        stats = report["statistics"]
        profit = report["profit_analysis"]
        
        md = f"""# A股预测报告 - {report['report_date']}

## 预测准确率统计

| 指标 | 数值 |
|------|------|
| 总预测次数 | {stats['total_predictions']} |
| 正确次数 | {stats['correct_predictions']} |
| 准确率 | {stats['accuracy']:.1f}% |

## 买入信号统计

| 指标 | 数值 |
|------|------|
| 买入信号数 | {stats['buy_signals']} |
| 盈利次数 | {stats['buy_wins']} |
| 买入胜率 | {stats['buy_win_rate']:.1f}% |

## 盈亏分析（每笔买入 1000 元）

| 指标 | 数值 |
|------|------|
| 总交易次数 | {profit['total_trades']} |
| 总投入 | {profit['total_investment']:.2f} 元 |
| 总盈亏 | {profit['total_profit']:+.2f} 元 |
| 收益率 | {profit['profit_rate']:+.2f}% |

### 交易明细

| 日期 | 代码 | 预测 | 实际涨跌 | 结果 | 盈亏 |
|------|------|------|----------|------|------|
"""
        
        for r in report.get("records", []):
            date = r.get("date", "")[:10]
            code = r.get("stock_code", "")
            pred = r.get("direction", "")
            actual = r.get("actual_change", 0)
            correct = "✓" if r.get("correct") else "✗"
            pnl = 1000 * (actual / 100)
            md += f"| {date} | {code} | {pred} | {actual:+.2f}% | {correct} | {pnl:+.2f} |\n"
        
        verdict = "策略表现优秀！" if profit['profit_rate'] > 5 else ("策略略有盈利" if profit['profit_rate'] > 0 else ("策略表现一般" if profit['profit_rate'] > -5 else "策略亏损严重"))
        
        md += f"""
## 综合评价

**{verdict}**

> 本报告仅供参考，不构成投资建议。股市有风险，入市需谨慎。
"""
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write(md)


def backtest(stock_code: str, days: int = 30) -> dict:
    """
    回测最近N天的预测效果
    
    模拟：
    1. 每天都做一次预测
    2. 如果预测是"买入"，则次日买入
    3. 计算累计收益
    """
    try:
        import akshare as ak
        
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=days+20)).strftime("%Y%m%d")
        
        df = ak.stock_zh_a_hist(
            symbol=stock_code,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq"
        )
        
        if df is None or len(df) < days + 10:
            return {"success": False, "error": "数据不足"}
        
        predictor = StockPredictor()
        
        predictions = []
        for i in range(10, len(df) - 1):
            history = df.iloc[:i+1].copy()
            result = predictor.predict(history)
            
            actual_change = (df["收盘"].iloc[i+1] / df["收盘"].iloc[i] - 1) * 100
            
            pred_correct = False
            if result.direction == "上涨" and actual_change > 0.5:
                pred_correct = True
            elif result.direction == "下跌" and actual_change < -0.5:
                pred_correct = True
            elif result.direction == "震荡" and -0.5 <= actual_change <= 0.5:
                pred_correct = True
            
            predictions.append({
                "date": df["日期"].iloc[i],
                "predicted": result.direction,
                "actual": "涨" if actual_change > 0.5 else ("跌" if actual_change < -0.5 else "震"),
                "actual_change": actual_change,
                "correct": pred_correct,
                "confidence": result.confidence,
                "action": result.action,
                "score": result.score
            })
        
        predictions = predictions[-days:] if len(predictions) > days else predictions
        
        total = len(predictions)
        correct = sum(1 for p in predictions if p["correct"])
        accuracy = correct / total * 100 if total > 0 else 0
        
        buy_predictions = [p for p in predictions if p["action"] == "买入"]
        buy_correct = sum(1 for p in buy_predictions if p["actual_change"] > 0)
        buy_accuracy = buy_correct / len(buy_predictions) * 100 if buy_predictions else 0
        
        investment = 1000
        total_profit = investment * sum(p["actual_change"] / 100 for p in buy_predictions)
        profit_rate = (total_profit / (investment * len(buy_predictions))) * 100 if buy_predictions else 0
        
        return {
            "success": True,
            "stock_code": stock_code,
            "backtest_days": days,
            "total_predictions": total,
            "accuracy": round(accuracy, 1),
            "buy_signals": len(buy_predictions),
            "buy_accuracy": round(buy_accuracy, 1),
            "total_profit": round(total_profit, 2),
            "profit_rate": round(profit_rate, 2),
            "predictions": predictions[-10:]
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="A股自动化预测与报告系统")
    parser.add_argument("--report", action="store_true", help="生成5日报告")
    parser.add_argument("--backtest", type=int, metavar="DAYS", help="回测最近N天")
    parser.add_argument("--stock", type=str, default="000001", help="回测的股票代码")
    parser.add_argument("--stocks", type=str, default="", help="批量预测的股票代码(逗号分隔)")
    
    args = parser.parse_args()
    
    if args.backtest:
        print(f"\n正在回测 {args.stock} 最近 {args.backtest} 天...")
        result = backtest(args.stock, args.backtest)
        
        if result.get("success"):
            print("\n" + "=" * 60)
            print(f"           回测报告 - {args.stock}")
            print("=" * 60)
            print(f"  回测天数: {result['backtest_days']}")
            print(f"  总预测: {result['total_predictions']} 次")
            print(f"  方向准确率: {result['accuracy']:.1f}%")
            print(f"  买入信号: {result['buy_signals']} 次")
            print(f"  买入胜率: {result['buy_accuracy']:.1f}%")
            print(f"  总盈亏: {result['total_profit']:+.2f} 元")
            print(f"  收益率: {result['profit_rate']:+.2f}%")
            print("=" * 60)
        else:
            print(f"\n回测失败: {result.get('error', '未知错误')}")
        return
    
    if args.report:
        report_gen = PredictionReport()
        report = report_gen.generate_5day_report()
        report_gen.print_report(report)
        report_gen.save_report(report)
        return
    
    if args.stocks:
        codes = [c.strip() for c in args.stocks.split(",")]
        predictor = AutoPredictor(codes)
    else:
        predictor = AutoPredictor()
    
    predictor.run_daily()
    
    print("\n" + "-" * 60)
    print("提示：")
    print("  --report     生成5日预测报告")
    print("  --backtest N 回测最近N天")
    print("-" * 60)


if __name__ == "__main__":
    main()
