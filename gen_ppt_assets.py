# 生成中期答辩PPT补充素材：技术路线图、防泄漏时间轴、评估指标公式、EWMA公式
# 输出目录：docs/ppt/assets/
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

OUT = 'docs/ppt/assets'
os.makedirs(OUT, exist_ok=True)
ACCENT = '#174994'
LIGHT = '#E9F0F8'


def box(ax, x, y, w, h, text, fc=LIGHT, ec=ACCENT, fs=13, tc='#1a1a1a', bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.02,rounding_size=0.08',
                                fc=fc, ec=ec, lw=1.4))
    ax.text(x + w / 2, y + h / 2, text, ha='center', va='center', fontsize=fs,
            color=tc, fontweight='bold' if bold else 'normal')


def arrow(ax, x1, y1, x2, y2):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle='-|>',
                                 mutation_scale=18, color=ACCENT, lw=1.6))


# ---------- 1. 技术路线横向流程图 ----------
steps = ['Tushare\n数据获取', '防泄漏\n预处理', '双向状态\n空间编码', '跨股票\n注意力', '波动自适\n应训练', '对比与\n消融评估']
fig, ax = plt.subplots(figsize=(12.4, 1.25))
ax.set_xlim(0, 12.4)
ax.set_ylim(0, 1.25)
ax.axis('off')
w, h, y = 1.75, 0.85, 0.2
for i, st in enumerate(steps):
    x = 0.15 + i * 2.06
    box(ax, x, y, w, h, st, fc=ACCENT if i in (2, 3, 4) else LIGHT,
        ec=ACCENT, fs=13, tc='white' if i in (2, 3, 4) else '#1a1a1a')
    if i < 5:
        arrow(ax, x + w + 0.05, y + h / 2, x + 2.06 - 0.05, y + h / 2)
fig.savefig(f'{OUT}/tech_route.png', dpi=200, bbox_inches='tight', transparent=True)
plt.close(fig)

# ---------- 2. 防泄漏时序切分图 ----------
fig, ax = plt.subplots(figsize=(9.6, 1.55))
ax.set_xlim(0, 9.6)
ax.set_ylim(0, 1.55)
ax.axis('off')
segs = [('训练集 70%', 0.7, '#2E75B6'), ('验证集 15%', 0.15, '#ED7D31'), ('测试集 15%', 0.15, '#548235')]
x = 0.3
for label, frac, color in segs:
    w = 8.6 * frac
    ax.add_patch(FancyBboxPatch((x, 0.72), w - 0.06, 0.42, boxstyle='round,pad=0.01,rounding_size=0.04',
                                fc=color, ec='none'))
    ax.text(x + (w - 0.06) / 2, 0.93, label, ha='center', va='center', fontsize=12, color='white', fontweight='bold')
    x += w
arrow(ax, 0.3, 0.52, 9.3, 0.52)
ax.text(9.32, 0.52, '时间', fontsize=11, va='center', color='#444444')
ax.text(4.8, 0.24, '标准化仅用训练集拟合  ·  pre_close标签修正  ·  模型选择仅用验证集（测试集零参与）',
        ha='center', fontsize=12, color=ACCENT, fontweight='bold')
fig.savefig(f'{OUT}/pipeline_leakfree.png', dpi=200, bbox_inches='tight', transparent=True)
plt.close(fig)

# ---------- 3. 评估指标公式（一行四式） ----------
fig, ax = plt.subplots(figsize=(13.2, 0.8))
ax.axis('off')
forms = [
    r'$\mathrm{MSE}=\frac{1}{N}\sum_{i=1}^{N}(\hat{y}_i-y_i)^2$',
    r'$\mathrm{MAE}=\frac{1}{N}\sum_{i=1}^{N}|\hat{y}_i-y_i|$',
    r'$R^2=1-\frac{\sum_i(y_i-\hat{y}_i)^2}{\sum_i(y_i-\bar{y})^2}$',
    r'$\mathrm{DA}=\frac{1}{N}\sum_{i=1}^{N}\mathbf{1}\{\mathrm{sign}(\hat{y}_i)=\mathrm{sign}(y_i)\}$',
]
for i, f in enumerate(forms):
    ax.text(0.125 + i * 0.25, 0.5, f, transform=ax.transAxes, ha='center', va='center', fontsize=15, color='#1a1a1a')
fig.savefig(f'{OUT}/formula_metrics.png', dpi=200, bbox_inches='tight', transparent=True)
plt.close(fig)

# ---------- 4. EWMA波动率与加权损失公式 ----------
fig, ax = plt.subplots(figsize=(5.8, 1.7))
ax.axis('off')
ax.text(0.5, 0.8, r'$\sigma_t^2=\lambda\,\sigma_{t-1}^2+(1-\lambda)\,r_{t-1}^2$',
        transform=ax.transAxes, ha='center', va='center', fontsize=16, color='#1a1a1a')
ax.text(0.5, 0.3, r'$\mathcal{L}=\frac{\sum_i w_i\,\ell_i}{\sum_i w_i},\quad w_i\in\{0.5,\ 1.0,\ 2.0\}$',
        transform=ax.transAxes, ha='center', va='center', fontsize=16, color='#1a1a1a')
fig.savefig(f'{OUT}/formula_ewma.png', dpi=200, bbox_inches='tight', transparent=True)
plt.close(fig)

print('素材已生成:', os.listdir(OUT))
