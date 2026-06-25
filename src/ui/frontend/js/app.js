/**
 * SavorAI — Frontend Application Logic
 *
 * Communicates with the Phase 4 Backend API to:
 *   - Populate location & cuisine dropdowns on load
 *   - Submit preference form and render recommendations
 *   - Handle error, empty, fallback, and loading states
 */

(function () {
  "use strict";

  // In production (Vercel), config.js sets window.RAILWAY_API_URL to the Railway backend URL.
  // In local dev, config.js sets it to "" so we fall back to the relative /api/v1 path.
  const API_BASE = (window.RAILWAY_API_URL || "") + "/api/v1";

  // ── DOM References ──────────────────────────────────────
  const locationSelect  = document.getElementById("location-select");
  const cuisineSelect   = document.getElementById("cuisine-select");
  const budgetMinSlider = document.getElementById("budget-slider-min");
  const budgetMaxSlider = document.getElementById("budget-slider-max");
  const budgetValue     = document.getElementById("budget-value");
  const budgetTrackFill = document.getElementById("budget-track-fill");
  const ratingSlider    = document.getElementById("rating-slider");
  const ratingValue     = document.getElementById("rating-value");
  const additionalPrefs = document.getElementById("additional-prefs");
  const form            = document.getElementById("recommend-form");
  const submitBtn       = document.getElementById("submit-btn");

  const appliedFilters  = document.getElementById("applied-filters");
  const aiSummary       = document.getElementById("ai-summary");
  const summaryText     = document.getElementById("summary-text");
  const fallbackNotice  = document.getElementById("fallback-notice");
  const loadingSkeleton = document.getElementById("loading-skeleton");
  const resultsGrid     = document.getElementById("results-grid");
  const errorState      = document.getElementById("error-state");
  const errorMessage    = document.getElementById("error-message");
  const errorSuggestions= document.getElementById("error-suggestions");
  const emptyState      = document.getElementById("empty-state");

  // ── Helpers ─────────────────────────────────────────────
  function formatCurrency(n) {
    return "₹" + Number(n).toLocaleString("en-IN");
  }

  function show(el) { el.classList.remove("hidden"); }
  function hide(el) { el.classList.add("hidden"); }

  function hideAllResults() {
    hide(appliedFilters);
    hide(aiSummary);
    hide(fallbackNotice);
    hide(loadingSkeleton);
    hide(resultsGrid);
    hide(errorState);
    hide(emptyState);
  }

  // ── Budget Dual-Range Logic ─────────────────────────────
  function updateBudgetDisplay() {
    let min = parseInt(budgetMinSlider.value, 10);
    let max = parseInt(budgetMaxSlider.value, 10);
    if (min > max) {
      // swap
      const tmp = min;
      min = max;
      max = tmp;
    }
    budgetValue.textContent = `${formatCurrency(min)} – ${formatCurrency(max)}`;
    // Update track fill
    const totalRange = parseInt(budgetMinSlider.max, 10) - parseInt(budgetMinSlider.min, 10);
    const leftPct  = ((Math.min(min, max) - parseInt(budgetMinSlider.min, 10)) / totalRange) * 100;
    const rightPct = ((Math.max(min, max) - parseInt(budgetMinSlider.min, 10)) / totalRange) * 100;
    budgetTrackFill.style.left  = leftPct + "%";
    budgetTrackFill.style.width = (rightPct - leftPct) + "%";
  }

  budgetMinSlider.addEventListener("input", updateBudgetDisplay);
  budgetMaxSlider.addEventListener("input", updateBudgetDisplay);
  updateBudgetDisplay();

  // ── Rating Slider Logic ─────────────────────────────────
  ratingSlider.addEventListener("input", () => {
    ratingValue.textContent = parseFloat(ratingSlider.value).toFixed(1);
  });

  // ── Derive budget tier from range ───────────────────────
  function deriveBudgetTier(minVal, maxVal) {
    // Map the selected range to the backend's budget tier:
    //   low:    max ≤ 500
    //   medium: min ≤ 1500 (general range)
    //   high:   min > 1500
    // We use the midpoint to decide
    const mid = (minVal + maxVal) / 2;
    if (mid <= 500) return "low";
    if (mid <= 1500) return "medium";
    return "high";
  }

  // ── Populate Dropdowns ──────────────────────────────────
  async function loadLocations() {
    try {
      const resp = await fetch(`${API_BASE}/locations`);
      if (!resp.ok) throw new Error("Failed to load locations");
      const data = await resp.json();
      locationSelect.innerHTML = '<option value="" disabled selected>Select location</option>';
      data.locations.forEach((loc) => {
        const opt = document.createElement("option");
        opt.value = loc;
        opt.textContent = loc;
        locationSelect.appendChild(opt);
      });
    } catch (e) {
      console.error("Error loading locations:", e);
      locationSelect.innerHTML = '<option value="" disabled selected>Error loading locations</option>';
    }
  }

  async function loadCuisines() {
    try {
      const resp = await fetch(`${API_BASE}/cuisines`);
      if (!resp.ok) throw new Error("Failed to load cuisines");
      const data = await resp.json();
      cuisineSelect.innerHTML = '<option value="">Any cuisine</option>';
      data.cuisines.forEach((c) => {
        const opt = document.createElement("option");
        opt.value = c;
        opt.textContent = c;
        cuisineSelect.appendChild(opt);
      });
    } catch (e) {
      console.error("Error loading cuisines:", e);
    }
  }

  // ── Render Applied Filters ──────────────────────────────
  function renderFilters(prefs) {
    appliedFilters.innerHTML = "";
    const chips = [
      { icon: "location_on", text: prefs.location },
      { icon: "payments", text: prefs.budgetLabel },
    ];
    if (prefs.cuisine) {
      chips.push({ icon: "local_pizza", text: prefs.cuisine });
    }
    if (prefs.min_rating > 0) {
      chips.push({ icon: "star", text: `≥${prefs.min_rating.toFixed(1)}`, filled: true });
    }
    chips.forEach((c) => {
      const span = document.createElement("span");
      span.className = "filter-chip";
      span.innerHTML = `<span class="material-symbols-outlined${c.filled ? ' filled-icon' : ''}" style="font-size:14px;">${c.icon}</span> ${c.text}`;
      appliedFilters.appendChild(span);
    });
    show(appliedFilters);
  }

  // ── Render Result Cards ─────────────────────────────────
  function renderResults(data) {
    resultsGrid.innerHTML = "";

    data.recommendations.forEach((rec, idx) => {
      const card = document.createElement("div");
      card.className = "result-card glass-panel";
      card.style.animationDelay = `${idx * 0.1}s`;

      // Cuisine tags HTML
      const cuisines = rec.cuisine.split(",").map((c) => c.trim()).filter(Boolean);
      const tagsHtml = cuisines
        .map((c) => `<span class="cuisine-tag">${c}</span>`)
        .join("");

      card.innerHTML = `
        <div class="card-glow"></div>
        <div class="card-header">
          <div class="card-left">
            <div class="card-name-row">
              <span class="rank-badge ${rec.rank === 1 ? 'rank-1' : ''}">${rec.rank}</span>
              <h3 class="restaurant-name">${escapeHtml(rec.name)}</h3>
            </div>
            <div class="cuisine-tags">${tagsHtml}</div>
          </div>
          <div class="card-right">
            <div class="card-rating">
              ${rec.rating.toFixed(1)}
              <span class="material-symbols-outlined">star</span>
            </div>
            <span class="card-cost">${formatCurrency(rec.estimated_cost)} for two</span>
          </div>
        </div>
        <div class="card-explanation">
          <span class="material-symbols-outlined explanation-quote">format_quote</span>
          <p class="explanation-text">${escapeHtml(rec.explanation)}</p>
        </div>
      `;
      resultsGrid.appendChild(card);
    });

    show(resultsGrid);
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  // ── Handle Form Submit ──────────────────────────────────
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    hideAllResults();

    const location = locationSelect.value;
    if (!location) {
      showError("Please select a location.");
      return;
    }

    const minBudget = Math.min(parseInt(budgetMinSlider.value), parseInt(budgetMaxSlider.value));
    const maxBudget = Math.max(parseInt(budgetMinSlider.value), parseInt(budgetMaxSlider.value));
    const cuisine = cuisineSelect.value || null;
    const minRating = parseFloat(ratingSlider.value);
    const additional = additionalPrefs.value.trim() || null;

    const prefs = {
      location,
      budgetLabel: `${formatCurrency(minBudget)} – ${formatCurrency(maxBudget)}`,
      cuisine,
      min_rating: minRating,
    };

    renderFilters(prefs);

    // Show loading
    show(loadingSkeleton);
    submitBtn.disabled = true;
    submitBtn.classList.add("loading");

    try {
      const resp = await fetch(`${API_BASE}/recommend`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          location,
          min_budget: minBudget,
          max_budget: maxBudget,
          cuisine,
          min_rating: minRating,
          additional,
        }),
      });

      hide(loadingSkeleton);
      submitBtn.disabled = false;
      submitBtn.classList.remove("loading");

      if (!resp.ok) {
        const errData = await resp.json().catch(() => null);
        if (errData && errData.detail) {
          const detail = errData.detail;
          const msg = detail.details?.[0]?.message || detail.error || "Request failed.";
          const suggestions = detail.details?.[0]?.suggestions || [];
          showError(msg, suggestions);
        } else {
          showError(`Server error (${resp.status}). Please try again.`);
        }
        return;
      }

      const data = await resp.json();

      // No recommendations
      if (!data.recommendations || data.recommendations.length === 0) {
        if (data.summary) {
          summaryText.textContent = `"${data.summary}"`;
          show(aiSummary);
        }
        show(emptyState);
        return;
      }

      // Show summary
      if (data.summary) {
        summaryText.textContent = `"${data.summary}"`;
        show(aiSummary);
      }

      // Show fallback notice
      if (data.metadata && data.metadata.fallback_applied) {
        show(fallbackNotice);
      }

      // Render cards
      renderResults(data);

    } catch (err) {
      hide(loadingSkeleton);
      submitBtn.disabled = false;
      submitBtn.classList.remove("loading");
      showError("Could not connect to the API. Please ensure the server is running.");
      console.error("Fetch error:", err);
    }
  });

  // ── Show Error ──────────────────────────────────────────
  function showError(msg, suggestions) {
    errorMessage.textContent = msg;
    errorSuggestions.innerHTML = "";
    if (suggestions && suggestions.length > 0) {
      suggestions.forEach((s) => {
        const chip = document.createElement("button");
        chip.className = "suggestion-chip";
        chip.textContent = s;
        chip.addEventListener("click", () => {
          // Set the location to the suggestion and re-submit
          locationSelect.value = s;
          form.dispatchEvent(new Event("submit"));
        });
        errorSuggestions.appendChild(chip);
      });
    }
    show(errorState);
  }

  // ── Initialization ──────────────────────────────────────
  async function init() {
    await Promise.all([loadLocations(), loadCuisines()]);
  }

  init();
})();
