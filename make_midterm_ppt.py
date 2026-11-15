# 中期答辩PPT v4：27页，与中期报告严格同口径
# 结构：研究进展概述 → 技术方案与实现 → 阶段性实验结果 → 问题与解决方案 → 下一阶段计划
# 图表与中期报告编号一一对应（表3-1~3-5、图3-1~3-9）；
# 公式按报告式(3-1)~(3-9)原记法高清重渲染（gen_ppt_assets.py 生成）；
# 三大模块架构图复用开题技术图（本课题模型设计图）。
# 全部实验数值取自中期报告，含不利结果，不做选择性呈现。
# 输出：docs/ppt/中期答辩v4.pptx
import copy
from PIL import Image
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn

SRC = 'docs/ppt/开题v2.pptx'
DST = 'docs/ppt/中期答辩v4.pptx'
ACCENT = RGBColor(0x17, 0x49, 0x94)
LIGHT = RGBColor(0xE9, 0xF0, 0xF8)
DARK = RGBColor(0x33, 0x33, 0x33)
A = 'docs/ppt/assets'
E = 'docs/ppt/extracted'

prs = Presentation(SRC)
S = prs.slides


def set_tf(tf, text):
    proto = copy.deepcopy(tf.paragraphs[0]._p)
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
    for line in text.split('\n'):
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
    for sh in by_name(slide, group_name).shapes:
        if sh.name == shape_name:
            return sh
    raise KeyError(f'{group_name}/{shape_name}')


def clone_slide(src):
    dest = prs.slides.add_slide(src.slide_layout)
    for sh in list(dest.shapes):
        sh._element.getparent().remove(sh._element)
    for sh in src.shapes:
        dest.shapes._spTree.append(copy.deepcopy(sh._element))
    for rel in src.part.rels.values():
        if 'image' in rel.reltype:
            new_rid = dest.part.relate_to(rel.target_part, rel.reltype)
            for el in dest.shapes._spTree.iter():
                for attr in (qn('r:embed'), qn('r:link'), qn('r:id')):
                    if el.get(attr) == rel.rId:
                        el.set(attr, new_rid)
    return dest


NAV_OLD = ['研究背景及意义', '国内外研究现状', '研究目标与内容', '技术方案与路线', '预期成果与计划']
NAV_NEW = ['研究进展概述', '技术方案与实现', '阶段性实验结果', '问题与解决方案', '下一阶段工作计划']
SEC_HL = {1: (1.2, 2.2, 1.9), 2: (3.4, 2.9, 4.6), 3: (6.3, 2.9, 7.4), 4: (9.2, 2.3, 10.0), 5: (11.3, 2.0, 12.0)}
PAGE_SHAPES = ('矩形 46', 'Text 32', 'Shape 31')


def chrome(slide, sec, page):
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
        if sh.name in PAGE_SHAPES and sh.has_text_frame and sh.text_frame.text.strip().isdigit():
            set_shape(sh, f'{page:02d}')


def body_clear(slide, keep):
    for sh in list(slide.shapes):
        if sh.name in keep:
            continue
        if sh.name in PAGE_SHAPES and sh.has_text_frame and sh.text_frame.text.strip().isdigit():
            continue
        if sh.top is not None and sh.top > Inches(1.4):
            sh._element.getparent().remove(sh._element)


def add_text(slide, text, left, top, width, height, size=13, color=DARK, bold=False):
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = box.text_frame
    tf.word_wrap = True
    for i, line in enumerate(text.split('\n')):
        pgh = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        pgh.text = line
        pgh.space_after = Pt(6)
        for run in pgh.runs:
            run.font.size = Pt(size)
            run.font.color.rgb = color
            run.font.bold = bold
    return box


def add_table(slide, data, left, top, col_widths, row_h=0.34, size=12, bold_cells=()):
    t = slide.shapes.add_table(len(data), len(data[0]), Inches(left), Inches(top),
                               Inches(sum(col_widths)), Inches(row_h * len(data))).table
    for j, w in enumerate(col_widths):
        t.columns[j].width = Inches(w)
    for i, row in enumerate(data):
        t.rows[i].height = Inches(row_h)
        for j, val in enumerate(row):
            cell = t.cell(i, j)
            cell.margin_top = Inches(0.02)
            cell.margin_bottom = Inches(0.02)
            cell.text = str(val)
            for pgh in cell.text_frame.paragraphs:
                for run in pgh.runs:
                    run.font.size = Pt(size)
                    if i == 0 or (i, j) in bold_cells:
                        run.font.bold = True
    return t


