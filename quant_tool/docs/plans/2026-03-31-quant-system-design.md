# A股量化分析系统 - 完整设计文档

**版本**: v2.0 Full Edition  
**日期**: 2026-03-31  
**目标**: 构建一个完整的A股量化分析决策系统

---

## 一、系统愿景

### 1.1 最终目标
构建一个**多维度融合**的A股量化分析系统，能够：
- 综合技术面、基本面、市场情绪三大维度
- 通过时间锁定回测验证策略有效性
- 提供明确的投资建议（买入/卖出/观望）
- 持续迭代优化，提升预测准确性

### 1.2 核心定位
| 定位 | 说明 |
|------|------|
| **不做什么** | 不做实盘交易下单，不预测具体价格 |
| **做什么** | 提供分析决策支持，告诉你"值得关注/回避" |
| **目标用户** | 有一定学习意愿的A股投资者 |

---

## 二、系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户界面层 (CLI/Web)                       │
│                    python main.py / Streamlit UI                 │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                       分析决策引擎                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ 技术分析模块 │  │ 基本面模块   │  │ 情绪分析模块 │             │
│  │ (Technical) │  │(Fundamental)│  │ (Sentiment) │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│         │                │                │                      │
│         └────────────────┼────────────────┘                      │
│                          ▼                                       │
│               ┌─────────────────────┐                            │
│               │   多因子融合引擎    │                            │
│               │ (Multi-Factor Model)│                            │
│               └─────────────────────┘                            │
│                          │                                       │
│                          ▼                                       │
│               ┌─────────────────────┐                            │
│               │    噪声过滤器       │                            │
│               │ (Noise Filter)      │                            │
│               └─────────────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                         数据层                                   │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌──────────┐  │
│  │ AkShare    │  │ 巨潮资讯   │  │ 东方财富   │  │ 雪球/贴吧│  │
│  │ (行情/指标)│  │ (财报/公告)│  │ (资金流)   │  │ (舆情)   │  │
│  └────────────┘  └────────────┘  └────────────┘  └──────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 三、核心模块设计

### 3.1 技术分析模块 (Technical Analyzer)

**职责**: 从K线数据中提取技术信号

**数据输入**:
- K线数据（日/周/月）
- 成交量数据

**技术指标库**:

| 指标类别 | 指标列表 | 说明 |
|----------|----------|------|
| 趋势类 | SMA, EMA, MACD | 判断方向 |
| 动量类 | RSI, KDJ, CCI | 判断超买超卖 |
| 波动类 | Bollinger, ATR | 判断波动幅度 |
| 量价类 | OBV, Volume Ratio | 判断资金流向 |
| 形态类 | 背离、突破 | 识别特定形态 |

**信号输出**:
```python
{
    "trend_score": +2,        # -3 ~ +3
    "momentum_score": +1,     # -3 ~ +3  
    "volume_score": 0,        # -2 ~ +2
    "signals": ["MACD金叉", "RSI超卖"],
    "overall": "偏多"         # 偏多/偏空/中性
}
```

**算法原理**:
```
趋势得分 = Σ(各指标信号 × 权重)
动量得分 = RSI标准化 + KDJ标准化 + CCI标准化
量价得分 = OBV方向 × 量比异常度
综合得分 = 趋势×40% + 动量×30% + 量价×30%
```

---

### 3.2 基本面分析模块 (Fundamental Analyzer)

**职责**: 评估股票的内在价值

**数据输入**:
- 财务报表（利润表、资产负债表、现金流量表）
- 财务指标（PE、PB、ROE、毛利率等）
- 公告信息（业绩预告、重大事项）

**评估维度**:

| 维度 | 指标 | 参考区间 |
|------|------|----------|
| 估值 | PE, PB | 行业对比 |
| 成长 | 营收增速、利润增速 | >20%为优秀 |
| 盈利 | ROE、毛利率、净利率 | 稳定或上升 |
| 偿债 | 资产负债率 | <60% |
| 现金流 | 经营现金流/净利润 | >80%为优秀 |

**信号输出**:
```python
{
    "valuation_score": +1,    # -2 ~ +2
    "growth_score": +2,       # -2 ~ +2
    "profitability_score": +1,# -2 ~ +2
    "overall": "良好"        # 优秀/良好/一般/较差
}
```

**关键处理**:
- 财报数据需要**对齐**（同一报告期）
- 异常值需要**剔除**（如一次性损益）
- 行业**对标比较**更合理

---

### 3.3 情绪分析模块 (Sentiment Analyzer) ⭐ 重点

**职责**: 从新闻、帖子、评论中提取市场情绪

