"""Build the Vietnamese application report using the user's Word template."""
from copy import deepcopy
from pathlib import Path
import json
import re
import shutil

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from PIL import Image
from docx import Document
from docx.enum.section import WD_SECTION_START
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
TARGET = Path(r'C:\Users\NGUYEN THANH NAM\Downloads\Mau bao cao_Do an_Khoa luan_Huong ung dung.docx')
BACKUP = TARGET.with_name(TARGET.stem + '_Mau_goc.docx')
OUTPUT = ROOT / 'docs' / 'report-assets'
OUTPUT.mkdir(exist_ok=True)
TITLE = 'ỨNG DỤNG ARANGODB XÂY DỰNG HỆ THỐNG GỢI Ý VIỆC LÀM VÀ ĐƯỜNG KẾT NỐI GIỚI THIỆU'
plt.rcParams.update({'font.family': 'Times New Roman', 'font.size': 13})


def diagram(name, size, nodes, edges):
    fig, ax = plt.subplots(figsize=size)
    ax.set(xlim=(0, 10), ylim=(0, 6))
    ax.axis('off')
    for key, (x, y, w, h, label) in nodes.items():
        rect = FancyBboxPatch((x-w/2, y-h/2), w, h,
                             boxstyle='round,pad=0.08,rounding_size=0.12',
                             linewidth=1.3, facecolor='#eff5f3', edgecolor='#155c50')
        ax.add_patch(rect)
        ax.text(x, y, label, ha='center', va='center', fontsize=13)
    for src, dst, label in edges:
        x1, y1, w1, h1, _ = nodes[src]
        x2, y2, w2, h2, _ = nodes[dst]
        dx, dy = x2-x1, y2-y1
        if abs(dx) > abs(dy):
            a=(x1+(w1/2+0.1)*(1 if dx>0 else -1), y1)
            b=(x2-(w2/2+0.1)*(1 if dx>0 else -1), y2)
        else:
            a=(x1,y1+(h1/2+0.1)*(1 if dy>0 else -1))
            b=(x2,y2-(h2/2+0.1)*(1 if dy>0 else -1))
        ax.add_patch(FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=15,
                                    color='#155c50',linewidth=1.2))
        if label:
            ax.text((a[0]+b[0])/2,(a[1]+b[1])/2+0.16,label,
                    ha='center',va='center',fontsize=11,
                    bbox={'facecolor':'white','edgecolor':'none','pad':1})
    fig.savefig(OUTPUT/name,dpi=220,bbox_inches='tight',facecolor='white')
    plt.close(fig)


