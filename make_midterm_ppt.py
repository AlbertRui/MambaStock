# 由开题答辩PPT生成中期答辩PPT：完整复用模板（母版/导航栏/装饰/版式），
# 仅替换文字、表格与配图。所有实验数值与中期报告文档口径一致。
# 用法：.venv/Scripts/python.exe make_midterm_ppt.py
# 输出：docs/ppt/中期答辩v1.pptx
import copy
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.oxml.ns import qn

SRC = 'docs/ppt/开题v2.pptx'
DST = 'docs/ppt/中期答辩v1.pptx'

prs = Presentation(SRC)
S = prs.slides


def set_tf(tf, text):
    """替换文本框全部内容，保留首个段落中最长run的字体格式；\n 分段"""
    lines = text.split('\n')
    p0 = tf.paragraphs[0]._p
    proto = copy.deepcopy(p0)
    for br in proto.findall(qn('a:br')):
        proto.remove(br)
    runs = proto.findall(qn('a:r'))
    if runs:
        donor = max(runs, key=lambda r: len(r.find(qn('a:t')).text or ''))
        for r in runs:
            if r is not donor:
                proto.remove(r)
    txBody = tf._txBody
    for p in list(txBody.findall(qn('a:p'))):
        txBody.remove(p)
    for line in lines:
        p = copy.deepcopy(proto)
        r = p.find(qn('a:r'))
        if r is not None:
            r.find(qn('a:t')).text = line
        txBody.append(p)


def set_shape(sh, text):
    set_tf(sh.text_frame, text)


def by_name(slide, name):
    for sh in slide.shapes:
        if sh.name == name:
            return sh
    raise KeyError(f'{name} not found')


def in_group(slide, group_name, shape_name):
    g = by_name(slide, group_name)
    for sh in g.shapes:
        if sh.name == shape_name:
            return sh
    raise KeyError(f'{group_name}/{shape_name}')


def set_table(tbl_shape, rows):
    t = tbl_shape.table
    assert len(rows) == len(t.rows), f'行数不符: {len(rows)} vs {len(t.rows)}'
    for r, line in zip(t.rows, rows):
        assert len(line) == len(r.cells), f'列数不符: {line}'
        for c, txt in zip(r.cells, line):
            set_tf(c.text_frame, txt)


def deep_find(shapes, name):
    for sh in shapes:
        if sh.name == name:
            return sh
        if sh.shape_type == 6:
            found = deep_find(sh.shapes, name)
            if found is not None:
                return found
    return None


# 五章节新名称（导航栏统一替换）
NAV_OLD = ['研究背景及意义', '国内外研究现状', '研究目标与内容', '技术方案与路线', '预期成果与计划']
NAV_NEW = ['研究进展概述', '核心模块实现', '阶段性实验结果', '问题与解决方案', '下一阶段工作计划']
# 各章节导航高亮矩形(left, width)与三角箭头left（英寸，取自原模板对应章节页）
SEC_HL = {1: (1.2, 2.2, 1.9), 2: (3.4, 2.9, 4.6), 3: (6.3, 2.9, 7.4), 4: (9.2, 2.3, 10.0), 5: (11.3, 2.0, 12.0)}


def chrome(slide, sec, page):
    """内容页公共元素：导航栏文字、章节高亮位置、页码"""
    for sh in slide.shapes:
        if sh.has_text_frame:
            txt = sh.text_frame.text.strip()
            if txt in NAV_OLD:
                set_shape(sh, NAV_NEW[NAV_OLD.index(txt)])
        if sh.name in ('矩形 32', '矩形 81', 'Shape 1'):
            l, w, _ = SEC_HL[sec]
            sh.left, sh.width = Inches(l), Inches(w)
        if sh.name in ('等腰三角形 33', '等腰三角形 92', 'Shape 11'):
            sh.left = Inches(SEC_HL[sec][2])
        if sh.name in ('矩形 46', 'Text 32') and sh.has_text_frame and sh.text_frame.text.strip().isdigit():
            set_shape(sh, f'{page:02d}')


def add_note(slide, text, left, top, width):
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(0.4))
    box.text_frame.text = text
    box.text_frame.paragraphs[0].runs[0].font.size = Pt(12)
    box.text_frame.paragraphs[0].runs[0].font.color.rgb = RGBColor(0x40, 0x40, 0x40)


