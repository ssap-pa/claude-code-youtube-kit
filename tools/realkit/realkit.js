/* 실사 UI 키트 — 시간 제어(realkit.js). 장면 HTML을 프레임 단위로 찍기 위해 모든 움직임을 t초 상태로 맞춘다.
   realkit.py가 window.RK_INIT = {dur, cues, seqs}를 넣고, 프레임마다 await RK.seek(t)를 부른 뒤 화면을 찍는다.
   브라우저에서 바로 열 때: 장면.html?t=2.5 (그 시각 정지), ?play=1 (실시간 재생, 신호는 RK_DEFAULT 또는 0).

   HTML에서 쓰는 속성
   - data-anim="drop@n1, out@c4+0.2"  : 움직임 목록(이름[:길이[:fill]]@시각). 이름은 아래 presets 또는 직접 만든 @keyframes 이름.
   - data-at="n1"                       : CSS에 적은 animation의 시작 시각만 바꿀 때(목록이면 쉼표).
   - <img data-seq="src/c0_bg" data-t0="ai">: JPEG 시퀀스(0000.jpg…) — t0 시각에 0번 프레임, 30fps로 넘김(앞뒤는 첫·끝 프레임 유지).
   - data-count="276" data-ct="rev" data-len="1" data-dec="2" data-pre="$" data-from="0": 숫자 세기(기본 ease-out).
     끝 시각을 신호로: data-ct-end="rev+0.7", 곡선: data-ease="out3|inout|lin".
     천 단위 쉼표는 기본으로 넣는다(12,000). 끄기: data-sep="none" — 연도는 data-year 한 단어로 같은 효과
       예) <span data-count="1178" data-from="1173" data-year data-ct="five"></span>  → 1173…1178 (1,178 아님)
     다른 구분 기호: data-sep=" " (12 000).
   - window.onInit(RK) : 위치 계산(RK.box는 transform을 무시한 레이아웃 좌표), window.onSeek(t, RK): 프레임마다 직접 그릴 것(three.js 장면 등, async 가능).
   - window.RK_HOOKS = [fn(t, RK)] : 공용 부품이 프레임마다 그릴 것. RK.extra = 빌더가 Shot(extra=…)로 넘긴 자료(자막 등).
   시각 표기: 숫자(초) 또는 신호 이름±초("like", "ai+0.3", "fail-0.25"). 신호는 realkit.py가 대사 단어 시각으로 만든다. */
