# 汇总调参结果：按"验证集MSE最小"预先固定的规则选超参，输出测试集指标，并与当前报告数值对照
import re, sys
from collections import defaultdict

LOG = 'results/experiment_log_v3_tuning.txt'
txt = open(LOG, encoding='utf-8').read()

# 解析每个实验块（取最后一次完整运行：含"最优验证"和"DA"行）
blocks = re.split(r'(?m)^=== ', txt)
runs = {}
for b in blocks:
    m = re.match(r'(.*?) \d{2}:\d{2} ===\n', b)
    if not m:
        continue
    tag = m.group(1)
    vm = re.search(r'最优验证 MSE: ([\d.]+)', b)
    da = re.search(r'DA\s+([\d.]+)', b)
    if not (vm and da):
        continue
    runs[tag] = {
        'val': float(vm.group(1)),
        'mse': float(re.search(r'\n  MSE\s+([\d.]+)', b).group(1)),
        'mae': float(re.search(r'MAE\s+([\d.]+)', b).group(1)),
        'r2': float(re.search(r'R2\s+([-\d.]+)', b).group(1)),
        'da': float(da.group(1)),
    }
print(f'解析到 {len(runs)} 组完整实验')

# 按 (主体, 模型配置) 分组，hidden/lr 作为候选超参
def key_single(tag):
    p = tag.split()
    return (p[0], p[1], p[2])           # code, model, volw
def key_panel(tag):
    p = tag.split()
    return (p[1], p[2])                  # arch=xx, volw=xx
def hp(tag):
    p = tag.split()
    return (p[4].split('=')[1], p[5].split('=')[1])  # hidden, lr

groups = defaultdict(list)
for tag, r in runs.items():
    k = key_panel(tag) if tag.startswith('PANEL8') else key_single(tag)
    groups[k].append((hp(tag), r))

sel = {}
for k, cands in groups.items():
    best = min(cands, key=lambda c: c[1]['val'])   # 预先固定规则：验证集 MSE 最小
    sel[k] = best

# 当前报告数值（表3-3 / 表3-4，v2 口径）
CUR = {
    ('600036.SH', 'baseline', 'volw=off'): (1.54, -0.1347, 0.4883),
    ('600036.SH', 'bimamba', 'volw=off'): (1.44, -0.0606, 0.4844),
    ('600036.SH', 'baseline', 'volw=on'): (1.52, -0.1216, 0.4844),
    ('600036.SH', 'bimamba', 'volw=on'): (1.60, -0.1833, 0.5430),
    ('601288.SH', 'baseline', 'volw=off'): (1.69, -0.0007, 0.5352),
    ('601288.SH', 'bimamba', 'volw=off'): (1.89, -0.1178, 0.4727),
    ('601288.SH', 'baseline', 'volw=on'): (1.70, -0.0059, 0.5352),
    ('601288.SH', 'bimamba', 'volw=on'): (1.73, -0.0243, 0.5078),
    ('601328.SH', 'baseline', 'volw=off'): (1.38, -0.0881, 0.4453),
    ('601328.SH', 'bimamba', 'volw=off'): (1.29, -0.0135, 0.5469),
    ('601328.SH', 'baseline', 'volw=on'): (1.41, -0.1060, 0.4766),
    ('601328.SH', 'bimamba', 'volw=on'): (1.54, -0.2118, 0.5078),
    ('601988.SH', 'baseline', 'volw=off'): (1.34, -0.0528, 0.4531),
    ('601988.SH', 'bimamba', 'volw=off'): (1.37, -0.0731, 0.5234),
    ('601988.SH', 'baseline', 'volw=on'): (1.47, -0.1572, 0.4727),
    ('601988.SH', 'bimamba', 'volw=on'): (1.35, -0.0623, 0.4531),
}
CUR_PANEL = {
    ('arch=off', 'volw=off'): (1.36, -0.0340, 0.4907),
    ('arch=on', 'volw=off'): (1.34, -0.0163, 0.4941),
    ('arch=off', 'volw=on'): (1.37, -0.0393, 0.4893),
    ('arch=on', 'volw=on'): (1.34, -0.0158, 0.4956),
}

print('\n===== 单股票（选股依据=验证集MSE最小） =====')
print(f"{'配置':<38} {'超参(h,lr)':<12} {'MSEe4':>7} {'R2':>8} {'DA':>7}   当前报告(R2/DA)")
for k in sorted(sel):
    (h, lr), r = sel[k]
    cur = CUR.get(k)
    cur_s = f'{cur[1]:.4f}/{cur[2]:.4f}' if cur else '  (Transformer 现有 -0.2242~-0.1370)'
    print(f"{' '.join(k):<38} {f'{h},{lr}':<12} {r['mse']*1e4:>7.2f} {r['r2']:>8.4f} {r['da']:>7.4f}   {cur_s}")

print('\n===== 面板 =====')
for k in sorted(sel):
    if not k[0].startswith('arch'):
        continue
    (h, lr), r = sel[k]
    cur = CUR_PANEL.get(k)
    cur_s = f'{cur[1]:.4f}/{cur[2]:.4f}' if cur else ' (Transformer 现有 -0.1753/0.4927)'
    print(f"{' '.join(k):<22} {f'{h},{lr}':<12} {r['mse']*1e4:>7.2f} {r['r2']:>8.4f} {r['da']:>7.4f}   {cur_s}")