# ========== S1 封面（汇报人/指导教师等字段保持原样，不改动） ==========
s = S[0]
set_shape(by_name(s, '文本框 9'), 'Mid-term Progress Report')
set_shape(by_name(s, '文本框 33'), '2026年10月')

# ========== S2 目录 ==========
s = S[1]
for g, name, txt in [('组合 60', '文本框 11', NAV_NEW[0]), ('组合 69', '文本框 72', NAV_NEW[1]),
                     ('组合 73', '文本框 76', NAV_NEW[2]), ('组合 77', '文本框 80', NAV_NEW[3]),
                     ('组合 81', '文本框 84', NAV_NEW[4])]:
    set_shape(in_group(s, g, name), txt)

# ========== 章节过渡页 ==========
for idx, cn, en in [(2, NAV_NEW[0], 'Research Progress Overview'),
                    (5, NAV_NEW[1], 'Core Module Implementation'),
                    (8, NAV_NEW[2], 'Experimental Results and Analysis'),
                    (11, NAV_NEW[3], 'Problems and Solutions'),
                    (17, NAV_NEW[4], 'Next-stage Work Plan')]:
    set_shape(by_name(S[idx], '文本框 8'), cn)
    set_shape(by_name(S[idx], '文本框 9'), en)

# ========== S4（1.1 研究目标与总体进展） ==========
s = S[3]
chrome(s, 1, 1)
set_shape(by_name(s, '文本框 34'), '1.1  研究目标与总体进展')
set_shape(by_name(s, '文本框 12'),
    '研究目标：针对MambaStock单向结构、跨股票关系建模与训练策略的不足，构建Bi-Mamba-Stock模型，'
    '在保持线性计算复杂度的前提下，提升股价预测精度与鲁棒性\n'
    '总体进展：严格按照开题报告技术路线推进，目前按计划完成阶段性目标\n'
    '已完成：数据预处理管线与除息口径修正、三大核心模块实现、4股单股票与8股面板完整实验、关键问题诊断与修复\n'
    '正在进行：沪深300全市场数据扩展与主流基线补充的准备工作')

# ========== S5（1.2 已完成工作概览） ==========
s = S[4]
chrome(s, 1, 2)
set_shape(by_name(s, '文本框 34'), '1.2  已完成工作概览')
for name, txt in [
    ('Text 3', '数据与标签'), ('Text 5', '防泄漏预处理管线'),
    ('Text 6', '对数收益率＋Z-score标准化，严格时序70%/15%/15%切分'),
    ('Text 8', '除息口径严谨修正'), ('Text 9', 'pre_close逐日修正收益率，与官方涨跌幅交叉校验一致'),
    ('Text 11', '三大核心模块实现'), ('Text 12', '双向选择性扫描＋跨股票注意力＋波动自适应损失'),
    ('Text 14', '完整实验矩阵'), ('Text 15', '4股×5配置单股票实验＋8股面板消融实验'),
    ('Text 17', '阶段结论：开题提出的三大创新模块均已落地并完成小规模验证，实验流程可复现、结果可对比，为全市场扩展奠定基础。'),
]:
    set_shape(in_group(s, '组合 24', name), txt)

# ========== S7（2.1 三大核心模块：设计与实现） ==========
s = S[6]
chrome(s, 2, 3)
set_shape(by_name(s, '文本框 34'), '2.1  三大核心模块：设计与实现')
for name, txt in [('文本框 4', '双向选择性扫描'), ('文本框 6', '跨股票注意力'),
                  ('文本框 10', '波动自适应训练'), ('文本框 14', '严谨实验设计')]:
    set_shape(deep_find(by_name(s, '组合 28').shapes, name), txt)
set_table(by_name(s, '表格 52'), [
    ['模块一：前向＋后向独立状态空间路径，可学习门控融合双向隐态',
     '模块二：Q/K/V来自双向编码隐态，缩放点积注意力，无图卷积',
     '模块三：EWMA波动率分低/中/高三档，损失权重0.5/1.0/2.0',
     '严格时序切分；标准化仅用训练集拟合；pre_close标签修正'],
    ['验证情况：模型维度32容量匹配后，双向结构在多数股票上MSE/MAE优于单向基线',
     '验证情况：注意力坍缩已诊断并修复，权重恢复差异化分布',
     '验证情况：招商银行股方向准确率0.5430，为该股票五组配置最高',
     '验证情况：单股票＋面板双场景实验，种子固定、结果可复现'],
    ['复杂度：仅增加一条扫描路径，保持O(L)线性复杂度',
     '参数量：面板模型约4.6万参数，轻量化设计',
     '机制：高波动样本获得更高学习优先级，增强极端行情鲁棒性',
     '评估口径：MSE/MAE/R²/方向准确率，验证集早停与最优权重回滚'],
])
set_shape(by_name(s, '文本框 54'), '三大模块均已实现并完成小规模验证；消融开关支持逐模块对照实验。')

