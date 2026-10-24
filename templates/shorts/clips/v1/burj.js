/* 예제 모형: Y자 평면 + 계단식 셋백 탑(실제 건물을 단순화한 설명용 모형, 1단위 = 1m). scene3d.js 다음에 넣는다.
   BURJ.build(S, {ghostAbove, color}) → {group, tiers:[mesh 묶음], height}
   - 날개 셋(120° 간격)이 층이 올라갈 때마다 한 날개씩 돌아가며 짧아진다(나선형 셋백). */
window.BURJ = {
  build(S, o = {}) {
    const T = S.T, grp = new T.Group(); S.scene.add(grp);
    const solid = S.mat(o.color || '#c6d6e6', { metal: .12, rough: .4 });
    const ghost = S.mat('#ffffff', { opacity: .18, rough: .9 }); ghost.depthWrite = false;
    const N = 27, top = 600, tiers = [];
    let wings = [1, 1, 1], y = 0;
    for (let i = 0; i < N; i++) {
      const h = top / N;
      const mat = o.ghostAbove != null && y >= o.ghostAbove ? ghost : solid;
      const blk = S.yBlock({ core: 17, wid: 30, len: 78, h, y, wings: wings.map(w => Math.max(0, w)), material: mat, parent: grp });
      blk.userData.y = y; tiers.push(blk);
      wings[i % 3] -= .095;   // 나선: 날개 하나씩 돌아가며 깎임
      y += h;
    }
    const spireMat = o.ghostAbove != null ? ghost : solid;   // 꼭대기 중심 기둥·첨탑
    for (let k = 0; k < 6; k++) {
      const h = 28, r = 15 - k * 2.1;
      const m = new T.Mesh(new T.CylinderGeometry(r * .92, r, h, 6), y >= (o.ghostAbove ?? 1e9) ? spireMat : solid);
      m.position.y = y + h / 2; m.castShadow = true; grp.add(m); y += h;
    }
    const spire = new T.Mesh(new T.ConeGeometry(4, 828 - y, 6), y >= (o.ghostAbove ?? 1e9) ? spireMat : solid);
    spire.position.y = y + (828 - y) / 2; grp.add(spire);
    return { group: grp, tiers, height: 828 };
  }
};
