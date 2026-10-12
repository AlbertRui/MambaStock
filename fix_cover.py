# 封面 v4：直接克隆《中期答辩模板》封面字段段落的原始 XML，仅替换字段值
# 模板实测规则（docs/中期答辩模板.docx P10-P17）：
#   全部 SimSun 粗体 sz=30（15磅），首行缩进 720，字符下划线 u=single
#   每行总宽 = 45 个半角单位（空格宽150twips，汉字=2单位，ASCII=1单位）
#   单字段行 = 标签(8单位) + 37单位下划线；双字段行 = 8 + 15 + 标签 + 18
#   值插入下划线空格正中，左右扣减空格保持总单位数不变 → 行右端自然对齐
import copy
import json
import shutil
import time
from docx import Document
from docx.oxml.ns import qn

TPL = 'docs/中期答辩模板.docx'
PATH = 'docs/基于Mamba状态空间模型的股票价格预测方法研究-中期.docx'

# 封面字段值存于 docs/cover_config.json（本地文件，已 gitignore，不进仓库）
with open('docs/cover_config.json', encoding='utf-8') as f:
    F = json.load(f)


def units(s):
    """半角单位宽度：汉字/全角=2，ASCII=1"""
    return sum(1 if ord(c) < 0x2E80 else 2 for c in s)


def fill(run, total, value):
    """把值放入下划线空格run正中，左右补空格使总宽=total单位"""
    pad = total - units(value)
    left, right = pad // 2, pad - pad // 2
    run.findall(qn('w:t'))[0].text = ' ' * left + value + ' ' * right


tpl = Document(TPL)
tp = [tpl.paragraphs[i]._p for i in range(10, 18)]  # 模板封面字段行 P10-P17

# (模板段索引, [(run序号, 下划线总单位数, 值), ...], 标签run替换文本)
SPEC = [
    (0, [(1, 37, F['title1'])], None),                 # 报告题目 行1
    (0, [(1, 37, F['title2'])], '　　　　'),           # 报告题目 行2（标签位补4个全角空格=8单位，下划线起点对齐）
    (1, [(1, 15, F['name']), (3, 18, F['student_id'])], None),        # 学生姓名/学号
    (2, [(1, 14, F['advisor']), (3, 18, F['advisor_title'])], None),  # 指导教师/职称
    (3, [], None),                                     # 学位类别（模板示例值，沿用）
    (4, [(1, 37, F['major'])], None),                  # 学科专业
    (5, [(1, 37, F['direction'])], None),              # 研究方向
    (6, [], None),                                     # 研究所（院系）（模板示例值，沿用）
    (7, [(1, 37, F['date'])], None),                   # 填表日期
]

new_paras = []
for tidx, fills, label in SPEC:
    p = copy.deepcopy(tp[tidx])
    runs = p.findall(qn('w:r'))
    if label is not None:
        runs[0].findall(qn('w:t'))[0].text = label
    for ridx, total, value in fills:
        fill(runs[ridx], total, value)
    new_paras.append(p)

shutil.copy(PATH, 'docs/中期_v21_backup_' + time.strftime('%Y%m%d_%H%M%S') + '.bak')
d = Document(PATH)
body = d.element.body
children = list(body.iterchildren())
cover_tbl = children[9]          # 封面表（v3 表格版，待删除）
anchor = children[8]             # 封面表前的空段落
assert cover_tbl.tag == qn('w:tbl'), '封面表位置不符合预期'
for p in new_paras:
    anchor.addnext(p)
    anchor = p
body.remove(cover_tbl)
d.save(PATH)
print('封面 v4 完成：模板 P10-P17 原样克隆，仅替换字段值')