**数据输入**:
| 来源 | 类型 | 获取难度 |
|------|------|----------|
| 东方财富股吧 | 散户帖子 | 中（需爬虫） |
| 雪球 | 投资者讨论 | 中（需爬虫/API） |
| 巨潮资讯 | 官方公告 | 低（AkShare有接口） |
| 新闻网站 | 财经新闻 | 中（需爬虫） |

**处理流程**:

```
原始文本
    │
    ▼
┌─────────────────┐
│  去重模块       │ ──── 基于标题/内容相似度
│ (Deduplication) │
└─────────────────┘
    │
    ▼
┌─────────────────┐
│  去噪模块       │ ──── 过滤广告、垃圾信息
│ (Noise Removal) │
└─────────────────┘
    │
    ▼
┌─────────────────┐
│  情感打分模块   │
│ (Sentiment Scorer)│
└─────────────────┘
    │
    ▼
┌─────────────────┐
│  信号聚合模块   │
│ (Signal Aggregator)│
└─────────────────┘
    │
    ▼
情绪信号
```

### 3.4 ⭐ 噪声处理方案（核心创新）

这是你特别关注的问题，我设计了**四层噪声过滤**：

#### 第一层：文本去噪

```python
class TextNoiseFilter:
    """文本噪声过滤器"""
    
    # 需要过滤的噪声模式
    NOISE_PATTERNS = [
        r"开户|荐股|微信\d+|QQ\d+",      # 广告类
        r"哈哈|呵呵|卧槽",                 # 无意义情绪词
        r"如图|如图所示|见下图",           # 无内容描述
        r"股票代码:\d{6}",                # 格式性文本
        r"本文不代表.*立场",               # 免责类
    ]
    
    def filter(self, text: str) -> bool:
        """返回True表示是噪声，False表示是有效文本"""
        for pattern in self.NOISE_PATTERNS:
            if re.search(pattern, text):
                return True
        return False
```

#### 第二层：情感信号去噪

```python
class SentimentNoiseFilter:
    """情感信号噪声过滤"""
    
    def filter_signals(self, signals: List[dict]) -> List[dict]:
        """过滤不可靠的情感信号"""
        # 1. 置信度过滤：低于阈值直接剔除
        signals = [s for s in signals if s["confidence"] >= 0.6]
        
        # 2. 时间衰减：越久远的声音权重越低
        signals = self._apply_time_decay(signals)
        
        # 3. 来源可信度：机构研报 > 财经媒体 > 散户帖子
        signals = self._apply_source_weight(signals)
        
        # 4. 交叉验证：多个独立来源的一致信号才可信
        signals = self._cross_validate(signals)
        
        return signals
```

#### 第三层：异常值剔除

```python
class OutlierFilter:
    """统计异常值过滤"""
    
    def remove_outliers(self, values: List[float], method="iqr") -> List[float]:
        """
        方法1: IQR法（四分位距）
        方法2: Z-score法（标准差）
        """
        if method == "iqr":
            q1, q3 = np.percentile(values, [25, 75])
            iqr = q3 - q1
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            return [v for v in values if lower <= v <= upper]
        else:
            mean = np.mean(values)
            std = np.std(values)
            return [v for v in values if abs(v - mean) <= 2.5 * std]
```

#### 第四层：信号一致性检验

```python
class SignalConsistencyChecker:
    """信号一致性检验"""
    
    def check(self, signals: dict) -> Tuple[bool, str]:
        """
        检查各维度信号是否一致
        返回: (是否一致, 原因说明)
        """
        tech = signals.get("technical", "neutral")
        fund = signals.get("fundamental", "neutral")
        sent = signals.get("sentiment", "neutral")
        
        # 统计各方向信号数量
        votes = {"看多": 0, "看空": 0, "中性": 0}
        if tech in ["偏多", "多头"]: votes["看多"] += 1
        if tech in ["偏空", "空头"]: votes["看空"] += 1
        if fund == "良好": votes["看多"] += 1
        if fund == "较差": votes["看空"] += 1
        if sent > 0.2: votes["看多"] += 1
        if sent < -0.2: votes["看空"] += 1
        
        # 一致性判断
        max_vote = max(votes.values())
        if max_vote >= 2:
            direction = max(votes, key=votes.get)
            confidence = max_vote / 3  # 0.33 ~ 1.0
            return True, f"{direction}（置信度{confidence:.0%}）"
        else:
            return False, "多空分歧严重，建议观望"
```

---

### 3.5 多因子融合引擎 (Multi-Factor Fusion Engine)

**核心思想**: 综合三个维度的信号，通过加权融合得出最终结论