# ========== S8（2.2 关键问题诊断与修复） ==========
s = S[7]
chrome(s, 2, 4)
set_shape(by_name(s, '文本框 34'), '2.2  关键问题诊断与修复')
set_table(by_name(s, '表格 1'), [
    ['发现的问题', '原因分析与解决方案'],
    ['除息日虚假收益：close.shift(1)计算收益率在除权除息日产生规律性污染样本',
     '改用pre_close逐日修正收益率，与官方涨跌幅字段交叉校验，最大偏差不超过0.00005'],
    ['小样本双向过拟合：模型维度16时双向参数量约为基线两倍，指标反劣于基线',
     '容量与正则匹配对照实验：模型维度32配合权重衰减后，双向结构稳定反超基线'],
    ['注意力权重坍缩：统一权重衰减下，跨股票注意力恒为均匀分布（各股1/8）',
     '注意力分支豁免权重衰减后重新训练，权重恢复差异化，整体指标保持基本稳定'],
    ['算力与数据约束：CPU单组实验约30分钟；数据接口存在限流',
     '迁移GPU云平台，单epoch由约138秒降至约2.3秒（约60倍）；下载管线支持限流重试与断点续传'],
])

# ========== S10（3.1 实验设置与评估口径） ==========
s = S[9]
chrome(s, 3, 5)
set_shape(by_name(s, '文本框 3'), '3.1  实验设置与评估口径')
set_shape(by_name(s, '文本框 6'),
    '实验数据：8只银行股（银行板块），2018.06—2025.12日频数据，各1843个交易日\n'
    '预测任务：60日滑动窗口 → 未来1日对数收益率，输入10维平稳化特征\n'
    '对比基线：单向MambaStock、Transformer\n'
    '模型规模：模型维度32、编码器2层；面板模型约4.6万参数\n'
    '评估指标：MSE、MAE、决定系数R²、方向准确率（DA）\n'
    '严谨性设计：严格时序切分，验证集早停与最优权重回滚，模型选择不使用测试集')

# ========== S11（3.2 单股票实验：核心结果） ==========
s = S[10]
chrome(s, 3, 6)
set_shape(by_name(s, '文本框 3'), '3.2  单股票实验：核心结果')
for name, txt in [
    ('Text 5', '01  招商银行（600036.SH）'), ('Text 7', '双向＋波动加权'),
    ('Text 8', '• 方向准确率0.5430，五组配置最高'),
    ('Text 9', '• 双向MSE 1.44×10⁻⁴，优于基线1.54'),
    ('Text 10', '• 双向MAE 8.77×10⁻³，全组最优'),
    ('Text 11', '• 双向MSE较基线下降6.5%'),
    ('Text 13', '02  交通银行（601328.SH）'), ('Text 15', '双向结构'),
    ('Text 16', '• 方向准确率0.5469，五组配置最高'),
    ('Text 17', '• MSE 1.29×10⁻⁴，较基线下降6.5%'),
    ('Text 18', '• MAE 8.72×10⁻³，优于基线9.20'),
    ('Text 19', '• R²由-0.0881改善至-0.0135'),
    ('Text 21', '03  四只股票总体结论'), ('Text 23', 'Overall Findings'),
    ('Text 24', '• 四股中三股最高DA由本文配置取得'),
    ('Text 25', '• 双向模块在多数股票上改善MSE/MAE'),
    ('Text 26', '• 波动加权对高波动股票DA提升明显'),
    ('Text 27', '• 日频R²普遍为负，以相对提升为评估口径'),
]:
    set_shape(in_group(s, '组合 27', name), txt)

