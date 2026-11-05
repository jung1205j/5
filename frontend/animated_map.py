"""Self-contained Leaflet/Canvas animation for a Streamlit iframe.

No personal data is sent to external services. Only the OpenStreetMap raster tile endpoint and Leaflet JS/CSS CDN are accessed.
Follow the OSMF Tile Usage Policy; for high traffic, use a dedicated tile provider.
"""
from __future__ import annotations

import json


def build_map_html(people, result: dict, geo: dict | None, selected_dong: str, focus_mode: str = "selected") -> str:
    """Render local-scenario steps in an isolated iframe, with client-side playback."""
    # Keep only the fields required for the map. Render text using textContent,
    # never innerHTML from dataset fields.
    person_data = [
        {
            "id": int(p["id"]), "lat": float(p["lat"]), "lng": float(p["lng"]),
            "dong": str(p["dong"]), "dong_code": str(p["dong_code"]), "group": str(p["group"]),
        }
        for p in people.to_dict("records")
    ]
    payload = {
        "people": person_data,
        "steps": result.get("steps", []),
        "geo": geo,
        "dong": str(selected_dong),
        "dong_code": str(result.get("dong_code", "")),
        "focus_mode": "selected" if focus_mode == "selected" else "all",
        "is_demo": bool(result.get("_is_demo", False)),
    }
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    # Prevent an uploaded field from terminating the script tag.
    raw = raw.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")

    html = r'''<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<style>
:root{--bg:#091a29;--line:#284159;--ink:#eef6ff;--muted:#a0b4c9;--teal:#37e2c2;--amber:#ffc078}
*{box-sizing:border-box}body{margin:0;color:var(--ink);font-family:system-ui,-apple-system,'Malgun Gothic','Apple SD Gothic Neo',sans-serif;background:#091a29}
.app{overflow:hidden;border:1px solid #263e50;border-radius:17px;background:#081827}
.stage{height:462px;position:relative;background:radial-gradient(circle at center,#13283a,#081827)}
#map{height:100%;width:100%;z-index:0}#load{position:absolute;z-index:5;inset:0;display:flex;align-items:center;justify-content:center;pointer-events:none;color:#bdd4e6;font-size:14px;background:#0c2030}
.leaflet-control-attribution{background:rgba(9,25,39,.83)!important;color:#b1c2d3!important;font-size:9px!important}
.leaflet-control-attribution a{color:#c5e8ed!important}
.leaflet-container{background:#0b1b2b!important}
/* Dark-looking raster backdrop without a basemap provider API key. Keep overlays unchanged. */
.leaflet-tile-pane{filter:invert(1) hue-rotate(180deg) brightness(.76) contrast(.88) saturate(.72)}
.hud{position:absolute;top:15px;left:15px;z-index:450;padding:12px 15px;border:1px solid rgba(116,157,170,.4);border-radius:12px;background:rgba(6,20,32,.88);backdrop-filter:blur(12px);pointer-events:none;box-shadow:0 8px 25px #071a2877;max-width:230px}
.hud small{font-size:10px;text-transform:uppercase;letter-spacing:.12em;color:#9ebdcf;font-weight:750}
.hud strong{display:block;font-size:22px;margin:2px 0 3px;letter-spacing:-.05em}
.hud .sub{font-size:12px;color:#c3d7e7}
.hud .live{display:inline-block;height:7px;width:7px;border-radius:50%;background:#38d9be;box-shadow:0 0 0 4px #38d9be20;margin-right:7px}
.legend{position:absolute;bottom:16px;left:15px;z-index:450;border:1px solid #355065;border-radius:10px;padding:10px 12px;background:rgba(6,19,31,.93);display:flex;gap:14px;flex-wrap:wrap;font-size:11px;color:#d6e6ef}
.legend span{white-space:nowrap}.dot{display:inline-block;height:9px;width:9px;margin-right:5px;border-radius:50%}.grey{background:#72849b}.teal{background:#37e2c2}.amber{background:#ffc078}
.controls{padding:14px 17px 15px;border-top:1px solid #2c4659;background:#0d2132}
.buttons{display:flex;align-items:center;gap:9px;flex-wrap:wrap}
button{padding:10px 14px;color:#e9f6ff;background:#183249;border:1px solid #35536b;border-radius:9px;cursor:pointer;font-size:12px;font-weight:750;white-space:nowrap}
button:hover{background:#24506a;border-color:#4bc8b8}button:focus-visible,input:focus-visible,select:focus-visible{outline:2px solid #7af5e0;outline-offset:2px}
button.primary{color:#072332;background:#46ddc6;border-color:#46ddc6;min-width:108px}button.primary:hover{background:#a3f5e8}
.speed{margin-left:auto;display:flex;gap:8px;align-items:center;font-size:12px;color:#b7cadd}
select{color:#eaf5ff;border:1px solid #35536b;background:#183249;border-radius:8px;padding:9px 6px}
.timeline{display:flex;align-items:center;gap:11px;margin-top:14px}
input[type=range]{flex:1;min-width:40px;accent-color:#48dfc4;cursor:pointer}
#stepLabel{color:#d9ebf6;min-width:108px;text-align:right;font-size:12px;font-weight:700}
.numbers{display:flex;gap:15px;margin-top:9px;flex-wrap:wrap;color:#9eb5c9;font-size:12px}.numbers b{color:#f0f9ff}
.leaflet-popup-content-wrapper{background:#0f2636!important;color:#e8f4ff!important;border:1px solid #345069;border-radius:10px!important}
.leaflet-popup-tip{background:#0f2636!important}
@media(max-width:620px){.stage{height:380px}.hud{padding:8px}.legend{font-size:10px;gap:7px}.buttons{gap:5px}button{font-size:11px;padding:9px}.speed{margin-left:0}.controls{padding:12px}}
</style></head><body>
<div class="app"><div class="stage"><div id="map"></div><div id="load">지도를 준비하고 있습니다…</div>
<div class="hud"><small><span class="live"></span>SIMULATION TIMELINE</small><div class="sub" id="locationName" style="margin-top:6px;color:#41e5ce;font-weight:700"></div><strong id="hudNumber">0명</strong><div class="sub" id="hudSubtitle">아직 소식을 듣지 않았습니다</div></div>
<div class="legend"><span><i class="dot grey"></i>미노출</span><span><i class="dot teal"></i>이전 단계 노출</span><span><i class="dot amber"></i>이번 단계 신규</span></div></div>
<div class="controls"><div class="buttons"><button id="reset">⏮ 처음</button><button id="back">← 이전</button><button class="primary" id="play">▶ 재생</button><button id="forward">다음 →</button><div class="speed"><label for="speed">속도</label><select id="speed"><option value="1600">느리게</option><option value="950" selected>보통</option><option value="400">빠르게</option></select></div></div>
<div class="timeline"><input id="timeline" type="range" min="0" max="0" value="0" aria-label="확산 단계"/><strong id="stepLabel">시작 전</strong></div>
<div class="numbers"><span>누적 노출 <b id="total">0</b>명</span><span>이번 단계 신규 <b id="new">0</b>명</span><span>전체 <b id="pop">0</b>명</span><span id="ratio">0.0% 도달</span></div></div></div>
<script type="application/json" id="map-data">__PAYLOAD__</script>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
(()=>{
'use strict';
const q = id => document.getElementById(id);
const data = JSON.parse(q('map-data').textContent);
const points = Array.isArray(data.people)?data.people:[];
const steps = Array.isArray(data.steps)?data.steps:[];
let step=0, timer=null, map=null;
const markers=new Map();
let reached=new Set(), newest=new Set();
function stop(){if(timer!==null){clearInterval(timer);timer=null;}q('play').textContent='▶ 재생';}
function update(n){
  step=Math.min(Math.max(0,n),steps.length);
  reached=new Set();newest=new Set();
  for(let i=0;i<step;i++)for(const id of (steps[i]||[]))reached.add(String(id));
  if(step>0)for(const id of (steps[step-1]||[]))newest.add(String(id));
  for(const [id,p] of markers){const col=newest.has(id)?'#ffc078':reached.has(id)?'#37e2c2':'#72849b';p.setStyle({color:col,fillColor:col,opacity:1,fillOpacity:reached.has(id)?0.92:0.46,radius:newest.has(id)?5:reached.has(id)?3.9:3.2});}
  q('total').textContent=reached.size.toLocaleString('ko-KR');
  q('new').textContent=newest.size.toLocaleString('ko-KR');
  q('pop').textContent=points.length.toLocaleString('ko-KR');
  q('ratio').textContent=points.length?(reached.size/points.length*100).toFixed(1)+'% 도달':'0.0% 도달';
  q('hudNumber').textContent=reached.size.toLocaleString('ko-KR')+'명';
  q('hudSubtitle').textContent=step===0?'아직 소식을 듣지 않았습니다':`전체 ${steps.length}단계 중 ${step}단계 · 신규 ${newest.size}명`;
  q('timeline').value=step;
  q('stepLabel').textContent=step===0?'확산 시작 전':`${step} / ${steps.length} 단계`;
  if(step===steps.length)stop();
}
function play(){if(timer!==null){stop();return;}if(step===steps.length)update(0);q('play').textContent='Ⅱ 일시정지';timer=setInterval(()=>{update(step+1);},Number(q('speed').value));update(step+1);}
q('play').addEventListener('click',play);
q('reset').addEventListener('click',()=>{stop();update(0)});
q('back').addEventListener('click',()=>{stop();update(step-1)});
q('forward').addEventListener('click',()=>{stop();update(step+1)});
q('timeline').addEventListener('input',ev=>{stop();update(Number(ev.target.value))});
q('speed').addEventListener('change',()=>{if(timer!==null){stop();play()}});
q('timeline').max=steps.length;
if(typeof L==='undefined'){
 q('load').textContent='지도 라이브러리를 불러오지 못했습니다. 인터넷 연결을 확인하거나 아래 호환 지도를 이용하세요.';
 return;
}
try{
  const meanLat=points.reduce((s,p)=>s+p.lat,0)/(points.length||1)||37.56;
  const meanLng=points.reduce((s,p)=>s+p.lng,0)/(points.length||1)||126.92;
  map=L.map('map',{zoomControl:false,preferCanvas:true,scrollWheelZoom:false,attributionControl:true}).setView([meanLat,meanLng],12);
  L.control.zoom({position:'topright'}).addTo(map);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors',maxZoom:19}).addTo(map);
  const canvas=L.canvas({padding:0.5});
  // The user selects a candidate site: preserve all citizen markers for diffusion,
  // but highlight and focus the map on that selected administrative dong.
  const selectedCode=String(data.dong_code||'');
  const selectedName=String(data.dong||'');
  const isSelected=(p)=>selectedCode ? String(p.dong_code)===selectedCode : String(p.dong)===selectedName;
  const isSelectedFeature=(f)=>{
    const props=(f&&f.properties)||{};
    return selectedCode && props.dong_code!==undefined
      ? String(props.dong_code)===selectedCode
      : String(props.dong||'')===selectedName;
  };
  let selectedArea=null;
  if(data.geo&&['Feature','FeatureCollection'].includes(data.geo.type)){
    const geoLayer=L.geoJSON(data.geo,{
      style:(f)=>isSelectedFeature(f)
        ? ({color:'#43e5c9',weight:3.5,opacity:1,fillColor:'#43e5c9',fillOpacity:.20})
        : ({color:'#7cb4c4',weight:1.2,opacity:.48,fillColor:'#43b8ba',fillOpacity:.045}),
      interactive:false
    }).addTo(map);
    geoLayer.eachLayer(layer=>{if(layer.feature&&isSelectedFeature(layer.feature))selectedArea=layer.getBounds();});
  }
  for(const p of points){if(!Number.isFinite(p.lat)||!Number.isFinite(p.lng))continue;
    const chosen=isSelected(p);
    const marker=L.circleMarker([p.lat,p.lng],{renderer:canvas,radius:chosen?3.8:3.0,color:'#72849b',fillColor:'#72849b',fillOpacity:chosen?.53:.27,stroke:false});
    const tooltip=document.createElement('div');
    const a=document.createElement('strong');a.textContent=`시민 ${p.id}`;tooltip.appendChild(a);
    const b=document.createElement('div');b.textContent=`${p.dong} · ${p.group}`;tooltip.appendChild(b);
    marker.bindPopup(tooltip);marker.addTo(map);markers.set(String(p.id),marker);
  }
  const validPoints=points.filter(p=>Number.isFinite(p.lat)&&Number.isFinite(p.lng));
  const chosenPoints=validPoints.filter(isSelected);
  if(data.focus_mode==='selected'){
    if(selectedArea&&selectedArea.isValid()){
      map.fitBounds(selectedArea.pad(.15),{maxZoom:15});
    }else if(chosenPoints.length){
      map.fitBounds(L.latLngBounds(chosenPoints.map(p=>[p.lat,p.lng])).pad(.25),{maxZoom:15});
    }else if(validPoints.length){
      map.fitBounds(L.latLngBounds(validPoints.map(p=>[p.lat,p.lng])).pad(.20),{maxZoom:13});
    }
  }else if(validPoints.length){
    map.fitBounds(L.latLngBounds(validPoints.map(p=>[p.lat,p.lng])).pad(.20),{maxZoom:13});
  }
  q('locationName').textContent=data.focus_mode==='selected'?'선택 지역 · '+selectedName:'전체 지역 보기';
  q('load').style.display='none';
  update(0);
  setTimeout(()=>map.invalidateSize(),100);
}catch(e){q('load').style.display='flex';q('load').textContent='지도 구성 오류: '+String(e.message||e);}
})();
</script></body></html>'''
    return html.replace("__PAYLOAD__", raw)
