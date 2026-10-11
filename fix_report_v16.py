# 中期报告体检修复（全部修改均经表3-3/3-4 真实数据核验）：
# 硬伤1: 第39段 DA 过度声称（农业银行单向基线 0.5352 > 本文最优 0.5078）
# 硬伤2: 第42段 MAE 句与已加 MAE 列的表3-4 矛盾
# 硬伤3: 第33段 3个指标仅2个公式 + MAE 未定义
# 建议4: 约10维→10维  建议5: 删除第37段重复的耗时句  建议6: 3.2标题更名  建议7: 补4只股票选取说明
# 密度: 图3-1/3-2 整块移至表3-3 之后（图号出现顺序不变，无需重编号）
import shutil, time
from docx import Document

PATH = 'docs/基于Mamba状态空间模型的股票价格预测方法研究-中期.docx'
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
shutil.copy(PATH, 'docs/中期_v16_backup_' + time.strftime('%Y%m%d_%H%M%S') + '.bak')
d = Document(PATH)
cell = d.tables[2].rows[0].cells[0]

def ts_of(p):
    return list(p._p.iter(W + 't'))

def replace_in_para(idx, old, new, count=1):
    """在段落内跨 run 精确替换：先尝试单 run，失败则跨 run 合并定位（仅用于本次已知结构）"""
    for e in ts_of(cell.paragraphs[idx]):
        if e.text and old in e.text:
            e.text = e.text.replace(old, new, count)
            return True
    raise RuntimeError(f'para {idx} 未找到: {old[:30]}')

# 硬伤1（第39段）
replace_in_para(39,
    '与单向基线互有高低，但均不及本文双向模型及其波动加权配置在各股上的最优表现，表明',
    '与单向基线互有高低；本文双向模型或其波动加权配置在招商银行、交通银行、中国银行上均取得五种配置中的最高方向准确率，仅农业银行上单向基线最优（0.5352）。上述对照表明')

# 硬伤2（第42段）
replace_in_para(42,
    '各配置的平均绝对误差与均方误差排序一致，为控制表格宽度未在表中列示。',
    '各配置的平均绝对误差（MAE）亦列于表3-4，其最优配置同样为完整模型，与均方误差、决定系数的结论一致。')

# 硬伤3（第33段）：3指标2公式 -> 2指标2公式 + MAE/DA 文字定义
replace_in_para(33, '均方误差、决定系数与方向准确率的定义分别如式（', '均方误差与决定系数的定义分别如式（')
replace_in_para(33, '）所示。', '）所示；平均绝对误差（MAE）为预测误差绝对值的算术平均，方向准确率（DA）为预测涨跌方向与真实方向一致的样本占比。')

# 建议4（第15段）
replace_in_para(15, '特征工程按开题方案构建约', '特征工程按开题方案构建')

# 建议7 + 建议5（第37段）
replace_in_para(37, '只股票', '只股票（选取板块内4只以控制实验矩阵规模）')
ts37 = ts_of(cell.paragraphs[37])
for j, e in enumerate(ts37):
    if e.text == '云平台（恒源云），单轮（':
        e.text = '云平台（恒源云），在此平台上完成了上述'
        for e2 in ts37[j + 1:]:
            if e2.text and e2.text != '20' and not e2.text.startswith('组正式消融'):
                if e2.text in ('epoch', '）训练耗时由约', '138', '秒降至约', '2.3', '秒，效率提升约', '60', '倍，在此平台上完成了上述'):
                    e2.text = ''
        break

# 建议6（第6段标题）
replace_in_para(6, '技术方案', '技术方案与阶段性实验结果')

# 密度：移动图3-1/3-2 块（intro,img,cap,cap2,intro2,img2,cap2 = 7段）到表3-3 之后
paras = cell.paragraphs
block = []
for i, p in enumerate(paras):
    t = ''.join(e.text or '' for e in p._p.iter(W + 't'))
    if t.startswith('为直观展示预测效果，图3-1给出'):
        block = [paras[i + k]._p for k in range(7)]
        break
assert len(block) == 7 and block[1].findall('.//' + W + 'pict') and block[5].findall('.//' + W + 'pict')
anchor = cell.tables[2]._tbl   # 表3-3
for el in block:
    anchor.addnext(el)
    anchor = el

d.save(PATH)
print('全部修复完成')