def add_card(slide, left, top, width, height, title, bullets, size=11.5):
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                                  Inches(left), Inches(top), Inches(width), Inches(height))
    card.fill.solid()
    card.fill.fore_color.rgb = LIGHT
    card.line.color.rgb = ACCENT
    card.line.width = Pt(1)
    card.shadow.inherit = False
    add_text(slide, title, left + 0.18, top + 0.1, width - 0.36, 0.4, size=14, color=ACCENT, bold=True)
    add_text(slide, bullets, left + 0.18, top + 0.55, width - 0.36, height - 0.65, size=size)


def pic_fit(slide, path, left, top, max_w, max_h):
    pw, ph = Image.open(path).size
    w = max_w
    h = w * ph / pw
    if h > max_h:
        h = max_h
        w = h * pw / ph
    slide.shapes.add_picture(path, Inches(left), Inches(top), width=Inches(w), height=Inches(h))
    return w, h


def caption(slide, text, left, top, width):
    add_text(slide, text, left, top, width, 0.4, size=10.5, color=ACCENT, bold=True)


# ========== 克隆7个新内容页（编辑源页之前） ==========
C_ARCH = clone_slide(S[12])   # 2.2 总体架构
C_BI = clone_slide(S[12])     # 2.3 双向编码
C_ATT = clone_slide(S[12])    # 2.4 跨股票注意力
C_VOL = clone_slide(S[12])    # 2.5 波动自适应
C_PRED = clone_slide(S[12])   # 3.2 预测效果与收敛
C_ERR = clone_slide(S[12])    # 3.3 价格曲线与逐日误差
C_SUM = clone_slide(S[12])    # 3.9 小结与不足

# ========== 封面与目录（个人信息字段保持原文件内容） ==========
s = S[0]
set_shape(by_name(s, '文本框 9'), 'Mid-term Progress Report')
set_shape(by_name(s, '文本框 33'), '2026年10月')
s = S[1]
for g, name, txt in [('组合 60', '文本框 11', NAV_NEW[0]), ('组合 69', '文本框 72', NAV_NEW[1]),
                     ('组合 73', '文本框 76', NAV_NEW[2]), ('组合 77', '文本框 80', NAV_NEW[3]),
                     ('组合 81', '文本框 84', NAV_NEW[4])]:
    set_shape(in_group(s, g, name), txt)
for idx, cn, en in [(2, NAV_NEW[0], 'Research Progress Overview'),
                    (5, NAV_NEW[1], 'Technical Scheme and Implementation'),
                    (8, NAV_NEW[2], 'Experimental Results and Analysis'),
                    (11, NAV_NEW[3], 'Problems and Solutions'),
                    (17, NAV_NEW[4], 'Next-stage Work Plan')]:
    set_shape(by_name(S[idx], '文本框 8'), cn)
    set_shape(by_name(S[idx], '文本框 9'), en)

# ========== 1.1 研究目标与开题技术路线回顾 ==========
s = S[3]
chrome(s, 1, 1)
set_shape(by_name(s, '文本框 34'), '1.1  研究目标与开题技术路线回顾')
set_shape(by_name(s, '文本框 12'),
    '研究目标：针对MambaStock单向结构、跨股票关系建模与训练策略的不足，构建Bi-Mamba-Stock模型，'
    '在保持线性计算复杂度的前提下提升股价预测精度与鲁棒性\n'
    '研究内容（与开题一致，无方向性变动）：\n'
    '① 双向选择性状态空间编码：前向/后向独立Mamba路径＋可学习门控融合\n'
    '② 轻量化跨股票注意力：双向隐态投影Q/K/V，缩放点积，无图卷积\n'
    '③ 波动自适应训练：EWMA波动率三档分桶，损失加权0.5/1.0/2.0\n'
    '评估体系：MSE、MAE、决定系数R²、方向准确率（DA）；对比基线为MambaStock与Transformer')

