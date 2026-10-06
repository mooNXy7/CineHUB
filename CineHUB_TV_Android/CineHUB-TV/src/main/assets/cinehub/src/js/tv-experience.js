/* CineHUB TV Experience 1.0.7 — additive TV-only UX layer. */
(function(){
'use strict';
function q(s){return document.querySelector(s)}
function make(tag,cls,text){var x=document.createElement(tag);if(cls)x.className=cls;if(text!=null)x.textContent=text;return x}
function click(sel){var x=q(sel);if(x)x.click()}
function addHeader(){
 var top=q('#topbar');if(!top||q('#tvHeaderNav'))return;
 var nav=make('nav','tv-header-nav glass');nav.id='tvHeaderNav';nav.setAttribute('aria-label','Navegação CineHUB TV');
 [['Início','home'],['Filmes','moviesScreen'],['Séries','seriesScreen'],['TV / Canais','tvScreen'],['Pesquisa','searchScreen']].forEach(function(a,i){
   var b=make('button','tv-header-btn press',a[0]);b.dataset.tvNav=a[1];b.tabIndex=0;
   b.addEventListener('click',function(){if(a[1]==='home')window.CineHUBTV?.goHome?.();else if(a[1]==='searchScreen')click('[data-action="search"]');else click('[data-screen="'+(a[1]==='moviesScreen'?'movies':a[1]==='seriesScreen'?'series':'tv')+'"]')});
   nav.appendChild(b);
 });
 top.insertAdjacentElement('afterend',nav);
}
function addHints(){
 if(q('#tvHints'))return;
 var h=make('div','tv-hints glass');h.id='tvHints';
 h.innerHTML='<span>↑ ↓ Navegar</span><span>← → Mover</span><span>OK Abrir</span><span>Back Voltar</span>';
 document.body.appendChild(h);
}
function addKeyboard(){
 var screen=q('#searchScreen'),input=q('#globalSearch');if(!screen||!input||q('#tvKeyboard'))return;
 var box=make('section','tv-keyboard glass');box.id='tvKeyboard';box.setAttribute('aria-label','Teclado virtual');
 var rows=[['Q','W','E','R','T','Y','U','I','O','P'],['A','S','D','F','G','H','J','K','L'],['Z','X','C','V','B','N','M'],['1','2','3','4','5','6','7','8','9','0']];
 rows.forEach(function(row){var r=make('div','tv-key-row');row.forEach(function(ch){var b=make('button','tv-key press',ch);b.tabIndex=0;b.onclick=function(){input.value+=ch;input.dispatchEvent(new Event('input',{bubbles:true}))};r.appendChild(b)});box.appendChild(r)});
 var actions=make('div','tv-key-row tv-key-actions');
 [['⌫','back'],['ESPAÇO','space'],['LIMPAR','clear']].forEach(function(a){var b=make('button','tv-key press',a[0]);b.onclick=function(){if(a[1]==='back')input.value=input.value.slice(0,-1);else if(a[1]==='space')input.value+=' ';else input.value='';input.dispatchEvent(new Event('input',{bubbles:true}))};actions.appendChild(b)});
 box.appendChild(actions);
 screen.querySelector('.search-results').before(box);
}
function exposeHomeSearch(){
 ['#tvSearchSection','#tvCategorySection'].forEach(function(s){var x=q(s);if(x)x.hidden=false});
}
function patchMediaKeys(){
 document.addEventListener('keydown',function(e){
   if(e.key==='Home'&&window.CineHUBTV?.goHome){e.preventDefault();window.CineHUBTV.goHome();return}
   if(e.key===' ' && document.activeElement===q('#globalSearch')){e.preventDefault();q('#globalSearch').value+=' ';q('#globalSearch').dispatchEvent(new Event('input',{bubbles:true}))}
 });
}
function init(){addHeader();addHints();exposeHomeSearch();addKeyboard();patchMediaKeys();setTimeout(function(){window.CineHUBTV?.goHome?.()},250)}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();