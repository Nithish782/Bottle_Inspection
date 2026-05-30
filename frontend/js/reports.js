// reports.js — Backend-integrated Reports Dashboard

const REPORTS_API = "http://localhost:8000/reports";

// ── State ─────────────────────────────────────────────────────────────
const reportState = {
    page: 1,
    limit: 20,
    status: "",
    defectType: "",
    cameraSource: "",
    startDate: "",
    endDate: "",
    sortBy: "timestamp",
    sortOrder: "desc",
    total: 0,
    totalPages: 0,
    polling: null,
};

// ── Init ──────────────────────────────────────────────────────────────
function initReports() {
    loadSummary();
    loadHistory();
    loadCameraAnalytics();
    loadAnalyticsCharts();
    loadCameraSourceFilter();
    startPolling();
}

async function loadCameraSourceFilter() {
    try {
        const res = await fetch(`${REPORTS_API}/camera-sources`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const sel = document.getElementById("filterCameraSource");
        if (!sel) return;
        const currentVal = sel.value;
        sel.innerHTML = '<option value="">All Cameras</option>' +
            (data.sources || []).map(s => `<option value="${s}">${s}</option>`).join('');
        if (currentVal) sel.value = currentVal;
    } catch (e) {
        console.log("Could not load camera sources:", e);
    }
}

function startPolling() {
    if (reportState.polling) clearInterval(reportState.polling);
    reportState.polling = setInterval(() => {
        loadSummary(true);
    }, 3000);
}

function stopPolling() {
    if (reportState.polling) {
        clearInterval(reportState.polling);
        reportState.polling = null;
    }
}

// ── Summary Cards ─────────────────────────────────────────────────────
async function loadSummary(silent) {
    try {
        const res = await fetch(`${REPORTS_API}/summary`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        document.getElementById("repTotal").textContent = data.total_bottles.toLocaleString();
        document.getElementById("repPassed").textContent = data.passed_bottles.toLocaleString();
        document.getElementById("repDefective").textContent = data.defective_bottles.toLocaleString();
        document.getElementById("repAccuracy").textContent = data.detection_accuracy + "%";
        document.getElementById("repCamera").textContent = data.active_camera_source;
        document.getElementById("repDuration").textContent = data.inspection_duration;

        if (!silent) showToast("Reports data loaded", "success");
    } catch (e) {
        if (!silent) showToast("Failed to load summary: " + e.message, "error");
    }
}

// ── History Table ─────────────────────────────────────────────────────
async function loadHistory() {
    const params = new URLSearchParams();
    params.set("page", reportState.page);
    params.set("limit", reportState.limit);
    if (reportState.status) params.set("status", reportState.status);
    if (reportState.defectType) params.set("defect_type", reportState.defectType);
    if (reportState.cameraSource) params.set("camera_source", reportState.cameraSource);
    if (reportState.startDate) params.set("start_date", reportState.startDate);
    if (reportState.endDate) params.set("end_date", reportState.endDate);
    if (reportState.sortBy) params.set("sort_by", reportState.sortBy);
    if (reportState.sortOrder) params.set("sort_order", reportState.sortOrder);

    const tbody = document.getElementById("reportsTableBody");
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:40px;color:var(--text-muted);"><div class="spinner" style="margin:0 auto 12px"></div>Loading...</td></tr>`;

    try {
        const res = await fetch(`${REPORTS_API}/history?${params}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        reportState.total = data.total;
        reportState.totalPages = data.total_pages;

        renderTable(data.records);
        renderPagination();
        updateExportUrls();
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:40px;color:var(--neon-red);">Failed to load history: ${e.message}</td></tr>`;
    }
}

function renderTable(records) {
    const tbody = document.getElementById("reportsTableBody");
    if (!records.length) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:40px;color:var(--text-muted);">No detection records found</td></tr>`;
        return;
    }

    tbody.innerHTML = records.map(r => {
        const isPass = r.status === "PASS";
        const statusColor = isPass ? "var(--neon-green)" : "var(--neon-red)";
        const confPct = (typeof r.confidence === 'number' ? (r.confidence * 100) : parseFloat(r.confidence || 0) * 100).toFixed(1);
        return `<tr>
            <td>${r.id}</td>
            <td>${r.timestamp}</td>
            <td><span style="font-family:var(--font-mono);font-weight:600;">${r.bottle_id}</span></td>
            <td><span style="display:inline-block;padding:2px 10px;border-radius:12px;font-size:11px;font-weight:700;background:${isPass ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)'};color:${statusColor};border:1px solid ${isPass ? 'rgba(16,185,129,0.3)' : 'rgba(239,68,68,0.3)'};">${r.status}</span></td>
            <td>${r.defect_type || '—'}</td>
            <td style="font-family:var(--font-mono);">${confPct}%</td>
            <td>${r.camera_source || '—'}</td>
        </tr>`;
    }).join("");
}

function renderPagination() {
    const container = document.getElementById("reportsPagination");
    const { page, totalPages } = reportState;
    if (totalPages <= 1) {
        container.innerHTML = "";
        return;
    }

    let html = `<div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;justify-content:center;">`;
    html += `<button class="btn btn-outline" style="padding:6px 12px;font-size:11px;" onclick="goToPage(${page - 1})" ${page <= 1 ? 'disabled' : ''}>Prev</button>`;

    const maxVisible = 7;
    let startP = Math.max(1, page - Math.floor(maxVisible / 2));
    let endP = Math.min(totalPages, startP + maxVisible - 1);
    if (endP - startP < maxVisible - 1) startP = Math.max(1, endP - maxVisible + 1);

    if (startP > 1) {
        html += `<button class="btn btn-outline" style="padding:6px 10px;font-size:11px;" onclick="goToPage(1)">1</button>`;
        if (startP > 2) html += `<span style="color:var(--text-muted);font-size:11px;">...</span>`;
    }
    for (let i = startP; i <= endP; i++) {
        const active = i === page;
        html += `<button class="btn ${active ? 'btn-primary' : 'btn-outline'}" style="padding:6px 10px;font-size:11px;${active ? '' : ''}" onclick="goToPage(${i})">${i}</button>`;
    }
    if (endP < totalPages) {
        if (endP < totalPages - 1) html += `<span style="color:var(--text-muted);font-size:11px;">...</span>`;
        html += `<button class="btn btn-outline" style="padding:6px 10px;font-size:11px;" onclick="goToPage(${totalPages})">${totalPages}</button>`;
    }

    html += `<button class="btn btn-outline" style="padding:6px 12px;font-size:11px;" onclick="goToPage(${page + 1})" ${page >= totalPages ? 'disabled' : ''}>Next</button>`;
    html += `<span style="color:var(--text-muted);font-size:11px;margin-left:8px;">${page} / ${totalPages}</span>`;
    html += `</div>`;
    container.innerHTML = html;
}

function goToPage(p) {
    if (p < 1 || p > reportState.totalPages) return;
    reportState.page = p;
    loadHistory();
}

function updateSort(col) {
    if (reportState.sortBy === col) {
        reportState.sortOrder = reportState.sortOrder === "asc" ? "desc" : "asc";
    } else {
        reportState.sortBy = col;
        reportState.sortOrder = "desc";
    }
    reportState.page = 1;
    loadHistory();
}

function updateExportUrls() {
    const params = new URLSearchParams();
    if (reportState.status) params.set("status", reportState.status);
    if (reportState.defectType) params.set("defect_type", reportState.defectType);
    if (reportState.cameraSource) params.set("camera_source", reportState.cameraSource);
    if (reportState.startDate) params.set("start_date", reportState.startDate);
    if (reportState.endDate) params.set("end_date", reportState.endDate);
    const qs = params.toString() ? "?" + params.toString() : "";

    document.getElementById("exportCsvBtn").onclick = () => window.open(`${REPORTS_API}/export/csv${qs}`, "_blank");
    document.getElementById("exportPdfBtn").onclick = () => window.open(`${REPORTS_API}/export/pdf`, "_blank");
    document.getElementById("exportExcelBtn").onclick = () => window.open(`${REPORTS_API}/export/excel${qs}`, "_blank");
}

// ── Filters ───────────────────────────────────────────────────────────
function applyFilters() {
    reportState.status = document.getElementById("filterStatus").value;
    reportState.defectType = document.getElementById("filterDefectType").value;
    reportState.cameraSource = document.getElementById("filterCameraSource").value;
    reportState.startDate = document.getElementById("filterStartDate").value;
    reportState.endDate = document.getElementById("filterEndDate").value;
    reportState.page = 1;
    loadHistory();
}

function resetFilters() {
    document.getElementById("filterStatus").value = "";
    document.getElementById("filterDefectType").value = "";
    document.getElementById("filterCameraSource").value = "";
    document.getElementById("filterStartDate").value = "";
    document.getElementById("filterEndDate").value = "";
    reportState.status = "";
    reportState.defectType = "";
    reportState.cameraSource = "";
    reportState.startDate = "";
    reportState.endDate = "";
    reportState.page = 1;
    loadHistory();
    loadCameraSourceFilter();
}

// ── Camera Analytics ──────────────────────────────────────────────────
async function loadCameraAnalytics() {
    try {
        const res = await fetch(`${REPORTS_API}/camera-analytics`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        renderCameraAnalytics(data.cameras || []);
    } catch (e) {
        document.getElementById("cameraAnalyticsContent").innerHTML =
            `<div style="color:var(--neon-red);font-size:12px;text-align:center;">Failed to load camera analytics</div>`;
    }
}

function renderCameraAnalytics(cameras) {
    const container = document.getElementById("cameraAnalyticsContent");
    if (!cameras.length) {
        container.innerHTML = `<div style="color:var(--text-muted);font-size:12px;text-align:center;">No camera data available</div>`;
        return;
    }
    container.innerHTML = `<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px;">` +
        cameras.map(c => {
            const accColor = c.accuracy >= 90 ? "var(--neon-green)" : c.accuracy >= 70 ? "var(--neon-amber)" : "var(--neon-red)";
            return `<div style="background:var(--surface-2);border:1px solid var(--border);border-radius:10px;padding:16px;">
                <div style="font-size:13px;font-weight:600;margin-bottom:10px;display:flex;align-items:center;gap:8px;">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--neon-cyan)" stroke-width="1.5"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>
                    ${c.camera}
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;font-size:12px;">
                    <div><span style="color:var(--text-muted);display:block;font-size:10px;text-transform:uppercase;">Total</span><span style="font-weight:700;font-family:var(--font-mono);">${c.total_bottles}</span></div>
                    <div><span style="color:var(--text-muted);display:block;font-size:10px;text-transform:uppercase;">Passed</span><span style="font-weight:700;font-family:var(--font-mono);color:var(--neon-green);">${c.passed_bottles}</span></div>
                    <div><span style="color:var(--text-muted);display:block;font-size:10px;text-transform:uppercase;">Rejected</span><span style="font-weight:700;font-family:var(--font-mono);color:var(--neon-red);">${c.rejected_bottles}</span></div>
                    <div><span style="color:var(--text-muted);display:block;font-size:10px;text-transform:uppercase;">Accuracy</span><span style="font-weight:700;font-family:var(--font-mono);color:${accColor};">${c.accuracy}%</span></div>
                </div>
            </div>`;
        }).join("") + `</div>`;
}

// ── Analytics Charts ──────────────────────────────────────────────────
let dailyChart = null;
let trendChart = null;

async function loadAnalyticsCharts() {
    try {
        const res = await fetch(`${REPORTS_API}/analytics`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        renderDailyChart(data.daily || []);
        renderTrendChart(data.daily || []);
    } catch (e) {
        console.error("Failed to load analytics charts:", e);
    }
}

function renderDailyChart(dailyData) {
    const ctx = document.getElementById("dailyChart");
    if (!ctx) return;
    if (dailyChart) dailyChart.destroy();

    const labels = dailyData.slice(-14).map(d => d.date.slice(5));
    const passData = dailyData.slice(-14).map(d => d.passed);
    const failData = dailyData.slice(-14).map(d => d.defective);

    const isDark = document.documentElement.getAttribute('data-theme') !== 'light';
    const gridColor = isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.06)';
    const textColor = isDark ? '#a1a1aa' : '#475569';

    dailyChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [
                {
                    label: 'Passed',
                    data: passData,
                    backgroundColor: 'rgba(16,185,129,0.7)',
                    borderColor: '#10b981',
                    borderWidth: 1,
                    borderRadius: 4,
                },
                {
                    label: 'Defective',
                    data: failData,
                    backgroundColor: 'rgba(239,68,68,0.7)',
                    borderColor: '#ef4444',
                    borderWidth: 1,
                    borderRadius: 4,
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: textColor, font: { size: 11 } }
                }
            },
            scales: {
                x: {
                    grid: { color: gridColor },
                    ticks: { color: textColor, font: { size: 10 } }
                },
                y: {
                    beginAtZero: true,
                    grid: { color: gridColor },
                    ticks: { color: textColor, font: { size: 10 } }
                }
            }
        }
    });
}