# ========== S13（3.3 八股面板消融实验结果） ==========
s = S[12]
chrome(s, 3, 7)
set_shape(by_name(s, '文本框 1'), '3.3  八股面板消融实验结果')
for name, txt in [
    ('Text 3', '📦 消融实验设置'),
    ('Text 4', '• 8只银行股面板，同板块小规模验证'),
    ('Text 5', '• 双向编码＋面板级跨股票注意力'),
    ('Text 6', '• 波动自适应损失作为可选消融开关'),
    ('Text 7', '• 参数量约4.6万，轻量化设计'),
    ('Text 8', '• 严格时序切分，验证集早停'),
    ('Text 10', '⚔️ 基线对比（h=1）'),
    ('Text 12', 'Transformer'), ('Text 13', 'MSE 1.55×10⁻⁴'),
    ('Text 15', '无注意力'), ('Text 21', '完整模型 ★'), ('Text 22', '本文方法'),
    ('Text 24', '📊 四组消融配置结果'),
    ('Text 27', '无注意力'), ('Text 28', 'MSE 1.36×10⁻⁴'), ('Text 29', 'DA 0.4907'),
    ('Text 32', '＋注意力'), ('Text 33', 'MSE 1.34×10⁻⁴'), ('Text 34', 'DA 0.4941'),
    ('Text 37', '＋波动加权'), ('Text 38', 'MSE 1.37×10⁻⁴'), ('Text 39', 'DA 0.4893'),
    ('Text 42', '完整模型'), ('Text 43', 'MSE 1.34×10⁻⁴'), ('Text 44', 'DA 0.4956（最高）'),
]:
    set_shape(by_name(s, name), txt)
set_shape(in_group(s, '组合 3', 'Text 16'), 'MSE 1.36×10⁻⁴')

# ========== S14（3.4 误差指标对比图） ==========
s = S[13]
chrome(s, 3, 8)
title = by_name(s, '文本框 1')
title.width = Inches(11.0)
set_shape(title, '3.4  误差指标对比：MSE 与 MAE')
pic = by_name(s, '图片 6')
pic._element.getparent().remove(pic._element)
s.shapes.add_picture('results/v3_mse_mae_compare.png', Inches(0.85), Inches(2.3), width=Inches(11.6))
add_note(s, '双向结构在招商银行、交通银行实现MSE与MAE双改善；完整模型在招商银行取得最低MAE。', 0.85, 7.05, 11.6)

# ========== S15（3.5 跨股票注意力权重分析） ==========
s = S[14]
chrome(s, 3, 9)
set_shape(by_name(s, '文本框 1'), '3.5  跨股票注意力权重分析')
set_shape(by_name(s, '文本框 7'),
    '诊断发现：统一权重衰减（1e-4）下，跨股票注意力权重恒为均匀分布（各股1/8），呈注意力坍缩现象\n'
    '机制分析：8只同质银行股场景下，板块等权均值已是较强特征，差异化权重收益有限，投影矩阵梯度弱，被权重衰减持续压缩至零\n'
    '修复验证：注意力分支（Q/K/V投影）豁免权重衰减后，权重恢复差异化（逐日偏差最大0.0124），'
    '对角线自注意力均值0.1263高于均匀基准0.125，整体指标保持基本稳定')
for name in ['图片 3', '图片 9']:
    pic = by_name(s, name)
    pic._element.getparent().remove(pic._element)
s.shapes.add_picture('results/panel_attn_h1_attn_v3.png', Inches(7.0), Inches(2.3), width=Inches(5.4))

# ========== S16（3.6 方向准确率对比） ==========
s = S[15]
chrome(s, 3, 10)
set_shape(by_name(s, '文本框 1'), '3.6  方向准确率（DA）对比')
set_shape(by_name(s, '文本框 5'),
    '核心结果：四只股票中三只的最高方向准确率由本文配置取得——交通银行（双向）0.5469、'
    '招商银行（双向＋波动加权）0.5430、中国银行（双向）0.5234\n'
    '面板结果：完整模型DA 0.4956，居四组消融配置首位；Transformer基线为0.4927\n'
    '评估口径：日频个股收益率可预测性极低，R²普遍为负属领域共识；'
    '以"相对基线提升＋方向准确率＋消融一致性"作为评估口径\n'
    '后续计划：以3—5个随机种子重复实验，报告均值与标准差，增强统计稳健性')
pic = by_name(s, '图片 4')
pic._element.getparent().remove(pic._element)
s.shapes.add_picture('results/v3_da_compare.png', Inches(5.9), Inches(2.6), width=Inches(7.0))