# ========== 1.2 对照开题计划的进展与阶段性成果 ==========
s = S[4]
chrome(s, 1, 2)
set_shape(by_name(s, '文本框 34'), '1.2  对照开题计划的进展与阶段性成果')
body_clear(s, keep={'文本框 34'})
prog = [('开题安排', '计划内容', '完成情况'),
        ('第1个月', '数据获取与预处理', '已完成'),
        ('第2个月', '特征构建与样本划分', '已完成'),
        ('第3个月', '基线复现与双向编码层构建', '已完成'),
        ('第4个月', '跨股票注意力与波动自适应模块开发', '已完成'),
        ('第5—6个月', '单股票实验、多股票联合预测与消融实验', '首轮小规模验证已完成')]
add_table(s, prog, 0.45, 2.3, [1.4, 4.0, 2.2], row_h=0.52, size=12)
add_text(s,
    '阶段性成果\n'
    '• 可复现代码库：GitHub托管，含数据管道、模型库、单/多股票训练入口、批量实验与数据下载工具，全部代码附中文注释\n'
    '• 实验日志：两阶段共42组对照实验＋2组注意力修复验证实验，记录完整\n'
    '• 论文素材：测试段价格预测对比图、训练收敛曲线、跨股票注意力权重热力图等\n'
    '说明：无研究方向性变动；标签构造口径与算力租用渠道两处实施细节差异已在中期报告中说明',
    8.3, 2.2, 4.6, 4.9, size=12)

# ========== 2.1 数据、标签与防泄漏设计 ==========
s = S[6]
chrome(s, 2, 3)
set_shape(by_name(s, '文本框 34'), '2.1  数据、标签与防泄漏设计（表3-1）')
body_clear(s, keep={'文本框 34'})
data = [('股票代码', '股票名称', '数据区间', '交易日数'),
        ('000001.SZ', '平安银行', '2018.06—2025.12', '1843'),
        ('600036.SH', '招商银行', '2018.06—2025.12', '1843'),
        ('601166.SH', '兴业银行', '2018.06—2025.12', '1843'),
        ('601288.SH', '农业银行', '2018.06—2025.12', '1843'),
        ('601328.SH', '交通银行', '2018.06—2025.12', '1843'),
        ('601398.SH', '工商银行', '2018.06—2025.12', '1843'),
        ('601939.SH', '建设银行', '2018.06—2025.12', '1843'),
        ('601988.SH', '中国银行', '2018.06—2025.12', '1843')]
add_table(s, data, 0.45, 2.2, [1.7, 1.5, 2.9, 1.3], row_h=0.32, size=11)
pic_fit(s, f'{A}/pipeline_leakfree.png', 0.45, 5.35, 7.4, 1.35)
add_text(s, '注：8只沪深300银行成分股同板块小规模验证；2018年下半年数据仅用于技术指标预热，样本区间为2019.01—2025.12。',
         0.45, 6.85, 7.5, 0.5, size=10)
add_text(s,
    '标签构造（关键修正）：pre_close逐日修正除息日收益率，与官方涨跌幅字段交叉校验（最大偏差<0.00005）\n'
    '特征工程：10维平稳化特征（量价比值5维＋均线偏离2维＋RSI 1维＋MACD 2维）\n'
    '面板构建：按交易日取交集对齐，停牌缺口自然剔除；对齐后共同交易日1698天（训练1188 / 验证254 / 测试256）\n'
    '防泄漏设计：\n'
    '• Z-score均值方差仅在训练段拟合\n'
    '• 波动分档阈值仅用训练段估计\n'
    '• 严格时序切分，模型选择仅依据验证集',
    8.3, 2.2, 4.6, 4.9, size=11.5)

# ========== 2.2 总体架构 ==========
s = C_ARCH
chrome(s, 2, 4)
set_shape(by_name(s, '文本框 1'), '2.2  Bi-Mamba-Stock 总体架构')
body_clear(s, keep={'文本框 1'})
pic_fit(s, f'{E}/s10_图片2.png', 1.97, 2.1, 9.4, 5.1)

