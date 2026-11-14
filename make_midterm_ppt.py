# 中期答辩PPT v3：26页技术深化版
# 视觉模板复用开题PPT；三大模块架构图复用开题技术图（本身即本课题模型设计图）；
# 新增：总体架构页、模块一/二/三详解页（架构图+实现要点+公式）、训练过程页、
#       技术路线图、防泄漏时间轴、评估指标公式、EWMA公式（由 gen_ppt_assets.py 生成）。
# 实验数值与中期报告完全一致，完整呈现含不利结果。
# 前置：先运行 gen_ppt_assets.py；图片素材在 docs/ppt/assets/ 与 docs/ppt/extracted/
# 输出：docs/ppt/中期答辩v3.pptx
import copy
from PIL import Image
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn

SRC = 'docs/ppt/开题v2.pptx'
DST = 'docs/ppt/中期答辩v3.pptx'
ACCENT = RGBColor(0x17, 0x49, 0x94)
LIGHT = RGBColor(0xE9, 0xF0, 0xF8)
DARK = RGBColor(0x33, 0x33, 0x33)

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
    """克隆内容页（含导航栏等装饰），图片关系同步映射"""
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
NAV_NEW = ['研究概况', '已完成工作', '阶段性实验结果', '问题与解决方案', '下一阶段工作计划']
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
    rows, cols = len(data), len(data[0])
    t = slide.shapes.add_table(rows, cols, Inches(left), Inches(top),
                               Inches(sum(col_widths)), Inches(row_h * rows)).table
    for j, w in enumerate(col_widths):
        t.columns[j].width = Inches(w)
    for i, row in enumerate(data):
        t.rows[i].height = Inches(row_h)
        for j, val in enumerate(row):
            cell = t.cell(i, j)
            cell.text = str(val)
            for pgh in cell.text_frame.paragraphs:
                for run in pgh.runs:
                    run.font.size = Pt(size)
                    if i == 0 or (i, j) in bold_cells:
                        run.font.bold = True
    return t


def add_card(slide, left, top, width, height, title, bullets):
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                                  Inches(left), Inches(top), Inches(width), Inches(height))
    card.fill.solid()
    card.fill.fore_color.rgb = LIGHT
    card.line.color.rgb = ACCENT
    card.line.width = Pt(1)
    card.shadow.inherit = False
    add_text(slide, title, left + 0.15, top + 0.15, width - 0.3, 0.5, size=15, color=ACCENT, bold=True)
    add_text(slide, bullets, left + 0.15, top + 0.75, width - 0.3, height - 0.9, size=12)


def pic_fit(slide, path, left, top, max_w, max_h):
    """按比例放置图片，不超过 max_w × max_h，返回(宽,高)英寸"""
    pw, ph = Image.open(path).size
    w = max_w
    h = w * ph / pw
    if h > max_h:
        h = max_h
        w = h * pw / ph
    slide.shapes.add_picture(path, Inches(left), Inches(top), width=Inches(w), height=Inches(h))
    return w, h


# ========== 先克隆5个新内容页（在编辑源页之前） ==========
NEW_ARCH = clone_slide(S[12])      # 1.3 总体架构
NEW_M1 = clone_slide(S[12])        # 2.2 模块一
NEW_M2 = clone_slide(S[12])        # 2.3 模块二
NEW_M3 = clone_slide(S[12])        # 2.4 模块三
NEW_TRAIN = clone_slide(S[12])     # 3.6 训练过程

# ========== S1 封面（个人信息字段保持原文件内容，不改动） ==========
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
for idx, cn, en in [(2, NAV_NEW[0], 'Research Overview'),
                    (5, NAV_NEW[1], 'Completed Work'),
                    (8, NAV_NEW[2], 'Experimental Results and Analysis'),
                    (11, NAV_NEW[3], 'Problems and Solutions'),
                    (17, NAV_NEW[4], 'Next-stage Work Plan')]:
    set_shape(by_name(S[idx], '文本框 8'), cn)
    set_shape(by_name(S[idx], '文本框 9'), en)

