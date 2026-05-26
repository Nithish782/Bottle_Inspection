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
    ...currentRect
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

function renderROIList() {
  const list = document.getElementById('roiList');
  if (rois.length === 0) {
    list.innerHTML = `<div style="font-size:11px; color:var(--text-muted); text-align:center">No ROIs configured</div>`;
    return;
  }
  list.innerHTML = rois.map(r => `
    <div class="roi-item" style="border-left: 3px solid ${r.color}">
      <span>${r.name}</span>
      <button class="btn btn-danger" style="padding:4px 8px; font-size:10px" onclick="deleteROI(${r.id})">Del</button>
    </div>
  `).join('');
  
  const norm_rois = rois.map(r => ({
    x: r.x / drawCanvas.width,
    y: r.y / drawCanvas.height,
    w: r.w / drawCanvas.width,
    h: r.h / drawCanvas.height,
    name: r.name,
    color: r.color
  }));
  
  // Update globally for the live feed overlay to pick up immediately
  window.activeROIs = norm_rois;
  
  fetch('http://localhost:8000/set-roi', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rois: norm_rois })
  }).catch(console.error);
}

function redrawROIs() {
  if (!drawCtx) return;
  drawCtx.clearRect(0, 0, drawCanvas.width, drawCanvas.height);
  
  // Draw saved ROIs
  rois.forEach(r => {
    drawCtx.strokeStyle = r.color;
    drawCtx.lineWidth = 2;
    drawCtx.strokeRect(r.x, r.y, r.w, r.h);
    drawCtx.fillStyle = r.color + '33'; // 20% opacity
    drawCtx.fillRect(r.x, r.y, r.w, r.h);
    
    drawCtx.fillStyle = r.color;
    drawCtx.font = '12px Inter';
    drawCtx.fillText(r.name, r.x + 4, r.y + 14);
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
