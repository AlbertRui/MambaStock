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

# ---------- 3. 报告公式高清重渲染（记法与中期报告式3-1~3-9完全一致） ----------
def render_formula(name, lines, figsize, fontsize=17):
    fig, ax = plt.subplots(figsize=figsize)
    ax.axis('off')
    n = len(lines)
    for i, f in enumerate(lines):
        ax.text(0.5, 1 - (i + 0.5) / n, f, transform=ax.transAxes,
                ha='center', va='center', fontsize=fontsize, color='#1a1a1a')
    fig.savefig(f'{OUT}/{name}.png', dpi=200, bbox_inches='tight', transparent=True)
    plt.close(fig)


# 式(3-1)(3-2)：状态空间模型连续/离散形式
render_formula('eq_ssm', [
    r"$h'(t)=Ah(t)+Bx(t),\quad y(t)=Ch(t)$",
    r'$h_t=Ah_{t-1}+Bx_t$',
], (5.6, 1.2))

# 式(3-3)(3-4)：双向扫描与门控融合
render_formula('eq_bi', [
    r'$h_f=\mathrm{Mamba}_f(x),\quad h_b=\mathrm{flip}(\mathrm{Mamba}_b(\mathrm{flip}(x)))$',
    r'$g=\sigma(W_g\,x+b_g),\quad h=g\odot h_f+(1-g)\odot h_b$',
], (6.4, 1.2))

# 式(3-5)：跨股票缩放点积注意力
render_formula('eq_attn', [
    r'$\mathrm{CrossStockAttn}(Q,K,V)=\mathrm{softmax}\left(\frac{QK^{\top}}{\sqrt{d}}\right)V$',
], (6.2, 0.75))

# 式(3-6)(3-7)：EWMA波动率与归一化加权损失
render_formula('eq_vol', [
    r'$\sigma_t^2=\lambda\,\sigma_{t-1}^2+(1-\lambda)\,r_{t-1}^2$',
    r'$w_i\in\{0.5,\ 1.0,\ 2.0\},\quad L=\frac{\sum_i w_i\,\ell_i}{\sum_i w_i}$',
], (5.6, 1.4))

# 式(3-8)(3-9)：MSE、R²与方向准确率评估口径
render_formula('eq_metrics', [
    r'$\mathrm{MSE}=\frac{1}{N}\sum_i(\hat{y}_i-y_i)^2$',
    r'$R^2=1-\frac{\sum_i(\hat{y}_i-y_i)^2}{\sum_i(y_i-\bar{y})^2},\quad \mathrm{DA}=\frac{1}{N}\sum_i I\{\hat{y}_i\,y_i>0\}$',
], (8.2, 1.5))

print('素材已生成:', os.listdir(OUT))