(function () {
  const I = window.RK_INIT || window.RK_DEFAULT || {};
  const qs = new URLSearchParams(location.search);
  // 신호: 빌더가 넘긴 값 우선, 정지 시안처럼 안 넘기면 장면의 RK_DEFAULT 값
  const RK = window.RK = { dur: +(I.dur || qs.get('dur') || 6), cues: Object.assign({}, (window.RK_DEFAULT || {}).cues, I.cues), seqInfo: I.seqs || {}, extra: I.extra || {}, t: 0, warns: [] };

  // 이름: [키프레임, 길이(초 또는 css 값), 타이밍, fill, 반복]
  RK.presets = {
    drop: ['m-drop', .42, 'var(--spring)', 'both'],
    pop: ['m-pop', .45, 'var(--spring)', 'both'],
    zin: ['m-zin', .45, 'var(--ease-out)', 'both'],
    rise: ['m-rise', .42, 'var(--ease-out)', 'both'],
    inl: ['m-inl', .45, 'var(--ease-out)', 'both'],
    inr: ['m-inr', .45, 'var(--ease-out)', 'both'],
    fade: ['m-fade', .4, 'ease', 'both'],
    punch: ['m-punch', .4, 'var(--ease-out)', 'both'],
    out: ['m-out', .32, 'var(--ease-in)', 'forwards'],
    outl: ['m-outl', .38, 'var(--ease-in)', 'forwards'],
    outr: ['m-outr', .38, 'var(--ease-in)', 'forwards'],
    fadeout: ['m-fadeout', .35, 'ease', 'forwards'],
    bump: ['m-bump', .45, 'ease-out', 'none'],
    ring: ['m-ring', .45, 'var(--spring)', 'both'],
    tap: ['m-tap', .6, 'ease-out', 'none'],
    draw: ['m-draw', .45, 'var(--ease-out)', 'both'],
    push: ['m-push', 'var(--dur)', 'linear', 'both'],
    prog: ['m-prog', 'var(--dur)', 'linear', 'both'],
    fill: ['m-fill', .35, 'ease-out', 'both'],
    hl: ['m-hl', .45, 'ease-out', 'both'],
    glow: ['m-glow', .9, 'ease-in-out', 'none'],
  };

  RK.warn = (m) => { RK.warns.push(m); console.warn('RK: ' + m); };
  RK.at = (v) => {
    if (v == null) return 0;
    v = String(v).trim();
    if (v === '') return 0;
    if (/^-?\d*\.?\d+$/.test(v)) return parseFloat(v);
    const m = v.match(/^([A-Za-z_]\w*)\s*([+-]\s*\d*\.?\d+)?$/);
    if (!m) { RK.warn('시각 형식 ' + v); return 0; }
    let b = RK.cues[m[1]];
    if (b == null) { RK.warn('없는 신호 ' + m[1]); b = 0; }
    return b + (m[2] ? parseFloat(m[2].replace(/\s/g, '')) : 0);
  };
  RK.box = (el) => {   // transform·애니메이션을 무시한 레이아웃 좌표(페이지 기준)
    let x = 0, y = 0, e = el;
    while (e) { x += e.offsetLeft; y += e.offsetTop; e = e.offsetParent; }
    const w = el.offsetWidth || +el.getAttribute('width') || 0, h = el.offsetHeight || +el.getAttribute('height') || 0;
    return { x, y, w, h, r: x + w, b: y + h, cx: x + w / 2, cy: y + h / 2 };
  };
  RK.clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
  RK.ease = { out3: p => 1 - Math.pow(1 - p, 3), inout: p => p < .5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2, lin: p => p };
  RK.prog = (t, at, len) => RK.clamp((t - RK.at(at)) / len);
  RK.css = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();

  function anim(el) {
    if (el._rk) return;
    el._rk = true;
    const parts = el.dataset.anim.split(',').map(s => s.trim()).filter(Boolean).map(it => {
      const [spec, at] = it.split('@');
      const [name, dur, fill] = spec.split(':').map(s => s && s.trim());
      const p = RK.presets[name] || [name, .5, 'var(--ease-out)', 'both'];
      let d = dur ? dur : p[1];
      d = /^[\d.]+$/.test(String(d)) ? d + 's' : d;
      return `${p[0]} ${d} ${p[2]} ${RK.at(at)}s ${p[4] || 1} normal ${fill || p[3]}`;
    });
    el.style.animation = parts.join(', ');
  }
  function fmt(v, el) {   // 천 단위 쉼표: data-sep="none"(또는 data-year)이면 끔 — 연도 1178이 '1,178'로 보이는 사고
    const dec = +(el.dataset.dec || 0), sep = el.dataset.year != null ? 'none' : (el.dataset.sep ?? ',');
    let s = v.toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec, useGrouping: sep !== 'none' && sep !== '' });
    if (sep !== ',' && sep !== 'none' && sep !== '') s = s.replace(/,/g, sep);
    return (el.dataset.pre || '') + s + (el.dataset.suf || '');
  }
  RK.fmt = fmt;

  RK.ready = (async () => {
    if (document.readyState === 'loading') await new Promise(r => addEventListener('DOMContentLoaded', r));
    document.documentElement.style.setProperty('--dur', RK.dur + 's');
    if (window.paintIcons) paintIcons();
    document.querySelectorAll('[data-anim]').forEach(anim);
    document.querySelectorAll('[data-at]:not([data-anim])').forEach(el => {
      el.style.animationDelay = el.dataset.at.split(',').map(x => RK.at(x) + 's').join(', ');
    });
    RK.seqs = [...document.querySelectorAll('img[data-seq]')].map(img => {
      const d = img.dataset.seq, inf = RK.seqInfo[d] || {};
      return { img, d, n: +(inf.n || img.dataset.n || 1), t0: RK.at(img.dataset.t0 || 0), fps: +(img.dataset.fps || 30), cur: -1 };
    });
    RK.counts = [...document.querySelectorAll('[data-count]')];
    await document.fonts.ready;
    await Promise.all([...document.images].map(im => im.complete ? 0 : new Promise(r => { im.onload = im.onerror = r; })));
    if (window.onInit) await window.onInit(RK);
    document.querySelectorAll('[data-anim]').forEach(anim);   // onInit이 새로 만든 요소(SVG 선 등)
    document.body.offsetWidth;
    document.getAnimations().forEach(a => a.pause());
    await RK.seek(+(qs.get('t') || 0));
    if (qs.get('play')) {
      const t0 = performance.now(), loop = async () => { await RK.seek(((performance.now() - t0) / 1000) % RK.dur); requestAnimationFrame(loop); };
      loop();
    }
    return true;
  })();

  RK.seek = async (t) => {
    RK.t = t;
    const ms = t * 1000;
    for (const el of RK.counts) {
      const from = +(el.dataset.from || 0), to = +el.dataset.count;
      const len = el.dataset.ctEnd ? RK.at(el.dataset.ctEnd) - RK.at(el.dataset.ct || 0) : +(el.dataset.len || 1);
      const ez = RK.ease[el.dataset.ease || 'out3'] || RK.ease.out3;
      el.textContent = fmt(from + (to - from) * ez(RK.prog(t, el.dataset.ct || 0, Math.max(.01, len))), el);
    }
    if (window.onSeek) await window.onSeek(t, RK);
    for (const f of (window.RK_HOOKS || [])) await f(t, RK);   // 공용 부품(captions.js 등)이 프레임마다 그릴 것
    for (const a of document.getAnimations()) { a.pause(); a.currentTime = ms; }
    const waits = [];
    for (const s of RK.seqs) {
      const i = Math.max(0, Math.min(s.n - 1, Math.floor((t - s.t0) * s.fps + 1e-6)));
      if (i !== s.cur) {
        s.cur = i;
        s.img.src = `${s.d}/${String(i).padStart(4, '0')}.jpg`;
        waits.push(s.img.decode().catch(() => RK.warn(`프레임 없음 ${s.d}/${i}`)));
      }
    }
    await Promise.all(waits);
    return t;
  };
})();
