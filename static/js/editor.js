(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const csrf = document.querySelector('meta[name=csrf-token]').content;
  const ta = $('content'), form = $('post-form'), grid = $('media-grid'), status = $('media-status');
  const draftKey = 'scp-draft-' + form.dataset.postId;
  const selected = new Set();

  function insert(before, after = '', ph = '') {
    const s = ta.selectionStart, e = ta.selectionEnd, sel = ta.value.slice(s, e) || ph;
    ta.setRangeText(before + sel + after, s, e, 'select'); ta.focus(); ta.dispatchEvent(new Event('input'));
  }
  function insertBlock(text) {
    const s = ta.selectionStart; ta.setRangeText('\n\n' + text + '\n\n', s, ta.selectionEnd, 'end');
    ta.focus(); ta.dispatchEvent(new Event('input'));
  }
  const actions = {
    bold: () => insert('**', '**', 'texte'), italic: () => insert('*', '*', 'texte'),
    h2: () => insert('\n## ', '', 'Titre'), h3: () => insert('\n### ', '', 'Sous-titre'),
    quote: () => insert('\n> ', '', 'citation'), list: () => insert('\n- ', '', 'élément'),
    code: () => insert('`', '`', 'code'), link: () => insert('[', '](https://)', 'texte'),
    redacted: () => insert('||', '||', 'texte expurgé'), warn: () => insert('⚠ '),
    youtube: () => { const u = prompt('Lien YouTube :'); if (u) insertBlock(`[[youtube: ${u.trim()}]]`); },
  };
  $('toolbar').addEventListener('click', e => { const b = e.target.closest('[data-act]'); if (b) actions[b.dataset.act](); });

  // ---- Médias ----
  const opt = () => ({ align: $('opt-align').value, width: $('opt-width').value, cap: $('opt-caption').value.trim().replace(/[|\]]/g, ' '),
                       loop: $('opt-loop').checked });
  function shortcode(url, kind) {
    const o = opt(); const parts = [url];
    if (o.align !== 'full') parts.push('align=' + o.align);
    if (o.width !== '100') parts.push('width=' + o.width);
    if (o.cap) parts.push('caption=' + o.cap);
    if (o.loop && kind === 'video') parts.push('loop');
    return `[[media: ${parts.join(' | ')}]]`;
  }
  function addItem(it, prepend = true) {
    const el = document.createElement('div'); el.className = 'mitem'; el.dataset.url = it.url; el.dataset.kind = it.kind; el.dataset.id = it.id;
    const th = it.kind === 'video' ? document.createElement('video') : document.createElement('img');
    th.className = 'mthumb'; th.src = it.url; th.title = it.name || ''; if (it.kind === 'video') { th.muted = true; th.preload = 'metadata'; } else th.loading = 'lazy';
    const k = document.createElement('span'); k.className = 'mkind'; k.textContent = it.kind === 'video' ? 'VIDÉO' : (/\.gif($|\?)/i.test(it.url) ? 'GIF' : 'IMAGE');
    const b = document.createElement('div'); b.className = 'mbtns';
    b.innerHTML = '<button type="button" data-m="insert">Insérer</button><button type="button" data-m="cover">Couverture</button><button type="button" data-m="select">Sélection</button><button type="button" data-m="del" class="del">Supprimer</button>';
    if (it.kind === 'video') b.querySelector('[data-m=cover]').remove();
    el.append(th, k, b); prepend ? grid.prepend(el) : grid.append(el); return el;
  }
  async function loadLibrary() {
    try { const r = await fetch('/admin/media'); const j = await r.json(); j.items.forEach(i => addItem(i, false)); if (!j.items.length) status.textContent = 'Bibliothèque vide.'; }
    catch { status.textContent = 'Impossible de charger la bibliothèque.'; }
  }
  grid.addEventListener('click', async e => {
    const btn = e.target.closest('[data-m]'), item = e.target.closest('.mitem'); if (!item) return;
    const url = item.dataset.url, kind = item.dataset.kind, act = btn ? btn.dataset.m : 'insert';
    if (act === 'insert') insertBlock(shortcode(url, kind));
    else if (act === 'cover') { $('cover').value = url; $('cover-preview').innerHTML = ''; const im = new Image(); im.src = url; $('cover-preview').append(im); }
    else if (act === 'select') { item.classList.toggle('sel'); item.classList.contains('sel') ? selected.add(url) : selected.delete(url); }
    else if (act === 'del' && confirm('Supprimer ce média ? Les documents qui l\'utilisent afficheront un lien cassé.')) {
      const r = await fetch(`/admin/media/${item.dataset.id}/delete`, { method: 'POST', headers: { 'X-CSRF-Token': csrf, 'Accept': 'application/json' } });
      if (r.ok) item.remove();
    }
  });
  $('insert-gallery').addEventListener('click', () => {
    if (selected.size < 2) { status.textContent = 'Sélectionne au moins 2 médias (bouton « Sélection »).'; return; }
    insertBlock(`[[gallery: ${[...selected].join(' | ')}]]`);
    grid.querySelectorAll('.sel').forEach(x => x.classList.remove('sel')); selected.clear();
  });
  async function upload(files, autoInsert) {
    files = [...files]; if (!files.length) return;
    const fd = new FormData(); files.forEach(f => fd.append('files', f));
    status.textContent = 'Envoi en cours…';
    try {
      const r = await fetch('/admin/upload', { method: 'POST', headers: { 'X-CSRF-Token': csrf, 'Accept': 'application/json' }, body: fd });
      const j = await r.json();
      (j.items || []).forEach(i => { addItem(i); if (autoInsert) insertBlock(shortcode(i.url, i.kind)); });
      status.textContent = (j.errors && j.errors.length) ? j.errors.join(' ') : (j.error || `${(j.items || []).length} média(s) ajouté(s).`);
    } catch { status.textContent = 'Échec de l\'envoi.'; }
  }
  const dz = $('dropzone'), fi = $('file-input');
  dz.addEventListener('click', e => { if (e.target !== fi) fi.click(); });
  fi.addEventListener('change', () => { upload(fi.files, false); fi.value = ''; });
  ['dragenter', 'dragover'].forEach(ev => dz.addEventListener(ev, e => { e.preventDefault(); dz.classList.add('over'); }));
  ['dragleave', 'drop'].forEach(ev => dz.addEventListener(ev, e => { e.preventDefault(); dz.classList.remove('over'); }));
  dz.addEventListener('drop', e => upload(e.dataTransfer.files, false));
  ta.addEventListener('dragover', e => e.preventDefault());
  ta.addEventListener('drop', e => { if (e.dataTransfer.files.length) { e.preventDefault(); upload(e.dataTransfer.files, true); } });
  ta.addEventListener('paste', e => { const fs = [...e.clipboardData.files]; if (fs.length) { e.preventDefault(); upload(fs, true); } });
  $('cover-clear').addEventListener('click', () => { $('cover').value = ''; $('cover-preview').innerHTML = '<span>Aucune couverture</span>'; });

  // ---- Aperçu ----
  let prevOn = false, timer;
  async function refreshPreview() {
    const r = await fetch('/admin/preview', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf, 'Accept': 'application/json' }, body: JSON.stringify({ content: ta.value }) });
    if (r.ok) $('preview').innerHTML = (await r.json()).html;
  }
  $('toggle-preview').addEventListener('click', () => {
    prevOn = !prevOn; $('preview').hidden = !prevOn; ta.hidden = prevOn; if (prevOn) refreshPreview();
    $('toggle-preview').textContent = prevOn ? '✎ Éditer' : '👁 Aperçu';
  });

  // ---- Compteur + brouillon local ----
  const count = () => { const w = ta.value.trim() ? ta.value.trim().split(/\s+/).length : 0; $('wordcount').textContent = `${w} mots · ≈ ${Math.max(1, Math.round(w / 200))} min`; };
  ta.addEventListener('input', () => {
    count(); clearTimeout(timer);
    timer = setTimeout(() => { try { localStorage.setItem(draftKey, JSON.stringify({ c: ta.value, t: form.elements.title.value })); $('draftstate').textContent = 'Brouillon local sauvegardé'; } catch {} if (prevOn) refreshPreview(); }, 800);
  });
  try {
    const saved = JSON.parse(localStorage.getItem(draftKey) || 'null');
    if (saved && saved.c && saved.c !== ta.value) {
      const b = document.createElement('button'); b.type = 'button'; b.className = 'btn small ghost'; b.textContent = '↺ Restaurer le brouillon local non enregistré';
      b.onclick = () => { ta.value = saved.c; if (saved.t && !form.elements.title.value) form.elements.title.value = saved.t; b.remove(); count(); };
      $('draftstate').replaceChildren(b);
    }
  } catch {}
  form.addEventListener('submit', () => { try { localStorage.removeItem(draftKey); } catch {} });
  count(); loadLibrary();
})();
