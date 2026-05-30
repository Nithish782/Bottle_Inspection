// overlay.js — Canvas bounding box + label drawing

const Overlay = (() => {
  const COLOR = {
    pass: "#00e676",
    warn: "#ffab00",
    fail: "#ff5252",
  };

  function getColor(bottle) {
    if (bottle.pass) return COLOR.pass;
    const fill  = bottle.fill  || "";
    const label = bottle.label || "";
    const isWarn = fill === "under_fill" || label === "label_torn";
    return isWarn ? COLOR.warn : COLOR.fail;
  }

  function draw(canvas, bottles, videoW, videoH) {
    const ctx = canvas.getContext("2d");
    const os = window.overlaySettings || {};
    const showBoxes = os.show_bounding_boxes !== false;
    const showLabels = os.show_labels !== false;
    const showConf = os.show_confidence_score !== false;
    const opacity = (os.overlay_opacity ?? 100) / 100;

    ctx.globalAlpha = opacity;

    const scaleX = canvas.width  / videoW;
    const scaleY = canvas.height / videoH;
    
    // Draw active ROIs first (underneath bottles)
    if (window.activeROIs && window.activeROIs.length) {
      window.activeROIs.forEach(r => {
        const rx = r.x * canvas.width;
        const ry = r.y * canvas.height;
        const rw = r.w * canvas.width;
        const rh = r.h * canvas.height;
        
        ctx.strokeStyle = r.color || "#06b6d4";
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 5]);
        ctx.strokeRect(rx, ry, rw, rh);
        ctx.setLineDash([]);
        
        ctx.fillStyle = r.color || "#06b6d4";
        ctx.font = '12px Inter';
        ctx.shadowBlur = 0;
        ctx.fillText(r.name || "ROI", rx + 4, ry + 14);
      });
    }

    if (!bottles || !bottles.length) { ctx.globalAlpha = 1; return; }

    bottles.forEach(b => {
      const [x1, y1, x2, y2] = b.box;
      const sx = x1 * scaleX, sy = y1 * scaleY;
      const sw = (x2 - x1) * scaleX, sh = (y2 - y1) * scaleY;
      const col = getColor(b);

      if (showBoxes) {
        // Glow
        ctx.shadowColor = col;
        ctx.shadowBlur  = 10;

        // Main rect
        ctx.strokeStyle = col;
        ctx.lineWidth   = 2;
        ctx.strokeRect(sx, sy, sw, sh);
        ctx.shadowBlur  = 0;

        // Corner brackets
        _corners(ctx, sx, sy, sw, sh, col);

        // Fill level dashed line
        _fillLine(ctx, b, sx, sy, sw, sh);
      }

      if (showLabels) {
        _label(ctx, b, sx, sy, col, showConf);
      }

      // Label bounding box (sub-label box)
      if (b.label_box && (showBoxes || showLabels)) {
        const [lx1, ly1, lx2, ly2] = b.label_box;
        const lsx = lx1 * scaleX, lsy = ly1 * scaleY;
        const lsw = (lx2 - lx1) * scaleX, lsh = (ly2 - ly1) * scaleY;
        
        ctx.strokeStyle = (b.label === "label_proper") ? COLOR.pass : ((b.label === "label_torn") ? COLOR.warn : COLOR.fail);
        ctx.lineWidth = 2;
        ctx.setLineDash([4, 4]);
        ctx.strokeRect(lsx, lsy, lsw, lsh);
        ctx.setLineDash([]);
        
        ctx.fillStyle = ctx.strokeStyle;
        ctx.font = "bold 10px Inter";
        ctx.shadowBlur = 0;
        ctx.fillText(b.label.replace(/_/g, " "), lsx + 2, lsy - 4);
      }
    });

    ctx.globalAlpha = 1;
  }

  function _corners(ctx, x, y, w, h, col) {
    const cs = Math.min(16, w * 0.15, h * 0.1);
    ctx.strokeStyle = col;
    ctx.lineWidth   = 3;
    const pts = [[x,y,1,1],[x+w,y,-1,1],[x,y+h,1,-1],[x+w,y+h,-1,-1]];
    pts.forEach(([cx, cy, dx, dy]) => {
      ctx.beginPath();
      ctx.moveTo(cx + dx * cs, cy);
      ctx.lineTo(cx, cy);
      ctx.lineTo(cx, cy + dy * cs);
      ctx.stroke();
    });
  }

  function _label(ctx, b, sx, sy, col, showConf) {
    const status = b.pass ? "PASS" : "FAIL";
    const fill   = (b.fill  || "").replace(/_/g, " ");
    const label  = (b.label || "").replace(/_/g, " ");
    let text = `#${b.id || "?"} ${status} | ${fill} | ${label}`;
    if (showConf) {
      const conf = Math.round((b.overall_conf || 0) * 100);
      text += ` | ${conf}%`;
    }

    ctx.font = "bold 12px Inter, sans-serif";
    const tw = ctx.measureText(text).width;

    ctx.fillStyle = "rgba(0,0,0,0.75)";
    ctx.fillRect(sx, sy - 24, tw + 18, 22);

    ctx.fillStyle = col;
    ctx.fillText(text, sx + 9, sy - 7);
  }

  function _fillLine(ctx, b, sx, sy, sw, sh) {
    const fill = b.fill || "";
    let ratio = 0.25;
    let lineCol = "#448aff";
    if (fill === "under_fill")  { ratio = 0.65; lineCol = "#ffab00"; }
    if (fill === "over_fill")   { ratio = 0.05; lineCol = "#ff5252"; }

    const fy = sy + sh * ratio;
    ctx.setLineDash([5, 4]);
    ctx.strokeStyle = lineCol;
    ctx.lineWidth   = 1.5;
    ctx.shadowBlur  = 0;
    ctx.beginPath();
    ctx.moveTo(sx + 6, fy);
    ctx.lineTo(sx + sw - 6, fy);
    ctx.stroke();
    ctx.setLineDash([]);
  }

  return { draw };
})();