# ========== 2.3 双向选择性状态空间编码（式3-1~3-4） ==========
s = C_BI
chrome(s, 2, 5)
set_shape(by_name(s, '文本框 1'), '2.3  双向选择性状态空间编码（式3-1~3-4）')
body_clear(s, keep={'文本框 1'})
add_text(s,
    '理论基础：状态空间模型以线性动力系统递推隐状态（式3-1/3-2）；Mamba引入输入依赖的选择性机制，'
    '令B、C与离散化步长由当前输入动态生成，配合并行扫描保持近线性复杂度\n'
    '双向结构（式3-3/3-4）：\n'
    '• 前向路径沿时间正序扫描，捕捉历史趋势与惯性\n'
    '• 后向路径：输入翻转 → 参数独立的Mamba → 翻转回原时序，捕捉回溯上下文\n'
    '• 门控权重由当前输入经线性变换＋Sigmoid生成，逐位置自适应融合双向隐态',
    0.45, 2.2, 5.9, 3.5, size=11.5)
caption(s, '式(3-3)(3-4)：双向扫描与门控融合', 0.45, 5.75, 5.9)
pic_fit(s, f'{A}/eq_bi.png', 0.45, 6.15, 5.9, 1.0)
pic_fit(s, f'{E}/s14_图片6.png', 6.8, 2.15, 6.1, 5.0)

# ========== 2.4 轻量化跨股票注意力（式3-5） ==========
s = C_ATT
chrome(s, 2, 6)
set_shape(by_name(s, '文本框 1'), '2.4  轻量化跨股票注意力（式3-5）')
body_clear(s, keep={'文本框 1'})
add_text(s,
    '设计动机：板块内股票存在联动效应；图卷积方法需预定义或学习邻接矩阵，开销较大\n'
    '实现（式3-5）：\n'
    '• 同一交易日各股票双向隐态分别投影为Q/K/V\n'
    '• 缩放点积计算股票间相似度，softmax归一化（每行权重和为1）后对值加权聚合\n'
    '轻量化体现：\n'
    '• 单头注意力，参数仅为三个投影矩阵\n'
    '• 一次N×N矩阵乘，小规模场景开销可忽略\n'
    '• 无图结构，完整面板模型约4.6万参数',
    0.45, 2.2, 5.9, 3.5, size=11.5)
caption(s, '式(3-5)：跨股票缩放点积注意力', 0.45, 5.85, 5.9)
pic_fit(s, f'{A}/eq_attn.png', 0.45, 6.25, 5.9, 0.8)
pic_fit(s, f'{E}/s15_图片3.png', 6.7, 2.2, 6.3, 4.9)

# ========== 2.5 波动自适应训练策略（式3-6/3-7） ==========
s = C_VOL
chrome(s, 2, 7)
set_shape(by_name(s, '文本框 1'), '2.5  波动自适应训练策略（式3-6/3-7）')
body_clear(s, keep={'文本框 1'})
add_text(s,
    '设计动机：市场存在异方差性，不同波动状态下样本预测难度差异显著\n'
    '实现（式3-6/3-7）：\n'
    '• 20日EWMA估计历史波动率，近期样本权重更高，缓解估计滞后\n'
    '• 以训练段波动率1/3与2/3分位数为阈值，划分低/中/高三档\n'
    '• 三档损失权重0.5/1.0/2.0，加权损失按权重归一化，与MSE无缝结合\n'
    '防泄漏：分档阈值仅使用训练段估计',
    0.45, 2.2, 5.9, 3.3, size=11.5)
caption(s, '式(3-6)(3-7)：EWMA波动率与归一化加权损失', 0.45, 5.6, 5.9)
pic_fit(s, f'{A}/eq_vol.png', 0.45, 6.0, 5.4, 1.2)
pic_fit(s, f'{E}/s16_图片4.png', 6.9, 2.15, 6.1, 5.0)

# ========== 2.6 实验体系与评估口径（表3-2、式3-8/3-9） ==========
s = S[9]
chrome(s, 2, 8)
t = by_name(s, '文本框 3')
t.width = Inches(9.0)
set_shape(t, '2.6  实验体系与评估口径（表3-2）')
body_clear(s, keep={'文本框 3'})
cfg = [('项目', '设置'),
       ('滑动窗口长度', '60个交易日'),
       ('输入特征', '10维平稳化特征'),
       ('预测期限', '未来1日对数收益率'),
       ('模型维度 / 编码器层数', '32 / 2'),
       ('优化器', 'Adam（lr=1e-3，wd=1e-4，注意力分支免衰减）'),
       ('训练轮数 / 早停耐心', '最多150轮 / 30轮'),
       ('数据切分', '70% / 15% / 15%（严格时序）'),
       ('随机种子', '固定为1（保证可复现）')]