def assets():
    diagram('architecture.png',(10,5),{
        'ui':(1.5,4.5,2.3,1.1,'React / TypeScript\nGiao diện tiếng Việt'),
        'proxy':(5,4.5,2.3,1.1,'Nginx\nAssets và API proxy'),
        'api':(8.5,4.5,2.3,1.1,'FastAPI\nAuth, policy, service'),
        'repo':(8.5,1.5,2.3,1.1,'Repository\npython-arango, AQL'),
        'db':(4.5,1.5,2.8,1.1,'ArangoDB 3.12.12\nDocuments, edges, graph'),
        'vol':(1,1.5,1.7,1.1,'Volumes\nLưu dữ liệu')},
        [('ui','proxy','HTTP'),('proxy','api','/api/v1'),('api','repo','Nghiệp vụ'),
         ('repo','db','Query / transaction'),('db','vol','')])
    diagram('graph.png',(10,5.8),{
        'user':(1.5,4.7,2,1,'users\nHồ sơ ứng viên'),
        'peer':(6.5,4.7,2.6,1,'users\nNgười giới thiệu'),
        'skill':(1.5,1.3,2,1,'skills\nKỹ năng'),
        'job':(5,1.3,2,1,'jobs\nViệc làm'),
        'company':(8.6,1.3,2.3,1,'companies\nDoanh nghiệp')},
        [('user','peer','connections (ANY)'),('user','skill','has_skill'),
         ('peer','company','works_at'),('job','skill','job_requires_skill'),
         ('job','company','job_at_company')])
    diagram('usecases.png',(10,5.5),{
        'a':(1.7,4.6,2.8,1,'Ứng viên'),
        'a2':(6.8,4.6,5.4,1,'Hồ sơ, gợi ý, graph\nỨng tuyển và gửi yêu cầu'),
        'b':(1.7,3.2,2.8,0.8,'Người giới thiệu'),
        'b2':(6.8,3.2,5.4,0.8,'Kết nối và xử lý referral'),
        'c':(1.7,1.9,2.8,0.8,'Quản lý tuyển dụng'),
        'c2':(6.8,1.9,5.4,0.8,'Quản lý jobs và applications'),
        'd':(1.7,0.6,2.8,0.8,'Quản trị viên'),
        'd2':(6.8,0.6,5.4,0.8,'Danh mục, tài khoản, xác minh, audit')},
        [('a','a2',''),('b','b2',''),('c','c2',''),('d','d2','')])
    diagram('workflow.png',(10,5.4),{
        'pending':(1.1,4.5,1.8,0.8,'pending'),
        'accepted':(4,4.5,1.8,0.8,'accepted'),
        'submitted':(6.8,4.5,1.8,0.8,'submitted'),
        'completed':(9,2.8,1.8,0.8,'completed'),
        'rejected':(1.1,1.1,1.8,0.8,'rejected'),
        'cancelled':(4,1.1,1.8,1.2,'cancelled\n(từ pending / accepted)'),
        'expired':(6.8,1.1,1.8,1.2,'expired\n(từ pending / accepted)')},
        [('pending','accepted','Chấp nhận'),('accepted','submitted','Bằng chứng'),
         ('submitted','completed','Kết quả'),('pending','rejected','Từ chối'),
         ('accepted','cancelled','Hủy'),('accepted','expired','Quá hạn')])
    # Terminal-state labels explicitly include both valid source states.
    data=json.loads((ROOT/'docs/reports/benchmark.json').read_text(encoding='utf-8'))
    labels=list(data['queries'])
    p50=[data['queries'][k]['p50_ms'] for k in labels]
    p95=[data['queries'][k]['p95_ms'] for k in labels]
    fig,ax=plt.subplots(figsize=(10,5.7))
    positions=list(range(len(labels)))
    ax.barh([x+0.18 for x in positions],p50,height=.34,label='p50',color='#155c50')
    ax.barh([x-.18 for x in positions],p95,height=.34,label='p95',color='#aa8230')
    ax.set_yticks(positions,labels)
    ax.invert_yaxis()
    ax.set_xlabel('Thời gian (ms) — 20 lần/query, tuần tự, local Docker')
    ax.legend(loc='lower right')
    ax.grid(axis='x',alpha=.15)
    ax.spines[['top','right']].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUTPUT/'benchmark.png',dpi=220,bbox_inches='tight')
    plt.close(fig)
    img=Image.open(ROOT/'docs/reports/frontend-dashboard-1440.png')
    # Crop only whitespace/below-the-fold content; preserve actual UI pixels.
    img.crop((225, 620, 1420, 1540)).save(OUTPUT/'dashboard.png')
    shutil.copy2(ROOT/'docs/reports/frontend-paths-1440.png',OUTPUT/'paths.png')


def font(run, size=13, bold=None):
    run.font.name='Times New Roman'
    run.font.size=Pt(size)
    if bold is not None: run.bold=bold
    run.font.color.rgb=RGBColor(0,0,0)
    rp=run._element.get_or_add_rPr()
    rf=rp.find(qn('w:rFonts'))
    if rf is None:
        rf=OxmlElement('w:rFonts');rp.append(rf)
    for key in ['ascii','hAnsi','eastAsia','cs']: rf.set(qn('w:'+key),'Times New Roman')


