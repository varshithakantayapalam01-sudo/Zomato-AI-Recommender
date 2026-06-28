/**
 * SavorAI — Frontend Application Logic
 *
 * Communicates with the Phase 4 Backend API to:
 *   - Populate location & cuisine dropdowns on load
 *   - Submit preference form and render recommendations
 *   - Handle error, empty, fallback, and loading states
 *   - Display cuisine-matched food images on cards
 */

(function () {
  "use strict";

  // In production (Vercel), config.js sets window.RAILWAY_API_URL to the Railway backend URL.
  // In local dev, config.js sets it to "" so we fall back to the relative /api/v1 path.
  let _railwayUrl = (window.RAILWAY_API_URL || "").trim();
  // Guard: auto-prepend https:// if a host was given without a protocol
  if (_railwayUrl && !_railwayUrl.startsWith("http://") && !_railwayUrl.startsWith("https://")) {
    _railwayUrl = "https://" + _railwayUrl;
  }
  const API_BASE = _railwayUrl + "/api/v1";

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

  // ── Cuisine → Food Image Mapping ────────────────────────
  // High-quality Unsplash images mapped to cuisine keywords.
  // Uses specific photo IDs for consistency and reliability.
  const CUISINE_IMAGES = {
    "biryani":       "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=600&h=340&fit=crop&q=80",
    "north indian":  "https://images.unsplash.com/photo-1585937421612-70a008356fbe?w=600&h=340&fit=crop&q=80",
    "south indian":  "https://images.unsplash.com/photo-1630383249896-424e482df921?w=600&h=340&fit=crop&q=80",
    "chinese":       "https://images.unsplash.com/photo-1525755662778-989d0524087e?w=600&h=340&fit=crop&q=80",
    "italian":       "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=600&h=340&fit=crop&q=80",
    "pizza":         "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=600&h=340&fit=crop&q=80",
    "pasta":         "https://images.unsplash.com/photo-1621996346565-e3dbc646d9a9?w=600&h=340&fit=crop&q=80",
    "continental":   "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=600&h=340&fit=crop&q=80",
    "mughlai":       "https://images.unsplash.com/photo-1599487488170-d11ec9c172f0?w=600&h=340&fit=crop&q=80",
    "fast food":     "https://images.unsplash.com/photo-1561758033-d89a9ad46330?w=600&h=340&fit=crop&q=80",
    "burger":        "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=600&h=340&fit=crop&q=80",
    "cafe":          "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=600&h=340&fit=crop&q=80",
    "bakery":        "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=600&h=340&fit=crop&q=80",
    "desserts":      "https://images.unsplash.com/photo-1551024506-0bccd828d307?w=600&h=340&fit=crop&q=80",
    "ice cream":     "https://images.unsplash.com/photo-1501443762994-82bd5dace89a?w=600&h=340&fit=crop&q=80",
    "thai":          "https://images.unsplash.com/photo-1562565652-a0d8f0c59eb4?w=600&h=340&fit=crop&q=80",
    "japanese":      "https://images.unsplash.com/photo-1580822184713-fc5400e7fe10?w=600&h=340&fit=crop&q=80",
    "sushi":         "https://images.unsplash.com/photo-1579871494447-9811cf80d66c?w=600&h=340&fit=crop&q=80",
    "korean":        "https://images.unsplash.com/photo-1590301157890-4810ed352733?w=600&h=340&fit=crop&q=80",
    "mexican":       "https://images.unsplash.com/photo-1565299585323-38d6b0865b47?w=600&h=340&fit=crop&q=80",
    "mediterranean": "https://images.unsplash.com/photo-1544025162-d76694265947?w=600&h=340&fit=crop&q=80",
    "kebab":         "https://images.unsplash.com/photo-1603360946369-dc9bb6258143?w=600&h=340&fit=crop&q=80",
    "seafood":       "https://images.unsplash.com/photo-1615141982883-c7ad0e69fd62?w=600&h=340&fit=crop&q=80",
    "street food":   "https://images.unsplash.com/photo-1601050690597-df0568f70950?w=600&h=340&fit=crop&q=80",
    "tandoori":      "https://images.unsplash.com/photo-1599487488170-d11ec9c172f0?w=600&h=340&fit=crop&q=80",
    "rolls":         "https://images.unsplash.com/photo-1626700051175-6818013e1d4f?w=600&h=340&fit=crop&q=80",
    "beverages":     "https://images.unsplash.com/photo-1544145945-f90425340c7e?w=600&h=340&fit=crop&q=80",
    "juice":         "https://images.unsplash.com/photo-1622597467836-f3285f2131b8?w=600&h=340&fit=crop&q=80",
    "american":      "https://images.unsplash.com/photo-1550547660-d9450f859349?w=600&h=340&fit=crop&q=80",
    "arabian":       "https://images.unsplash.com/photo-1541518763669-27fef04b14ea?w=600&h=340&fit=crop&q=80",
    "wraps":         "https://images.unsplash.com/photo-1626700051175-6818013e1d4f?w=600&h=340&fit=crop&q=80",
    "sandwich":      "https://images.unsplash.com/photo-1528735602780-2552fd46c7af?w=600&h=340&fit=crop&q=80",
    "momos":         "https://images.unsplash.com/photo-1534422298391-e4f8c172dddb?w=600&h=340&fit=crop&q=80",
    "healthy food":  "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=600&h=340&fit=crop&q=80",
    "salad":         "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=600&h=340&fit=crop&q=80",
    "steak":         "https://images.unsplash.com/photo-1544025162-d76694265947?w=600&h=340&fit=crop&q=80",
    "grill":         "https://images.unsplash.com/photo-1555939594-58d7cb561ad1?w=600&h=340&fit=crop&q=80",
    "bbq":           "https://images.unsplash.com/photo-1555939594-58d7cb561ad1?w=600&h=340&fit=crop&q=80",
    "dosa":          "https://images.unsplash.com/photo-1630383249896-424e482df921?w=600&h=340&fit=crop&q=80",
    "idli":          "https://images.unsplash.com/photo-1589301760014-d929f3979dbc?w=600&h=340&fit=crop&q=80",
    "chettinad":     "https://images.unsplash.com/photo-1585937421612-70a008356fbe?w=600&h=340&fit=crop&q=80",
    "kerala":        "https://images.unsplash.com/photo-1585937421612-70a008356fbe?w=600&h=340&fit=crop&q=80",
    "andhra":        "https://images.unsplash.com/photo-1585937421612-70a008356fbe?w=600&h=340&fit=crop&q=80",
    "finger food":   "https://images.unsplash.com/photo-1601050690597-df0568f70950?w=600&h=340&fit=crop&q=80",
    "pan asian":     "https://images.unsplash.com/photo-1580822184713-fc5400e7fe10?w=600&h=340&fit=crop&q=80",
    "asian":         "https://images.unsplash.com/photo-1580822184713-fc5400e7fe10?w=600&h=340&fit=crop&q=80",
    "tibetan":       "https://images.unsplash.com/photo-1534422298391-e4f8c172dddb?w=600&h=340&fit=crop&q=80",
    "european":      "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=600&h=340&fit=crop&q=80",
    "french":        "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=600&h=340&fit=crop&q=80",
  };

  // Default food image when no cuisine match
  const DEFAULT_FOOD_IMAGE = "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=600&h=340&fit=crop&q=80";

  /**
   * Get the best food image URL for a given cuisine string.
   * Tries each cuisine keyword against our map, returns the first match.
   */
  function getFoodImage(cuisineStr) {
    if (!cuisineStr) return DEFAULT_FOOD_IMAGE;
    const cuisines = cuisineStr.split(",").map(c => c.trim().toLowerCase());
    for (const c of cuisines) {
      // Direct match
      if (CUISINE_IMAGES[c]) return CUISINE_IMAGES[c];
      // Partial match (e.g., "north indian" inside "North Indian, Mughlai")
      for (const [key, url] of Object.entries(CUISINE_IMAGES)) {
        if (c.includes(key) || key.includes(c)) return url;
      }
    }
    return DEFAULT_FOOD_IMAGE;
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

  /**
   * Fetch a URL with automatic retries.
   * On 503 (backend still starting / dataset loading), we wait and retry.
   * On other errors we also retry up to maxRetries times.
   *
   * @param {string} url
   * @param {number} maxRetries   - total attempts (default 10 ≈ ~30 s total)
   * @param {number} baseDelayMs  - initial wait before first retry
   * @returns {Promise<Response>}
   */
  async function fetchWithRetry(url, maxRetries = 10, baseDelayMs = 2000) {
    for (let attempt = 0; attempt < maxRetries; attempt++) {
      try {
        const resp = await fetch(url);
        // 503 means the backend is still loading the dataset — wait and retry
        if (resp.status === 503) {
          if (attempt < maxRetries - 1) {
            const delay = baseDelayMs * Math.pow(1.4, attempt); // gentle exponential back-off
            await new Promise((r) => setTimeout(r, delay));
            continue;
          }
          // exhausted retries — surface the 503
          return resp;
        }
        return resp;
      } catch (networkErr) {
        // Network error (CORS, server down, etc.)
        if (attempt < maxRetries - 1) {
          const delay = baseDelayMs * Math.pow(1.4, attempt);
          await new Promise((r) => setTimeout(r, delay));
        } else {
          throw networkErr;
        }
      }
    }
  }

  async function loadLocations() {
    locationSelect.innerHTML = '<option value="" disabled selected>Loading locations…</option>';
    try {
      const resp = await fetchWithRetry(`${API_BASE}/locations`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
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
      locationSelect.innerHTML = '<option value="" disabled selected>Error loading locations — refresh to retry</option>';
    }
  }

  async function loadCuisines() {
    try {
      const resp = await fetchWithRetry(`${API_BASE}/cuisines`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
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

      // Get cuisine-matched food image
      const foodImageUrl = getFoodImage(rec.cuisine);

      card.innerHTML = `
        <div class="card-image-wrapper">
          <img
            class="card-food-image"
            src="${foodImageUrl}"
            alt="${escapeHtml(cuisines[0] || 'Food')} dish"
            loading="lazy"
            onerror="this.src='${DEFAULT_FOOD_IMAGE}'"
          />
          <div class="card-image-overlay"></div>
          <div class="card-rank-overlay">
            <span class="rank-badge ${rec.rank === 1 ? 'rank-1' : ''}">${rec.rank}</span>
          </div>
          <div class="card-rating-overlay">
            <span class="card-rating-pill">
              ${rec.rating.toFixed(1)}
              <span class="material-symbols-outlined filled-icon" style="font-size:14px;">star</span>
            </span>
          </div>
        </div>
        <div class="card-body">
          <div class="card-header">
            <div class="card-left">
              <h3 class="restaurant-name">${escapeHtml(rec.name)}</h3>
              <div class="cuisine-tags">${tagsHtml}</div>
            </div>
            <div class="card-right">
              <span class="card-cost">${formatCurrency(rec.estimated_cost)} for two</span>
            </div>
          </div>
          <div class="card-explanation">
            <span class="material-symbols-outlined explanation-quote">format_quote</span>
            <p class="explanation-text">${escapeHtml(rec.explanation)}</p>
          </div>
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
