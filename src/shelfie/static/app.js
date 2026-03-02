/* ── Shelfie Web UI ─────────────────────────────────────────── */

const API = {
  search:    (q) => fetch(`/api/search?q=${encodeURIComponent(q)}`).then(r => r.json()),
  logRead:   (d) => fetch('/api/reads', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(d) }).then(r => { if (!r.ok) return r.json().then(e => Promise.reject(e)); return r.json(); }),
  listReads: (p) => { const u = new URL('/api/reads', location.origin); Object.entries(p || {}).forEach(([k, v]) => { if (v) u.searchParams.set(k, v); }); return fetch(u).then(r => r.json()); },
  recommend: (d) => fetch('/api/recommend', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(d) }).then(r => { if (!r.ok) return r.json().then(e => Promise.reject(e)); return r.json(); }),
  sessions:  ()  => fetch('/api/sessions').then(r => r.json()),
};

/* ── Tab Navigation ──────────────────────────────────────────── */

const tabBtns = document.querySelectorAll('.tab-btn');
const views   = document.querySelectorAll('.view');

function switchTab(name) {
  tabBtns.forEach(b => b.classList.toggle('active', b.dataset.tab === name));
  views.forEach(v => v.classList.toggle('hidden', v.id !== `view-${name}`));
  if (name === 'bookshelf') loadBookshelf();
  if (name === 'recommend') loadRecHistory();
}
window.switchTab = switchTab;

tabBtns.forEach(b => b.addEventListener('click', () => switchTab(b.dataset.tab)));

/* ── Voice Input (Web Speech API) ────────────────────────────── */

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

function attachVoice(micBtn, target, { onResult, continuous = false } = {}) {
  if (!SpeechRecognition) {
    micBtn.style.display = 'none';
    return;
  }
  let recognition = null;

  micBtn.addEventListener('click', () => {
    if (recognition) { recognition.stop(); return; }

    recognition = new SpeechRecognition();
    recognition.continuous = continuous;
    recognition.interimResults = false;
    recognition.lang = 'en-US';
    micBtn.classList.add('listening');

    recognition.onresult = (e) => {
      const transcript = Array.from(e.results).map(r => r[0].transcript).join(' ').trim();
      if (target.tagName === 'TEXTAREA') {
        target.value = target.value ? target.value + ' ' + transcript : transcript;
      } else {
        target.value = transcript;
      }
      if (onResult) onResult(transcript);
    };
    recognition.onerror = () => { micBtn.classList.remove('listening'); recognition = null; };
    recognition.onend  = () => { micBtn.classList.remove('listening'); recognition = null; };
    recognition.start();
  });
}

/* ── Helpers ─────────────────────────────────────────────────── */

function esc(str) {
  if (!str) return '';
  const el = document.createElement('span');
  el.textContent = str;
  return el.innerHTML;
}

function starsHtml(rating) {
  return `<span class="text-yellow-400 tracking-wide">${'\u2605'.repeat(rating)}${'\u2606'.repeat(5 - rating)}</span>`;
}

function statusPill(status) {
  const cls = status === 'read' ? 'status-read' : status === 'reading' ? 'status-reading' : 'status-did-not-finish';
  return `<span class="status-pill ${cls}">${esc(status)}</span>`;
}

function formatDate(iso) {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  } catch { return iso; }
}

/* ── Bookshelf ───────────────────────────────────────────────── */

const shelfGrid  = document.getElementById('bookshelf-grid');
const shelfEmpty = document.getElementById('bookshelf-empty');