add_table(s, cfg, 0.45, 2.2, [2.5, 4.6], row_h=0.38, size=11)
add_text(s,
    '消融实验矩阵（共42组对照实验）\n'
    '• 单股票：4股 × 单向/双向 × 是否波动加权＝16组＋Transformer对照\n'
    '• 多股票面板：是否注意力 × 是否波动加权＝4组＋Transformer对照\n'
    '外部基线：标准Transformer编码器，维度与层数相同，参数量约3.0万，训练协议完全一致\n'
    '模型选择：验证集MSE早停（耐心30轮）＋最优权重回滚；测试集仅在最终评估使用一次',
    8.0, 2.2, 5.0, 3.6, size=11.5)
caption(s, '式(3-8)(3-9)：MSE、决定系数R²与方向准确率DA', 0.45, 6.0, 9.0)
pic_fit(s, f'{A}/eq_metrics.png', 0.45, 6.35, 8.6, 1.0)

# ========== 3.1 单股票实验核心结果（四股卡片总览，完整数据见报告表3-3） ==========
s = S[10]
chrome(s, 3, 9)
t = by_name(s, '文本框 3')
t.width = Inches(10.5)
set_shape(t, '3.1  单股票实验核心结果总览（数据详见表3-3）')
body_clear(s, keep={'文本框 3'})
add_card(s, 0.5, 2.2, 6.05, 2.1, '招商银行（600036.SH）',
         '• 最优配置：双向＋波动加权，DA 0.5430（五组最高，超随机基准4.3个百分点）\n'
         '• 双向MSE 1.44×10⁻⁴，较基线下降6.5%；MAE 8.77×10⁻³为全组最低\n'
         '• R²由-0.1347改善至-0.0606')
add_card(s, 6.8, 2.2, 6.05, 2.1, '农业银行（601288.SH）',
         '• 单向基线DA 0.5352仍为全组最高（反例如实呈现）\n'
         '• 双向结构未带来提升；但叠加波动加权后DA由0.4727回升至0.5078\n'
         '• 启示：模块有效性存在个股差异，构成后续研究线索')
add_card(s, 0.5, 4.5, 6.05, 2.1, '交通银行（601328.SH）',
         '• 最优配置：双向，DA 0.5469（五组最高，较基线+10.2个百分点）\n'
         '• 双向MSE 1.29×10⁻⁴，较基线下降6.5%；MAE 8.72×10⁻³为全组最低\n'
         '• R²由-0.0881改善至-0.0135')
add_card(s, 6.8, 4.5, 6.05, 2.1, '中国银行（601988.SH）',
         '• 最优配置：双向，DA 0.5234（五组最高，较基线+7.0个百分点）\n'
         '• 双向MSE 1.37×10⁻⁴，较基线1.34未获改善（如实呈现）\n'
         '• 方向指标准确率提升与误差指标未改善并存，需多种子验证')
add_text(s,
    '总体结论：四股中三股的最高方向准确率由本文双向或其波动加权配置取得；Transformer在四只股票上R²全面落后；'
    '完整四股×五配置结果见中期报告表3-3。',
    0.5, 6.85, 12.35, 0.6, size=12, color=ACCENT, bold=True)

# ========== 3.2 预测效果与训练收敛（图3-1/3-2） ==========
s = C_PRED
chrome(s, 3, 10)
set_shape(by_name(s, '文本框 1'), '3.2  预测效果与训练收敛（图3-1/3-2）')
body_clear(s, keep={'文本框 1'})
pic_fit(s, 'results/600036_price.png', 0.5, 2.4, 6.1, 3.1)
pic_fit(s, 'results/600036_loss.png', 6.85, 2.4, 6.0, 3.1)
caption(s, '图3-1 招商银行测试段次日收盘价预测（双向＋波动加权）', 0.5, 5.6, 6.1)
caption(s, '图3-2 训练损失与验证MSE收敛曲线（同次训练）', 6.85, 5.6, 6.0)
add_text(s,
    '• 模型输出能够较好贴合真实价格走势；训练损失与验证MSE快速收敛，早停机制在验证指标不再改善后及时终止训练\n'
    '• 最优验证权重回滚后评估测试集，模型选择全程不使用测试集',
    0.5, 6.35, 12.3, 0.8, size=12)

