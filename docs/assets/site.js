(function () {
  var d = document, side = d.getElementById('side'), menu = d.getElementById('menu');
  menu.addEventListener('click', function () { menu.setAttribute('aria-expanded', side.classList.toggle('open')); });
  d.querySelector('main').addEventListener('click', function () { side.classList.remove('open'); });
  var bar = d.getElementById('progress');
  addEventListener('scroll', function () {
    var h = d.documentElement.scrollHeight - innerHeight; bar.style.width = (h > 0 ? scrollY / h * 100 : 0) + '%';
  }, { passive: true });
  d.querySelectorAll('.doc pre:not(.mermaid)').forEach(function (pre) {
    var b = d.createElement('button'); b.className = 'copy'; b.textContent = 'Copier';
    b.onclick = function () {
      navigator.clipboard.writeText(pre.querySelector('code').innerText).then(function () {
        b.textContent = '✓ Copié'; setTimeout(function () { b.textContent = 'Copier'; }, 1500);
      });
    };
    pre.appendChild(b);
  });
  if (d.querySelector('pre.mermaid')) {
    import('https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs').then(function (m) {
      m.default.initialize({ startOnLoad: false, theme: 'dark', securityLevel: 'strict' });
      m.default.run({ querySelector: 'pre.mermaid' });
    }).catch(function () {});
  }
})();
