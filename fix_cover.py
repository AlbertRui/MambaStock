# 封面 v3：模板几何精确复刻 + 矢量边框线
# 版式完全按《中期答辩模板》实测尺寸（twips）：
#   首行缩进 720；4字标签 1200；7字标签（研究所（院系））2100；
#   单字段横线 5550（模板 37 空格×150）；双字段行 2250/600/2700（模板 15/4/18 空格单位）
#   每行右端统一在 720+6750=7470 处（模板规则）
# 横线 = 值单元格下框线（0.75磅矢量线，PDF 中绝对均匀，解决字符下划线转PDF粗细不一）
import shutil, time
from docx import Document
from docx.oxml import parse_xml

PATH = 'docs/基于Mamba状态空间模型的股票价格预测方法研究-中期.docx'
shutil.copy(PATH, 'docs/中期_v20_backup_' + time.strftime('%Y%m%d_%H%M%S') + '.bak')
d = Document(PATH)

F = ('<w:rFonts w:ascii="SimSun" w:hAnsi="SimSun" w:eastAsia="宋体"/>'
     '<w:b/><w:bCs/><w:sz w:val="30"/><w:szCs w:val="30"/>')
# 列：标签段1400 | 补段850 | 中段1300 | 次标签650 | 末值2550  （合计6750，首行缩进720）
# （标签列按粗体15磅加宽：4字粗体≈1250→1400；"研究所（院系）"跨两列=2250，7字粗体≈2190）
COLS = (1400, 850, 1300, 650, 2550)

def cell(text, c0, c1, line):
    """c0..c1 为列区间（含端点），line=True 表示该单元格带下框线"""
    width = sum(COLS[c0:c1 + 1])
    span = f'<w:gridSpan w:val="{c1 - c0 + 1}"/>' if c1 > c0 else ''
    border = ('<w:tcBorders><w:bottom w:val="single" w:sz="6" w:space="0" w:color="000000"/></w:tcBorders>'
              if line else '<w:tcBorders><w:bottom w:val="nil"/></w:tcBorders>')
    align = 'center' if line else 'left'
    return (f'<w:tc><w:tcPr><w:tcW w:w="{width}" w:type="dxa"/>{span}{border}'
            f'<w:vAlign w:val="bottom"/></w:tcPr>'
            f'<w:p><w:pPr><w:spacing w:line="300" w:lineRule="exact"/><w:jc w:val="{align}"/>'
            f'<w:rPr>{F}</w:rPr></w:pPr>'
            f'<w:r><w:rPr>{F}</w:rPr><w:t xml:space="preserve">{text}</w:t></w:r></w:p></w:tc>')

def row(*cells):
    return ('<w:tr><w:trPr><w:trHeight w:val="375" w:hRule="atLeast"/></w:trPr>'
            + ''.join(cells) + '</w:tr>')

ROWS = [
    row(cell('报告题目', 0, 0, False), cell('基于Mamba状态空间模型的', 1, 4, True)),
    row(cell('', 0, 0, False), cell('股票价格预测方法研究', 1, 4, True)),
    row(cell('学生姓名', 0, 0, False), cell('***', 1, 2, True),
        cell('学号', 3, 3, False), cell('***', 4, 4, True)),
    row(cell('指导教师', 0, 0, False), cell('***', 1, 2, True),
        cell('职称', 3, 3, False), cell('副教授', 4, 4, True)),
    row(cell('学位类别', 0, 0, False), cell('电子信息硕士', 1, 4, True)),
    row(cell('学科专业', 0, 0, False), cell('人工智能', 1, 4, True)),
    row(cell('研究方向', 0, 0, False), cell('模式识别与机器学习', 1, 4, True)),
    row(cell('研究所（院系）', 0, 1, False), cell('人工智能学院', 2, 4, True)),  # 7字标签占两列=2100，与模板一致
    row(cell('填表日期', 0, 0, False), cell('2026.10.07', 1, 4, True)),
]

grid = ''.join(f'<w:gridCol w:w="{w}"/>' for w in COLS)
tbl_xml = (
    '<w:tbl xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
    '<w:tblPr><w:tblW w:w="6750" w:type="dxa"/><w:tblInd w:w="720" w:type="dxa"/>'
    '<w:tblLayout w:type="fixed"/>'
    '<w:tblBorders>'
    '<w:top w:val="none" w:sz="0" w:space="0"/><w:left w:val="none" w:sz="0" w:space="0"/>'
    '<w:bottom w:val="none" w:sz="0" w:space="0"/><w:right w:val="none" w:sz="0" w:space="0"/>'
    '<w:insideH w:val="none" w:sz="0" w:space="0"/><w:insideV w:val="none" w:sz="0" w:space="0"/>'
    '</w:tblBorders>'
    '<w:tblCellMar><w:left w:w="0" w:type="dxa"/><w:right w:w="0" w:type="dxa"/>'
    '<w:top w:w="0" w:type="dxa"/><w:bottom w:w="0" w:type="dxa"/></w:tblCellMar>'
    '</w:tblPr>'
    f'<w:tblGrid>{grid}</w:tblGrid>' + ''.join(ROWS) + '</w:tbl>'
)

# 当前封面 = 段落9..17（v2 重建的 9 个字段段）；删除并插入表格到段落8之后
victims = [d.paragraphs[i]._p for i in range(9, 18)]
d.paragraphs[8]._p.addnext(parse_xml(tbl_xml))
for el in victims:
    el.getparent().remove(el)

d.save(PATH)
print('封面 v3 完成：模板几何 + 0.75磅矢量边框线')