async function loadBookshelf() {
  const status = document.getElementById('filter-status').value;
  const rating = document.getElementById('filter-rating').value;
  const reads  = await API.listReads({ status, min_rating: rating });

  shelfGrid.innerHTML = '';
  shelfEmpty.classList.toggle('hidden', reads.length > 0);

  reads.forEach(r => {
    const card = document.createElement('div');
    card.className = 'card flex flex-col gap-2.5';
    card.innerHTML = `
      <div>
        <p class="font-semibold text-white leading-snug">${esc(r.title)}</p>
        <p class="text-sm text-gray-400 mt-0.5">${esc(r.author)}</p>
      </div>
      <div class="flex items-center gap-2">
        ${starsHtml(r.rating)}
        ${statusPill(r.status)}
      </div>
      ${r.review ? `<p class="text-[13px] text-gray-400 line-clamp-2 leading-relaxed">${esc(r.review)}</p>` : ''}
      ${r.finished_at ? `<p class="text-xs text-gray-500">${formatDate(r.finished_at)}</p>` : ''}
    `;
    shelfGrid.appendChild(card);
  });
}

document.getElementById('filter-status').addEventListener('change', loadBookshelf);
document.getElementById('filter-rating').addEventListener('change', loadBookshelf);

/* ── Log ─────────────────────────────────────────────────────── */

const logQuery    = document.getElementById('log-query');
const logResults  = document.getElementById('log-results');
const stepSearch  = document.getElementById('log-step-search');
const stepDetails = document.getElementById('log-step-details');
const stepDone    = document.getElementById('log-step-done');

let chosenBook = null;
let logRating  = 3;

async function doLogSearch() {
  const q = logQuery.value.trim();
  if (!q) return;
  logResults.innerHTML = '<div class="flex justify-center py-6"><div class="search-spinner"></div></div>';

  try {
    const results = await API.search(q);
    if (!results.length) {
      logResults.innerHTML = '<p class="text-gray-500 text-sm py-4">No results found. Try a different name.</p>';
      return;
    }
    logResults.innerHTML = '';
    results.forEach(book => {
      const el = document.createElement('div');
      el.className = 'card card-selectable';
      el.innerHTML = `
        <p class="font-semibold text-white">${esc(book.title)}</p>
        <p class="text-sm text-gray-400 mt-0.5">${esc(book.author)}${book.published_date ? ' <span class="text-gray-500">\u00b7 ' + esc(book.published_date) + '</span>' : ''}</p>
        ${book.description ? `<p class="text-[13px] text-gray-500 mt-1.5 line-clamp-2">${esc(book.description.slice(0, 160))}</p>` : ''}
      `;
      el.addEventListener('click', () => selectBook(book));
      logResults.appendChild(el);
    });
  } catch {
    logResults.innerHTML = '<p class="text-red-400 text-sm py-4">Search failed. Please try again.</p>';
  }
}

function selectBook(book) {
  chosenBook = book;
  document.getElementById('log-chosen-title').textContent = book.title;
  document.getElementById('log-chosen-author').textContent = book.author;
  logRating = 3;
  renderStars();
  document.getElementById('log-status').value = 'read';
  document.getElementById('log-date').valueAsDate = new Date();
  document.getElementById('log-review').value = '';
  stepSearch.classList.add('hidden');
  stepDetails.classList.remove('hidden');
}

function renderStars() {
  document.querySelectorAll('#log-stars .star').forEach(s => {
    const v = parseInt(s.dataset.star);
    s.innerHTML = v <= logRating ? '\u2605' : '\u2606';
    s.classList.toggle('filled', v <= logRating);
  });
}
renderStars();

document.getElementById('log-stars').addEventListener('click', e => {
  const star = e.target.closest('.star');
  if (star) { logRating = parseInt(star.dataset.star); renderStars(); }
});

document.getElementById('log-search-btn').addEventListener('click', doLogSearch);
logQuery.addEventListener('keydown', e => { if (e.key === 'Enter') doLogSearch(); });

document.getElementById('log-back-btn').addEventListener('click', () => {
  stepDetails.classList.add('hidden');
  stepSearch.classList.remove('hidden');
});

