# 大乐透 / 双色球历史数据与候选号码实验室

这是一个零第三方运行时依赖的 Python 命令行项目。它会从用户提供的官方接口拉取
大乐透和双色球当前可用的完整历史开奖，保存为 JSON/CSV，并依据历史统计生成默认
5 组加权随机候选号码。

> **重要：仅供娱乐。开奖是独立随机事件，历史统计不能预测下一期，也不能提高中奖概率。**

## 环境

- Windows、macOS 或 Linux
- Python 3.12+

## 使用

在本项目目录运行：

```powershell
# 联网抓取完整历史、保存数据、各生成 5 组
python -m lottery_lab run

# 固定随机种子，方便复现
python -m lottery_lab run --seed 20260814

# 不联网，直接用上次保存的数据
python -m lottery_lab generate --offline --seed 20260814

# 使用低重叠覆盖模式生成各 5 组
python -m lottery_lab generate --offline --mode coverage --seed 20260814

# 改为各生成 8 组，并指定数据目录
python -m lottery_lab run --count 8 --data-dir D:\lottery-data
```

生成文件：

- `data/dlt_history.json`、`data/dlt_history.csv`
- `data/ssq_history.json`、`data/ssq_history.csv`

CSV 使用 UTF-8 BOM，方便直接用 Excel 打开。程序只在明确执行 `generate --offline`
时复用缓存；在线抓取失败会报告错误，不会悄悄把旧数据当成新数据。

## 生成模式

### `weighted`（默认）

每个号码的抽样权重由三项组成：

- 全部历史出现频率：50%
- 最近 50 期出现频率：35%
- 从最新一期起的遗漏期数：15%

三项分别按号码池平均值归一化并做平滑，确保每个合法号码始终有非零概率；每一注
使用加权不放回抽样，因此同一区内不会重复。这个方法只是把“热号、近期号、遗漏号”
组合成一种透明的随机策略，不是统计预测模型。

### `coverage`（低重叠覆盖）

在固定注数内平衡每个号码的使用次数，并对重复号码对、明显连号、等差图案和极端
奇偶分布增加惩罚。默认 5 注时：

- 大乐透覆盖 25 个不同前区号码、10 个不同后区号码
- 双色球覆盖 30 个不同红球号码、5 个不同蓝球号码

该模式优化的是多注分散度和小奖覆盖结构，不会提高 5 注一等奖的总概率。

## 数据源

- 大乐透：中国体彩网 `getHistoryPageListV1.qry`（`gameNo=85`）
- 双色球：中国福彩网 `client_json.php`（`lotteryId=1`）

接口可能调整结构或访问策略。程序固定超时、最多重试 3 次，并严格校验分页总数和
每期号码；若接口结构改变，会明确失败，避免生成基于残缺历史的结果。

## 验证

```powershell
python -m unittest discover -s tests -v
python -m compileall -q lottery_lab tests
```