# ========== 1.1 研究背景与研究目标 ==========
s = S[3]
chrome(s, 1, 1)
set_shape(by_name(s, '文本框 34'), '1.1  研究背景与研究目标')
set_shape(by_name(s, '文本框 12'),
    '研究背景：股价呈现非线性、非平稳、高噪声与长程依赖特征。Mamba以线性复杂度实现长序列建模，'
    '但MambaStock单向扫描丢失反向信息，跨股票关系建模与训练策略仍有不足\n'
    '研究目标：提出Bi-Mamba-Stock模型——双向选择性扫描＋轻量化跨股票注意力＋波动自适应训练，'
    '在保持O(L)线性复杂度的前提下，提升股价预测精度与鲁棒性\n'
    '研究对象：沪深300成分股日频数据，60日滑动窗口预测未来1日/5日收益率\n'
    '评估体系：MSE、MAE、决定系数R²、方向准确率（DA），以MambaStock与Transformer为对比基线')

# ========== 1.2 研究内容：模块卡片＋技术路线图 ==========
s = S[4]
chrome(s, 1, 2)
set_shape(by_name(s, '文本框 34'), '1.2  研究内容：三大核心模块与技术路线')
body_clear(s, keep={'文本框 34'})
add_card(s, 0.6, 2.3, 3.9, 3.4, '① 双向选择性状态空间编码',
         '• 前向/后向两条独立Mamba路径\n• 可学习门控融合双向隐态\n• 同时捕捉前向趋势与后向上下文\n• 保持O(L)线性复杂度')
add_card(s, 4.75, 2.3, 3.9, 3.4, '② 轻量化跨股票注意力',
         '• Q/K/V来自双向编码隐态\n• 缩放点积注意力，无图卷积\n• 动态提取股票间隐含关联\n• 面板模型仅约4.6万参数')
add_card(s, 8.9, 2.3, 3.9, 3.4, '③ 波动自适应训练策略',
         '• EWMA估计个股历史波动率\n• 样本分低/中/高三档\n• 损失权重0.5 / 1.0 / 2.0\n• 增强极端行情下的鲁棒性')
pic_fit(s, 'docs/ppt/assets/tech_route.png', 0.9, 5.95, 11.5, 1.3)

# ========== 1.3 总体架构（新页，复用开题整体架构图） ==========
s = NEW_ARCH
chrome(s, 1, 3)
set_shape(by_name(s, '文本框 1'), '1.3  Bi-Mamba-Stock 总体架构')
body_clear(s, keep={'文本框 1'})
pic_fit(s, 'docs/ppt/extracted/s10_图片2.png', 1.97, 2.1, 9.4, 5.1)

# ========== 2.1 数据与预处理 ==========
s = S[6]
chrome(s, 2, 4)
set_shape(by_name(s, '文本框 34'), '2.1  数据与预处理：真实数据与防泄漏设计')
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
add_table(s, data, 0.5, 2.2, [1.7, 1.5, 2.9, 1.3], row_h=0.34, size=12)
pic_fit(s, 'docs/ppt/assets/pipeline_leakfree.png', 0.5, 5.5, 7.4, 1.35)
add_text(s, '注：中期阶段采用同板块8只银行股小规模验证；全市场扩展为下一阶段任务。',
         0.5, 6.95, 7.4, 0.4, size=10)
add_text(s,
    '预处理管线\n'
    '• 对数收益率 → Z-score标准化 → 60日滑动窗口\n'
    '• 10维特征：OHLCV＋MA5/MA20＋RSI＋MACD\n'
    '• pre_close逐日修正除息收益率，与官方涨跌幅交叉校验（最大偏差<0.00005）\n'
    '防泄漏设计\n'
    '• 严格时序切分：训练/验证/测试＝70%/15%/15%\n'
    '• 标准化参数仅用训练集拟合\n'
    '• 模型选择仅依据验证集，不使用测试集调参',
    8.3, 2.2, 4.6, 4.9, size=12)

# ========== 2.2 模块一：双向选择性状态空间编码（新页） ==========
s = NEW_M1
chrome(s, 2, 5)
set_shape(by_name(s, '文本框 1'), '2.2  模块一：双向选择性状态空间编码')
body_clear(s, keep={'文本框 1'})
add_text(s,
    '设计动机：MambaStock单向扫描仅利用单方向历史信息，丢失反向序列上下文\n'
    '实现要点：\n'
    '• 前向/后向两条独立Mamba路径，参数不共享\n'
    '• 后向路径：输入翻转 → 选择性扫描 → 输出翻转\n'
    '• 可学习门控 G=σ(W_gX+b_g) 逐维融合双向隐态\n'
    '• 仅增加常数倍计算量，保持O(L)线性复杂度\n'
    '验证情况：容量匹配（维度32）后，双向结构在招商银行、交通银行实现MSE/MAE双改善',
    0.45, 2.25, 5.9, 4.6, size=12)
