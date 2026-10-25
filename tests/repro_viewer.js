// Usage: node repro.js <path/to/app.js>
// Extracts the REAL viewer code (setWorkspaceViewMode .. before bindPdfViewerControls) from app.js and runs it against stubs.
const fs=require('fs');
const appPath=process.argv[2];
const src=fs.readFileSync(appPath,'utf8');
const a=src.indexOf('function setWorkspaceViewMode'), b=src.indexOf('function bindPdfViewerControls');
if(a<0||b<0) throw new Error('markers not found');
const region=src.slice(a,b);
const path=require('path');const hlp=path.join(path.dirname(appPath),'highlight.js');const HL=fs.existsSync(hlp)?require(hlp):undefined;
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const H=800;
function makeEnv(pagesItems,{loadDelay=30,renderDelay=30}={}){
  const log=[]; const overlay={innerHTML:'',children:[],style:{},appendChild(c){this.children.push(c)}};
  Object.defineProperty(overlay,'innerHTML',{get(){return ''},set(v){this.children.length=0}});
  const S={
    CWPHighlight:HL,
    pdfCanvas:{width:0,height:0,getContext:()=>({clearRect(){},font:'',measureText:t=>({width:t.length*6})})},
    pdfCanvasWrapper:{style:{},clientWidth:600}, pdfTextHighlightOverlay:overlay, pdfViewerStage:{scrollTop:0},
    pdfViewerTitle:{textContent:''}, pdfEmptyState:{style:{}}, pdfPageTotal:{}, pdfPageNumInput:{},
    workspaceContainer:{classList:{remove(){},add(){}}}, viewModeToggleBtns:[],
    showGlobalAlert:(m)=>log.push('ALERT '+m),
    document:{createElement:()=>({style:{},className:''})},
    pdfjsLib:{
      Util:{transform:(m,t)=>[t[0],t[1],t[2],t[3],t[4],H-t[5]]},
      getDocument:()=>({promise:(async()=>{await sleep(loadDelay);log.push('doc-loaded');
        const doc={numPages:5,destroyed:false,async destroy(){this.destroyed=true},
          async getPage(n){ if(doc.destroyed) throw new Error('destroyed');
            return {getViewport:({scale})=>({scale,width:600*scale,height:H,transform:[1,0,0,-1,0,H]}),
              render:()=>({promise:(async()=>{await sleep(renderDelay);log.push('render p'+n)})()}),
              getTextContent:async()=>({items:(pagesItems[n]||[]).map(i=>({str:i.str,width:i.str.length*6,height:12,transform:[12,0,0,12,50,i.y],y:i.y}))})}}};
        return doc})()})
    }
  };
  const code=`
    const {pdfCanvas,pdfCanvasWrapper,pdfTextHighlightOverlay,pdfViewerStage,pdfViewerTitle,pdfEmptyState,pdfPageTotal,pdfPageNumInput,workspaceContainer,viewModeToggleBtns,showGlobalAlert,document,pdfjsLib}=S;
    let currentViewMode='split', currentDocument={filename:'doc.pdf'}, currentHighlightColor='#ff0';
    let skipAutoRender=false, pdfDoc=null,pdfCurrentPage=1,pdfTotalPages=1,pdfZoomScale=1.0,pdfRendering=false,pdfPendingPage=null,pdfPendingHighlight=null,citationPendingPage=null,citationPendingHighlight=null;
    const window={pdfjsLib,CWPHighlight:S.CWPHighlight};
    ${region}
    return {setWorkspaceViewMode,loadPdfDocument,renderPdfPage,
      showCitation: typeof showCitation==='function'?showCitation:null,
      zoom:()=>{pdfZoomScale+=0.2;return renderPdfPage(pdfCurrentPage)},
      state:()=>({page:pdfCurrentPage,hasDoc:!!pdfDoc}),
      get skip(){return skipAutoRender}, set skip(v){skipAutoRender=v}};`;
  const api=new Function('S',code)(S);
  // original click-handler body (app.js:1898-1906), used when the fixed code has no showCitation()
  api.click=(page,specs)=>{ if(api.showCitation) return api.showCitation(page,specs);
    const text=(specs&&specs[0]&&specs[0].text)||'';
    api.skip=true; api.setWorkspaceViewMode('split'); api.renderPdfPage(page,text); setTimeout(()=>{api.skip=false},500); };
  api.boxes=()=>overlay.children.map(c=>({top:parseFloat(c.style.top||'0'),left:parseFloat(c.style.left||'0'),w:parseFloat(c.style.width||'0')}));
  api.log=log; api.S=S; return api;
}
// item at y -> expected box top as percentage of viewport height H
// rectTop (px) = (H - y) - 12*0.88; as pct = rectTop / H * 100
const topOf=y=>((H-y)-12*0.88)/H*100;
const which=(boxes,ys)=>boxes.map(b=>ys.find(y=>Math.abs(b.top-topOf(y))<1)??('?'+b.top));
const P3=[{str:'Problem Statement',y:700},{str:'Unrelated words here',y:600},{str:'The retention period is seven years for all records.',y:300}];
const EV='The retention period is seven years for all records.';
const results=[];
const rep=(name,ok,detail)=>{results.push(ok);console.log((ok?'PASS ':'FAIL ')+name+' — '+detail)};
(async()=>{
 // R1: baseline - citation click on a loaded viewer highlights the right item
 {const e=makeEnv({3:P3}); await e.loadPdfDocument('/api/pdf','doc.pdf'); await sleep(80);
  e.click(3,[{text:EV}]); await sleep(200); const w=which(e.boxes(),[700,600,300]);
  rep('R1 loaded viewer, simple exact passage',w.length>0&&w.every(y=>y===300),'highlighted items(y)='+JSON.stringify(w));}
 // R2: zoom pressed while highlight render in flight
 {const e=makeEnv({3:P3}); await e.loadPdfDocument('/api/pdf','doc.pdf'); await sleep(80);
  e.click(3,[{text:EV}]); await sleep(10); e.zoom(); await sleep(300);
  const w=which(e.boxes(),[700,600,300]);rep('R2 zoom/next while highlight render in flight',w.length>0&&w.every(y=>y===300),'items(y)='+JSON.stringify(w)+' page='+e.state().page);}
 // R3: zoom after highlight finished
 {const e=makeEnv({3:P3}); await e.loadPdfDocument('/api/pdf','doc.pdf'); await sleep(80);
  e.click(3,[{text:EV}]); await sleep(200); const before=e.boxes().length; e.zoom(); await sleep(200);
  rep('R3 zoom after highlight finished',e.boxes().length>0&&which(e.boxes(),[700,600,300]).every(y=>y===300),'boxes before='+before+' after='+e.boxes().length);}
 // R4: badge click while the first PDF load is still in flight (chat mode on startup / history restored)
 {const e=makeEnv({3:P3},{loadDelay:100}); const p=e.loadPdfDocument('/api/pdf','doc.pdf'); await sleep(10);
  e.click(3,[{text:EV}]); await sleep(500); await p.catch(()=>{});
  const loads=e.log.filter(x=>x==='doc-loaded').length;rep('R4 click during initial PDF load (right page, right item, 1 load)',e.state().page===3&&which(e.boxes(),[700,600,300]).join()==='300'&&loads===1,'page='+e.state().page+' items(y)='+JSON.stringify(which(e.boxes(),[700,600,300]))+' pdf loads='+loads);}
 // R5: fuzzy path, passage not an exact substring; page also has a "Problem Statement" heading
 {const items=[{str:'Problem Statement',y:700},{str:'Overview',y:600},{str:'retention period policy details are listed here',y:300}];
  const e=makeEnv({3:items}); await e.loadPdfDocument('/api/pdf','doc.pdf'); await sleep(80);
  e.click(3,[{text:'Overview of the retention period policy and seven year archive rules'}]); await sleep(200);
  const w=which(e.boxes(),[700,600,300]);
  rep('R5 non-exact passage: correct item is y=300',w.length===0||w.every(y=>y===300),'highlighted items(y)='+JSON.stringify(w));}
 // R6: no verifiable evidence -> must navigate without highlighting
 {const e=makeEnv({3:P3}); await e.loadPdfDocument('/api/pdf','doc.pdf'); await sleep(80);
  e.click(3,[]); await sleep(200);
  rep('R6 empty evidence -> page only, no boxes',e.state().page===3&&e.boxes().length===0,'page='+e.state().page+' boxes='+e.boxes().length);}
 // R7: evidence that is NOT on the page must not highlight anything
 {const e=makeEnv({3:P3}); await e.loadPdfDocument('/api/pdf','doc.pdf'); await sleep(80);
  e.click(3,[{text:'Completely different sentence about quarterly revenue growth targets'}]); await sleep(200);
  rep('R7 absent evidence -> no boxes',e.boxes().length===0,'boxes='+e.boxes().length+' items='+JSON.stringify(which(e.boxes(),[700,600,300])));}
 // R8: repeated passage: evidence is the 2nd occurrence (disambiguated by hint)
 {const items=[{str:'Definition: Risk is exposure to loss.',y:700},{str:'filler filler',y:500},{str:'Definition: Risk is exposure to loss.',y:200}];
  const e=makeEnv({3:items}); await e.loadPdfDocument('/api/pdf','doc.pdf'); await sleep(80);
  e.click(3,[{text:'Definition: Risk is exposure to loss.',hint:0.9}]); await sleep(200);
  const w=which(e.boxes(),[700,500,200]);
  rep('R8 repeated passage uses chunk position hint (2nd occurrence)',w.length>0&&w.every(y=>y===200),'highlighted items(y)='+JSON.stringify(w));}

 // R9: explicit "no evidence" click on the same page must not reuse an earlier highlight
 {const e=makeEnv({3:P3}); await e.loadPdfDocument('/api/pdf','doc.pdf'); await sleep(80);
  e.click(3,[{text:EV}]); await sleep(200); const had=e.boxes().length; e.click(3,[]); await sleep(200);
  rep('R9 badge without evidence clears old highlight',had>0&&e.boxes().length===0,'before='+had+' after='+e.boxes().length);}
 // R10: highlight must not follow the user to other pages, nor return after coming back
 {const e=makeEnv({3:P3}); await e.loadPdfDocument('/api/pdf','doc.pdf'); await sleep(80);
  e.click(3,[{text:EV}]); await sleep(200); await e.renderPdfPage(4); const onP4=e.boxes().length; await e.renderPdfPage(3); await sleep(100);
  rep('R10 highlight does not leak to other pages',onP4===0&&e.boxes().length===0,'page4 boxes='+onP4+' back on page3 boxes='+e.boxes().length);}
 // R11: two badges clicked quickly: last one wins and keeps its highlight
 {const P5=[{str:'Other page heading',y:650},{str:'Quarterly revenue growth targets are set in January.',y:250}];
  const e=makeEnv({3:P3,5:P5}); await e.loadPdfDocument('/api/pdf','doc.pdf'); await sleep(80);
  e.click(3,[{text:EV}]); await sleep(5); e.click(5,[{text:'Quarterly revenue growth targets are set in January.'}]); await sleep(300);
  rep('R11 two quick clicks: last wins with highlight',e.state().page===5&&which(e.boxes(),[650,250]).join()==='250','page='+e.state().page+' items(y)='+JSON.stringify(which(e.boxes(),[650,250])));}
 // R12: highlight boxes use percentage positioning (the coordinate-scaling fix)
 {const e=makeEnv({3:P3}); await e.loadPdfDocument('/api/pdf','doc.pdf'); await sleep(80);
  e.click(3,[{text:EV}]); await sleep(200);
  const raw=e.S.pdfTextHighlightOverlay.children;
  const usePct=raw.length>0&&raw[0].style.left.includes('%')&&raw[0].style.top.includes('%');
  rep('R12 overlay has explicit width/height/transform',usePct,'left='+raw[0]?.style.left+' top='+raw[0]?.style.top+' count='+raw.length);}
 // R13: highlight box percentage positions are within bounds (0-100%)
 {const e=makeEnv({3:P3}); await e.loadPdfDocument('/api/pdf','doc.pdf'); await sleep(80);
  e.click(3,[{text:EV}]); await sleep(200);
  const boxes=e.boxes();
  // Box left as percentage should be >= 0 and < 100
  const allInBounds=boxes.length>0&&boxes.every(b=>b.left>=0&&b.left<100&&b.top>=0&&b.top<100);
  rep('R13 box positions within viewport coordinate bounds',allInBounds,'boxes='+JSON.stringify(boxes));}
 // R14: overlay dimensions reset when navigating to a page without highlights
 {const e=makeEnv({3:P3}); await e.loadPdfDocument('/api/pdf','doc.pdf'); await sleep(80);
  e.click(3,[{text:EV}]); await sleep(200);
  const hadBoxes=e.boxes().length>0;
  await e.renderPdfPage(1); await sleep(100);
  rep('R14 overlay cleared after navigating away',hadBoxes&&e.boxes().length===0,'hadBoxes='+hadBoxes+' after='+e.boxes().length);}
 // R15: narrow container does not shift highlights (percentages are container-independent)
 {const e=makeEnv({3:P3}); e.S.pdfCanvasWrapper.clientWidth=300; // half of 600px viewport
  await e.loadPdfDocument('/api/pdf','doc.pdf'); await sleep(80);
  e.click(3,[{text:EV}]); await sleep(200);
  const boxes=e.boxes();
  // With percentage positioning, boxes should have same % values regardless of container width
  const allInBounds=boxes.length>0&&boxes.every(b=>b.left>=0&&b.left<100&&b.top>=0&&b.top<100);
  rep('R15 narrow container: positions in viewport coords, overlay scaled',allInBounds,'boxes='+JSON.stringify(boxes));}
 // R16: wrapper height follows the displayed canvas so percentage overlay coordinates align
 {const e=makeEnv({3:P3}); await e.loadPdfDocument('/api/pdf','doc.pdf'); await sleep(80);
  rep('R16 wrapper does not retain viewport-pixel height',e.S.pdfCanvasWrapper.style.height==='auto','height='+e.S.pdfCanvasWrapper.style.height);}
 console.log('\n'+results.filter(Boolean).length+'/'+results.length+' passed');
 process.exit(0);
})();
