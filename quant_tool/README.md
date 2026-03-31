# A股量化分析工具

基于 Python 的 A股量化分析工具，支持数据收集、技术指标计算、纯交易数据分析和回测。

## 功能特性

| 模块 | 功能 |
|------|------|
| **数据收集** | AkShare/新浪财经行情、财务数据、资金流向 |
| **技术指标** | SMA/EMA/RSI/MACD/KDJ/布林带/OBV/ATR |
| **交易分析** | 量价关系、背离检测、趋势判断 |
| **情绪分析** | 散户情绪、市场情绪指数 |
| **回测引擎** | RSI均值回归策略回测 |

## 项目结构

```
quant_tool/
├── config/
│   └── settings.py        # 配置文件
├── data/
│   ├── collectors/        # 数据收集
│   │   ├── akshare_collector.py   # AkShare数据
│   │   └── sentiment_collector.py # 情绪数据
│   └── processors/        # 数据处理
│       ├── cleaner.py      # 清洗模块
│       └── indicator.py    # 指标计算
├── analyzers/              # 分析器
│   ├── technical_analyzer.py  # 技术分析
│   └── sentiment_analyzer.py  # 情绪分析
├── backtest/               # 回测
│   └── engine.py           # 回测引擎
├── utils/                  # 工具
├── main.py                # 入口
└── requirements.txt
```

## 快速开始

### 1. 安装依赖

```bash
cd quant_tool
pip install -r requirements.txt
```

### 2. 运行分析

```bash
# 分析单只股票
python main.py --stock 000001

# 回测策略
python main.py --stock 000001 --mode backtest

# 批量分析
python main.py --stocks 000001,600519,000858 --mode batch
```

## 使用示例

### Python API

```python
from data.collectors.akshare_collector import AkShareCollector
from analyzers.technical_analyzer import TechnicalAnalyzer

collector = AkShareCollector()
kline_df = collector.get_historical_kline("000001")

analyzer = TechnicalAnalyzer()
result = analyzer.analyze(kline_df)

print(result["summary"])
```

### 自定义策略回测

```python
from backtest.engine import BacktestEngine
from data.processors.indicator import IndicatorCalculator

def my_strategy(df, i):
    if i < 20:
        return "hold"
    close = df["收盘"]
    rsi = IndicatorCalculator.calculate_rsi(close, 14)
    if rsi.iloc[i] < 30:
        return "buy"
    elif rsi.iloc[i] > 70:
        return "sell"
    return "hold"

engine = BacktestEngine(initial_capital=1000000)
results = engine.run(kline_df, my_strategy)
engine.print_summary(results)
```

## 技术指标

| 指标 | 说明 |
|------|------|
| SMA/EMA | 移动平均线 |
| RSI | 相对强弱指数 |
| MACD | 指数平滑异同移动平均线 |
| KDJ | 随机指标 |
| Bollinger | 布林带 |
| OBV | 能量潮 |
| ATR | 平均真实波幅 |

## 数据源

- **AkShare** - 新浪财经行情数据
- **东方财富** - 资金流向
- **雪球** - 散户情绪（需登录）

## 注意事项

1. 本工具仅供学习研究，不构成投资建议
2. 回测结果不代表实际收益
3. 情绪数据爬虫可能被封禁，请合理设置请求频率