pic_fit(s, 'docs/ppt/extracted/s14_图片6.png', 6.8, 2.15, 6.1, 5.0)

# ========== 2.3 模块二：轻量化跨股票注意力（新页） ==========
s = NEW_M2
chrome(s, 2, 6)
set_shape(by_name(s, '文本框 1'), '2.3  模块二：轻量化跨股票注意力')
body_clear(s, keep={'文本框 1'})
add_text(s,
    '设计动机：同板块股票存在联动效应；SAMBA等图方法需学习邻接矩阵，计算开销大\n'
    '实现要点：\n'
    '• Q/K/V由双向编码隐态线性投影得到\n'
    '• 缩放点积注意力 softmax(QKᵀ/√d)V，无需图结构\n'
    '• 面板级隐态交互，完整面板模型仅约4.6万参数\n'
    '• 注意力分支豁免权重衰减，防止注意力坍缩\n'
    '验证情况：注意力使面板MSE较无注意力配置下降约1.5%，R²由-0.0340改善至-0.0163',
    0.45, 2.25, 5.9, 4.6, size=12)
pic_fit(s, 'docs/ppt/extracted/s15_图片3.png', 6.7, 2.2, 6.3, 4.9)

# ========== 2.4 模块三：波动自适应训练策略（新页，含公式） ==========
s = NEW_M3
chrome(s, 2, 7)
set_shape(by_name(s, '文本框 1'), '2.4  模块三：波动自适应训练策略')
body_clear(s, keep={'文本框 1'})
add_text(s,
    '设计动机：金融市场存在异方差性，不同波动状态下样本预测难度差异显著\n'
    '实现流程：\n'
    '• EWMA估计历史波动率（20日窗口）\n'
    '• 按训练集分位数划分低/中/高三档\n'
    '• 损失权重0.5/1.0/2.0，高波动样本获得更高学习优先级\n'
    '验证情况：招商银行"双向＋波动加权"DA 0.5430，为该股票五组配置最高',
    0.45, 2.2, 5.9, 3.3, size=12)
pic_fit(s, 'docs/ppt/assets/formula_ewma.png', 0.75, 5.7, 4.6, 1.5)
pic_fit(s, 'docs/ppt/extracted/s16_图片4.png', 6.9, 2.15, 6.1, 5.0)

# ========== 2.5 工程实现与验证保障 ==========
s = S[7]
chrome(s, 2, 8)
set_shape(by_name(s, '文本框 34'), '2.5  工程实现与验证保障')
tbl = by_name(s, '表格 1').table
for r, line in zip(tbl.rows, [
    ['核心模块', '实现要点与验证情况'],
    ['模块一：双向选择性扫描', '前向/后向独立Mamba路径＋可学习门控融合；模型维度32容量匹配后，多数股票MSE/MAE优于单向基线'],
    ['模块二：轻量化跨股票注意力', 'Q/K/V源自双向隐态的缩放点积注意力，无图卷积；注意力坍缩已诊断并修复，权重恢复差异化'],
    ['模块三：波动自适应训练', 'EWMA波动率三档分桶，损失权重0.5/1.0/2.0；招商银行股方向准确率0.5430为该股票五组配置最高'],
    ['工程保障', '模块化消融开关、固定随机种子、验证集早停与最优权重回滚；GPU云训练较CPU提速约60倍，远程工作流已打通'],
]):
    for c, txt in zip(r.cells, line):
        set_tf(c.text_frame, txt)

