from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

DEEP=RGBColor(0x07,0x17,0x3F); BLUE=RGBColor(0x00,0x42,0xA6); YEL=RGBColor(0xEA,0xFE,0x07)
RED=RGBColor(0xE4,0x37,0x00); WHITE=RGBColor(0xFF,0xFF,0xFF); SOFT=RGBColor(0xC9,0xD3,0xEA)
CARD=RGBColor(0x0E,0x24,0x5C); SKY=RGBColor(0x2E,0x96,0xF5)
F="Fira Sans"; FB="Fira Sans ExtraBold"

prs=Presentation(); prs.slide_width=Inches(13.333); prs.slide_height=Inches(7.5)
BL=prs.slide_layouts[6]

def bg(s,img='/tmp/space_plain.png'):
    s.shapes.add_picture(img,0,0,prs.slide_width,prs.slide_height)

def text(s,x,y,w,h,t,size=18,color=WHITE,bold=False,font=F,align=PP_ALIGN.LEFT,anchor=MSO_ANCHOR.TOP,spacing=None,lines=None):
    tb=s.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h)); tf=tb.text_frame; tf.word_wrap=True
    tf.margin_left=tf.margin_right=tf.margin_top=tf.margin_bottom=0; tf.vertical_anchor=anchor
    paras=lines or [t]
    for i,p in enumerate(paras):
        para=tf.paragraphs[0] if i==0 else tf.add_paragraph(); para.alignment=align
        if spacing: para.space_after=Pt(spacing)
        runs=p if isinstance(p,list) else [(p,{})]
        for rt,st in runs:
            r=para.add_run(); r.text=rt; fo=r.font; fo.name=st.get('font',font); fo.size=Pt(st.get('size',size))
            fo.bold=st.get('bold',bold); fo.color.rgb=st.get('color',color)
    return tb

def box(s,x,y,w,h,fill=CARD,line=None,shape=MSO_SHAPE.ROUNDED_RECTANGLE,radius=0.08):
    sh=s.shapes.add_shape(shape,Inches(x),Inches(y),Inches(w),Inches(h))
    sh.fill.solid(); sh.fill.fore_color.rgb=fill
    if line: sh.line.color.rgb=line; sh.line.width=Pt(1.25)
    else: sh.line.fill.background()
    if shape==MSO_SHAPE.ROUNDED_RECTANGLE: sh.adjustments[0]=radius
    sh.shadow.inherit=False
    return sh

def header(s,kicker,title,n):
    bg(s)
    text(s,0.7,0.45,8,0.3,kicker.upper(),12,YEL,True,FB)
    b=box(s,0.7,0.85,11.93,0.95,BLUE,radius=0.18)
    text(s,1.0,0.85,11.4,0.95,title,30,YEL,True,FB,anchor=MSO_ANCHOR.MIDDLE)
    text(s,0.7,7.0,8,0.3,"ROTAWISE  ·  NASA SPACE APPS CHALLENGE 2026  ·  ABUJA",10,SOFT,False)
    text(s,11.6,7.0,1.03,0.3,f"{n:02d} / 07",10,SOFT,align=PP_ALIGN.RIGHT)

# 1 TITLE
s=prs.slides.add_slide(BL); bg(s,'/tmp/space_bg.png')
text(s,0.8,0.7,11,0.35,"NASA SPACE APPS CHALLENGE  ·  NOVEMBER 14–15, 2026  ·  ABUJA",14,YEL,True,FB)
text(s,0.8,1.5,11,1.6,"ROTAWISE",96,WHITE,True,FB)
b=box(s,0.8,3.15,8.6,0.95,BLUE,radius=0.2)
text(s,1.1,3.15,8.2,0.95,"FIELD MEMORY FROM NASA SATELLITES",28,YEL,True,FB,anchor=MSO_ANCHOR.MIDDLE)
text(s,0.8,4.45,11.5,0.5,"Challenge: Field Shift: Adapting Farms with NASA Data",18,WHITE)
text(s,0.8,5.35,11.8,1.2,"",16,SOFT,lines=[
  [("Presented by ",{'color':SOFT}),("Team Rotawise",{'bold':True,'color':WHITE})],
  [("Jothan Jerry Kato (lead) · Adamilo Aaron Daniel · Umar Faruq Oladoja · Miracle Mathew · Sadiq Bashir Abdullahi · Ndazibari Charles Joshua",{'size':14,'color':SOFT})],
  [("November 2026",{'size':14,'color':SOFT})]],spacing=6)

