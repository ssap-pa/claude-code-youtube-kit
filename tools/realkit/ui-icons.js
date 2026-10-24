// 변형 시안용 UI 아이콘 (직접 그린 SVG, 특정 앱 상표 모양 아님)
// 사용: <i data-ic="heart" data-c="#fff" data-f="1"></i>  (data-f=1 → 채움)
window.IC = {
  heart: (c, f) => f
    ? `<svg viewBox="0 0 24 24"><path fill="${c}" d="M12 20.6l-1.3-1.2C5.8 15 2.6 12.1 2.6 8.6 2.6 5.8 4.8 3.6 7.6 3.6c1.6 0 3.2.8 4.4 2 1.2-1.2 2.8-2 4.4-2 2.8 0 5 2.2 5 5 0 3.5-3.2 6.4-8.1 10.8z"/></svg>`
    : `<svg viewBox="0 0 24 24" fill="none" stroke="${c}" stroke-width="2" stroke-linejoin="round"><path d="M12 20.6l-1.3-1.2C5.8 15 2.6 12.1 2.6 8.6 2.6 5.8 4.8 3.6 7.6 3.6c1.6 0 3.2.8 4.4 2 1.2-1.2 2.8-2 4.4-2 2.8 0 5 2.2 5 5 0 3.5-3.2 6.4-8.1 10.8z"/></svg>`,
  comment: (c) => `<svg viewBox="0 0 24 24" fill="none" stroke="${c}" stroke-width="2" stroke-linejoin="round"><path d="M20.5 11.6a8.4 8.4 0 0 1-12.3 7.5L3.5 20.5l1.4-4.6A8.4 8.4 0 1 1 20.5 11.6z"/></svg>`,
  send: (c) => `<svg viewBox="0 0 24 24" fill="none" stroke="${c}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"><path d="M21.5 2.5L10.6 13.4"/><path d="M21.5 2.5l-7 19-3.9-8.1-8.1-3.9z"/></svg>`,
  more: (c) => `<svg viewBox="0 0 24 24" fill="${c}"><circle cx="5" cy="12" r="2"/><circle cx="12" cy="12" r="2"/><circle cx="19" cy="12" r="2"/></svg>`,
  camera: (c) => `<svg viewBox="0 0 24 24" fill="none" stroke="${c}" stroke-width="2" stroke-linejoin="round"><path d="M3 8.5A2.5 2.5 0 0 1 5.5 6h2l1.6-2.2h5.8L16.5 6h2A2.5 2.5 0 0 1 21 8.5v9a2.5 2.5 0 0 1-2.5 2.5h-13A2.5 2.5 0 0 1 3 17.5z"/><circle cx="12" cy="12.8" r="3.8"/></svg>`,
  home: (c, f) => `<svg viewBox="0 0 24 24" fill="${f ? c : 'none'}" stroke="${c}" stroke-width="2" stroke-linejoin="round"><path d="M3.5 10.2L12 3.5l8.5 6.7V20a.8.8 0 0 1-.8.8h-5v-6.3h-5.4v6.3h-5a.8.8 0 0 1-.8-.8z"/></svg>`,
  search: (c) => `<svg viewBox="0 0 24 24" fill="none" stroke="${c}" stroke-width="2.2" stroke-linecap="round"><circle cx="10.5" cy="10.5" r="7"/><path d="M15.8 15.8l5 5"/></svg>`,
  plus: (c) => `<svg viewBox="0 0 24 24" fill="none" stroke="${c}" stroke-width="2" stroke-linecap="round"><rect x="3" y="3" width="18" height="18" rx="5"/><path d="M12 8v8M8 12h8"/></svg>`,
  play: (c, f) => f
    ? `<svg viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="5" fill="${c}"/><path d="M10 8.3v7.4l6-3.7z" fill="#000"/></svg>`
    : `<svg viewBox="0 0 24 24" fill="none" stroke="${c}" stroke-width="2" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="5"/><path d="M10 8.3v7.4l6-3.7z"/></svg>`,
  person: (c) => `<svg viewBox="0 0 24 24" fill="${c}"><circle cx="12" cy="8" r="4.2"/><path d="M3.8 20.5c0-4.3 3.7-7.2 8.2-7.2s8.2 2.9 8.2 7.2z"/></svg>`,
  personPlus: (c) => `<svg viewBox="0 0 24 24" fill="${c}"><circle cx="9.5" cy="8" r="4"/><path d="M2 20.3c0-4.1 3.4-6.9 7.5-6.9s7.5 2.8 7.5 6.9z"/><rect x="18.4" y="6.4" width="2.2" height="8.4" rx="1.1"/><rect x="15.3" y="9.5" width="8.4" height="2.2" rx="1.1"/></svg>`,
  link: (c) => `<svg viewBox="0 0 24 24" fill="none" stroke="${c}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13.5a4.6 4.6 0 0 0 6.9.5l3-3a4.6 4.6 0 0 0-6.5-6.5l-1.6 1.6"/><path d="M14 10.5a4.6 4.6 0 0 0-6.9-.5l-3 3a4.6 4.6 0 0 0 6.5 6.5l1.6-1.6"/></svg>`,
  lock: (c, f) => f
    ? `<svg viewBox="0 0 24 24"><path d="M7 10.5V7.8a5 5 0 0 1 10 0v2.7" fill="none" stroke="${c}" stroke-width="2.4" stroke-linecap="round"/><rect x="4.2" y="10" width="15.6" height="11.5" rx="3" fill="${c}"/></svg>`
    : `<svg viewBox="0 0 24 24" fill="none" stroke="${c}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 10.5V7.8a5 5 0 0 1 10 0v2.7"/><rect x="4.2" y="10.3" width="15.6" height="11" rx="3"/><path d="M12 14.6v2.6"/></svg>`,
  sparkle: (c) => `<svg viewBox="0 0 24 24"><path fill="${c}" d="M10 2.5c.5 4.4 2.5 7.1 8 8.9-5.5 1.8-7.5 4.5-8 8.9-.5-4.4-2.5-7.1-8-8.9 5.5-1.8 7.5-4.5 8-8.9z"/><path fill="${c}" d="M19 1.5c.2 1.8 1 2.8 3.2 3.5-2.2.7-3 1.7-3.2 3.5-.2-1.8-1-2.8-3.2-3.5 2.2-.7 3-1.7 3.2-3.5z"/></svg>`,
  close: (c) => `<svg viewBox="0 0 24 24" fill="none" stroke="${c}" stroke-width="2.4" stroke-linecap="round"><path d="M5.5 5.5l13 13M18.5 5.5l-13 13"/></svg>`,
  chevDown: (c) => `<svg viewBox="0 0 24 24" fill="none" stroke="${c}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9.5l6 6 6-6"/></svg>`,
  signal: (c) => `<svg viewBox="0 0 34 22" fill="${c}"><rect x="0" y="14" width="6" height="8" rx="1.6"/><rect x="9" y="10" width="6" height="12" rx="1.6"/><rect x="18" y="5" width="6" height="17" rx="1.6"/><rect x="27" y="0" width="6" height="22" rx="1.6"/></svg>`,
  wifi: (c) => `<svg viewBox="0 0 30 22" fill="${c}"><path d="M15 21.5l-4.4-4.6a6.4 6.4 0 0 1 8.8 0z"/><path d="M15 9.8c3.1 0 5.9 1.2 8 3.2l-2.6 2.7a7.7 7.7 0 0 0-10.8 0L7 13c2.1-2 4.9-3.2 8-3.2z"/><path d="M15 2.5c5.1 0 9.7 2 13.1 5.3l-2.6 2.7a15 15 0 0 0-21 0L1.9 7.8A18.8 18.8 0 0 1 15 2.5z"/></svg>`,
  battery: (c) => `<svg viewBox="0 0 46 22"><rect x="1" y="1" width="39" height="20" rx="6" fill="none" stroke="${c}" stroke-opacity=".45" stroke-width="2"/><rect x="4" y="4" width="30" height="14" rx="3.4" fill="${c}"/><path d="M42.5 7.5v7a3.4 3.4 0 0 0 0-7z" fill="${c}" fill-opacity=".5"/></svg>`,
  dollar: (c) => `<svg viewBox="0 0 24 24" fill="none" stroke="${c}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2.5v19"/><path d="M16.8 6.2c-.9-1.2-2.6-2-4.8-2-2.9 0-4.7 1.5-4.7 3.6 0 5 9.7 2.7 9.7 8 0 2.2-2 3.8-5 3.8-2.3 0-4.2-.9-5.2-2.3"/></svg>`,
  card: (c) => `<svg viewBox="0 0 24 24" fill="none" stroke="${c}" stroke-width="2" stroke-linejoin="round"><rect x="2.5" y="5" width="19" height="14" rx="3"/><path d="M2.5 9.8h19"/><path d="M6 15h4" stroke-linecap="round"/></svg>`,
  check: (c) => `<svg viewBox="0 0 24 24" fill="none" stroke="${c}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>`,
  trendUp: (c) => `<svg viewBox="0 0 24 24" fill="none" stroke="${c}" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/></svg>`,
  eyeOff: (c) => `<svg viewBox="0 0 24 24" fill="none" stroke="${c}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3l18 18"/><path d="M10.6 5.2A10.6 10.6 0 0 1 12 5c5.5 0 9 5.5 9.5 7-.3.9-1.4 2.8-3.2 4.4M6.4 6.6C4.3 8 2.9 10.2 2.5 12c.5 1.5 4 7 9.5 7 1.6 0 3-.4 4.3-1.1"/><path d="M9.9 9.9a3 3 0 0 0 4.2 4.2"/></svg>`,
  flag: (c) => `<svg viewBox="0 0 24 24" fill="none" stroke="${c}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 21V4"/><path d="M5 4.5c4.5-2.2 7.5 2.2 13 0v9c-5.5 2.2-8.5-2.2-13 0"/></svg>`,
  eye: (c) => `<svg viewBox="0 0 24 24" fill="none" stroke="${c}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M2.5 12C3.6 9 7.2 5 12 5s8.4 4 9.5 7c-1.1 3-4.7 7-9.5 7s-8.4-4-9.5-7z"/><circle cx="12" cy="12" r="3"/></svg>`,
  calendar: (c) => `<svg viewBox="0 0 24 24" fill="none" stroke="${c}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="3.5" y="5" width="17" height="15.5" rx="3"/><path d="M3.5 10h17M8 3v4M16 3v4"/></svg>`,
  bag: (c) => `<svg viewBox="0 0 24 24" fill="none" stroke="${c}" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round"><path d="M5 8h14l-1 12.5H6z"/><path d="M8.8 10.5V6.8a3.2 3.2 0 0 1 6.4 0v3.7"/></svg>`,
};

function paintIcons(root = document) {
  root.querySelectorAll('[data-ic]').forEach(el => {
    const f = IC[el.dataset.ic];
    if (!f) { console.warn('no icon', el.dataset.ic); return; }
    el.innerHTML = f(el.dataset.c || 'currentColor', el.dataset.f === '1');
  });
}
