// stats.js — Metrics, FPS tracking, charts, log panel

const Stats = (() => {
  let fpsTimestamps = [];
  let latencies     = [];
  let throughput    = Array(20).fill(0);
  let confHistory   = [];
  let defects = { fill_under:0, fill_over:0, label_torn:0, label_missing:0 };

  // ── FPS ─────────────────────────────────────────────────────────────
  function tickFps() {
    const now = performance.now();
    fpsTimestamps.push(now);
    while (fpsTimestamps[0] < now - 1000) fpsTimestamps.shift();
    return fpsTimestamps.length;
  }

  function pushLatency(ms) {
    latencies.push(ms);
    if (latencies.length > 100) latencies.shift();
  }

  function avgLatency() {
    if (!latencies.length) return 0;
    return latencies.reduce((a,b)=>a+b,0) / latencies.length;
  }

  // ── Bottle results ───────────────────────────────────────────────────
  function processBottles(bottles) {
    throughput.push(bottles.length);
    if (throughput.length > 20) throughput.shift();

    bottles.forEach(b => {
      if (b.overall_conf) { confHistory.push(b.overall_conf); }
      if (confHistory.length > 200) confHistory.shift();
      if (!b.pass) {
        if (b.fill  === "fill_under")    defects.fill_under++;
        if (b.fill  === "fill_over")     defects.fill_over++;
        if (b.label === "label_torn")    defects.label_torn++;
        if (b.label === "label_missing") defects.label_missing++;
      }
    });
  }

  function avgConf() {
    if (!confHistory.length) return null;
    return confHistory.reduce((a,b)=>a+b,0) / confHistory.length;
  }

  // ── Throughput mini chart ────────────────────────────────────────────
  function renderChart(el) {
    const max = Math.max(...throughput, 1);
    el.innerHTML = throughput.map((v, i) => {
      const pct = Math.round(v / max * 100) || 4;
      const age = throughput.length - 1 - i;
      const op  = (0.25 + 0.75 * (1 - age / throughput.length)).toFixed(2);
      return `<div style="flex:1;height:${pct}%;background:var(--blue,#448aff);
              opacity:${op};border-radius:3px 3px 0 0;min-height:3px"></div>`;
    }).join("");
  }

  // ── Defect breakdown ─────────────────────────────────────────────────
  function renderDefects(el) {
    const items = [
      { key:"fill_under",    label:"Underfill",     col:"var(--amber,#ffab00)" },
      { key:"fill_over",     label:"Overfill",      col:"var(--red,#ff5252)"   },
      { key:"label_torn",    label:"Torn Label",    col:"#ff7043"              },
      { key:"label_missing", label:"Missing Label", col:"var(--red,#ff5252)"   },
    ];
    const total = Object.values(defects).reduce((a,b)=>a+b,0) || 1;
    el.innerHTML = items.map(it => {
      const pct = Math.round(defects[it.key] / total * 100);
      return `<div style="display:flex;align-items:center;gap:8px;font-size:12px;margin-bottom:5px">
        <span style="color:var(--text3,#555d78);min-width:90px">${it.label}</span>
        <div style="flex:1;height:5px;background:var(--surface3,#242840);border-radius:3px;overflow:hidden">
          <div style="height:100%;width:${pct}%;background:${it.col};border-radius:3px;transition:width .3s"></div>
        </div>
        <span style="color:${it.col};min-width:26px;text-align:right;font-weight:600">${defects[it.key]}</span>
      </div>`;
    }).join("");
  }

  // ── Log panel ────────────────────────────────────────────────────────
  const LOG_COLORS = { green:"#00e676", red:"#ff5252", amber:"#ffab00", blue:"#448aff", gray:"#555d78" };

  function log(el, msg, type="blue") {
    const col = LOG_COLORS[type] || LOG_COLORS.blue;
    const t   = new Date().toLocaleTimeString("en-US", { hour12:false });
    const item = document.createElement("div");
    item.style.cssText = "display:flex;align-items:center;gap:8px;padding:6px 8px;" +
      "background:var(--surface2,#1c2030);border-radius:6px;font-size:11px;margin-bottom:4px";
    item.innerHTML = `
      <div style="width:6px;height:6px;border-radius:50%;background:${col};flex-shrink:0"></div>
      <div style="color:var(--text3,#555d78);font-variant-numeric:tabular-nums;min-width:52px">${t}</div>
      <div style="color:var(--text2,#8b91a8);flex:1">${msg}</div>`;
    el.insertBefore(item, el.firstChild);
    while (el.children.length > 60) el.removeChild(el.lastChild);
  }

  function reset() {
    fpsTimestamps = []; latencies = []; confHistory = [];
    throughput = Array(20).fill(0);
    defects = { fill_under:0, fill_over:0, label_torn:0, label_missing:0 };
  }

  return { tickFps, pushLatency, avgLatency, avgConf,
           processBottles, renderChart, renderDefects, log, reset, defects };
})();