# 2 PROBLEM
s=prs.slides.add_slide(BL); header(s,"The problem","SAME FIELD, SAME CROP, SEASON AFTER SEASON",2)
text(s,0.7,2.15,11.9,1.2,"Savanna smallholders plant maize on the same land year after year. The soil tires, Striga weed spreads and fertilizer keeps getting dearer. Extension advice is generic, agents are too few, and no one tells the farmer what to change on their own plot.",19,WHITE)
for i,(v,l) in enumerate([("<2 t/ha","Mean maize yield in the Guinea savanna"),("70–100%","Crop losses farmers report from Striga"),("₦50,000+","One 50 kg bag of urea")]):
    x=0.7+i*4.05; box(s,x,3.65,3.8,2.0)
    text(s,x+0.3,3.9,3.3,0.9,v,44,YEL,True,FB)
    text(s,x+0.3,4.85,3.3,0.7,l,15,SOFT)
text(s,0.7,6.0,11.9,0.6,"",15,WHITE,lines=[[("Who it hurts most: ",{'bold':True,'color':YEL}),("smallholders on 0.5 to 2 hectares in the northern and middle belt savanna, most with a basic phone and no data.",{})]])
text(s,0.7,6.6,11.9,0.3,"Sources: Heliyon 2022 · Striga farmer surveys, northern Nigeria · market reports 2025–26",10,SOFT)

# 3 INSIGHT + SOLUTION
s=prs.slides.add_slide(BL); header(s,"Key insight · Our solution","SATELLITES ALREADY REMEMBER EVERY SEASON",3)
text(s,0.7,2.1,11.9,0.8,"Farmers rarely keep records, but NASA has watched each field every few days for years. Rotawise turns that memory into one rotation choice the farmer can act on.",18,WHITE)
steps=[("01","Field memory","Each season since 2020 read as cereal like, legume like or bare, with a confidence score.","NASA HLS"),
       ("02","Soil fatigue","A 0 to 100 score from the cereal run, the greenness trend and soil carbon, nitrogen and pH.","NASA HLS · SoilGrids"),
       ("03","Climate test","Rain onset, dry spells and heat today, and rain and hot days projected for the 2040s.","NASA POWER · NEX-GDDP-CMIP6"),
       ("04","Rotation choice","The current rotation against four others, with reasons, evidence, naira, gaps and risks.","Nigerian field trials")]
for i,(n,t,d,src) in enumerate(steps):
    x=0.7+i*3.03; box(s,x,3.05,2.85,3.6)
    text(s,x+0.25,3.25,2.4,0.5,n,26,YEL,True,FB)
    text(s,x+0.25,3.8,2.4,0.5,t,20,WHITE,True)
    text(s,x+0.25,4.35,2.4,1.5,d,14,SOFT)
    c=box(s,x+0.25,5.95,2.35,0.45,BLUE,radius=0.5); text(s,x+0.25,5.95,2.35,0.45,src,11,YEL,True,align=PP_ALIGN.CENTER,anchor=MSO_ANCHOR.MIDDLE)

