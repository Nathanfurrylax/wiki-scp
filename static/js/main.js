(() => {
  'use strict';
  const d = document, root = d.documentElement;
  root.classList.add('js');
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const $$ = (s, c = d) => [...c.querySelectorAll(s)];

  // Menu mobile
  $$('[data-nav-toggle]').forEach(b => b.addEventListener('click', () =>
    b.setAttribute('aria-expanded', d.getElementById('nav').classList.toggle('open'))));

  // Confirmations
  d.addEventListener('click', e => {
    const c = e.target.closest('[data-confirm]');
    if (c && !confirm(c.dataset.confirm)) e.preventDefault();
    const cp = e.target.closest('[data-copy]');
    if (cp) navigator.clipboard?.writeText(cp.dataset.copy).then(() => {
      const t = cp.textContent; cp.textContent = '✓ Lien copié'; setTimeout(() => cp.textContent = t, 1600);
    });
    const r = e.target.closest('.redacted'); if (r) r.classList.toggle('show');
    const z = e.target.closest('img[data-zoom]');
    if (z) { const lb = d.createElement('div'); lb.className = 'lightbox'; lb.innerHTML = '<img alt="">';
      lb.firstChild.src = z.currentSrc || z.src; lb.addEventListener('click', () => lb.remove()); d.body.appendChild(lb); }
  });
  addEventListener('keydown', e => { if (e.key === 'Escape') $$('.lightbox').forEach(l => l.remove()); });

  // Apparition au scroll
  const rev = $$('.reveal');
  if ('IntersectionObserver' in window && !reduce) {
    const io = new IntersectionObserver(es => es.forEach(en => {
      if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); }
    }), { threshold: .12, rootMargin: '0px 0px -40px' });
    rev.forEach(el => io.observe(el));
  } else rev.forEach(el => el.classList.add('in'));

  // Spotlight de la souris
  $$('.hero').forEach(h => h.addEventListener('pointermove', e => {
    const r = h.getBoundingClientRect();
    h.style.setProperty('--mx', (e.clientX - r.left) + 'px'); h.style.setProperty('--my', (e.clientY - r.top) + 'px');
  }));

  // Inclinaison 3D des cartes
  if (!reduce && matchMedia('(hover:hover)').matches) $$('[data-tilt]').forEach(c => {
    c.addEventListener('pointermove', e => {
      const r = c.getBoundingClientRect(), x = (e.clientX - r.left) / r.width - .5, y = (e.clientY - r.top) / r.height - .5;
      c.style.setProperty('--ry', (x * 6) + 'deg'); c.style.setProperty('--rx', (-y * 6) + 'deg');
    });
    c.addEventListener('pointerleave', () => { c.style.setProperty('--rx', '0deg'); c.style.setProperty('--ry', '0deg'); });
  });

  // Compteurs animés
  $$('[data-count]').forEach(el => {
    const n = +el.dataset.count; if (reduce || !n) { el.textContent = n; return; }
    const t0 = performance.now();
    (function step(t) { const p = Math.min(1, (t - t0) / 1200); el.textContent = Math.round(n * (1 - Math.pow(1 - p, 3)));
      if (p < 1) requestAnimationFrame(step); })(t0);
  });

  // Séquence de démarrage (machine à écrire)
  const boot = d.getElementById('boot');
  if (boot) {
    const lines = $$('[data-line]', boot);
    if (reduce) lines.forEach(l => l.classList.add('on'));
    else { let i = 0;
      const next = () => { if (i >= lines.length) return; const l = lines[i++], txt = l.textContent;
        lines.forEach(x => x.classList.remove('cur')); l.textContent = ''; l.classList.add('on'); let k = 0;
        const tick = () => { l.textContent = txt.slice(0, ++k); k < txt.length ? setTimeout(tick, 18) : setTimeout(next, 220); }; tick(); };
      next(); }
  }

  // Neige TV (canvas)
  const cv = d.getElementById('static');
  if (cv && !reduce) {
    const ctx = cv.getContext('2d'); cv.width = 160; cv.height = 90; const img = ctx.createImageData(160, 90);
    let last = 0;
    (function draw(t) { if (t - last > 90) { last = t;
      for (let i = 0; i < img.data.length; i += 4) { const v = Math.random() * 255 | 0; img.data[i] = v * .5; img.data[i + 1] = v * .8; img.data[i + 2] = v; img.data[i + 3] = 255; }
      ctx.putImageData(img, 0, 0); }
      if (!d.hidden) requestAnimationFrame(draw); else setTimeout(() => requestAnimationFrame(draw), 500); })(0);
  }

  // Horloge
  const clock = d.getElementById('clock');
  if (clock) { const tick = () => clock.textContent = 'RÉSEAU DE LA FONDATION // ' + new Date().toLocaleTimeString('fr-FR'); tick(); setInterval(tick, 1000); }

  // Barre de lecture + sommaire
  const bar = d.getElementById('progress'), prose = d.getElementById('prose');
  if (bar) addEventListener('scroll', () => {
    const h = root.scrollHeight - innerHeight; bar.style.width = (h > 0 ? scrollY / h * 100 : 0) + '%'; }, { passive: true });
  const toc = d.getElementById('toc');
  if (toc && prose) {
    const hs = $$('h2,h3', prose);
    if (hs.length > 1) {
      hs.forEach((h, i) => { h.id = 'sec-' + i; const a = d.createElement('a'); a.href = '#sec-' + i;
        a.textContent = h.textContent; a.style.paddingLeft = h.tagName === 'H3' ? '10px' : '0'; toc.appendChild(a); });
      const links = $$('a', toc);
      const so = new IntersectionObserver(es => es.forEach(en => { if (en.isIntersecting) {
        links.forEach(l => l.classList.toggle('on', l.hash === '#' + en.target.id)); } }), { rootMargin: '-20% 0px -70%' });
      hs.forEach(h => so.observe(h));
    }
  }
})();