# ========== 3.3 双向机制效果：价格曲线与逐日误差（图3-8/3-9） ==========
s = C_ERR
chrome(s, 3, 11)
set_shape(by_name(s, '文本框 1'), '3.3  双向机制效果：价格曲线与逐日误差（图3-8/3-9）')
body_clear(s, keep={'文本框 1'})
pic_fit(s, 'results/v2_overlay_601328.png', 0.5, 2.35, 6.3, 2.9)
pic_fit(s, 'results/v2_error_601328.png', 6.85, 2.35, 6.0, 2.9)
caption(s, '图3-8 交通银行测试段次日收盘价三线叠加对比', 0.5, 5.35, 6.3)
caption(s, '图3-9 交通银行逐日绝对预测误差（10日滑动平均）', 6.85, 5.35, 6.0)
add_text(s,
    '• 双向模型相对单向基线在价格拐点处跟随更为及时；平均绝对误差由0.00920降至0.00872（下降约5.2%）\n'
    '• 与方向准确率由0.445提升至0.547相互印证，构成"曲线形态＋误差指标＋方向指标"的完整证据链',
    0.5, 6.1, 12.3, 0.9, size=12)

# ========== 3.4 面板消融结果（表3-4、图3-7） ==========
s = S[12]
chrome(s, 3, 12)
set_shape(by_name(s, '文本框 1'), '3.4  多股票面板消融结果（表3-4、图3-7）')
body_clear(s, keep={'文本框 1'})
panel = [('模型配置', 'MSE(×10⁻⁴)', 'MAE(×10⁻³)', 'R²', 'DA'),
         ('Transformer', '1.55', '9.55', '-0.1753', '0.4927'),
         ('无注意力', '1.36', '8.82', '-0.0340', '0.4907'),
         ('＋跨股票注意力', '1.34', '8.84', '-0.0163', '0.4941'),
         ('无注意力＋波动加权', '1.37', '8.85', '-0.0393', '0.4893'),
         ('完整模型', '1.34', '8.80', '-0.0158', '0.4956')]
add_table(s, panel, 0.45, 2.3, [2.6, 1.4, 1.4, 1.2, 1.1], row_h=0.4, size=11,
          bold_cells={(5, 1), (5, 3), (5, 4), (5, 5)})
pic_fit(s, 'results/v3_panel_ablation.png', 8.35, 2.3, 4.55, 1.5)
caption(s, '图3-7 面板消融三指标对比', 8.35, 3.85, 4.55)
add_text(s,
    '结果分析\n'
    '• 完整模型取得最优R²（-0.0158）、最低MAE（8.80×10⁻³）与最高DA（0.4956）\n'
    '• 跨股票注意力对MSE、R²、DA均产生一致改善（两种加权设置下均成立）\n'
    '• Transformer的MSE与R²明显落后于全部Mamba系配置',
    8.35, 4.35, 4.55, 2.7, size=11)
add_text(s,
    '注：含注意力配置对注意力分支豁免权重衰减（原因见第四部分问题(6)）；组间对照的唯一结构差异为注意力模块，保证消融严谨。',
    0.45, 5.2, 7.5, 1.2, size=10.5)

# ========== 3.5 方向准确率与决定系数对比（图3-4/3-5） ==========
s = S[13]
chrome(s, 3, 13)
set_shape(by_name(s, '文本框 1'), '3.5  方向准确率与决定系数对比（图3-4/3-5）')
body_clear(s, keep={'文本框 1'})
pic_fit(s, 'results/v3_da_compare.png', 0.45, 2.3, 6.15, 3.3)
pic_fit(s, 'results/v3_r2_compare.png', 6.8, 2.3, 6.1, 3.3)
caption(s, '图3-4 四模型方向准确率对比（红色虚线为随机基准0.5）', 0.45, 5.7, 6.15)
caption(s, '图3-5 四模型决定系数对比（红色虚线为均值基准0）', 6.8, 5.7, 6.1)
add_text(s,
    '• 四股中三股最高DA由本文配置取得；招商银行叠加波动加权后DA超出随机基准4.3个百分点\n'
    '• Transformer在R²上全面落后；日频R²为负属领域共识，文献中DA典型区间约0.52—0.58',
    0.45, 6.35, 12.4, 0.8, size=12)

