# 封面 v2：严格按《中期答辩模板》封面结构重建 —— 段落 + 字符下划线（模板原生方案），
# 所有 run 统一 SimSun 粗体 15pt(sz=30/szCs=21)，下划线粗细一致；
# 每行右端对齐（标签宽 + 下划线宽 = 45 半角单位，与模板一致），值在下划线内居中。
# 长题目保留两行结构，第二行用 8 个无下划线空格对齐到同一左端，下划线同长。
import shutil, time
from docx import Document
from docx.oxml import parse_xml

PATH = 'docs/基于Mamba状态空间模型的股票价格预测方法研究-中期.docx'
shutil.copy(PATH, 'docs/中期_v19_backup_' + time.strftime('%Y%m%d_%H%M%S') + '.bak')
d = Document(PATH)

F = ('<w:rFonts w:ascii="SimSun" w:hAnsi="SimSun" w:hint="eastAsia"/>'
     '<w:b/><w:bCs/><w:sz w:val="30"/><w:szCs w:val="21"/>')
def run(text, u):
    uu = '<w:u w:val="single"/>' if u else ''
    return (f'<w:r><w:rPr>{F}{uu}</w:rPr><w:t xml:space="preserve">{text}</w:t></w:r>')

LINES = [
    [('报告题目', 0), ('    基于Mamba状态空间模型的    ', 1), ('  ', 0)],
    [('        ', 0), ('        股票价格预测方法研究         ', 1)],
    [('学生姓名', 0), ('     ***      ', 1), ('学号', 0), (' ***  ', 1), (' ', 0)],
    [('指导教师', 0), ('    ***    ', 1), (' 职称', 0), ('      副教授      ', 1), (' ', 0)],
    [('学位类别', 0), ('            电子信息硕士             ', 1), (' ', 0)],
    [('学科专业', 0), ('              人工智能               ', 1), (' ', 0)],
    [('研究方向', 0), ('         模式识别与机器学习          ', 1), (' ', 0)],
    [('研究所（院系）', 0), ('         人工智能学院          ', 1)],
    [('填表日期', 0), ('             2026.10.07              ', 1), (' ', 0)],
]

def para_xml(runs):
    body = ''.join(run(t, u) for t, u in runs)
    return ('<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:pPr><w:spacing w:line="300" w:lineRule="auto"/>'
            '<w:ind w:firstLineChars="239" w:firstLine="720"/>'
            f'<w:rPr>{F}</w:rPr></w:pPr>{body}</w:p>')

# 当前封面：段落0-8（空/标题）+ 我上一版插入的表格 + 段落9（空）+ 中国科学院大学制…
cover_tbl = d.tables[0]._tbl
anchor = d.paragraphs[8]._p          # 表格前的空段
for runs in LINES:                    # 依次插到 anchor 之后（即表格之前）
    el = parse_xml(para_xml(runs))
    anchor.addnext(el)
    anchor = el
cover_tbl.getparent().remove(cover_tbl)   # 删除上一版的表格

d.save(PATH)
print('封面已按模板重建：9 行段落 + 统一字号字符下划线')
