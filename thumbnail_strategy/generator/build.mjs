import fs from 'fs';
import * as d3 from 'd3-geo';
import * as topo from 'topojson-client';
const W=1280,H=720;
const world=JSON.parse(fs.readFileSync('node_modules/world-atlas/countries-10m.json'));
const countries=topo.feature(world,world.objects.countries).features;
const de=JSON.parse(fs.readFileSync('germanyHigh.json'));
const WEST=['DE-BW','DE-BY','DE-HB','DE-HE','DE-HH','DE-NI','DE-NW','DE-RP','DE-SH','DE-SL'];
// amcharts geojson winding may be reversed for d3 (expects clockwise for exterior). fix via rewind
function rewind(f){const g=JSON.parse(JSON.stringify(f));const fixRing=(r,ext)=>{let a=0;for(let i=0;i<r.length-1;i++)a+=(r[i+1][0]-r[i][0])*(r[i+1][1]+r[i][1]);const cw=a>0; if(cw!==ext) r.reverse();};
 const polys=g.geometry.type==='Polygon'?[g.geometry.coordinates]:g.geometry.coordinates; polys.forEach(p=>p.forEach((r,i)=>fixRing(r,i===0))); return g;}
const west=de.features.filter(f=>WEST.includes(f.properties.id)).map(rewind);
const east=de.features.filter(f=>!WEST.includes(f.properties.id)).map(rewind);
const uk=countries.find(f=>f.properties.name==='United Kingdom');
const ger=countries.find(f=>f.properties.name==='Germany');
const box={type:'MultiPoint',coordinates:[[-10.0,46.7],[-10.0,59.3],[17.5,59.3],[17.5,46.7]]};
const proj=d3.geoMercator().fitExtent([[0,0],[W,H]],box);
// shift so UK left, Germany right-center
const path=d3.geoPath(proj);
const grat=d3.geoGraticule().step([5,5])();
const font=f=>fs.readFileSync(f).toString('base64');
const anton=font('node_modules/@fontsource/anton/files/anton-latin-400-normal.woff2');
const mont=font('node_modules/@fontsource/montserrat/files/montserrat-latin-900-normal.woff2');
const landT=JSON.parse(fs.readFileSync('node_modules/world-atlas/land-10m.json'));const land0=topo.feature(landT,landT.objects.land);const land={type:'MultiPolygon',coordinates:(land0.geometry?land0.geometry.coordinates:land0.features.flatMap(f=>f.geometry.type==='Polygon'?[f.geometry.coordinates]:f.geometry.coordinates)).filter(pg=>{const g={type:'Polygon',coordinates:pg};const b=d3.geoBounds(g);return d3.geoArea(g)<6 && (b[0][0]>b[1][0] || b[1][0]>-30)&&b[0][0]<45&&b[1][1]>35&&b[0][1]<75;})};
const others0=countries.filter(f=>{const n=f.properties.name; if(n==='Germany'||n==='United Kingdom'||n==='Antarctica'||n==='Maldives')return false; const b=d3.geoBounds(f); return b[1][0]>-30&&b[0][0]<45&&b[1][1]>35&&b[0][1]<75;}).map(f=>`<path d="${path(f)||''}"/>`).join('');
const westD=west.map(f=>path(f)).join(' ');
const eastD=east.map(f=>path(f)).join(' ');
const ukD=path(uk);
const c=(f)=>proj(f);
export function svg(variant){
 const ukc=path.centroid(uk), wc=d3.geoPath(proj).centroid({type:'FeatureCollection',features:west});
 return {ukc,wc,html:`<!doctype html><html><head><style>
@font-face{font-family:Anton;src:url(data:font/woff2;base64,${anton})}
@font-face{font-family:Mont;src:url(data:font/woff2;base64,${mont})}
html,body{margin:0;width:${W}px;height:${H}px;overflow:hidden;background:#000}
</style></head><body>
<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
<defs>
 <radialGradient id="sea" cx="55%" cy="45%" r="75%"><stop offset="0" stop-color="#2f86c9"/><stop offset=".6" stop-color="#1b5d9a"/><stop offset="1" stop-color="#0a2a52"/></radialGradient>
 <linearGradient id="land" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#a7adb0"/><stop offset="1" stop-color="#868e93"/></linearGradient>
 <linearGradient id="red" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ff5a4e"/><stop offset="1" stop-color="#b0121c"/></linearGradient>
 <linearGradient id="gold" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff27a"/><stop offset=".45" stop-color="#ffd21f"/><stop offset="1" stop-color="#e79a00"/></linearGradient>
 <filter id="glowG" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="18"/></filter>
 <filter id="glowR" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="14"/></filter>
 <filter id="sh" x="-20%" y="-20%" width="140%" height="140%"><feDropShadow dx="0" dy="6" stdDeviation="6" flood-color="#000" flood-opacity=".55"/></filter>
 <filter id="tex"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" seed="3"/><feColorMatrix values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 .08 0"/><feComposite in2="SourceGraphic" operator="in"/></filter>
 <pattern id="hatch" width="10" height="10" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="10" height="10" fill="#80888c"/><line x1="0" y1="0" x2="0" y2="10" stroke="#656c70" stroke-width="4"/></pattern>
 <radialGradient id="vig" cx="50%" cy="50%" r="72%"><stop offset=".55" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".55"/></radialGradient>
</defs>
<rect width="${W}" height="${H}" fill="url(#sea)"/>
<path d="${path(grat)}" fill="none" stroke="#fff" stroke-opacity=".07" stroke-width="1.5"/>
<g filter="url(#sh)"><path d="${path(land)}" fill="url(#land)" stroke="#fffaf0" stroke-opacity=".8" stroke-width="2"/></g><path d="${eastD}" fill="url(#hatch)" stroke="#fffaf0" stroke-opacity=".6" stroke-width="1.5"/>
<!-- UK -->
<path d="${ukD}" fill="#ff2a2a" opacity=".55" filter="url(#glowR)"/>
<path d="${ukD}" fill="url(#red)" stroke="#fff" stroke-width="4" stroke-linejoin="round" filter="url(#sh)"/>
<!-- West Germany -->
<path d="${westD}" fill="#ffd400" stroke="#ffd400" stroke-width="34" opacity=".9" filter="url(#glowG)"/>
<path d="${westD}" fill="#fff6b0" stroke="#fff" stroke-width="10" stroke-linejoin="round"/>
<path d="${westD}" fill="url(#gold)" stroke="url(#gold)" stroke-width="1"/>
<path d="${ukD} ${westD}" fill="#000" filter="url(#tex)"/>
<rect width="${W}" height="${H}" fill="url(#vig)"/>
${variant}
</svg></body></html>`};
}