def field(p, instruction, fallback=''):
    r=p.add_run(); begin=OxmlElement('w:fldChar');begin.set(qn('w:fldCharType'),'begin')
    r._r.append(begin)
    r=p.add_run(); t=OxmlElement('w:instrText');t.set(qn('xml:space'),'preserve');t.text=' '+instruction+' '
    r._r.append(t)
    r=p.add_run(); sep=OxmlElement('w:fldChar');sep.set(qn('w:fldCharType'),'separate');r._r.append(sep)
    p.add_run(fallback)
    r=p.add_run();end=OxmlElement('w:fldChar');end.set(qn('w:fldCharType'),'end');r._r.append(end)
    for r in p.runs:font(r)


def style(doc,name,size=13,bold=False,align=WD_ALIGN_PARAGRAPH.JUSTIFY,outline=None):
    st=doc.styles[name] if name in doc.styles else doc.styles.add_style(name,WD_STYLE_TYPE.PARAGRAPH)
    st.font.name='Times New Roman';st.font.size=Pt(size);st.font.bold=bold;st.font.color.rgb=RGBColor(0,0,0)
    st.element.get_or_add_rPr().append(OxmlElement('w:rFonts'))
    rf=st.element.rPr.findall(qn('w:rFonts'))[-1]
    for k in ['ascii','hAnsi','eastAsia','cs']:rf.set(qn('w:'+k),'Times New Roman')
    pf=st.paragraph_format
    pf.alignment=align;pf.line_spacing=1.3;pf.space_before=Pt(6);pf.space_after=Pt(6)
    pf.first_line_indent=Cm(.8) if name=='Normal' else Cm(0)
    pf.widow_control=True
    if outline is not None:
        pr=st.element.get_or_add_pPr();ol=pr.find(qn('w:outlineLvl'))
        if ol is None:ol=OxmlElement('w:outlineLvl');pr.append(ol)
        ol.set(qn('w:val'),str(outline))
    if name.startswith('Heading') or name=='ReportFront':pf.keep_with_next=True
    if name=='Heading 1' or name=='ReportFront':pf.page_break_before=True
    return st


def geometry(sec):
    sec.page_width=Cm(21);sec.page_height=Cm(29.7)
    sec.left_margin=Cm(3.5);sec.right_margin=Cm(2.5)
    sec.top_margin=Cm(2.5);sec.bottom_margin=Cm(2.5)
    sec.header_distance=Cm(1.25);sec.footer_distance=Cm(1.25)


def numbering(sec,fmt):
    sec.footer.is_linked_to_previous=False
    sec.header.is_linked_to_previous=False
    for child in list(sec.footer._element):sec.footer._element.remove(child)
    p=sec.footer.add_paragraph()
    p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent=Cm(0);p.paragraph_format.space_before=Pt(0);p.paragraph_format.space_after=Pt(0)
    field(p,'PAGE')
    node=sec._sectPr.find(qn('w:pgNumType'))
    if node is None:node=OxmlElement('w:pgNumType');sec._sectPr.append(node)
    node.set(qn('w:fmt'),fmt);node.set(qn('w:start'),'1')


def text(doc,content,sty='Normal'):
    p=doc.add_paragraph(style=sty);p.add_run(content)
    for r in p.runs:font(r,13)
    return p


def heading(doc,content,level=1,front=False):
    p=doc.add_paragraph(content,style='ReportFront' if front else 'Heading '+str(level))
    for r in p.runs:font(r,18 if level==1 else 14 if level==2 else 13,True)
    return p