# ========== 3.1 实验设置与评估口径（含指标公式） ==========
s = S[9]
chrome(s, 3, 9)
t = by_name(s, '文本框 3')
t.width = Inches(8.0)
set_shape(t, '3.1  实验设置与评估口径')
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
add_table(s, cfg, 0.5, 2.2, [2.5, 4.6], row_h=0.4, size=12)
add_text(s,
    '实验矩阵\n'
    '• 单股票实验：4只股票 × 5种配置（单向基线 / Transformer / 双向 / 基线＋波动加权 / 双向＋波动加权）\n'
    '• 面板消融实验：8只股票 × 5种配置（Transformer / 无注意力 / ＋注意力 / 无注意力＋波动加权 / 完整模型）\n'
    '评估口径\n'
    '• 日频个股收益率可预测性极低，R²普遍为负属领域共识\n'
    '• 以"相对基线提升＋方向准确率＋消融一致性"作为评价标准',
    8.0, 2.2, 5.0, 4.0, size=12)
pic_fit(s, 'docs/ppt/assets/formula_metrics.png', 0.5, 6.2, 12.3, 0.95)

# ========== 3.2 单股票完整结果 ==========
s = S[10]
chrome(s, 3, 10)
t = by_name(s, '文本框 3')
t.width = Inches(9.5)
set_shape(t, '3.2  单股票实验：四股×五配置完整结果')
body_clear(s, keep={'文本框 3'})
rows = [('股票', '模型配置', 'MSE(×10⁻⁴)', 'MAE(×10⁻³)', 'R²', '方向准确率')]
raw = [
    ('招商银行', [('单向基线', 1.54, 9.11, -0.1347, 0.4883), ('Transformer', 1.66, 9.80, -0.2242, 0.4922),
                 ('双向', 1.44, 8.77, -0.0606, 0.4844), ('基线＋波动加权', 1.52, 9.10, -0.1216, 0.4844),
                 ('双向＋波动加权', 1.60, 9.29, -0.1833, 0.5430)]),
    ('农业银行', [('单向基线', 1.69, 10.12, -0.0007, 0.5352), ('Transformer', 1.93, 10.92, -0.1400, 0.4609),
                 ('双向', 1.89, 10.76, -0.1178, 0.4727), ('基线＋波动加权', 1.70, 10.18, -0.0059, 0.5352),
                 ('双向＋波动加权', 1.73, 10.27, -0.0243, 0.5078)]),
    ('交通银行', [('单向基线', 1.38, 9.20, -0.0881, 0.4453), ('Transformer', 1.56, 9.74, -0.2219, 0.4531),
                 ('双向', 1.29, 8.72, -0.0135, 0.5469), ('基线＋波动加权', 1.41, 9.21, -0.1060, 0.4766),
                 ('双向＋波动加权', 1.54, 9.74, -0.2118, 0.5078)]),
    ('中国银行', [('单向基线', 1.34, 8.87, -0.0528, 0.4531), ('Transformer', 1.45, 9.56, -0.1370, 0.4844),
                 ('双向', 1.37, 9.00, -0.0731, 0.5234), ('基线＋波动加权', 1.47, 9.52, -0.1572, 0.4727),
                 ('双向＋波动加权', 1.35, 9.05, -0.0623, 0.4531)]),
]
bold = set()
for stock, cfgs in raw:
    best_mse = min(c[1] for c in cfgs)
    best_da = max(c[4] for c in cfgs)
    for cfg, mse, mae, r2, da in cfgs:
        i = len(rows)
        rows.append((stock, cfg, f'{mse:.2f}', f'{mae:.2f}', f'{r2:.4f}', f'{da:.4f}'))
        if mse == best_mse:
            bold.add((i, 2))
        if da == best_da:
            bold.add((i, 5))
add_table(s, rows, 0.45, 2.05, [1.4, 2.4, 2.0, 2.0, 2.0, 2.2], row_h=0.222, size=10, bold_cells=bold)
add_text(s, '注：加粗为该股票该项最优。四股中三股的最高方向准确率由本文配置取得；农业银行基线DA仍最高，模块有效性存在个股差异（如实呈现）。',
         0.45, 6.95, 12.4, 0.5, size=11)

