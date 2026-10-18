/* ────────────────────────────────────────────────
   FileConvert – Frontend Logic
   ──────────────────────────────────────────────── */

// ── State ─────────────────────────────────────────
let currentCategory = 'image';
let jobCounter = 0;

const IMAGE_EXTS = ['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'tiff', 'tif', 'ico'];
const DOC_EXTS = ['pdf', 'txt', 'docx', 'html', 'htm', 'csv', 'xlsx', 'md'];

const DROP_HINTS = {
    image: 'JPG · PNG · WEBP · GIF · BMP · TIFF · ICO',
    document: 'PDF · DOCX · TXT · HTML · CSV · XLSX · MD',
};

// ── Category ──────────────────────────────────────
function setCategory(cat) {
    currentCategory = cat;
    document.getElementById('tabImage').classList.toggle('active', cat === 'image');
    document.getElementById('tabDocument').classList.toggle('active', cat === 'document');
    document.getElementById('dropSub').textContent = DROP_HINTS[cat];
    document.getElementById('fileInput').value = '';
}

// ── Drag & Drop ───────────────────────────────────
function onDragOver(e) {
    e.preventDefault();
    document.getElementById('dropzone').classList.add('drag-over');
}
function onDragLeave(e) {
    document.getElementById('dropzone').classList.remove('drag-over');
}
function onDrop(e) {
    e.preventDefault();
    document.getElementById('dropzone').classList.remove('drag-over');
    handleFiles(Array.from(e.dataTransfer.files));
}
function onFileSelect(e) {
    handleFiles(Array.from(e.target.files));
}

// ── File handling ─────────────────────────────────
function getExt(filename) {
    return filename.split('.').pop().toLowerCase();
}
function detectCategory(filename) {
    const ext = getExt(filename);
    if (IMAGE_EXTS.includes(ext)) return 'image';
    if (DOC_EXTS.includes(ext)) return 'document';
    return null;
}

async function handleFiles(files) {
    for (const file of files) {
        const cat = detectCategory(file.name) || currentCategory;
        const ext = getExt(file.name);

        // Fetch valid targets from server
        let targets = [];
        try {
            const res = await fetch(`/api/targets?filename=${encodeURIComponent(file.name)}&category=${cat}`);
            const data = await res.json();
            targets = data.targets || [];
        } catch (err) {
            targets = [];
        }

        if (targets.length === 0) {
            addJobUnsupported(file, cat);
            continue;
        }

        addJob(file, cat, ext, targets);
    }
}

// ── Build job UI ──────────────────────────────────
function addJobUnsupported(file, cat) {
    const id = ++jobCounter;
    const list = document.getElementById('jobList');
    const item = document.createElement('div');
    item.className = 'job-item';
    item.id = `job-${id}`;
    item.innerHTML = `
    <div class="job-icon ${cat === 'image' ? 'img' : 'doc'}">${cat === 'image' ? '🖼️' : '📄'}</div>
    <div class="job-info">
      <div class="job-name">${escHtml(file.name)}</div>
      <div class="job-status-text error">지원하지 않는 파일 형식입니다.</div>
    </div>
    <div class="job-actions">
      <button class="btn-remove" onclick="removeJob(${id})" title="삭제">✕</button>
    </div>`;
    list.prepend(item);
}

function addJob(file, cat, ext, targets) {
    const id = ++jobCounter;
    const list = document.getElementById('jobList');

    const optionsHtml = targets.map(t =>
        `<option value="${t}">${t.toUpperCase()}</option>`
    ).join('');

    const item = document.createElement('div');
    item.className = 'job-item';
    item.id = `job-${id}`;
    item.innerHTML = `
    <div class="job-icon ${cat === 'image' ? 'img' : 'doc'}">${cat === 'image' ? '🖼️' : '📄'}</div>
    <div class="job-info">
      <div class="job-name" title="${escHtml(file.name)}">${escHtml(file.name)}</div>
      <div class="job-format-row">
        <span class="fmt-badge">${ext.toUpperCase()}</span>
        <span class="fmt-arrow">→</span>
        <select class="fmt-select" id="select-${id}">${optionsHtml}</select>
      </div>
      <div class="job-status-bar"><div class="job-status-fill" id="fill-${id}"></div></div>
      <div class="job-status-text" id="status-${id}">변환 준비 완료</div>
    </div>
    <div class="job-actions" id="actions-${id}">
      <button class="btn-convert" id="cvtBtn-${id}" onclick="convertJob(${id})">변환</button>
      <button class="btn-remove" onclick="removeJob(${id})" title="삭제">✕</button>
    </div>`;

    // Store file reference
    item._file = file;
    item._cat = cat;
    list.prepend(item);
}

function removeJob(id) {
    const el = document.getElementById(`job-${id}`);
    if (el) {
        el.style.opacity = '0';
        el.style.transform = 'translateX(-10px)';
        el.style.transition = 'all 0.2s ease';
        setTimeout(() => el.remove(), 200);
    }
}

// ── Convert ───────────────────────────────────────
async function convertJob(id) {
    const item = document.getElementById(`job-${id}`);
    const select = document.getElementById(`select-${id}`);
    const fill = document.getElementById(`fill-${id}`);
    const status = document.getElementById(`status-${id}`);
    const actions = document.getElementById(`actions-${id}`);
    const cvtBtn = document.getElementById(`cvtBtn-${id}`);

    if (!item || !item._file) return;

    const outputFormat = select.value;
    const category = item._cat;
    const file = item._file;

    // ── Loading state ──────────────────────────────
    cvtBtn.disabled = true;
    cvtBtn.innerHTML = '<span class="spinner"></span>변환 중...';
    fill.classList.remove('complete', 'error');
    fill.style.width = '0%';
    status.textContent = '변환 중...';
    status.className = 'job-status-text';

    // Animate progress bar pretend
    let pct = 0;
    const progressTimer = setInterval(() => {
        pct = Math.min(pct + Math.random() * 12, 88);
        fill.style.width = pct + '%';
    }, 200);

    try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('output_format', outputFormat);
        formData.append('category', category);

        const res = await fetch('/api/convert', { method: 'POST', body: formData });

        clearInterval(progressTimer);

        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: '알 수 없는 오류' }));
            throw new Error(err.detail || '변환 실패');
        }

        // ── Success ────────────────────────────────
        fill.style.width = '100%';
        fill.classList.add('complete');
        status.textContent = '✓ 변환 완료!';
        status.className = 'job-status-text success';

        const blob = await res.blob();
        const url = URL.createObjectURL(blob);

        // Extract suggested filename from Content-Disposition
        const cd = res.headers.get('Content-Disposition') || '';
        const fnMatch = cd.match(/filename="?([^";]+)"?/);
        const baseName = fnMatch ? fnMatch[1] : `converted.${outputFormat}`;

        // Replace convert button with download button
        cvtBtn.remove();
        const dlBtn = document.createElement('a');
        dlBtn.href = url;
        dlBtn.download = baseName;
        dlBtn.className = 'btn-download';
        dlBtn.innerHTML = '⬇ 다운로드';
        actions.prepend(dlBtn);

        // Refresh stats dynamically
        updateStats();

    } catch (err) {
        clearInterval(progressTimer);
        fill.style.width = '100%';
        fill.classList.add('error');
        status.textContent = `오류: ${err.message}`;
        status.className = 'job-status-text error';

        cvtBtn.disabled = false;
        cvtBtn.innerHTML = '다시 시도';
    }
}

// ── Live Stats Fetcher ────────────────────────────
async function updateStats() {
    try {
        const res = await fetch('/api/stats');
        if (!res.ok) return;
        const data = await res.json();

        const elTodayVisitors = document.getElementById('statTodayVisitors');
        const elTotalVisitors = document.getElementById('statTotalVisitors');
        const elTodayBytes = document.getElementById('statTodayBytes');
        const elTotalBytes = document.getElementById('statTotalBytes');

        if (elTodayVisitors) elTodayVisitors.textContent = `${data.today_visitors.toLocaleString()}명`;
        if (elTotalVisitors) elTotalVisitors.textContent = `${data.total_visitors.toLocaleString()}명`;
        if (elTodayBytes) elTodayBytes.textContent = data.today_bytes_formatted;
        if (elTotalBytes) elTotalBytes.textContent = data.total_bytes_formatted;
    } catch (e) {
        console.error('Failed to update stats:', e);
    }
}

// Auto load stats on start
document.addEventListener('DOMContentLoaded', updateStats);
// Periodic refresh every 30s
setInterval(updateStats, 30000);

// ── Utilities ─────────────────────────────────────
function escHtml(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