# 4 EXPERIENCE
s=prs.slides.add_slide(BL); header(s,"The experience","ONE CLEAR ANSWER, ON ANY PHONE",4)
j=[("BEFORE","Malam Musa in Zaria plans maize again, the fourth season in a row."),
   ("DURING","He dials the short code, picks Hausa and his farm, and gets the reply in seconds."),
   ("AFTER","His extension officer sees the same plan on the dashboard map and checks seed and soil phosphorus with him.")]
for i,(k,v) in enumerate(j):
    y=2.2+i*1.45; box(s,0.7,y,1.5,1.2,BLUE,radius=0.15)
    text(s,0.7,y,1.5,1.2,k,15,YEL,True,FB,align=PP_ALIGN.CENTER,anchor=MSO_ANCHOR.MIDDLE)
    text(s,2.45,y+0.1,5.0,1.1,v,17,WHITE,anchor=MSO_ANCHOR.MIDDLE)
text(s,0.7,6.6,7,0.3,"Farmer name is illustrative · live at rotawise-five.vercel.app",10,SOFT)
ph=box(s,8.35,2.05,4.25,4.75,RGBColor(0x02,0x0A,0x22),line=SKY,radius=0.09)
text(s,8.65,2.25,3.7,0.3,"USSD  ·  ROTAWISE",11,SOFT,True)
scr=box(s,8.65,2.7,3.65,3.0,RGBColor(0xC9,0xD6,0xB8),radius=0.04)
text(s,8.85,2.85,3.25,2.7,"Plant SOYBEAN next season, then maize. Saves 0.6-2.4 bags urea/ha (N30-N120k). Cuts Striga up to 76%. Confirm with your extension agent.",15,RGBColor(0x1D,0x24,0x14),font="Fira Mono")
text(s,8.65,5.9,3.65,0.7,"Live reply · Zaria pilot farm · urea ₦50,000/bag",11,SOFT)

# 5 INCLUSIVE
s=prs.slides.add_slide(BL); header(s,"Inclusive by design","BUILT FOR THE FARMER MOST TOOLS LEAVE OUT",5)
rows=[("Who could be excluded","The barrier","What we designed differently","How we validate"),
 ("Farmers with basic phones","No smartphone, no data","USSD on any phone, replies under 182 characters","Field test in five LGAs"),
 ("Farmers who don't read English","Language","Hausa and English now, Hausa voice next","Native speaker review of every message"),
 ("Women and tenant farmers","No land papers or records","Plot history read from orbit, nothing to fill in","Pilot with women's cooperatives"),
 ("Farmers on tiny mixed plots","30 m pixels can misread","A confidence score on every season; the farmer confirms","Test against labelled fields")]
tbl=s.shapes.add_table(5,4,Inches(0.7),Inches(2.15),Inches(11.93),Inches(4.4)).table
for c,w in enumerate([3.0,2.6,3.6,2.73]): tbl.columns[c].width=Inches(w)
for r,row in enumerate(rows):
    for c,v in enumerate(row):
        cell=tbl.cell(r,c); cell.fill.solid(); cell.fill.fore_color.rgb=BLUE if r==0 else (CARD if r%2 else RGBColor(0x0B,0x1E,0x4E))
        cell.margin_left=cell.margin_right=Inches(0.15); cell.vertical_anchor=MSO_ANCHOR.MIDDLE
        tf=cell.text_frame; tf.text=""; p=tf.paragraphs[0]; ru=p.add_run(); ru.text=v
        ru.font.name=FB if r==0 else F; ru.font.size=Pt(13 if r==0 else 15); ru.font.bold=(r==0 or c==0)
        ru.font.color.rgb=YEL if r==0 else (WHITE if c==0 else SOFT)
text(s,0.7,6.65,11,0.3,"Free to the farmer · no app download · no sign up",12,YEL,True)