```python
class MultiFactorEngine:
    """多因子融合引擎"""
    
    def __init__(self):
        # 因子权重（可根据回测结果调整）
        self.weights = {
            "technical": 0.40,      # 技术面 40%
            "fundamental": 0.30,   # 基本面 30%
            "sentiment": 0.30       # 情绪面 30%
        }
    
    def fuse(self, signals: dict) -> dict:
        """
        融合多因子信号
        """
        tech_score = self._normalize_technical(signals["technical"])
        fund_score = self._normalize_fundamental(signals["fundamental"])
        sent_score = self._normalize_sentiment(signals["sentiment"])
        
        # 加权得分
        final_score = (
            tech_score * self.weights["technical"] +
            fund_score * self.weights["fundamental"] +
            sent_score * self.weights["sentiment"]
        )
        
        # 噪声过滤后的信号一致性检验
        is_consistent, reason = SignalConsistencyChecker().check(signals)
        
        # 生成最终建议
        if not is_consistent:
            action = "观望"
            reason = "多空信号不一致，需要等待明确方向"
        elif final_score >= 0.3:
            action = "可以考虑买入"
        elif final_score <= -0.3:
            action = "建议回避"
        else:
            action = "轻度观望"
        
        return {
            "action": action,
            "score": final_score,
            "confidence": abs(final_score) if is_consistent else 0,
            "reason": reason,
            "signals": {
                "technical": tech_score,
                "fundamental": fund_score,
                "sentiment": sent_score
            }
        }
```

---

### 3.6 时间锁定回测系统 (Time-Locked Backtest)

**核心思想**: 模拟"穿越到过去某一天"，只使用该时间点之前的数据来判断应该买入还是卖出，然后看后一天的实际情况是否正确。

```python
class TimeLockedBacktest:
    """时间锁定回测引擎"""
    
    def run(self, stock_code: str, target_date: str, 
            lookback_days: int = 60) -> dict:
        """
        执行单次时间锁定回测
        
        Args:
            stock_code: 股票代码
            target_date: 目标日期 "YYYY-MM-DD"
            lookback_days: 回看多少天的数据
        
        Returns:
            {
                "target_date": "2026-03-20",
                "prediction": "买入",
                "actual_next_day": "涨",
                "hit": True,
                "data_used": ["K线数据60天", "新闻30篇", "公告5份"]
            }
        """
        # 1. 确定数据截止日期（target_date前一天）
        cutoff_date = self._get_previous_trading_day(target_date)
        
        # 2. 只加载cutoff_date之前的数据
        kline_data = self._load_data_until(stock_code, cutoff_date, lookback_days)
        news_data = self._load_news_until(stock_code, cutoff_date, days=30)
        fundamentals = self._load_financials_until(stock_code, cutoff_date)
        
        # 3. 执行分析（不包含target_date及之后的数据）
        signals = {
            "technical": self._analyze_technical(kline_data),
            "fundamental": self._analyze_fundamental(fundamentals),
            "sentiment": self._analyze_sentiment(news_data)
        }
        
        prediction = MultiFactorEngine().fuse(signals)
        
        # 4. 获取target_date次日的实际涨跌
        next_day_data = self._get_next_trading_day_data(stock_code, target_date)
        actual = "涨" if next_day_data["change_pct"] > 0 else "跌"
        
        # 5. 判断是否命中
        hit = (
            (prediction["action"] == "买入" and actual == "涨") or
            (prediction["action"] == "建议回避" and actual == "跌")
        )
        
        return {
            "target_date": target_date,
            "prediction": prediction["action"],
            "actual_next_day": actual,
            "actual_change_pct": next_day_data["change_pct"],
            "hit": hit,
            "confidence": prediction["confidence"]
        }
    
    def run_continuous(self, stock_code: str, 
                       start_date: str, end_date: str) -> dict:
        """
        连续多轮回测（连续命中测试）
        
        例如：测试2026年1月~3月共60个交易日
        每天执行一次判断，统计总体命中率
        """
        results = []
        dates = self._get_trading_days(start_date, end_date)
        
        for date in dates:
            result = self.run(stock_code, date)
            results.append(result)
        
        # 统计
        total = len(results)
        hits = sum(1 for r in results if r["hit"])
        hit_rate = hits / total if total > 0 else 0
        
        # 连续命中分析
        max_consecutive_hits = self._calc_max_consecutive(results, hit=True)
        
        return {
            "total_tests": total,
            "hits": hits,
            "hit_rate": hit_rate,
            "max_consecutive_hits": max_consecutive_hits,
            "results": results
        }
```

