/* 3D 장면 도우미(three.js r160, vendor/three.min.js 다음에 넣는다) — 로우폴리·건축 모형 느낌의 장면을 코드로 만들고,
   프레임 시각 t에 맞춰 카메라·물체를 움직여 그린다(실시간 재생이 아니라 RK.seek(t)마다 같은 그림 → 렌더 결과가 매번 같다).

   쓰는 법(장면 HTML):
     <div id="stage"></div>
     <script src=".../vendor/three.min.js"></script><script src=".../scene3d.js"></script>
     <script>
       S3D.start((T, S) => {               // T = THREE, S = 도우미
         S.ground(); S.box({w:40, h:300, d:40, color:'#d9dde3'});
         return t => { S.orbit(t, {from:-30, to:20, dur:6, radius:420, height:180, look:[0,150,0]}); };   // 매 프레임
       });
     </script>
   도우미: S.ground() 바닥 / S.box() 상자 / S.mat(색) 평면 음영 재질 / S.particles() 바람 입자
          S.orbit() 카메라 / S.ease·S.prog(t, 시작, 길이) / S.tag(el, 3D 위치) 3D 위치에 HTML 꼬리표 붙이기
          S.section() 잘라 본 땅 단면(지층 + 묻힌 기초) / S.viewHalf(거리) 그 거리에서 화면에 보이는 반폭·반높이
   보이는 느낌(로우폴리 3D): 평면 음영(flat shading) + 베이지·회색 위주 + 따뜻한 오후 햇빛. 건축 모형처럼 숫자·위치가 정확한 도식.
   S3D.start(build, {light: 'cool'})로 예전(조금 차가운) 빛, {sky: [위, 아래]}로 하늘색을 바꾼다.
*/
(function () {
  const T = window.THREE;
  const W = innerWidth, H = innerHeight;
  const S = window.S3D = {};
  S.ease = { out: x => 1 - Math.pow(1 - x, 3), inout: x => x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2, lin: x => x };
  S.prog = (t, a, len) => Math.max(0, Math.min(1, (t - a) / Math.max(1e-3, len)));
  S.lerp = (a, b, k) => a + (b - a) * k;

  S.start = (build, opt = {}) => {
    const stage = document.getElementById('stage') || document.body.appendChild(Object.assign(document.createElement('div'), { id: 'stage' }));
    const renderer = new T.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    renderer.setPixelRatio(1); renderer.setSize(W, H);
    renderer.outputColorSpace = T.SRGBColorSpace; renderer.toneMapping = T.ACESFilmicToneMapping; renderer.toneMappingExposure = opt.exposure || 1.05;
    renderer.shadowMap.enabled = true; renderer.shadowMap.type = T.PCFSoftShadowMap;
    stage.appendChild(renderer.domElement);
    const scene = new T.Scene();
    const sky = opt.sky || ['#bcd3e6', '#f3e7d3'];   // 위·아래 하늘색(맑은 오후 건축 모형 느낌)
    scene.background = gradient(sky[0], sky[1]);
    scene.fog = new T.Fog(opt.fog || sky[1], opt.fogNear || 1400, opt.fogFar || 5200);
    const cam = new T.PerspectiveCamera(opt.fov || 42, W / H, 1, 20000);
    const cool = opt.light === 'cool';   // 기본은 따뜻한 오후 빛(모형 사진 느낌), 'cool'은 v1.1까지의 빛
    scene.add(new T.HemisphereLight(cool ? '#eef4ff' : '#f6f0e4', cool ? '#c9b796' : '#c7ae86', 1.6));
    const fill = new T.DirectionalLight(cool ? '#dfe9ff' : '#e4ebf6', .9); fill.position.set(700, 400, -600); scene.add(fill);   // 그림자 쪽이 새까맣지 않게
    const sun = new T.DirectionalLight(cool ? '#fff1dc' : '#ffe6c4', cool ? 2.2 : 2.3); sun.position.set(-600, 1200, 500); sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048); Object.assign(sun.shadow.camera, { left: -1200, right: 1200, top: 1200, bottom: -1200, near: 10, far: 4000 });
    scene.add(sun);
    Object.assign(S, { T, scene, cam, renderer, sun });
    const update = build(T, S) || (() => {});
    (window.RK_HOOKS = window.RK_HOOKS || []).unshift(async t => { update(t); cam.updateMatrixWorld(); S._tags.forEach(f => f()); renderer.render(scene, cam); });
  };

  function gradient(top, bottom) {
    const c = document.createElement('canvas'); c.width = 4; c.height = 512; const g = c.getContext('2d');
    const gr = g.createLinearGradient(0, 0, 0, 512); gr.addColorStop(0, top); gr.addColorStop(1, bottom); g.fillStyle = gr; g.fillRect(0, 0, 4, 512);
    const tx = new T.CanvasTexture(c); tx.colorSpace = T.SRGBColorSpace; return tx;
  }

  // 결정적 난수(같은 씨앗 = 같은 장면)
  S.rand = (seed => () => (seed = (seed * 16807) % 2147483647) / 2147483647)(7);
  S.mat = (color, o = {}) => new T.MeshStandardMaterial({ color, flatShading: true, roughness: o.rough ?? .85, metalness: o.metal ?? 0, transparent: o.opacity != null, opacity: o.opacity ?? 1, emissive: o.emissive || '#000' });

  S.ground = (o = {}) => {   // 로우폴리 바닥(살짝 울퉁불퉁) + 도시 블록
    const g = new T.PlaneGeometry(o.size || 14000, o.size || 14000, 90, 90); g.rotateX(-Math.PI / 2);
    const p = g.attributes.position;
    for (let i = 0; i < p.count; i++) { const x = p.getX(i), z = p.getZ(i), d = Math.hypot(x, z); p.setY(i, d < (o.flat || 500) ? 0 : (S.rand() - .5) * (o.bump || 14) ); }   // 멀리까지 평평하게 — 안개 속으로 지평선이 녹아든다
    g.computeVertexNormals();
    const m = new T.Mesh(g, S.mat(o.color || '#e3d3b4')); m.receiveShadow = true; S.scene.add(m);
    if (o.city !== false) {   // 낮은 건물 블록들(모형 도시)
      for (let i = 0; i < (o.blocks || 220); i++) {
        const r = (o.cityMin || 260) + S.rand() * 1800,   // cityMin: 카메라가 지나는 반지름 안엔 건물을 두지 않는다
            a = S.rand() * Math.PI * 2, w = 24 + S.rand() * 60, h = 12 + Math.pow(S.rand(), 3) * (o.cityH || 160);
        const b = S.box({ w, h, d: w * (.6 + S.rand() * .8), color: S.rand() < .5 ? '#eceef1' : '#d7dadf', x: Math.cos(a) * r, z: Math.sin(a) * r });
        b.rotation.y = S.rand() * Math.PI;
      }
    }
    return m;
  };

  S.box = (o) => {
    const m = new T.Mesh(new T.BoxGeometry(o.w, o.h, o.d ?? o.w), o.material || S.mat(o.color || '#dfe2e6', o));
    m.position.set(o.x || 0, (o.y || 0) + o.h / 2, o.z || 0); m.castShadow = true; m.receiveShadow = true; (o.parent || S.scene).add(m); return m;
  };

  // Y자 평면(날개 셋) 한 층 덩어리: 가운데 육각 기둥 + 120°마다 날개
  S.yBlock = (o) => {
    const grp = new T.Group(); const mat = o.material || S.mat(o.color || '#dfe5ea', { metal: .25, rough: .5 });
    const core = new T.Mesh(new T.CylinderGeometry(o.core, o.core, o.h, 6), mat); core.position.y = o.h / 2; grp.add(core);
    for (let k = 0; k < 3; k++) {
      if (o.wings && !o.wings[k]) continue;
      const len = o.len * (o.wings ? o.wings[k] : 1);
      const wing = new T.Mesh(new T.BoxGeometry(o.wid, o.h, len), mat);
      const a = k * 2 * Math.PI / 3; wing.position.set(Math.sin(a) * len / 2, o.h / 2, Math.cos(a) * len / 2); wing.rotation.y = a; grp.add(wing);
    }
    grp.traverse(m => { if (m.isMesh) { m.castShadow = true; m.receiveShadow = true; } });
    grp.position.y = o.y || 0; (o.parent || S.scene).add(grp); return grp;
  };

  // 바람 입자: 왼쪽에서 오른쪽으로 흐르는 점들. fn(i, t) → [x, y, z]를 직접 줄 수도 있다
  S.particles = (n, color = '#ffffff', size = 7) => {
    const g = new T.BufferGeometry(); g.setAttribute('position', new T.BufferAttribute(new Float32Array(n * 3), 3));
    const pts = new T.Points(g, new T.PointsMaterial({ color, size, sizeAttenuation: true, transparent: true, opacity: .9, depthWrite: false }));
    S.scene.add(pts); pts.seed = Array.from({ length: n }, () => [S.rand(), S.rand(), S.rand()]);
    pts.place = (fn, t) => { const a = g.attributes.position.array; pts.seed.forEach((s, i) => { const [x, y, z] = fn(s, t, i); a[i * 3] = x; a[i * 3 + 1] = y; a[i * 3 + 2] = z; }); g.attributes.position.needsUpdate = true; };
    return pts;
  };

  // 바람 꼬리 선: 입자마다 지금 위치와 dt초 전 위치를 잇는 짧은 선(밝은 배경에서도 흐름이 보인다)
  S.streaks = (n, color = '#1e88ff', dt = .12, opacity = .85) => {
    const g = new T.BufferGeometry(); g.setAttribute('position', new T.BufferAttribute(new Float32Array(n * 6), 3));
    const ln = new T.LineSegments(g, new T.LineBasicMaterial({ color, transparent: true, opacity, depthWrite: false }));
    S.scene.add(ln); ln.seed = Array.from({ length: n }, () => [S.rand(), S.rand(), S.rand()]); ln.base = opacity;
    ln.place = (fn, t) => {
      const a = g.attributes.position.array;
      ln.seed.forEach((s, i) => {
        const p = fn(s, t, i), q = fn(s, t - dt, i);
        const jump = Math.hypot(p[0] - q[0], p[1] - q[1], p[2] - q[2]) > 400;   // 화면 끝에서 처음으로 돌아간 입자는 선을 그리지 않는다
        a.set(p, i * 6); a.set(jump ? p : q, i * 6 + 3);
      });
      g.attributes.position.needsUpdate = true;
    };
    return ln;
  };

  // 바람 꼬리 점: 입자마다 지금~dt초 전 위치에 점 k개(앞쪽일수록 크고 진함) — 1px 선보다 휴대폰에서 잘 보인다
  S.trails = (n, color = '#1e7cf2', dt = .16, k = 5, size = 9, opacity = .9) => {
    const g = new T.BufferGeometry(); g.setAttribute('position', new T.BufferAttribute(new Float32Array(n * k * 3), 3));
    const pts = new T.Points(g, new T.PointsMaterial({ color, size, sizeAttenuation: false, transparent: true, opacity, depthWrite: false }));
    S.scene.add(pts); pts.seed = Array.from({ length: n }, () => [S.rand(), S.rand(), S.rand()]);
    pts.place = (fn, t) => {
      const a = g.attributes.position.array;
      pts.seed.forEach((s, i) => { const p0 = fn(s, t, i);
        for (let j = 0; j < k; j++) { const p = j ? fn(s, t - dt * j / (k - 1), i) : p0; const far = Math.hypot(p[0] - p0[0], p[1] - p0[1], p[2] - p0[2]) > 300; a.set(far ? p0 : p, (i * k + j) * 3); } });
      g.attributes.position.needsUpdate = true;
    };
    return pts;
  };

  // 카메라: 목표점 둘레를 도는 궤도(각도는 도)
  S.orbit = (t, o) => {
    const k = (o.ease || S.ease.inout)(S.prog(t, o.at || 0, o.dur || 6));
    const a = (S.lerp(o.from, o.to, k)) * Math.PI / 180, r = S.lerp(o.radius, o.radius2 ?? o.radius, k), h = S.lerp(o.height, o.height2 ?? o.height, k);
    const L = o.look || [0, 0, 0], L2 = o.look2 || L;
    S.cam.position.set(Math.sin(a) * r, h, Math.cos(a) * r);
    S.cam.lookAt(S.lerp(L[0], L2[0], k), S.lerp(L[1], L2[1], k), S.lerp(L[2], L2[2], k));
  };

  // 그 거리(카메라 → 물체)에서 화면에 보이는 반폭·반높이(3D 단위). 세로(9:16)는 좌우가 좁다: fov 42면 거리 900에서 반폭 약 194
  S.viewHalf = (dist) => { const h = Math.tan(S.cam.fov * Math.PI / 360) * dist; return { w: h * S.cam.aspect, h }; };

  // 세로 안전 영역(px): 위 220·아래 380은 쇼츠 버튼·제목이 덮고, cap은 말 자막 띠(vertical.css .cap top 1120, 두 줄까지)
  S.SAFE = { top: 220, bottom: H - 380, side: 40, cap: [1100, 1260], gap: 12 };

  // HTML 꼬리표를 3D 위치에 붙인다(카메라가 움직여도 따라감). pos = [x, y, z] 또는 () => [x, y, z](움직이는 물체 따라가기)
  // 세로 화면에선 기본으로 안전 영역 안에 붙잡고(화면 밖·버튼 밑으로 안 나감) 말 자막 띠를 피해 위·아래로 비킨다.
  //   S.tag(el, pos, {safe: false}) 끄기 / {avoid: false} 자막 띠 피하기만 끄기 / {avoid: [위, 아래]} 다른 띠
  // 카메라 뒤로 간 점의 꼬리표는 숨긴다.
  S._tags = [];
  S.tag = (el, pos, o = {}) => {
    const v = new T.Vector3(), A = S.SAFE, safe = o.safe ?? (H > W);
    S._tags.push(() => {
      v.set(...(typeof pos === 'function' ? pos() : pos)).project(S.cam);
      let x = (v.x + 1) / 2 * W, y = (1 - v.y) / 2 * H;
      el.style.visibility = v.z > 1 ? 'hidden' : '';
      if (safe) {
        const w = el.offsetWidth, h = el.offsetHeight, cap = o.avoid === false ? null : (o.avoid || A.cap);
        x = Math.max(A.side + w / 2, Math.min(W - A.side - w / 2, x));
        y = Math.max(A.top + h / 2, Math.min(A.bottom - h / 2, y));
        if (cap && y + h / 2 > cap[0] - A.gap && y - h / 2 < cap[1] + A.gap) y = y < (cap[0] + cap[1]) / 2 ? cap[0] - A.gap - h / 2 : cap[1] + A.gap + h / 2;
      }
      el.style.left = x + 'px'; el.style.top = y + 'px';
    });
  };

  // 잘라 본 땅 단면(앞면이 z=0인 지층 상자들) + 선택: 묻힌 기초(뒤쪽 반원 + 잘린 면). 탑·다리·건물이 왜 기우는지·버티는지 설명할 때.
  //   const soil = S.section({ layers: [{name:'top', top:0, bottom:-8, color:'#8fb05f'}, …], found: {r: 98, h: 30} });
  //   soil.layers.clay.material.emissive.setRGB(.3, .1, .1)   // 한 층 강조
  //   o: w 폭(1300), d 깊이(700), x·z 위치, layers(기본 S.SOIL = 잔디·모래·무른 점토·깊은 모래), found {r 반지름, h 두께, y 윗면(0), color}
  //   S.ground()와 같이 쓰지 않는다(맨 위 층이 바닥 노릇을 한다). 1단위 = 10cm로 잡으면 숫자 맞추기 쉽다.
  S.SOIL = [{ name: 'top', top: 0, bottom: -8, color: '#8fb05f' }, { name: 'sand', top: -8, bottom: -70, color: '#d4b483' },
            { name: 'clay', top: -70, bottom: -300, color: '#8e9aa5' }, { name: 'deep', top: -300, bottom: -420, color: '#b99a63' }];
  S.section = (o = {}) => {
    const grp = new T.Group(); (o.parent || S.scene).add(grp);
    const Wd = o.w || 1300, D = o.d || 700, layers = {};
    (o.layers || S.SOIL).forEach((L, i) => {
      const m = new T.Mesh(new T.BoxGeometry(Wd, L.top - L.bottom, D), S.mat(L.color, { rough: 1 }));
      m.position.set(o.x || 0, (L.top + L.bottom) / 2, (o.z || 0) - D / 2); m.receiveShadow = true; grp.add(m); layers[L.name || i] = m;
    });
    let found = null;
    if (o.found) {
      const f = o.found, fm = S.mat(f.color || '#a9a196', { rough: .9 }), y = (f.y || 0) - f.h / 2;
      found = new T.Mesh(new T.CylinderGeometry(f.r, f.r, f.h, 32, 1, false, Math.PI / 2, Math.PI), fm);   // 단면이라 뒤쪽 반원만
      found.position.set(o.x || 0, y, o.z || 0); grp.add(found);
      const face = new T.Mesh(new T.BoxGeometry(f.r * 2, f.h, 2), fm); face.position.set(o.x || 0, y, o.z || 0); grp.add(face);
    }
    return { group: grp, layers, found };
  };
})();