document.getElementById('log-save-btn').addEventListener('click', async () => {
  if (!chosenBook) return;
  const btn = document.getElementById('log-save-btn');
  btn.disabled = true;
  btn.textContent = 'Saving...';

  try {
    const payload = {
      title: chosenBook.title,
      author: chosenBook.author,
      isbn: chosenBook.isbn || '',
      rating: logRating,
      review: document.getElementById('log-review').value.trim(),
      status: document.getElementById('log-status').value,
      finished_at: document.getElementById('log-date').value || null,
    };
    await API.logRead(payload);

    document.getElementById('log-done-title').textContent = chosenBook.title;
    document.getElementById('log-done-sub').textContent =
      '\u2605'.repeat(logRating) + '\u2606'.repeat(5 - logRating) + '  \u2014  logged!';

    stepDetails.classList.add('hidden');
    stepDone.classList.remove('hidden');
  } catch (err) {
    alert(err.detail || 'Failed to save. Please try again.');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Save';
  }
});

document.getElementById('log-another-btn').addEventListener('click', () => {
  chosenBook = null;
  logQuery.value = '';
  logResults.innerHTML = '';
  stepDone.classList.add('hidden');
  stepSearch.classList.remove('hidden');
  logQuery.focus();
});

attachVoice(document.getElementById('log-mic'), logQuery, { onResult: () => doLogSearch() });
attachVoice(document.getElementById('review-mic'), document.getElementById('log-review'), { continuous: true });

/* ── Search ──────────────────────────────────────────────────── */

const searchQuery   = document.getElementById('search-query');
const searchResults = document.getElementById('search-results');

async function doSearch() {
  const q = searchQuery.value.trim();
  if (!q) return;
  searchResults.innerHTML = '<div class="flex justify-center py-6"><div class="search-spinner"></div></div>';

  try {
    const results = await API.search(q);
    if (!results.length) {
      searchResults.innerHTML = '<p class="text-gray-500 text-sm py-4">No results found.</p>';
      return;
    }
    searchResults.innerHTML = '';
    results.forEach((book, i) => {
      const ratingStr = book.average_rating
        ? `${book.average_rating.toFixed(1)}/5 (${book.ratings_count})`
        : '';
      const el = document.createElement('div');
      el.className = 'card';
      el.innerHTML = `
        <div class="flex justify-between items-start gap-4">
          <div class="min-w-0 flex-1">
            <p class="font-semibold text-white">${esc(book.title)}</p>
            <p class="text-sm text-gray-400 mt-0.5">${esc(book.author)}</p>
            <div class="flex flex-wrap gap-x-3 mt-1.5 text-xs text-gray-500">
              ${book.published_date ? `<span>${esc(book.published_date)}</span>` : ''}
              ${book.page_count ? `<span>${book.page_count} pages</span>` : ''}
              ${ratingStr ? `<span>${ratingStr}</span>` : ''}
              ${book.isbn ? `<span>ISBN ${esc(book.isbn)}</span>` : ''}
            </div>
            ${book.categories?.length ? `<p class="text-xs text-gray-500 mt-1">${book.categories.map(esc).join(', ')}</p>` : ''}
            ${book.description ? `<p class="text-[13px] text-gray-400 mt-2 line-clamp-3">${esc(book.description.slice(0, 300))}</p>` : ''}
          </div>
          <span class="text-xs text-gray-600 font-mono shrink-0">#${i + 1}</span>
        </div>
        ${book.info_url ? `<a href="${esc(book.info_url)}" target="_blank" rel="noopener" class="inline-block text-xs text-brand-400 hover:text-brand-500 mt-2.5">More info &rarr;</a>` : ''}
      `;
      searchResults.appendChild(el);
    });
  } catch {
    searchResults.innerHTML = '<p class="text-red-400 text-sm py-4">Search failed.</p>';
  }
}

document.getElementById('search-btn').addEventListener('click', doSearch);
searchQuery.addEventListener('keydown', e => { if (e.key === 'Enter') doSearch(); });
attachVoice(document.getElementById('search-mic'), searchQuery, { onResult: () => doSearch() });

/* ── Recommend ───────────────────────────────────────────────── */