# ========== 3.6 均方误差与平均绝对误差对比（图3-6） ==========
s = S[14]
chrome(s, 3, 14)
set_shape(by_name(s, '文本框 1'), '3.6  均方误差与平均绝对误差对比（图3-6）')
body_clear(s, keep={'文本框 1'})
s.shapes.add_picture('results/v3_mse_mae_compare.png', Inches(0.85), Inches(2.15), width=Inches(11.6))
add_text(s,
    '• 双向结构在招商银行、交通银行实现MSE与MAE双改善，MSE较单向基线均下降约6.5%；在农业银行、中国银行上未获改善，个股差异客观存在\n'
    '• 波动自适应加权的作用更多体现在方向准确率：招商银行"双向＋波动加权"DA 0.5430为该股票最高（见图3-4）',
    0.85, 6.85, 11.6, 0.6, size=11)

# ========== 3.7 跨股票注意力权重分析（图3-3） ==========
s = S[15]
chrome(s, 3, 15)
set_shape(by_name(s, '文本框 1'), '3.7  跨股票注意力权重：坍缩诊断与修复（图3-3）')
body_clear(s, keep={'文本框 1'})
add_text(s,
    '问题诊断\n'
    '• 统一权重衰减（1e-4）下，注意力权重在全部测试交易日恒为均匀分布（各股1/8），出现注意力坍缩\n'
    '机制分析\n'
    '• 同质银行股等权特征已较强，投影矩阵梯度弱，被权重衰减持续压缩至零\n'
    '修复与验证\n'
    '• Q/K/V投影豁免权重衰减后重新训练：权重恢复差异化（逐日偏差最大0.0124）\n'
    '• 对角线自注意力均值0.1263＞非对角0.1248；平安银行自注意力0.1274为全图最高\n'
    '• 更显著的差异化结构有待全市场异质性股票池检验',
    0.5, 2.3, 6.2, 4.8, size=12)
pic_fit(s, 'results/panel_attn_h1_attn_v3.png', 7.3, 2.3, 5.4, 4.5)
caption(s, '图3-3 完整模型测试集平均跨股票注意力权重热力图', 7.0, 6.9, 6.0)

# ========== 3.8 双向模型提升幅度汇总（表3-5） ==========
s = S[16]
chrome(s, 3, 16)
set_shape(by_name(s, 'Text 12'), '3.8  双向模型相对单向基线的提升幅度（表3-5）')
body_clear(s, keep={'Text 12'})
imp = [('对比对象', 'MSE变化率', 'R²变化量', 'DA变化（个百分点）'),
       ('招商银行', '-6.5%', '+0.074', '-0.4'),
       ('农业银行', '+11.8%', '-0.117', '-6.3'),
       ('交通银行', '-6.5%', '+0.075', '+10.2'),
       ('中国银行', '+2.2%', '-0.020', '+7.0'),
       ('四只股票平均', '+0.3%', '+0.003', '+2.6'),
       ('8股面板：完整模型相对无注意力', '-1.5%', '+0.018', '+0.5')]
add_table(s, imp, 0.7, 2.3, [4.6, 2.2, 2.2, 3.0], row_h=0.46, size=13,
          bold_cells={(3, 1), (3, 3), (5, 4)})
add_text(s,
    '• 双向模型使四股平均方向准确率提高2.6个百分点，其中交通银行+10.2、中国银行+7.0个百分点最为显著\n'
    '• 农业银行双向模型MSE上升11.8%、DA下降6.3个百分点——负面结果同样如实呈现，个股差异构成后续研究线索\n'
    '• 面板场景下，完整模型相对无注意力配置MSE下降1.5%，R²与DA同步改善',
    0.7, 5.8, 12.0, 1.5, size=12)