**连续命中判定标准**:
- 连续5轮命中：基础可信
- 连续10轮命中：较高可信
- 连续20轮命中：高度可信，可以考虑小资金试仓

---

## 四、数据源清单

### 4.1 已接入数据源

| 数据源 | 类型 | 接口 | 状态 |
|--------|------|------|------|
| AkShare | 行情/K线 | akshare | ✅ 已完成 |
| AkShare | 技术指标 | 自实现 | ✅ 已完成 |
| AkShare | 资金流向 | akshare | ✅ 已完成 |
| AkShare | 北向资金 | akshare | ✅ 已完成 |

### 4.2 待接入数据源

| 数据源 | 类型 | 优先级 | 预计工时 |
|--------|------|--------|----------|
| 巨潮资讯 | 财报/公告 | P0 | 1天 |
| 东方财富 | 股吧帖子 | P1 | 2天 |
| 雪球 | 投资者帖子 | P1 | 2天 |
| 新闻网站 | 财经新闻 | P2 | 3天 |
| 聚宽 | 历史回测数据 | P1 | 1天 |

---

## 五、输出示例

### 5.1 单次分析输出

```
======================================================================
              A股量化分析系统 v2.0 - 完整分析
======================================================================

股票: 000001 (平安银行)
分析日期: 2026-03-31
数据截止: 2026-03-28

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【综合结论】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🟢 推荐操作: 可以考虑买入
置信度: 78%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【三维度评分】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 技术面: +0.65 (偏多)
   • 趋势: 上涨趋势 (得分+2)
   • RSI: 56.5 中性，但KDJ超买
   • MACD: 多头排列
   • 信号: 顶背离警告

📋 基本面: +0.50 (良好)
   • PE: 6.2 (行业偏低)
   • ROE: 12.3% (稳定)
   • 营收增速: +8.5%
   • 评级: 良好

💬 情绪面: +0.30 (轻度看多)
   • 近期正面新闻: 12篇
   • 负面新闻: 3篇
   • 股吧情绪: 偏多
   • 噪声过滤后有效信号: 8条

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【多空逻辑链】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

看多逻辑:
  1. 技术面MACD金叉，形成上涨趋势
  2. 基本面PE较低，估值有优势
  3. 北向资金持续净流入

风险提示:
  1. KDJ处于超买区，短期可能回调
  2. 布林带上轨承压
  3. 建议控制仓位，不宜追高

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【时间锁定回测验证】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

测试区间: 2026-01-01 ~ 2026-03-28 (60个交易日)
测试结果:
  • 总测试次数: 60
  • 命中次数: 38
  • 命中率: 63.3%
  • 最长连续命中: 8轮

⚠️ 提示: 命中率>60%为可接受水平，>70%为优秀

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【次日预测】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

预测: 震荡偏多
预计波动区间: 11.2 ~ 11.8元
建议操作: 观望或轻仓布局

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 免责声明
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

本工具仅供参考，不构成投资建议！
股市有风险，入市需谨慎。
```

---

## 六、里程碑计划

| 阶段 | 内容 | 优先级 | 预计时间 |
|------|------|--------|----------|
| **Phase 1** | 完善技术分析模块 | P0 | 已完成 |
| **Phase 2** | 接入基本面数据（财报/指标） | P0 | 2天 |
| **Phase 3** | 实现四层噪声过滤器 | P0 | 3天 |
| **Phase 4** | 情绪分析模块（去重去噪+情感打分） | P1 | 4天 |
| **Phase 5** | 多因子融合引擎 | P1 | 2天 |
| **Phase 6** | 时间锁定回测系统 | P1 | 3天 |
| **Phase 7** | 连续命中验证 | P2 | 2天 |
| **Phase 8** | Streamlit可视化界面 | P2 | 3天 |

**总计**: 约19个工作日（可并行开发）

---

## 七、技术栈

| 组件 | 技术选型 | 理由 |
|------|----------|------|
| 数据获取 | AkShare, Requests | 免费、覆盖广 |
| 数据处理 | Pandas, NumPy | 事实标准 |
| 文本分析 | 规则方法 / LLM API | 规则可控，LLM更智能 |
| 终端绘图 | Plotext | 轻量级 |
| Web界面 | Streamlit | 快速开发 |
| 回测 | 自研 | 灵活控制 |

---

## 八、待确认事项

1. **情绪数据源优先级**: 东方财富股吧 vs 雪球，你更倾向哪个先接入？
2. **是否需要Streamlit界面**: 当前是命令行，是否需要Web界面？
3. **是否接入LLM API**: 情感分析可以使用免费的规则方法，或付费的GPT/Claude API？

---

*文档版本: 1.0*
*最后更新: 2026-03-31*
