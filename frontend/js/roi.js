// roi.js - Region of Interest drawing logic for Page 3

const bgCanvas = document.getElementById('roi-bg-canvas');
const drawCanvas = document.getElementById('roi-draw-canvas');
const drawCtx = drawCanvas?.getContext('2d');
const bgCtx = bgCanvas?.getContext('2d');

let isDrawMode = false;
let isDrawing = false;
let startX, startY, currentX, currentY;
let currentRect = null;
let rois = []; // Array of { name, color, x, y, w, h }

function initROICanvas() {
  if (!drawCanvas || !bgCanvas) return;
  
  // Resize canvases to match container
  const container = drawCanvas.parentElement;
  drawCanvas.width = container.clientWidth;
  drawCanvas.height = container.clientHeight;
  bgCanvas.width = container.clientWidth;
  bgCanvas.height = container.clientHeight;

  // Capture current frame from main video if available
  const mainVideo = document.getElementById('videoEl');
  if (mainVideo && mainVideo.readyState >= 2) {
    bgCtx.drawImage(mainVideo, 0, 0, bgCanvas.width, bgCanvas.height);
  } else {
    // Fill with dark placeholder
    bgCtx.fillStyle = '#121214';
    bgCtx.fillRect(0, 0, bgCanvas.width, bgCanvas.height);
    bgCtx.fillStyle = '#3f3f46';
    bgCtx.font = '14px Inter';
    bgCtx.textAlign = 'center';
    bgCtx.fillText('No video feed available. Start camera first to draw accurate ROIs.', bgCanvas.width/2, bgCanvas.height/2);
  }
}

function toggleDrawMode() {
  isDrawMode = !isDrawMode;
  const btn = document.getElementById('btnDraw');
  if (isDrawMode) {
    btn.textContent = 'Cancel Drawing';
    btn.classList.replace('btn-outline', 'btn-danger');
    initROICanvas(); // refresh background snapshot
    drawCanvas.style.cursor = 'crosshair';
  } else {
    btn.textContent = 'Start Drawing ROI';
    btn.classList.replace('btn-danger', 'btn-outline');
    currentRect = null;
    drawCanvas.style.cursor = 'default';
    redrawROIs();
  }
}

function saveROI() {
  if (!currentRect) {
    alert("Please draw an ROI first!");
    return;
  }
  const name = document.getElementById('roiName').value || `Region ${rois.length + 1}`;
  const color = document.getElementById('roiColor').value;
  
  rois.push({
    id: Date.now(),
    name,
    color,
    x: currentRect.x / drawCanvas.width,
    y: currentRect.y / drawCanvas.height,
    w: currentRect.w / drawCanvas.width,
    h: currentRect.h / drawCanvas.height
  });
  
  currentRect = null;
  document.getElementById('roiName').value = '';
  toggleDrawMode();
  renderROIList();
  
  const btn = document.getElementById('btnSaveROI');
  if (btn) {
    const oldText = btn.textContent;
    btn.textContent = "Region Saved!";
    btn.style.background = "var(--neon-green)";
    btn.style.color = "#000";
    setTimeout(() => {
      btn.textContent = oldText;
      btn.style.background = "";
      btn.style.color = "";
    }, 2000);
  }
}

function deleteROI(id) {
  rois = rois.filter(r => r.id !== id);
  renderROIList();
  redrawROIs();
}

function editROI(id) {
  const roi = rois.find(r => r.id === id);
  if (!roi) return;
  
  document.getElementById('roiName').value = roi.name;
  
  const colorSelect = document.getElementById('roiColor');
  if (colorSelect) {
    colorSelect.value = roi.color;
  }
  
  currentRect = {
    x: roi.x * drawCanvas.width,
    y: roi.y * drawCanvas.height,
    w: roi.w * drawCanvas.width,
    h: roi.h * drawCanvas.height
  };
  
  rois = rois.filter(r => r.id !== id);
  renderROIList();
  
  if (!isDrawMode) {
    toggleDrawMode();
  } else {
    redrawROIs();
  }
}