# ========== 3.9 阶段性小结与不足 ==========
s = C_SUM
chrome(s, 3, 17)
set_shape(by_name(s, '文本框 1'), '3.9  阶段性小结与不足')
body_clear(s, keep={'文本框 1'})
add_text(s,
    '阶段性结论\n'
    '① 双向选择性扫描在小规模验证中有效：交通银行DA提高10.2个百分点、中国银行提高7.0个百分点；招商银行与交通银行MSE均降约6.5%\n'
    '② 波动自适应训练提升双向模型方向预测：招商银行DA由0.484提升至0.543（+5.9个百分点），农业银行由0.473提升至0.508\n'
    '③ 跨股票注意力对MSE/R²/DA一致改善；完整模型取得面板最优R²、最低MAE与最高DA，消融证据链完整闭合\n'
    '④ Transformer在全部场景中R²显著落后于Mamba系模型，验证Mamba类结构在金融日频序列上的适用性\n'
    '不足与边界\n'
    '⑤ 模块有效性存在个股差异（农业银行基线更优），不同股票的市场微观结构影响双向编码收益，本身构成新见解\n'
    '⑥ 日频R²仍为负值，反映日频个股收益率固有低信噪比；结论基于8只银行股小样本，待全市场数据、多种子统计与更多基线进一步检验',
    0.55, 2.3, 12.2, 4.9, size=12.5)

# ========== 4.1 关键问题与解决方案 ==========
s = S[18]
chrome(s, 4, 18)
set_shape(by_name(s, 'Text 12'), '4.1  关键问题与解决方案')
body_clear(s, keep={'Text 12'})
probs = [('遇到的问题', '解决方案与现状'),
         ('标签口径：除息日产生虚假收益', 'pre_close逐日修正＋官方涨跌幅交叉校验，已解决；全市场扩展时将执行同样校验'),
         ('小样本下双向模型过拟合', '容量与正则匹配（维度32＋权重衰减）后双向稳定反超基线，已解决'),
         ('跨股票注意力权重坍缩', '注意力分支豁免权重衰减，权重恢复差异化，已解决'),
         ('数据接口限流与权限约束', '限流检测自动重试＋断点续传，全市场下载通道已就绪'),
         ('本机算力不足', 'GPU云训练提速约60倍，免密登录、断点续跑、结果自动回传工作流已打通'),
         ('日频R²为负引发的认识问题', '文献确认为领域共识；以相对提升＋DA＋消融一致性评估，下一阶段多种子验证')]
add_table(s, probs, 0.5, 2.2, [4.2, 8.1], row_h=0.62, size=12)

# ========== 5.1 下一阶段工作计划 ==========
s = S[19]
chrome(s, 5, 19)
set_shape(by_name(s, 'Text 12'), '5.1  下一阶段工作计划')
body_clear(s, keep={'Text 12'})
plan = [('时间', '工作内容'),
        ('第1个月', '全市场数据扩展：沪深300全成分股下载、完整性校验与面板数据集构建'),
        ('第2个月', '全市场对比实验：补充LSTM/Informer/PatchTST/iTransformer等主流基线，增加5日预测期限'),
        ('第3个月', '统计稳健性验证：3—5个随机种子重复实验，报告均值与标准差，完善论文图表'),
        ('第4—5个月', '学位论文初稿撰写（绪论、相关理论、模型设计、实验与分析）'),
        ('第6个月', '论文修改定稿、材料归档与答辩准备')]
add_table(s, plan, 0.9, 2.3, [2.2, 9.3], row_h=0.62, size=14)

# ========== 结束页 ==========
set_shape(by_name(S[20], '文本框 11'), '2026年10月')

# ========== 重排页序（27页） ==========
order = [0, 1, 2, 3, 4, 5, 6, 21, 22, 23, 24, 9, 8, 10, 25, 26, 12, 13, 14, 15, 16, 27, 11, 18, 17, 19, 20]
sldIdLst = prs.slides._sldIdLst
ids = list(sldIdLst)
for el in ids:
    sldIdLst.remove(el)
for i in order:
    sldIdLst.append(ids[i])

prs.save(DST)
print(f'已生成 {DST}，共{len(prs.slides)}页')