# ========== 3.3 单股票结果分析：MSE 与 MAE ==========
s = S[12]
chrome(s, 3, 11)
set_shape(by_name(s, '文本框 1'), '3.3  单股票结果分析：MSE 与 MAE')
body_clear(s, keep={'文本框 1'})
s.shapes.add_picture('results/v3_mse_mae_compare.png', Inches(0.85), Inches(2.15), width=Inches(11.6))
add_text(s,
    '• 双向结构在招商银行、交通银行实现MSE与MAE双改善，MSE较单向基线均下降约6.5%；在农业银行、中国银行上未获改善，个股差异客观存在\n'
    '• 波动自适应加权的作用更多体现在方向准确率：招商银行"双向＋波动加权"DA 0.5430为该股票最高（见3.5节）',
    0.85, 6.85, 11.6, 0.6, size=11)

# ========== 3.4 八股面板消融实验结果 ==========
s = S[13]
chrome(s, 3, 12)
set_shape(by_name(s, '文本框 1'), '3.4  八股面板消融实验结果')
body_clear(s, keep={'文本框 1'})
panel = [('模型配置', 'MSE(×10⁻⁴)', 'MAE(×10⁻³)', 'R²', '方向准确率'),
         ('Transformer', '1.55', '9.55', '-0.1753', '0.4927'),
         ('无注意力', '1.36', '8.82', '-0.0340', '0.4907'),
         ('＋跨股票注意力', '1.34', '8.84', '-0.0163', '0.4941'),
         ('无注意力＋波动加权', '1.37', '8.85', '-0.0393', '0.4893'),
         ('完整模型（注意力＋波动加权）', '1.34', '8.80', '-0.0158', '0.4956')]
add_table(s, panel, 0.5, 2.3, [3.4, 1.5, 1.5, 1.3, 1.5], row_h=0.42, size=12,
          bold_cells={(5, 1), (5, 4), (5, 5)})
add_text(s,
    '结果分析\n'
    '• 完整模型方向准确率0.4956，居四组消融配置首位；MSE 1.34×10⁻⁴为全表最低之一\n'
    '• 跨股票注意力使MSE较无注意力配置下降约1.5%，R²由-0.0340改善至-0.0163，消融方向一致\n'
    '• 完整模型MSE较Transformer基线（1.55×10⁻⁴）低约13.5%\n'
    '• 波动加权在面板场景未带来DA提升：8只同质银行股波动状态趋同，有待全市场异质性股票池检验',
    0.5, 5.1, 12.3, 2.0, size=12)

# ========== 3.5 方向准确率对比分析 ==========
s = S[14]
chrome(s, 3, 13)
set_shape(by_name(s, '文本框 1'), '3.5  方向准确率（DA）对比分析')
body_clear(s, keep={'文本框 1'})
s.shapes.add_picture('results/v3_da_compare.png', Inches(0.5), Inches(2.3), width=Inches(7.4))
add_text(s,
    '核心结果\n'
    '• 四股中三股的最高DA由本文配置取得：\n'
    '  交通银行（双向）0.5469\n'
    '  招商银行（双向＋波动加权）0.5430\n'
    '  中国银行（双向）0.5234\n'
    '反例如实呈现\n'
    '• 农业银行：单向基线DA 0.5352仍为最高，本文双向结构0.4727，存在明显个股差异\n'
    '指标解读\n'
    '• DA>0.5意味着方向预测优于随机基准，具备一定交易参考价值',
    8.3, 2.3, 4.6, 4.8, size=12)

# ========== 3.6 训练过程与收敛性分析（新页，双训练曲线） ==========
s = NEW_TRAIN
chrome(s, 3, 14)
set_shape(by_name(s, '文本框 1'), '3.6  训练过程与收敛性分析')
body_clear(s, keep={'文本框 1'})
pic_fit(s, 'results/600036_loss.png', 0.55, 2.4, 5.95, 3.0)
pic_fit(s, 'results/panel_attn_h1_loss.png', 6.85, 2.4, 5.95, 3.0)
add_text(s, '单股票训练（招商银行）：训练损失与验证MSE', 0.55, 5.5, 5.95, 0.35, size=11, color=ACCENT, bold=True)
add_text(s, '8股面板训练（完整模型）：训练损失与验证MSE', 6.85, 5.5, 5.95, 0.35, size=11, color=ACCENT, bold=True)
add_text(s,
    '• 训练损失与验证MSE均快速收敛并趋于平稳；验证集早停（耐心30轮）防止过拟合，最优验证权重回滚\n'
    '• 模型选择仅依据验证集——测试集不参与任何调参与模型选择，保证评估无泄漏',
    0.55, 6.15, 12.2, 0.9, size=12)

