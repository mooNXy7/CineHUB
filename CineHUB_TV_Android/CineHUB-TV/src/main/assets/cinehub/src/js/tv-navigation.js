/* CineHUB TV Navigation 1.0.6 — Android TV / TV Box D-pad layer. */
(function(){
'use strict';
var root=window.CineHUBTVNavigation||{};root.version='1.0.6';
var SELECTOR='button:not([disabled]),a[href],input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';
var KEY={LEFT:21,RIGHT:22,UP:19,DOWN:20,ENTER:23,BACK:4};
function visible(el){if(!el||el.hidden)return false;var c=getComputedStyle(el),r=el.getBoundingClientRect();return c.display!=='none'&&c.visibility!=='hidden'&&parseFloat(c.opacity||1)>0&&r.width>1&&r.height>1}
function active(el){var x=el.closest('.system-modal,.sheet,.detail,.player,.screen');return x?x.classList.contains('active'):!document.querySelector('.system-modal.active,.sheet.active,.detail.active,.player.active,.screen.active')}
function list(){return Array.prototype.slice.call(document.querySelectorAll(SELECTOR)).filter(function(x){return visible(x)&&active(x)})}
function focus(el){if(!el||!visible(el))return;document.querySelectorAll('.cinehub-tv-focus').forEach(function(x){x.classList.remove('cinehub-tv-focus')});el.classList.add('cinehub-tv-focus');try{el.focus({preventScroll:true})}catch(_){el.focus()}try{el.scrollIntoView({behavior:'smooth',block:'nearest',inline:'nearest'})}catch(_){}}
function center(x){var r=x.getBoundingClientRect();return{x:r.left+r.width/2,y:r.top+r.height/2,w:r.width,h:r.height}}
function move(dir){
 var from=document.activeElement;if(!from||!visible(from)||!active(from))from=list()[0];
 var all=list();if(!from){return}if(!all.length)return;
 var a=center(from),best=null,score=1e9;
 all.forEach(function(x){if(x===from)return;var b=center(x),dx=b.x-a.x,dy=b.y-a.y;
   var p=dir==='left'?-dx:dir==='right'?dx:dir==='up'?-dy:dy;if(p<=5)return;
   var cross=(dir==='left'||dir==='right')?Math.abs(dy):Math.abs(dx);
   var s=p+cross*1.6;if(s<score){score=s;best=x}
 });
 if(best)focus(best);
}
function press(){var x=document.activeElement;if(!x||!visible(x)||!active(x)){focus(list()[0]);return}if(/^(INPUT|TEXTAREA|SELECT)$/.test(x.tagName))return;try{x.click()}catch(_){}}
function back(){
 var x=document.querySelector('.system-modal.active,.player.active,.detail.active,.sheet.active,.screen.active');
 if(!x)return false;var b=x.querySelector('[data-close]');if(b){b.click();return true}return false;
}
function initial(){var m=document.querySelector('.system-modal.active');if(m){focus(m.querySelector('button'));return}var l=document.querySelector('.player.active,.detail.active,.sheet.active,.screen.active');if(l){focus(l.querySelector('button,a[href],input'));return}focus(document.querySelector('#heroPlay')||document.querySelector('.dock-btn'))}
document.addEventListener('keydown',function(e){var k=e.keyCode||e.which;if(k===21||k===22||k===19||k===20){e.preventDefault();move(k===21?'left':k===22?'right':k===19?'up':'down')}else if(k===23||k===66){e.preventDefault();press()}else if(k===4||e.key==='Escape'){if(back())e.preventDefault()}},true);
document.addEventListener('focusin',function(e){if(visible(e.target))focus(e.target)});
document.addEventListener('click',function(e){var x=e.target.closest('button,a,.card,.explore-card');if(x)setTimeout(function(){focus(x)},0)},true);
var last='';new MutationObserver(function(){var x=document.querySelector('.system-modal.active,.player.active,.detail.active,.sheet.active,.screen.active');var k=x?(x.id||x.className):'home';if(k!==last){last=k;setTimeout(initial,80)}}).observe(document.body,{subtree:true,attributes:true,attributeFilter:['class','hidden']});
setTimeout(initial,700);window.CineHUBTVNavigation=root;
})();