# 图3-6（新增）：单股票场景四模型 MSE + MAE 双子图分组对比
# 数据口径 = 报告 v2 口径（hidden=32, lr=1e-3, wd=1e-4, seed=1），与表3-3 完全一致
# 数据来源：results/experiment_log_v2.txt（Mamba 配置与 Transformer 单股票）—— 真实实验日志
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.font_manager import FontProperties

zh = FontProperties(family='Microsoft YaHei')

stocks = ['招商银行\n600036.SH', '农业银行\n601288.SH', '交通银行\n601328.SH', '中国银行\n601988.SH']
labels = ['Transformer', 'Baseline (uni-Mamba)', 'Bi-Mamba (ours)', 'Bi-Mamba + VolWeight (ours)']
colors = ['#2ca02c', '#7f7f7f', '#1f77b4', '#ff7f0e']

# 列序与图3-4/3-5 一致：Transformer / 单向基线 / 双向 / 双向+波动加权
MSE = [[1.66, 1.93, 1.56, 1.45],   # Transformer
       [1.54, 1.69, 1.38, 1.34],   # 单向基线
       [1.44, 1.89, 1.29, 1.37],   # 双向
       [1.60, 1.73, 1.54, 1.35]]   # 双向+波动加权
MAE = [[9.80, 10.92, 9.74, 9.56],
       [9.11, 10.12, 9.20, 8.87],
       [8.77, 10.76, 8.72, 9.00],
       [9.29, 10.27, 9.74, 9.05]]

fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), dpi=160)
for ax, data, ylab, ylim in zip(axes, (MSE, MAE),
                                (r'MSE ($\times 10^{-4}$)', r'MAE ($\times 10^{-3}$)'),
                                ((1.0, 2.05), (8.0, 11.4))):
    n, m = len(stocks), len(labels)
    x = np.arange(n); w = 0.19
    for i in range(m):
        bars = ax.bar(x + (i - (m - 1) / 2) * w, data[i], w, color=colors[i], label=labels[i])
        for b, v in zip(bars, data[i]):
            ax.text(b.get_x() + b.get_width() / 2, v + (ylim[1] - ylim[0]) * 0.012,
                    f'{v:.2f}', ha='center', va='bottom', fontsize=7.5)
    ax.set_xticks(x); ax.set_xticklabels(stocks, fontproperties=zh, fontsize=9)
    ax.set_ylabel(ylab, fontsize=10); ax.set_ylim(*ylim)
    ax.grid(axis='y', alpha=0.3); ax.set_axisbelow(True)
axes[1].set_xlabel('Stock', fontsize=10)
axes[0].set_xlabel('Stock', fontsize=10)
fig.legend(labels, loc='lower center', ncol=4, fontsize=9, frameon=True)
fig.tight_layout(rect=(0, 0.09, 1, 1))
fig.savefig('results/v3_mse_mae_compare.png')
print('saved results/v3_mse_mae_compare.png')