# 6 IMPACT
s=prs.slides.add_slide(BL); header(s,"Impact · Feasibility","A LEGUME BREAK PAYS THE FARMER BACK",6)
for i,(v,l) in enumerate([("2.4 bags","Urea saved per hectare when soybean comes before maize, about ₦120,000"),("+68%","Maize yield after soybean vs continuous maize"),("−76%","Striga after two legume seasons")]):
    x=0.7+i*2.6; box(s,x,2.15,2.4,2.3)
    text(s,x+0.2,2.3,2.0,0.8,v,32,YEL,True,FB); text(s,x+0.2,3.15,2.05,1.25,l,12,SOFT)
text(s,0.7,4.6,7.6,0.3,"Upper values, northern Guinea savanna · NJSER 2008 · Yusuf et al. 2009 · Kureh et al. 2006",9,SOFT)
farms=[("Farm","Cereal run","Fatigue","Advice"),("Zaria","3","52","Maize → Soybean"),("Dawakin Tofa","4","60","Sorghum → Cowpea"),("Bida","mixed","53","Maize → Soybean"),("Bokkos","4","57","Maize → Soybean"),("Gwagwalada","4","58","Maize → Soybean")]
text(s,8.6,2.1,4.0,0.3,"REAL NASA DATA · 5 PILOT FARMS",11,YEL,True,FB)
t2=s.shapes.add_table(6,4,Inches(8.6),Inches(2.45),Inches(4.03),Inches(2.6)).table
for c,w in enumerate([1.25,0.7,0.65,1.43]): t2.columns[c].width=Inches(w)
for r,row in enumerate(farms):
    for c,v in enumerate(row):
        cell=t2.cell(r,c); cell.fill.solid(); cell.fill.fore_color.rgb=BLUE if r==0 else CARD
        cell.margin_left=cell.margin_right=Inches(0.06); cell.margin_top=cell.margin_bottom=Inches(0.03)
        tf=cell.text_frame; tf.text=""; ru=tf.paragraphs[0].add_run(); ru.text=v; ru.font.name=F; ru.font.size=Pt(10.5)
        ru.font.bold=(r==0); ru.font.color.rgb=YEL if r==0 else WHITE
for i,(h,b) in enumerate([("Success looks like","Farmers switching to a legume, urea bags saved, yield and Striga checked each season."),
                          ("Feasible","Open NASA data, no hardware, already live. Partners: ADP extension services, cooperatives, a USSD aggregator."),
                          ("Risks","Pixel limits on tiny plots, price swings, trust. Handled with confidence scores, editable prices and agent sign off.")]):
    x=0.7+i*4.05; text(s,x,5.15,3.8,0.35,h,15,YEL,True); text(s,x,5.55,3.8,1.3,b,13,SOFT)

# 7 PROTOTYPE + ASK
s=prs.slides.add_slide(BL); header(s,"Prototype · Next steps · The ask","WORKING TODAY ON REAL NASA DATA",7)
s.shapes.add_picture('/tmp/pd/dash_detail.png',Inches(0.7),Inches(2.1),height=Inches(4.6))
cols=[("Built and tested","Live dashboard, USSD in Hausa and English, open API. 1,824 satellite readings across five pilot farms."),
      ("Next","Check readings against labelled fields, pilot in five LGAs, add Hausa voice, Yoruba and Igbo."),
      ("The ask","Pilot access through state ADPs and cooperatives, labelled field data for testing, and a USSD short code partner.")]
for i,(h,b) in enumerate(cols):
    y=2.1+i*1.45; box(s,5.95,y,6.68,1.3)
    text(s,6.2,y+0.15,6.2,0.35,h,17,YEL,True,FB); text(s,6.2,y+0.55,6.2,0.75,b,13.5,WHITE)
text(s,5.95,6.42,6.7,0.5,"",13,YEL,lines=[[("Thank you  ·  ",{"bold":True,"color":WHITE}),("rotawise-five.vercel.app  ·  github.com/Jothankato05/Rotawise",{"bold":True,"color":YEL})]])

prs.save('/tmp/pd/Rotawise_Pitch_Deck.pptx'); print('saved')
