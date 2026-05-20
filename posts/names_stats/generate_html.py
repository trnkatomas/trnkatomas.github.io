#!/usr/bin/env python3
"""Generate a self-contained bump-chart HTML for Czech baby-name rankings."""

import csv, json
from pathlib import Path

YEARS = [2016, 2017, 2018, 2019, 2022, 2023, 2024]


def read_data():
    data = {}
    with open('names.csv', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            y, reg, g = int(r['year']), r['region'], r['gender']
            try:
                rank = int(r['rank'].split('-')[0])
            except (ValueError, AttributeError):
                rank = 9999
            data.setdefault(y, {}).setdefault(reg, {'boy': [], 'girl': []})
            data[y][reg][g].append({'rank': rank, 'name': r['name']})
    for y in data:
        for reg in data[y]:
            for g in ('boy', 'girl'):
                data[y][reg][g].sort(key=lambda x: x['rank'])
    return data


def main():
    data = read_data()
    all_regions = sorted({r for y in data for r in data[y]})
    regions = ['Česko'] + [r for r in all_regions if r != 'Česko']

    out = {}
    for y in YEARS:
        out[y] = {}
        for reg in regions:
            e = data.get(y, {}).get(reg, {'boy': [], 'girl': []})
            out[y][reg] = {'boy': e['boy'][:100], 'girl': e['girl'][:100]}

    data_json  = json.dumps(out, ensure_ascii=False, separators=(',', ':'))
    region_opts = '\n'.join(f'      <option value="{r}">{r}</option>' for r in regions)

    html = HTML_TEMPLATE.replace('%%DATA%%', data_json).replace('%%REGIONS%%', region_opts)
    Path('index.html').write_text(html, encoding='utf-8')
    print(f'Generated index.html  ({len(html)//1024} KB)')


# ---------------------------------------------------------------------------
HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="cs">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Nejoblíbenější dětská jména v ČR</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#fefef8;font-family:'Segoe UI',system-ui,sans-serif}

/* ── top toolbar ── */
#toolbar{
  position:sticky;top:0;z-index:50;
  background:#fff;border-bottom:1px solid #e2e8f0;
  padding:8px 16px;display:flex;align-items:center;gap:10px;
  flex-wrap:wrap;box-shadow:0 1px 4px rgba(0,0,0,.06)
}
.tb-sep{color:#cbd5e1;user-select:none}
.tb-lbl{font-size:12px;font-weight:600;color:#64748b;white-space:nowrap}
.btns{display:flex;gap:3px}
.btn{
  padding:5px 11px;border:1px solid #e2e8f0;border-radius:6px;
  background:#f8fafc;cursor:pointer;font-size:13px;font-weight:500;color:#475569;
  transition:background .12s,color .12s;white-space:nowrap
}
.btn:hover{background:#f1f5f9}
.btn.boy {background:#1d4ed8;color:#fff;border-color:#1d4ed8}
.btn.girl{background:#be123c;color:#fff;border-color:#be123c}
select{padding:5px 8px;border:1px solid #e2e8f0;
  border-radius:6px;font-size:13px;background:#f8fafc;color:#334155}
.tb-note{font-size:11px;color:#94a3b8;margin-left:auto;white-space:nowrap}
.search-wrap{position:relative;display:flex;align-items:center}
#sq{
  padding:5px 28px 5px 10px;border:1px solid #e2e8f0;border-radius:6px;
  font-size:13px;background:#f8fafc;color:#334155;width:160px;
  transition:border-color .15s,width .2s
}
#sq:focus{outline:none;border-color:#94a3b8;width:200px}
#sq::-webkit-search-cancel-button{cursor:pointer}

#wrap{overflow-x:auto;padding:16px 16px 48px}

/* ── SVG text / path classes ── */
.yr  {font:700 15px/1 'Segoe UI',system-ui;fill:#1e293b}
.gap {font:10px/1 'Segoe UI',system-ui;fill:#94a3b8;text-anchor:middle}
.nm  {font:13px/1 'Segoe UI',system-ui;cursor:default}
.nm.boy {fill:#2563eb}  .nm.girl{fill:#be123c}
.nm.dim {opacity:.35}   .nm.hi  {font-weight:700}

.ln           {fill:none;stroke-width:1.4}
.ln.boy       {stroke:#2563eb}
.ln.girl      {stroke:#be123c}
.ln.norm      {opacity:.28}
.ln.gapyr     {opacity:.18;stroke-dasharray:5 4}
.ln.dim       {opacity:.10}
.ln.hi        {opacity:.88;stroke-width:2.6}
.ln.gapyr.hi  {opacity:.65}
</style>
</head>
<body>

<div id="toolbar">
  <span class="tb-lbl">Pohlaví:</span>
  <div class="btns">
    <button class="btn boy" id="bb" onclick="setG('boy')">Chlapci</button>
    <button class="btn"     id="bg" onclick="setG('girl')">Dívky</button>
  </div>
  <span class="tb-sep">|</span>
  <label class="tb-lbl" for="rs">Kraj:</label>
  <select id="rs" onchange="setR(this.value)">
%%REGIONS%%
  </select>
  <span class="tb-sep">|</span>
  <label class="tb-lbl" for="ns">Top:</label>
  <select id="ns" onchange="setN(+this.value)">
    <option value="10">10</option>
    <option value="20">20</option>
    <option value="30" selected>30</option>
    <option value="50">50</option>
  </select>
  <span class="tb-sep">|</span>
  <div class="search-wrap">
    <input id="sq" type="search" placeholder="Hledat jméno…" oninput="onSearch(this.value)" autocomplete="off">
  </div>
  <span class="tb-note" id="nt">⚠ 2016–2019: kumulativní data &nbsp;·&nbsp; 2022–2024: roční narozených</span>
</div>

<div id="wrap"><svg id="viz"></svg></div>

<script>
const DATA  = %%DATA%%;
const YEARS = [2016,2017,2018,2019,2022,2023,2024];

// layout
const CW=128, GW=54, BIG=74, ROW=19, HDR=44, MT=14, ML=24, MB=28;

let G='boy', R='Česko', N=30, hovered=null, searchQ='';

function setG(g){
  G=g;
  document.getElementById('bb').className='btn'+(g==='boy' ?' boy' :'');
  document.getElementById('bg').className='btn'+(g==='girl'?' girl':'');
  render();
}
function setR(r){ R=r; render(); }
function setN(n){ N=n; render(); }

function visYears(){ return R==='Česko'?YEARS:YEARS.filter(y=>y>=2022); }

function colX(yi,yrs){
  let x=ML;
  for(let i=0;i<yi;i++){
    x+=CW+GW;
    if(yrs[i]===2019&&yrs[i+1]===2022) x+=BIG;
  }
  return x;
}
function nameY(i){ return MT+HDR+i*ROW+ROW*.75; }

function getNames(yr){
  return (DATA[yr]?.[R]?.[G]||DATA[yr]?.['Česko']?.[G]||[]).slice(0,N);
}

// ── render (called on state change) ────────────────────────────────────────
function render(){
  const yrs=visYears();
  const ydata={}, npos={};

  yrs.forEach((yr,yi)=>{
    const names=getNames(yr);
    ydata[yr]=names;
    const x=colX(yi,yrs);
    names.forEach((e,i)=>{
      const y=nameY(i);
      (npos[e.name]=npos[e.name]||[]).push({yi,yr,x,y});
    });
  });

  const W=colX(yrs.length,yrs)+ML;
  const H=MT+HDR+N*ROW+MB;
  const svg=document.getElementById('viz');
  svg.setAttribute('width',W);
  svg.setAttribute('height',H);
  svg.setAttribute('viewBox',`0 0 ${W} ${H}`);

  const lines=[], texts=[];

  // connectors (drawn first, appear behind text)
  for(const [name,pos] of Object.entries(npos)){
    for(let i=0;i<pos.length-1;i++){
      const a=pos[i], b=pos[i+1];
      if(b.yi!==a.yi+1) continue;
      const isGap=(a.yr===2019&&b.yr===2022);
      const x1=a.x+CW, x2=b.x, cpx=(x1+x2)/2;
      const d=`M${x1},${a.y}C${cpx},${a.y} ${cpx},${b.y} ${x2},${b.y}`;
      const base=isGap?'gapyr':'norm';
      lines.push(`<path class="ln ${G} ${base}" d="${d}" data-name="${name}"/>`);
    }
  }

  // year headers
  yrs.forEach((yr,yi)=>{
    const x=colX(yi,yrs);
    texts.push(`<text class="yr" x="${x}" y="${MT+28}">${yr}</text>`);
    if(yr===2022&&yrs.includes(2019)){
      const px=colX(yi-1,yrs)+CW;
      texts.push(`<text class="gap" x="${(px+x)/2}" y="${MT+28}">2020–21</text>`);
    }
    ydata[yr].forEach((e,i)=>{
      texts.push(`<text class="nm ${G}" x="${x}" y="${nameY(i)}" data-name="${e.name}" data-rank="${e.rank}">${e.name}</text>`);
    });
  });

  svg.innerHTML=lines.join('')+texts.join('');
  svg.addEventListener('mouseover',onHover,{passive:true});
  svg.addEventListener('mouseleave',onLeave,{passive:true});
  if(searchQ) applySearch(searchQ);
}

// ── search ─────────────────────────────────────────────────────────────────
function onSearch(q){
  searchQ=q.trim();
  hovered=null;
  // reset any rank labels left by hover
  document.querySelectorAll('#viz text[data-name]').forEach(el=>{
    el.textContent=el.dataset.name;
  });
  searchQ ? applySearch(searchQ) : clearHover();
}

function applySearch(q){
  const lq=q.toLowerCase();
  const showRank=q.length>=3;
  document.querySelectorAll('#viz [data-name]').forEach(el=>{
    const match=el.dataset.name.toLowerCase().includes(lq);
    const cls=el.classList;
    cls.remove('norm');
    if(match){
      cls.add('hi'); cls.remove('dim');
      if(el.tagName==='text'&&el.dataset.rank)
        el.textContent=showRank ? el.dataset.rank+'. '+el.dataset.name : el.dataset.name;
    } else {
      cls.add('dim'); cls.remove('hi');
    }
  });
}

// ── hover (DOM-only, no full re-render) ────────────────────────────────────
function onHover(e){
  if(searchQ) return;  // search takes precedence
  const el=e.target.closest('[data-name]');
  const name=el?.dataset.name;
  if(!name||name===hovered) return;
  hovered=name;
  applyHover(name);
}
function onLeave(){
  if(searchQ) return;
  hovered=null; clearHover();
}

function applyHover(name){
  document.querySelectorAll('#viz [data-name]').forEach(el=>{
    const match=el.dataset.name===name;
    const cls=el.classList;
    if(match){
      cls.add('hi'); cls.remove('dim','norm');
      if(el.tagName==='text'&&el.dataset.rank)
        el.textContent=el.dataset.rank+'. '+name;
    } else {
      cls.add('dim'); cls.remove('hi','norm');
    }
  });
}
function clearHover(){
  document.querySelectorAll('#viz [data-name]').forEach(el=>{
    const cls=el.classList;
    cls.remove('hi','dim');
    if(el.tagName==='path'&&!cls.contains('gapyr')) cls.add('norm');
    if(el.tagName==='text') el.textContent=el.dataset.name;
  });
}

render();
</script>
</body>
</html>
"""

if __name__ == '__main__':
    main()
