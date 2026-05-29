(function() {
  const API_URL = "http://localhost:8000/settings";
  let currentSettings = {};

  const $ = id => document.getElementById(id);

  async function init() {
    await loadSettings();
    bindEvents();
  }

  async function loadSettings() {
    const loadingEl = $("settingsLoading");
    const contentEl = $("settingsContent");
    if (loadingEl) loadingEl.style.display = "flex";
    if (contentEl) contentEl.style.display = "none";

    try {
      const res = await fetch(API_URL);
      const data = await res.json();
      if (data.settings) {
        currentSettings = data.settings;
        populateUI();
      }
    } catch (e) {
      showToast("Failed to load settings. Backend may be offline.", "error");
    } finally {
      if (loadingEl) loadingEl.style.display = "none";
      if (contentEl) contentEl.style.display = "block";
    }
  }

  function populateUI() {
    Object.entries(currentSettings).forEach(([key, value]) => {
      const el = $(key);
      if (!el) return;
      if (el.type === "checkbox") {
        el.checked = Boolean(value);
      } else if (el.type === "range") {
        el.value = value;
        const display = $(key + "Value");
        if (display) display.textContent = value + "%";
      } else {
        el.value = value;
      }
    });
    if (window.overlaySettings) {
      Object.assign(window.overlaySettings, currentSettings);
    }
  }

  async function saveSetting(key, value) {
    try {
      const res = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ settings: { [key]: value } })
      });
      const data = await res.json();
      if (data.status === "ok") {
        currentSettings = data.settings;
        showToast("Setting saved", "success");
        applySettingLive(key, value);
      }
    } catch (e) {
      showToast("Failed to save setting", "error");
    }
  }

  function applySettingLive(key, value) {
    if (window.overlaySettings) {
      window.overlaySettings[key] = value;
    }
    if (key === "default_camera_source") {
      localStorage.setItem("defaultSource", value);
    }
    if (key === "camera_resolution") {
      localStorage.setItem("cameraResolution", value);
    }
  }

  function bindEvents() {
    document.querySelectorAll("[data-setting]").forEach(el => {
      const key = el.dataset.setting;
      const handler = () => {
        let value = el.value;
        if (el.type === "checkbox") value = el.checked;
        if (el.type === "number" || el.type === "range") value = parseFloat(el.value);
        saveSetting(key, value);
      };
      el.addEventListener("change", handler);
      if (el.type === "range") {
        el.addEventListener("input", () => {
          const display = $(key + "Value");
          if (display) display.textContent = el.value + "%";
        });
      }
    });
  }

  window.clearDetectionHistory = function() {
    const modal = document.getElementById("clearHistoryModal");
    if (modal) modal.style.display = "flex";
  };

  window.confirmClearHistory = async function() {
    const btn = document.querySelector("#clearHistoryModal .btn-danger");
    if (btn) {
      btn.disabled = true;
      btn.textContent = "Clearing...";
    }
    try {
      // Call backend to clear all detection history and reports
      const res = await fetch("http://localhost:8000/reports/clear-history", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}"
      });
      const data = await res.json();
      if (data.status === "ok") {
        // Clear frontend localStorage
        localStorage.removeItem("detectionHistory");

        // Reset live page counters
        const ids = ["mBottles", "mPass", "mFail"];
        ids.forEach(id => {
          const el = document.getElementById(id);
          if (el) el.textContent = "0";
        });

        // Refresh reports page data if initialized
        if (typeof initReports === "function") {
          initReports();
        }

        showToast("All detection history and reports cleared", "success");
      } else {
        showToast("Failed to clear history", "error");
      }
    } catch (e) {
      showToast("Failed to clear history: " + e.message, "error");
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.textContent = "Clear History";
      }
      window.cancelClearHistory();
    }
  };

  window.cancelClearHistory = function() {
    const modal = document.getElementById("clearHistoryModal");
    if (modal) modal.style.display = "none";
  };

  window.resetAllSettings = function() {
    const modal = $("resetModal");
    if (modal) modal.style.display = "flex";
  };

  window.confirmReset = async function() {
    try {
      const res = await fetch(API_URL + "/reset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}"
      });
      const data = await res.json();
      if (data.status === "ok") {
        currentSettings = data.settings;
        populateUI();
        showToast("All settings reset to defaults", "success");
      }
    } catch (e) {
      showToast("Failed to reset settings", "error");
    }
    window.cancelReset();
  };

  window.cancelReset = function() {
    const modal = $("resetModal");
    if (modal) modal.style.display = "none";
  };

  function showToast(message, type) {
    const container = $("toastContainer");
    if (!container) return;
    const toast = document.createElement("div");
    toast.className = "toast toast-" + (type || "info");
    toast.innerHTML = '<span>' + message + '</span><button class="toast-close" onclick="this.parentElement.remove()">&times;</button>';
    container.appendChild(toast);
    setTimeout(() => {
      if (toast.parentElement) toast.remove();
    }, 4000);
  }

  window.showToast = showToast;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