function renderTrendChart(dailyData) {
    const ctx = document.getElementById("trendChart");
    if (!ctx) return;
    if (trendChart) trendChart.destroy();

    const data = dailyData.slice(-30);
    const labels = data.map(d => d.date.slice(5));
    const totals = data.map(d => d.total);

    const isDark = document.documentElement.getAttribute('data-theme') !== 'light';
    const gridColor = isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.06)';
    const textColor = isDark ? '#a1a1aa' : '#475569';

    trendChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [{
                label: 'Daily Inspections',
                data: totals,
                borderColor: '#06b6d4',
                backgroundColor: 'rgba(6,182,212,0.1)',
                fill: true,
                tension: 0.4,
                pointRadius: 3,
                pointBackgroundColor: '#06b6d4',
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: textColor, font: { size: 11 } }
                }
            },
            scales: {
                x: {
                    grid: { color: gridColor },
                    ticks: { color: textColor, font: { size: 10 } }
                },
                y: {
                    beginAtZero: true,
                    grid: { color: gridColor },
                    ticks: { color: textColor, font: { size: 10 } }
                }
            }
        }
    });
}

// ── Toast helper (reuse existing if available) ────────────────────────
function showToast(msg, type) {
    if (typeof window.showToast === 'function') {
        window.showToast(msg, type);
        return;
    }
    const container = document.getElementById("toastContainer");
    if (!container) return;
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<span>${msg}</span><button class="toast-close" onclick="this.parentElement.remove()">&times;</button>`;
    container.appendChild(toast);
    setTimeout(() => { if (toast.parentElement) toast.remove(); }, 4000);
}

// ── Sort indicators in table headers ──────────────────────────────────
function updateSortIndicator(col) {
    document.querySelectorAll(".sortable-th").forEach(th => {
        th.querySelector(".sort-icon").textContent = "";
        if (th.dataset.col === col) {
            th.querySelector(".sort-icon").textContent = reportState.sortOrder === "asc" ? " ▲" : " ▼";
        }
    });
}

// ── Navigate to Reports ──────────────────────────────────────────────
// This is called when the reports nav item is clicked
function openReports() {
    initReports();
}