def table(doc,caption,rows):
    p=text(doc,caption,'TableCaption');p.paragraph_format.keep_with_next=True
    tb=doc.add_table(rows=1,cols=len(rows[0]));tb.autofit=False
    # Table width matches the 15 cm text column.
    widths={2:[5,10],3:[4,5,6],4:[3.5,2,3,6.5],5:[4.5,2,2.5,2.5,3.5]}.get(len(rows[0]),[15/len(rows[0])]*len(rows[0]))
    for col,w in zip(tb.columns,widths):col.width=Cm(w)
    for j,v in enumerate(rows[0]):tb.rows[0].cells[j].text=v
    trpr=tb.rows[0]._tr.get_or_add_trPr();repeat=OxmlElement('w:tblHeader');trpr.append(repeat)
    for row in rows[1:]:
        cells=tb.add_row().cells
        for j,v in enumerate(row):cells[j].text=v
    for i,row in enumerate(tb.rows):
        rp=row._tr.get_or_add_trPr();rp.append(OxmlElement('w:cantSplit'))
        for j,cell in enumerate(row.cells):
            cell.width=Cm(widths[j])
            if i==0:
                sh=OxmlElement('w:shd');sh.set(qn('w:fill'),'E8F0ED');cell._tc.get_or_add_tcPr().append(sh)
            for p in cell.paragraphs:
                p.style=doc.styles['TableText']
                for r in p.runs:font(r,12,i==0)
    pr=tb._tbl.tblPr
    borders=OxmlElement('w:tblBorders')
    for key in ['top','left','bottom','right','insideH','insideV']:
        b=OxmlElement('w:'+key);b.set(qn('w:val'),'single');b.set(qn('w:sz'),'4');b.set(qn('w:color'),'777777');borders.append(b)
    pr.append(borders)
    doc.add_paragraph().paragraph_format.space_after=Pt(0)


def figure(doc,name,caption):
    im=Image.open(OUTPUT/name);w,h=im.size
    width=15
    if h/w*width>17:width=17*w/h
    p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent=Cm(0);p.paragraph_format.keep_with_next=True
    p.add_run().add_picture(str(OUTPUT/name),width=Cm(width))
    text(doc,caption,'FigureCaption')