# ========== S17（3.7 阶段性结论） ==========
s = S[16]
chrome(s, 3, 11)
set_shape(by_name(s, 'Text 12'), '3.7  阶段性结论')
set_shape(by_name(s, '文本框 35'), '实验条件与可复现性')
for name, txt in [
    ('Text 16', '硬件：GPU云平台训练，单epoch由约138秒降至约2.3秒'),
    ('Text 19', '软件：Python 3.9＋PyTorch 2.0，随机种子固定'),
    ('Text 22', '数据：Tushare Pro日频数据，下载管线支持断点续传'),
]:
    set_shape(in_group(s, '组合 24', name), txt)
set_table(by_name(s, 'Table 0'), [
    ['维度', '阶段性结论'],
    ['模块有效性', '双向结构在容量匹配后于多数股票改善MSE/MAE；波动加权提升高波动股票DA'],
    ['整体优势', '四股中三股最高DA由本文配置取得；面板完整模型DA居四组首位'],
    ['严谨性', '除息口径修正、防泄漏切分、验证集模型选择，实验可复现'],
    ['局限性', '日频R²普遍为负；小样本结论有待全市场、多种子进一步验证'],
])

# ========== S19（4.1 问题复盘与应对策略） ==========
s = S[18]
chrome(s, 4, 12)
set_shape(by_name(s, 'Text 12'), '4.1  问题复盘与应对策略')
for name, txt in [
    ('Text 13', '已解决的问题'),
    ('Text 17', '标签口径：除息日虚假收益 → pre_close逐日修正并交叉校验'),
    ('Text 20', '小样本过拟合：低维度双向反劣 → 容量与正则匹配后稳定反超'),
    ('Text 23', '注意力坍缩：权重恒为均匀分布 → 注意力分支豁免权重衰减'),
    ('Text 24', '下一步重点'),
    ('Text 27', '数据扩展：8只银行股 → 沪深300全市场面板（下载管线已就绪）'),
    ('Text 29', '统计稳健：单种子 → 3—5个随机种子，报告均值与标准差'),
    ('Text 31', '基线扩充：补充LSTM/Informer/PatchTST/iTransformer等主流模型对比'),
]:
    set_shape(in_group(s, '组合 77', name), txt)

# ========== S20（5.1 下一阶段工作计划） ==========
s = S[19]
chrome(s, 5, 13)
set_shape(by_name(s, 'Text 12'), '5.1  下一阶段工作计划')
pic = by_name(s, '图片 20')
pic._element.getparent().remove(pic._element)
plan = [
    ('时间', '工作内容'),
    ('第1个月', '全市场数据扩展：沪深300全成分股下载、完整性校验与面板数据集构建'),
    ('第2个月', '全市场对比实验：补充LSTM/Informer/PatchTST/iTransformer等主流基线，增加5日预测期限'),
    ('第3个月', '统计稳健性验证：3—5个随机种子重复实验，报告均值与标准差，完善论文图表'),
    ('第4—5个月', '学位论文初稿撰写（绪论、相关理论、模型设计、实验与分析）'),
    ('第6个月', '论文修改定稿、材料归档与答辩准备'),
]
gt = s.shapes.add_table(6, 2, Inches(0.9), Inches(2.3), Inches(11.5), Inches(4.4)).table
gt.columns[0].width = Inches(2.2)
gt.columns[1].width = Inches(9.3)
for r, (a, b) in zip(gt.rows, plan):
    r.cells[0].text, r.cells[1].text = a, b
    for c in r.cells:
        for pgh in c.text_frame.paragraphs:
            for run in pgh.runs:
                run.font.size = Pt(14)
for run in gt.rows[0].cells[0].text_frame.paragraphs[0].runs + gt.rows[0].cells[1].text_frame.paragraphs[0].runs:
    run.font.bold = True

# ========== S21 结束页 ==========
set_shape(by_name(S[20], '文本框 11'), '2026年10月')

# ========== 重排页序：结果章节扩展为7页，问题/计划各1页 ==========
order = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 14, 15, 16, 11, 18, 17, 19, 20]
sldIdLst = prs.slides._sldIdLst
ids = list(sldIdLst)
for el in ids:
    sldIdLst.remove(el)
for i in order:
    sldIdLst.append(ids[i])

prs.save(DST)
print(f'已生成 {DST}，共{len(prs.slides)}页')
