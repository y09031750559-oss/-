const T=(x,y,txt,size,fill='#fff',stroke='#111',anchor='middle',rot=0)=>`<g transform="translate(${x},${y}) rotate(${rot})" filter="url(#sh)"><text text-anchor="${anchor}" font-family="Anton" font-size="${size}" fill="${fill}" stroke="${stroke}" stroke-width="${size*0.12}" paint-order="stroke" stroke-linejoin="round" letter-spacing="2">${txt}</text></g>`;
const box=(x,y,txt,size,fg='#ff2b2b',bg='#0b0b0b',pad=22)=>{const w=txt.length*size*0.5+pad*2;return `<g transform="translate(${x},${y})" filter="url(#sh)"><rect x="${-w/2}" y="${-size*0.95}" width="${w}" height="${size*1.18}" rx="8" fill="${bg}"/><text text-anchor="middle" font-family="Anton" font-size="${size}" fill="${fg}" letter-spacing="3">${txt}</text></g>`};
const medal=(x,y,s=1)=>`<g transform="translate(${x},${y}) scale(${s})" filter="url(#sh)"><path d="M-22,-70 L-6,-18 L6,-18 L22,-70 Z" fill="#1f4fbf"/><path d="M-22,-70 L-12,-70 L2,-18 L-6,-18Z" fill="#d22"/><path d="M22,-70 L12,-70 L-2,-18 L6,-18Z" fill="#d22"/><circle r="30" cy="10" fill="url(#gold)" stroke="#a86b00" stroke-width="4"/><circle r="20" cy="10" fill="none" stroke="#fff3a0" stroke-width="3" opacity=".8"/><text y="22" text-anchor="middle" font-family="Anton" font-size="34" fill="#8a5600">1</text></g>`;
const coins=(x,y,s=1)=>{let g='';for(let i=0;i<6;i++){g+=`<ellipse cx="0" cy="${-i*13}" rx="34" ry="11" fill="#d99100" stroke="#8a5a00" stroke-width="2"/><rect x="-34" y="${-i*13-11}" width="68" height="11" fill="#e8a800"/><ellipse cx="0" cy="${-i*13-11}" rx="34" ry="11" fill="url(#gold)" stroke="#a86b00" stroke-width="2"/>`;}
 let g2='';for(let i=0;i<4;i++){g2+=`<ellipse cx="0" cy="${-i*13}" rx="34" ry="11" fill="#d99100" stroke="#8a5a00" stroke-width="2"/><rect x="-34" y="${-i*13-11}" width="68" height="11" fill="#e8a800"/><ellipse cx="0" cy="${-i*13-11}" rx="34" ry="11" fill="url(#gold)" stroke="#a86b00" stroke-width="2"/>`;}
 return `<g transform="translate(${x},${y}) scale(${s})" filter="url(#sh)"><g transform="translate(-40,10)">${g2}</g>${g}<text x="0" y="-74" text-anchor="middle" font-family="Anton" font-size="34" fill="#8a5600">$</text></g>`};
const spark=(x,y,r)=>`<path transform="translate(${x},${y})" d="M0,${-r} Q${r*0.15},${-r*0.15} ${r},0 Q${r*0.15},${r*0.15} 0,${r} Q${-r*0.15},${r*0.15} ${-r},0 Q${-r*0.15},${-r*0.15} 0,${-r}Z" fill="#fffbe0"/>`;
export default {
 v1:(u,w)=> T(u[0]+45,u[1]+95,'WON',120) + medal(u[0]-175,u[1]-95,1.3)
   + T(w[0]-10,w[1]+60,'LOST',120) + coins(w[0]+215,w[1]+95,1.25)
   + spark(w[0]+90,w[1]-150,22)+spark(w[0]-110,w[1]-60,14)+spark(w[0]+140,w[1]-20,12)
   + box(640,140,'WHY?',150),
 v2:(u,w)=> T(u[0]+10,u[1]+20,'$3.2B',110) + T(u[0]+10,u[1]+92,'U.S. AID',58,'#fff','#111')
   + T(w[0]-10,w[1]+30,'$1.4B',110) + T(w[0]-10,w[1]+102,'U.S. AID',58,'#fff','#111')
   + spark(w[0]+90,w[1]-150,22)+spark(w[0]-110,w[1]-60,14)+spark(w[0]+140,w[1]-20,12)
   + box(905,125,'WHO GOT RICH?',92),
};