def build():
    if not BACKUP.exists():shutil.copy2(TARGET,BACKUP)
    doc=Document(BACKUP)
    original_paragraphs=list(doc.paragraphs)
    keep_end=original_paragraphs[47]._p
    body=doc._element.body
    passed=False
    for element in list(body):
        if passed and element.tag!=qn('w:sectPr'):body.remove(element)
        if element is keep_end:passed=True
    for sec in doc.sections:
        geometry(sec)
    style(doc,'Normal')
    style(doc,'Heading 1',18,True,WD_ALIGN_PARAGRAPH.CENTER,0)
    style(doc,'Heading 2',14,True,WD_ALIGN_PARAGRAPH.LEFT,1)
    style(doc,'Heading 3',13,True,WD_ALIGN_PARAGRAPH.LEFT,2)
    style(doc,'ReportFront',18,True,WD_ALIGN_PARAGRAPH.CENTER)
    style(doc,'ReportTOCTitle',18,True,WD_ALIGN_PARAGRAPH.CENTER)
    doc.styles['ReportTOCTitle'].paragraph_format.page_break_before=True
    doc.styles['ReportTOCTitle'].paragraph_format.keep_with_next=True
    style(doc,'FigureCaption',13,False,WD_ALIGN_PARAGRAPH.CENTER)
    style(doc,'TableCaption',13,False,WD_ALIGN_PARAGRAPH.CENTER)
    style(doc,'TableText',12,False,WD_ALIGN_PARAGRAPH.LEFT)
    style(doc,'CodeBlock',13,False,WD_ALIGN_PARAGRAPH.LEFT)
    for name in ['TableText','CodeBlock']:
        pf=doc.styles[name].paragraph_format;pf.space_before=Pt(0);pf.space_after=Pt(0);pf.line_spacing=1.3
    for name in ['TOC 1','TOC 2','TOC 3']:
        style(doc,name,13,False,WD_ALIGN_PARAGRAPH.LEFT)
        doc.styles[name].paragraph_format.space_before=Pt(0)
        doc.styles[name].paragraph_format.space_after=Pt(3)
    covers=doc.paragraphs[:48]
    replacements={10:TITLE,34:TITLE,12:'Ngành: [Cần bổ sung]',36:'Ngành: [Cần bổ sung]',
                  39:'[Cần bổ sung họ tên giảng viên hướng dẫn]',
                  23:'TP. HỒ CHÍ MINH, tháng 10 năm 2026',47:'TP. HỒ CHÍ MINH, tháng 10 năm 2026',
                  7:'[Cần bổ sung loại báo cáo]',31:'[Cần bổ sung loại báo cáo]'}
    for start in [16,42]:
        for j in range(3):replacements[start+j]=f'{j+1}. [Cần bổ sung MSSV – Họ tên – Lớp]'
    for i,p in enumerate(covers):
        if i in replacements:
            # Preserve paragraph properties including the template section break.
            for child in list(p._p):
                if child.tag!=qn('w:pPr'):p._p.remove(child)
            p.add_run(replacements[i])
        pf=p.paragraph_format
        pf.first_line_indent=Cm(0);pf.line_spacing=1.1;pf.space_before=Pt(0);pf.space_after=Pt(4)
        pf.keep_with_next=False;pf.keep_together=True
        if not p.text and 'w:drawing' not in p._p.xml:
            pf.space_after=Pt(0);pf.line_spacing=Pt(10)
        for r in p.runs:font(r,18 if i in [10,34] else 14,True if i in [0,1,2,7,10,24,25,26,31,34] else None)
        if i not in [16,17,18,42,43,44]:p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    covers[24].paragraph_format.page_break_before=True
    # The first section (two covers) has no page number.
    doc.sections[0].footer.is_linked_to_previous=False
    for child in list(doc.sections[0].footer._element):doc.sections[0].footer._element.remove(child)
    doc.sections[0].footer.add_paragraph()
    # Reuse the original template's preliminary section boundary.
    preliminary=doc.sections[-1];geometry(preliminary);numbering(preliminary,'lowerRoman')
    for border in preliminary._sectPr.findall(qn('w:pgBorders')):preliminary._sectPr.remove(border)
    p=heading(doc,'LỜI CẢM ƠN',front=True);p.paragraph_format.page_break_before=False
    text(doc,'Nhóm thực hiện xin trân trọng cảm ơn Nhà trường và Khoa Công nghệ Thông tin đã tạo điều kiện học tập, nghiên cứu để thực hiện đề tài. Nhóm xin cảm ơn giảng viên hướng dẫn đã hỗ trợ định hướng chuyên môn và góp ý cho quá trình hoàn thiện báo cáo.')
    text(doc,'Nhóm cũng xin cảm ơn các tác giả và cộng đồng phát triển ArangoDB, FastAPI, React cùng các công cụ mã nguồn mở đã cung cấp tài liệu và nền tảng kỹ thuật phục vụ việc xây dựng ứng dụng. Báo cáo còn những hạn chế về dữ liệu đánh giá và phạm vi thử nghiệm; nhóm mong nhận được góp ý để tiếp tục hoàn thiện.')
    text(doc,'TP. Hồ Chí Minh, tháng 10 năm 2026\nNhóm thực hiện', 'FigureCaption')
    p=doc.add_paragraph('MỤC LỤC',style='ReportTOCTitle')
    for r in p.runs:font(r,18,True)
    field(doc.add_paragraph(), 'TOC \\o "1-3" \\t "ReportFront,1" \\h \\z \\u', 'Mục lục tự động')
    heading(doc,'DANH MỤC CÁC KÝ HIỆU VÀ CHỮ VIẾT TẮT',front=True)
    table(doc,'',[['Viết tắt','Tiếng Anh','Tiếng Việt'],
        ['AQL','ArangoDB Query Language','Ngôn ngữ truy vấn ArangoDB'],
        ['API','Application Programming Interface','Giao diện lập trình ứng dụng'],
        ['ATS','Applicant Tracking System','Hệ thống quản lý ứng viên'],
        ['DBMS','Database Management System','Hệ quản trị cơ sở dữ liệu'],
        ['DTO','Data Transfer Object','Đối tượng truyền dữ liệu'],
        ['HTTP','Hypertext Transfer Protocol','Giao thức truyền siêu văn bản'],
        ['JWT','JSON Web Token','Token xác thực dạng JSON'],
        ['MVP','Minimum Viable Product','Sản phẩm khả dụng tối thiểu'],
        ['NDCG','Normalized Discounted Cumulative Gain','Chỉ số chất lượng thứ hạng chuẩn hóa'],
        ['RPO / RTO','Recovery Point / Time Objective','Mục tiêu điểm/thời gian phục hồi'],
        ['SLA','Service Level Agreement','Cam kết mức dịch vụ'],
        ['TLS','Transport Layer Security','Bảo mật lớp truyền tải'],
        ['UUID','Universally Unique Identifier','Định danh duy nhất']])
    heading(doc,'DANH MỤC HÌNH',front=True)
    field(doc.add_paragraph(),'TOC \\t "FigureCaption,1" \\h \\z','Danh mục hình tự động')
    heading(doc,'DANH MỤC BẢNG',front=True)
    field(doc.add_paragraph(),'TOC \\t "TableCaption,1" \\h \\z','Danh mục bảng tự động')
    sec=doc.add_section(WD_SECTION_START.NEW_PAGE);geometry(sec);numbering(sec,'decimal')
    for border in sec._sectPr.findall(qn('w:pgBorders')):sec._sectPr.remove(border)
    # Remove template header content in body sections.
    for sec in list(doc.sections)[1:]:
        for p in sec.header.paragraphs:p.clear()
    lines=(ROOT/'docs/bao-cao-arangodb.md').read_text(encoding='utf-8').splitlines()
    i=0;first_main=True
    while i<len(lines):
        line=lines[i].strip()
        if not line:i+=1;continue
        if line.startswith('# '):
            p=heading(doc,line[2:])
            if first_main:p.paragraph_format.page_break_before=False;first_main=False
        elif line.startswith('## '):heading(doc,line[3:],2)
        elif line.startswith('### '):heading(doc,line[4:],3)
        elif line.startswith('@table '):
            cap=line[7:];rows=[];i+=1
            while i<len(lines) and lines[i].startswith('|'):
                rows.append([c.strip() for c in lines[i].strip().strip('|').split('|')]);i+=1
            table(doc,cap,rows);continue
        elif line.startswith('@figure '):
            name,cap=line[8:].split('|',1);figure(doc,name.strip(),cap.strip())
        elif line=='@code':
            i+=1
            while i<len(lines) and lines[i]!='@endcode':
                p=text(doc,lines[i],'CodeBlock')
                sh=OxmlElement('w:shd');sh.set(qn('w:fill'),'F5F5F5');p._p.get_or_add_pPr().append(sh)
                if i+1<len(lines) and lines[i+1]!='@endcode':p.paragraph_format.keep_with_next=True
                i+=1
        else:
            p=text(doc,line)
            if re.match(r'^\[\d+\]',line):
                p.paragraph_format.first_line_indent=Cm(0)
        i+=1
    # Correct attribution for non-caption centered paragraphs and blank captions.
    for p in doc.paragraphs:
        if p.style.name=='FigureCaption' and not p.text.startswith('Hình '):p.style=doc.styles['Normal'];p.alignment=WD_ALIGN_PARAGRAPH.CENTER
        if p.style.name=='TableCaption' and not p.text:p._element.getparent().remove(p._element)
    settings=doc.settings.element
    update=settings.find(qn('w:updateFields'))
    if update is None:update=OxmlElement('w:updateFields');settings.append(update)
    update.set(qn('w:val'),'true')
    doc.core_properties.title=TITLE
    doc.core_properties.subject='Báo cáo hướng ứng dụng theo mẫu Khoa Công nghệ Thông tin'
    doc.core_properties.author='[Cần bổ sung thông tin sinh viên]'
    doc.core_properties.keywords='ArangoDB, AQL, graph, gợi ý việc làm, referral'
    draft=OUTPUT/'Bao_cao_ArangoDB.docx'
    doc.save(draft)
    # Save to the path expressly requested by the user, keeping the untouched template.
    shutil.copy2(draft,TARGET)
    print(json.dumps({'target':str(TARGET),'backup':str(BACKUP),'paragraphs':len(doc.paragraphs),
                      'tables':len(doc.tables),'images':len(doc.inline_shapes),'sections':len(doc.sections)},ensure_ascii=False))


if __name__=='__main__':
    assets()
    build()
