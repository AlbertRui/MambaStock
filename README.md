# Bi-Mamba-Stock：基于 Mamba 状态空间模型的股票价格预测

硕士毕业论文工程实现。在 [MambaStock](https://github.com/zshicode/MambaStock) 基线之上扩展三个创新模块，并配套完整的数据管道、无泄露实验流程与消融实验体系。

## 三大创新模块（对应代码位置）

| 模块 | 说明 | 实现 |
|:---|:---|:---|
| ① 双向选择性扫描 | 前向/后向两条独立状态空间路径 + 可学习门控融合 | `models.py` → `BidirectionalMamba` |
| ② 轻量化跨股票注意力 | 同板块股票隐态间缩放点积注意力，捕捉板块联动 | `models.py` → `CrossStockAttention`，训练入口 `train_panel.py` |
| ③ 波动自适应训练 | EWMA 波动率 → 低/中/高三档 → 损失加权 0.5/1.0/2.0 | `models.py` → `VolatilityAdaptiveLoss`，分档在 `data.py` |

## 项目结构

```
mamba.py / pscan.py     Mamba 核心（选择性扫描，纯 PyTorch 实现，CPU/GPU 均可）
models.py               模型库：单向基线 + 三大创新模块 + 面板模型
data.py                 数据管道：特征工程、pre_close 修正标签、时序切分、防泄露标准化
train.py                单股票训练入口（模块一/三消融）
train_panel.py          多股票面板训练入口（模块二消融 + 注意力热力图输出）
download.py             Tushare 批量下载（限流重试、断点续下）
refill_basic.py         数据补全工具（每日指标列）
run_experiments*.sh     批量实验脚本（断点续跑，结果追加到 results/ 日志）
main.py                 原版 MambaStock 基线（保留作对照）
docs/csv/               股票日线数据（Tushare 格式 CSV）
results/                实验日志与图表（收敛曲线、价格还原、注意力热力图）
```

## 快速开始

```bash
pip install -r requirements.txt

# 单股票：单向基线 vs 双向（模块一），--vol-weight 开启波动加权（模块三）
python train.py --csv docs/csv/600036.SH.csv --model baseline
python train.py --csv docs/csv/600036.SH.csv --model bimamba --vol-weight

# 多股票面板：模块二消融（--no-attention 关闭注意力）
python train_panel.py
python train_panel.py --no-attention

# 下载新数据（需 Tushare Pro token，写入 .env 的 TUSHARE_TOKEN 或 --token 传入）
python download.py --codes 600036.SH 601288.SH

# 批量消融实验（可中断重跑，已完成配置自动跳过）
bash run_experiments_v2.sh
```

## 实验设计要点（时序严谨性）

- 标签为未来 horizon 日累计对数收益率，基于 `pre_close` 逐日修正，除权除息日不产生假收益
- Z-score 与波动分档阈值**只用训练段拟合**，再应用到验证/测试段
- 样本严格按时间顺序切分（70/15/15），验证集早停 + 最优权重回滚，不用测试集调参
- 固定随机种子；同配置重跑结果逐位一致（GPU 上已验证）

## 结果速览（v2，8 只银行股 2019–2025，horizon=1）

- 模块一：双向在 601328 上 DA +10.2pp（0.547 vs 0.445）、MSE -6.5%
- 模块二：跨股票注意力对 MSE/R² 有一致改善；完整模型（注意力+波动加权）在面板 R² 与 DA 上同时最优
- 完整消融矩阵见 `results/experiment_log_v2.txt`（20 组对照实验）

## 致谢与引用

Mamba 模型部分代码参考 [alxndrTL/mamba.py](https://github.com/alxndrTL/mamba.py)，基线模型来自 MambaStock：

```
@article{shi2024mamba,
  title={MambaStock: Selective state space model for stock prediction},
  author={Zhuangwei Shi},
  journal={arXiv preprint arXiv:2402.18959},
  year={2024},
}
```