const recForm    = document.getElementById('rec-form');
const recLoading = document.getElementById('rec-loading');
const recResults = document.getElementById('rec-results');

document.getElementById('rec-submit').addEventListener('click', async () => {
  const mood = document.getElementById('rec-mood').value.trim();
  if (!mood) { document.getElementById('rec-mood').focus(); return; }
  const direction = document.querySelector('input[name="direction"]:checked')?.value || 'balance';

  recForm.classList.add('hidden');
  recLoading.classList.remove('hidden');
  recResults.classList.add('hidden');

  try {
    const session = await API.recommend({ mood, direction });
    renderRecs(session);
    recLoading.classList.add('hidden');
    recResults.classList.remove('hidden');
  } catch (err) {
    recLoading.classList.add('hidden');
    recForm.classList.remove('hidden');
    alert(err.detail || 'Failed to get recommendations.');
  }
});

function renderRecs(session) {
  recResults.innerHTML = `
    <div class="flex items-center justify-between mb-4">
      <p class="text-sm text-gray-400">${session.recommendations.length} recommendations</p>
      <button class="btn-secondary text-xs" id="rec-new-btn">New request</button>
    </div>
  `;

  session.recommendations.forEach((rec, i) => {
    const badge = matchBadge(rec.match_type);
    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = `
      <div class="flex items-start gap-3">
        <span class="text-brand-400 font-bold text-sm mt-0.5 shrink-0">#${i + 1}</span>
        <div class="min-w-0">
          <p class="font-semibold text-white">${esc(rec.title)} <span class="font-normal text-gray-400">by ${esc(rec.author)}</span></p>
          <p class="text-[13px] text-gray-400 mt-1.5 leading-relaxed">${esc(rec.reason)}</p>
          <span class="badge ${badge.cls} mt-2 inline-block">${badge.label}</span>
        </div>
      </div>
    `;
    recResults.appendChild(card);
  });

  document.getElementById('rec-new-btn').addEventListener('click', () => {
    recResults.classList.add('hidden');
    recForm.classList.remove('hidden');
    loadRecHistory();
  });
}

function matchBadge(type) {
  const map = {
    'safe bet':     { cls: 'badge-safe',    label: 'safe bet' },
    'stretch pick': { cls: 'badge-stretch', label: 'stretch pick' },
    'wild card':    { cls: 'badge-wild',    label: 'wild card' },
  };
  return map[type] || { cls: 'badge-safe', label: type };
}

async function loadRecHistory() {
  const container = document.getElementById('rec-history');
  const emptyMsg  = document.getElementById('rec-history-empty');

  try {
    const sessions = await API.sessions();
    container.innerHTML = '';
    emptyMsg.classList.toggle('hidden', sessions.length > 0);

    sessions.forEach(session => {
      const el = document.createElement('div');
      el.className = 'card';

      let html = `
        <div class="flex items-center gap-2 mb-3">
          <span class="text-xs text-gray-500">${formatDate(session.created_at)}</span>
          <span class="font-medium text-sm text-gray-200">${esc(session.mood)}</span>
          <span class="text-xs text-gray-500">${session.direction}</span>
        </div>
        <div class="space-y-1">
      `;
      session.recommendations.forEach((rec, i) => {
        const badge = matchBadge(rec.match_type);
        html += `<p class="text-sm text-gray-300 pl-3"><span class="text-brand-400 font-medium">#${i + 1}</span> ${esc(rec.title)} <span class="text-gray-500">by ${esc(rec.author)}</span> <span class="badge ${badge.cls}">${badge.label}</span></p>`;
      });
      html += '</div>';
      el.innerHTML = html;
      container.appendChild(el);
    });
  } catch {
    container.innerHTML = '';
    emptyMsg.classList.remove('hidden');
  }
}

attachVoice(document.getElementById('mood-mic'), document.getElementById('rec-mood'), { continuous: true });

/* ── Boot ────────────────────────────────────────────────────── */

loadBookshelf();
