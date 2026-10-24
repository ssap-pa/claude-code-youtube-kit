/* 말 자막 — 빌더가 V.captions(...)로 만든 묶음을 Shot(extra={'caps': …})로 넘기면 단어 시각에 맞춰 띄운다.
   묶음: [{t0, t1, text, hl}] (장면 묶음 시작 기준 초). hl = 노랗게 칠할 낱말 목록. */
(function () {
  const el = document.createElement('div'); el.className = 'cap';
  const ready = () => document.body.appendChild(el);
  document.readyState === 'loading' ? addEventListener('DOMContentLoaded', ready) : ready();
  const esc = s => s.replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
  const re = s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  let last = null;
  (window.RK_HOOKS = window.RK_HOOKS || []).push((t, RK) => {
    const caps = (RK.extra && RK.extra.caps) || [];
    const c = caps.find(c => t >= c.t0 && t < c.t1) || null;
    if (c === last) return;
    last = c;
    if (!c) { el.innerHTML = ''; return; }
    let h = esc(c.text);
    if (c.hl && c.hl.length) h = h.replace(new RegExp(c.hl.map(re).join('|'), 'g'), m => `<b>${m}</b>`);
    el.innerHTML = h;
  });
})();