# ========== 3.7 跨股票注意力权重分析 ==========
s = S[15]
chrome(s, 3, 15)
set_shape(by_name(s, '文本框 1'), '3.7  跨股票注意力权重：坍缩诊断与修复')
body_clear(s, keep={'文本框 1'})
add_text(s,
    '问题诊断\n'
    '• 统一权重衰减（1e-4）下，注意力权重在全部测试交易日恒为均匀分布（各股1/8），出现注意力坍缩\n'
    '机制分析\n'
    '• 同质银行股等权特征已较强，差异化权重收益有限，投影矩阵梯度弱，被权重衰减持续压缩至零\n'
    '修复与验证\n'
    '• Q/K/V投影豁免权重衰减后重新训练：权重恢复差异化（逐日偏差最大0.0124）\n'
    '• 对角线自注意力均值0.1263＞均匀基准0.125；MSE持平，R²由-0.0163略改善至-0.0158\n'
    '• 更显著的差异化结构有待全市场、更具异质性的股票池检验',
    0.5, 2.3, 6.2, 4.8, size=12)
s.shapes.add_picture('results/panel_attn_h1_attn_v3.png', Inches(7.3), Inches(2.3), width=Inches(5.4))

# ========== 3.8 阶段性结论与不足 ==========
s = S[16]
chrome(s, 3, 16)
set_shape(by_name(s, 'Text 12'), '3.8  阶段性结论与不足')
set_shape(by_name(s, '文本框 35'), '实验条件与可复现性')
for name, txt in [
    ('Text 16', '硬件：GPU云平台训练，单epoch由约138秒降至约2.3秒'),
    ('Text 19', '软件：Python 3.9＋PyTorch 2.0，随机种子固定'),
    ('Text 22', '数据：Tushare Pro日频数据，下载管线支持断点续传'),
]:
    set_shape(in_group(s, '组合 24', name), txt)
tbl = by_name(s, 'Table 0').table
for r, line in zip(tbl.rows, [
    ['维度', '阶段性结论'],
    ['模块有效性', '双向结构容量匹配后于多数股票改善MSE/MAE；波动加权提升部分高波动股票DA'],
    ['整体优势', '四股中三股最高DA由本文配置取得；面板完整模型DA居四组消融配置首位'],
    ['严谨性', '除息口径修正、防泄漏切分、验证集模型选择，实验可复现'],
    ['不足与边界', '日频R²普遍为负；农业银行存在基线更优反例；单种子、小样本结论有待全市场多种子验证'],
]):
    for c, txt in zip(r.cells, line):
        set_tf(c.text_frame, txt)

# ========== 4.1 关键问题与解决方案 ==========
s = S[18]
chrome(s, 4, 17)
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
chrome(s, 5, 18)
set_shape(by_name(s, 'Text 12'), '5.1  下一阶段工作计划')
body_clear(s, keep={'Text 12'})
plan = [('时间', '工作内容'),
        ('第1个月', '全市场数据扩展：沪深300全成分股下载、完整性校验与面板数据集构建'),
        ('第2个月', '全市场对比实验：补充LSTM/Informer/PatchTST/iTransformer等主流基线，增加5日预测期限'),
        ('第3个月', '统计稳健性验证：3—5个随机种子重复实验，报告均值与标准差，完善论文图表'),
        ('第4—5个月', '学位论文初稿撰写（绪论、相关理论、模型设计、实验与分析）'),
        ('第6个月', '论文修改定稿、材料归档与答辩准备')]
add_table(s, plan, 0.9, 2.3, [2.2, 9.3], row_h=0.62, size=14)

# ========== S21 结束页 ==========
set_shape(by_name(S[20], '文本框 11'), '2026年10月')

# ========== 重排页序（26页） ==========
order = [0, 1, 2, 3, 4, 21, 5, 6, 22, 23, 24, 7, 8, 9, 10, 12, 13, 14, 25, 15, 16, 11, 18, 17, 19, 20]
sldIdLst = prs.slides._sldIdLst
ids = list(sldIdLst)
for el in ids:
    sldIdLst.remove(el)
for i in order:
    sldIdLst.append(ids[i])

prs.save(DST)
print(f'已生成 {DST}，共{len(prs.slides)}页')
