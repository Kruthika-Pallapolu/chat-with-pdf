const assert=require('assert'); const {locate}=require('../public/highlight.js');
let pass=0,fail=0; const t=(n,f)=>{try{f();pass++;console.log('ok   '+n)}catch(e){fail++;console.log('FAIL '+n+'\n     '+e.message)}};
const it=s=>({str:s}); const itemsOf=r=>r.segments.map(s=>s.itemIndex);
t('passage split across 3 items (no spaces between items)',()=>{
  const items=[it('Intro words'),it('Records must be re'),it('tained for seven '),it('years after closure.'),it('Tail')];
  const r=locate(items,'Records must be retained for seven years after closure.'); assert(r.ok); assert.deepStrictEqual(itemsOf(r),[1,2,3]);});
t('whitespace-only items between words',()=>{
  const items=[it('The system'),it(' '),it('shall retain'),it('  '),it('records for audit.')];
  const r=locate(items,'The system shall retain records for audit.'); assert(r.ok); assert.deepStrictEqual(itemsOf(r),[0,2,4]);});
t('line-end hyphen and ligature',()=>{
  const items=[it('Policies are re-'),it('viewed by the ﬁnance department yearly.')];
  const r=locate(items,'Policies are re-\nviewed by the finance department yearly.'); assert(r.ok);});
t('offset accuracy: only the matched slice of an item is returned',()=>{
  const items=[it('Heading text here. The retention period is seven years. More text follows.')];
  const r=locate(items,'The retention period is seven years.'); assert(r.ok);
  const s=r.segments[0]; assert.strictEqual(items[0].str.slice(s.start,s.end),'The retention period is seven years');});
t('target deep in the page (old offset-drift case: item 20 of 30)',()=>{
  const items=Array.from({length:30},(_,i)=>it(`Line number ${i} has some words`));
  const r=locate(items,items[20].str+' '+items[21].str); assert(r.ok); assert.deepStrictEqual(itemsOf(r),[20,21]);});
t('absent evidence -> ok:false (no guess)',()=>{
  const r=locate([it('Problem Statement'),it('Unrelated words here')],'Completely different sentence about quarterly revenue'); assert.strictEqual(r.ok,false); assert.strictEqual(r.reason,'not-found');});
t('paraphrase that is not verbatim -> ok:false',()=>{
  const r=locate([it('Records must be retained for seven years after closure.')],'Keep documentation for seven years once an account ends'); assert.strictEqual(r.ok,false);});
t('too-short evidence refused',()=>{ assert.strictEqual(locate([it('seven years')],'seven years').ok,false); });
const rep=[it('Definition: Risk is exposure to loss.'),it('filler '.repeat(40)),it('Definition: Risk is exposure to loss.')];
t('repeated phrase without hint -> ambiguous, no highlight',()=>{ const r=locate(rep,'Definition: Risk is exposure to loss.'); assert.strictEqual(r.ok,false); assert.strictEqual(r.reason,'ambiguous');});
t('repeated phrase with hint near 2nd occurrence -> 2nd item',()=>{ const r=locate(rep,'Definition: Risk is exposure to loss.',0.95); assert(r.ok); assert.deepStrictEqual(itemsOf(r),[2]);});
t('repeated phrase with hint near 1st occurrence -> 1st item',()=>{ const r=locate(rep,'Definition: Risk is exposure to loss.',0.02); assert(r.ok); assert.deepStrictEqual(itemsOf(r),[0]);});
t('repeated phrase, hint midway (equidistant) -> ambiguous',()=>{ const r=locate(rep,'Definition: Risk is exposure to loss.',0.5); assert.strictEqual(r.ok,false);});
t('empty / missing items',()=>{ assert.strictEqual(locate([],'some long enough evidence string here').ok,false); assert.strictEqual(locate(null,'some long enough evidence string here').ok,false);});
console.log(`\n${pass} passed, ${fail} failed`); process.exit(fail?1:0);
