import fs from "node:fs/promises";
import pptxgen from "pptxgenjs";
const [input, output] = process.argv.slice(2);
const {outline, sources} = JSON.parse(await fs.readFile(input,"utf8"));
if (!Array.isArray(outline.slides) || outline.slides.length !== outline.slide_count || outline.slide_count > 12) throw Error("INVALID_OUTLINE");
const pptx = new pptxgen();
pptx.layout="LAYOUT_WIDE";
pptx.title=outline.presentation_title;
pptx.author="Memora AI";
pptx.lang=outline.language==="zh"?"zh-CN":"en-US";
pptx.theme={headFontFace:"WenQuanYi Zen Hei",bodyFontFace:"WenQuanYi Zen Hei",lang:pptx.lang};
for (const [i, item] of outline.slides.entries()) {
  const slide=pptx.addSlide(); slide.background={color:"F8FAF6"};
  slide.addShape(pptx.ShapeType.rect,{x:0,y:0,w:0.18,h:7.5,fill:{color:"345B49"},line:{color:"345B49"}});
  const text=(value,options)=>slide.addText(value,{fontFace:"WenQuanYi Zen Hei",color:"233B31",margin:0,breakLine:false,...options});
  // Explicit wrapping by estimated display width keeps CJK/Latin within fixed boxes.
  const wrap=(value,limit)=>{
    let lines=[""],width=0;
    // Keep ISO dates and ordinary words intact; CJK remains character-wrapped.
    const tokens=value.match(/\d{4}-\d{2}-\d{2}|[A-Za-z0-9][A-Za-z0-9_.:/-]*|[\s\S]/gu)||[];
    for (const token of tokens) {
      if(token==="\n"){lines.push("");width=0;continue;}
      const units=[...token].reduce((sum,ch)=>sum+(ch.codePointAt(0)>255?2:1),0);
      const pieces=units>limit?[...token]:[token];
      for(const piece of pieces){
        const size=[...piece].reduce((sum,ch)=>sum+(ch.codePointAt(0)>255?2:1),0);
        if(width+size>limit){lines.push("");width=0;}
        lines[lines.length-1]+=piece;width+=size;
      }
    }return lines.join("\n");
  };
  text(wrap(item.title,64),{x:0.7,y:0.55,w:12,h:1.1,fontSize:22,bold:true});
  const columns=["two_column","risk_matrix"].includes(item.type)?2:1;
  for(const [j,bullet] of item.bullets.entries()){
    if(bullet.length>160)throw Error("TEXT_OVERFLOW");
    const col=columns===2?j%2:0,row=columns===2?Math.floor(j/2):j;
    const body=wrap(bullet,columns===2?42:88);
    if(body.split("\n").length>(columns===2?4:2))throw Error("TEXT_OVERFLOW");
    text(body,{x:0.8+col*6.1,y:1.85+row*(columns===2?1.45:0.68),w:columns===2?5.7:11.7,h:columns===2?1.3:0.63,fontSize:columns===2?18:17});
  }
  const refs=item.source_refs.map(ref=>sources.find(s=>s.ref===ref));
  if(refs.some(s=>!s))throw Error("INVALID_SOURCE");
  text(refs.map((s,j)=>`[${j+1}] ${s.title.slice(0,18)}`).join(" | "),{x:0.7,y:6.65,w:11.7,h:0.4,fontSize:9});
  text(`${i+1} / ${outline.slide_count}`,{x:11.8,y:7.08,w:1,h:0.2,fontSize:10});
  slide.addNotes([item.speaker_notes,JSON.stringify(item.statements||[]),...refs.map(s=>JSON.stringify(s))].join("\n"));
}
await pptx.writeFile({fileName:output});