function renderROIList() {
  const list = document.getElementById('roiList');
  
  if (rois.length === 0) {
    list.innerHTML = `<div style="font-size:11px; color:var(--text-muted); text-align:center">No ROIs configured</div>`;
  } else {
    list.innerHTML = rois.map(r => `
      <div class="roi-item" style="border-left: 3px solid ${r.color}">
        <span>${r.name}</span>
        <div>
          <button class="btn btn-outline" style="padding:4px 8px; font-size:10px; margin-right: 4px;" onclick="editROI(${r.id})">Edit</button>
          <button class="btn btn-danger" style="padding:4px 8px; font-size:10px" onclick="deleteROI(${r.id})">Del</button>
        </div>
      </div>
    `).join('');
  }
  
  const norm_rois = rois.map(r => ({
    x: r.x, y: r.y, w: r.w, h: r.h, name: r.name, color: r.color
  }));
  
  window.activeROIs = norm_rois;
  
  fetch('http://localhost:8000/set-roi', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rois: norm_rois })
  }).catch(console.error);
}

function syncROIs(fetched_rois) {
  rois = fetched_rois.map((r, i) => ({
    id: Date.now() + i,
    x: r.x, y: r.y, w: r.w, h: r.h,
    name: r.name, color: r.color || "#06b6d4"
  }));
  renderROIList();
}

function redrawROIs() {
  if (!drawCtx) return;
  drawCtx.clearRect(0, 0, drawCanvas.width, drawCanvas.height);
  
  // Draw saved ROIs (converted to absolute for drawing)
  rois.forEach(r => {
    const rx = r.x * drawCanvas.width;
    const ry = r.y * drawCanvas.height;
    const rw = r.w * drawCanvas.width;
    const rh = r.h * drawCanvas.height;
    
    drawCtx.strokeStyle = r.color;
    drawCtx.lineWidth = 2;
    drawCtx.strokeRect(rx, ry, rw, rh);
    
    // No fill, just outline as requested, but keep name
    drawCtx.fillStyle = r.color;
    drawCtx.font = '12px Inter';
    drawCtx.fillText(r.name, rx + 4, ry + 14);
  });
  
  // Draw current rect if drawing
  if (currentRect) {
    const color = document.getElementById('roiColor').value;
    drawCtx.strokeStyle = color;
    drawCtx.lineWidth = 2;
    drawCtx.setLineDash([5, 5]);
    drawCtx.strokeRect(currentRect.x, currentRect.y, currentRect.w, currentRect.h);
    drawCtx.setLineDash([]);
  }
}

// Event Listeners for drawing
if (drawCanvas) {
  drawCanvas.addEventListener('mousedown', (e) => {
    if (!isDrawMode) return;
    isDrawing = true;
    const rect = drawCanvas.getBoundingClientRect();
    startX = e.clientX - rect.left;
    startY = e.clientY - rect.top;
  });

  drawCanvas.addEventListener('mousemove', (e) => {
    if (!isDrawing || !isDrawMode) return;
    const rect = drawCanvas.getBoundingClientRect();
    currentX = e.clientX - rect.left;
    currentY = e.clientY - rect.top;
    
    currentRect = {
      x: Math.min(startX, currentX),
      y: Math.min(startY, currentY),
      w: Math.abs(currentX - startX),
      h: Math.abs(currentY - startY)
    };
    
    redrawROIs();
  });

  drawCanvas.addEventListener('mouseup', () => {
    isDrawing = false;
  });

  drawCanvas.addEventListener('mouseleave', () => {
    isDrawing = false;
  });
  
  // Handle window resize
  window.addEventListener('resize', () => {
    if (document.getElementById('page-roi').classList.contains('active')) {
      initROICanvas();
      redrawROIs();
    }
  });
}
