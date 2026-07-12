// Global State Variables
let recipes = [];
let driveLinks = {};
let minRatingSelected = 4.0;

// Pantry elements to exclude from shopping lists
const PANTRY_ITEMS = new Set([
  "salt", "kosher salt", "black pepper", "pepper", "olive oil", "extra-virgin olive oil",
  "oil", "butter", "unsalted butter", "garlic", "garlic cloves", "garlic clove",
  "onion", "yellow onion", "white onion", "red onion", "onions", "water"
]);

// Ingredient classification helper rules
const CATEGORY_KEYWORDS = {
  "Produce": ["lemon", "lime", "spinach", "parsley", "basil", "shallot", "potato", "onion", "garlic", "tomato", "chive", "pepper", "oregano", "cilantro", "ginger", "lettuce", "cabbage", "celery", "pea", "corn", "herb", "leaf", "leaves"],
  "Meat & Seafood": ["chicken", "thigh", "breast", "turkey", "beef", "pork", "steak", "bacon", "salami", "sausage", "veal", "lamb", "shrimp", "fish", "salmon", "tuna", "cod", "halibut", "scallop", "crab", "lobster", "seafood"],
  "Dairy & Eggs": ["cream", "parmesan", "cheese", "milk", "butter", "egg", "yogurt", "cheddar", "mozzarella", "ricotta", "feta"],
  "Canned Goods & Grains": ["rice", "grain", "pasta", "noodle", "broth", "stock", "bean", "lentil", "chickpea", "tomato paste", "can", "canned"],
  "Pantry & Spices": ["flour", "sugar", "honey", "tahini", "mayonnaise", "mustard", "vinegar", "soy sauce", "hoisin", "spice", "cinnamon", "cumin", "turmeric", "paprika", "clove", "cardamom", "ginger", "oil", "sauce", "syrup", "breadcrumbs", "panko"]
};

// DOM Elements
const mealsSlider = document.getElementById("meals-slider");
const mealsValue = document.getElementById("meals-value");
const categorySelect = document.getElementById("category-select");
const includeInput = document.getElementById("include-input");
const excludeInput = document.getElementById("exclude-input");
const generateBtn = document.getElementById("generate-btn");
const resultsWelcome = document.getElementById("results-welcome");
const planContainer = document.getElementById("plan-container");
const loadingOverlay = document.getElementById("loading-overlay");
const loadingText = document.getElementById("loading-text");
const menuMealsCount = document.getElementById("menu-meals-count");
const menuGrid = document.getElementById("menu-grid");
const shoppingListContainer = document.getElementById("shopping-list-container");
const instructionsContainer = document.getElementById("instructions-container");
const copyListBtn = document.getElementById("copy-list-btn");
const shareListBtn = document.getElementById("share-list-btn");

// Settings Modal Elements
const openSettingsBtn = document.getElementById("open-settings-btn");
const closeSettingsBtn = document.getElementById("close-settings-btn");
const saveSettingsBtn = document.getElementById("save-settings-btn");
const settingsModal = document.getElementById("settings-modal");
const apiKeyInput = document.getElementById("api-key-input");

// Tab Toggle Elements
const tabManualBtn = document.getElementById("tab-manual-btn");
const tabAiBtn = document.getElementById("tab-ai-btn");
const manualSection = document.getElementById("manual-controls-section");
const aiSection = document.getElementById("ai-chat-section");

// AI Chat Elements
const chatMessagesContainer = document.getElementById("chat-messages-container");
const chatTextInput = document.getElementById("chat-text-input");
const chatSendBtn = document.getElementById("chat-send-btn");
const chatKeyMissing = document.getElementById("chat-key-missing");
const chatInputArea = document.getElementById("chat-input-area");

// Handle meals slider change
mealsSlider.addEventListener("input", (e) => {
  mealsValue.textContent = e.target.value;
});

// Setup Rating Button Selectors
const ratingButtons = document.querySelectorAll(".rating-btn");
ratingButtons.forEach(btn => {
  btn.addEventListener("click", () => {
    ratingButtons.forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    minRatingSelected = parseFloat(btn.getAttribute("data-val"));
  });
});

// Settings Modal Action handlers
openSettingsBtn.addEventListener("click", () => {
  apiKeyInput.value = localStorage.getItem("gemini_api_key") || "";
  settingsModal.style.display = "flex";
});

closeSettingsBtn.addEventListener("click", () => {
  settingsModal.style.display = "none";
});

settingsModal.addEventListener("click", (e) => {
  if (e.target === settingsModal) {
    settingsModal.style.display = "none";
  }
});

saveSettingsBtn.addEventListener("click", () => {
  const key = apiKeyInput.value.trim();
  localStorage.setItem("gemini_api_key", key);
  settingsModal.style.display = "none";
  updateChatLockState();
  if (key) {
    openSettingsBtn.innerHTML = "<span>✓ AI Connected</span>";
    openSettingsBtn.style.color = "var(--color-success)";
    openSettingsBtn.style.borderColor = "var(--color-success)";
  } else {
    openSettingsBtn.innerHTML = "<span>⚙️ Setup AI Chat</span>";
    openSettingsBtn.style.color = "";
    openSettingsBtn.style.borderColor = "";
  }
});

// Toggle controls panels
tabManualBtn.addEventListener("click", () => {
  tabManualBtn.classList.add("active");
  tabAiBtn.classList.remove("active");
  manualSection.style.display = "block";
  aiSection.style.display = "none";
});

tabAiBtn.addEventListener("click", () => {
  tabAiBtn.classList.add("active");
  tabManualBtn.classList.remove("active");
  aiSection.style.display = "flex";
  manualSection.style.display = "none";
  updateChatLockState();
  // Scroll to bottom of chat
  chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
});

function updateChatLockState() {
  const key = localStorage.getItem("gemini_api_key");
  if (key) {
    chatKeyMissing.style.display = "none";
    chatInputArea.style.display = "flex";
  } else {
    chatKeyMissing.style.display = "block";
    chatInputArea.style.display = "none";
  }
}

// Initialize Application and load databases
async function initializeApp() {
  try {
    // Check initial API Key state
    const existingKey = localStorage.getItem("gemini_api_key");
    if (existingKey) {
      openSettingsBtn.innerHTML = "<span>✓ AI Connected</span>";
      openSettingsBtn.style.color = "var(--color-success)";
      openSettingsBtn.style.borderColor = "var(--color-success)";
    }

    // 1. Fetch Drive links first
    try {
      loadingText.textContent = "Loading Google Drive mappings...";
      const linksRes = await fetch("drive_links.json");
      if (linksRes.ok) {
        driveLinks = await linksRes.json();
        console.log("Loaded drive links mapping:", Object.keys(driveLinks).length, "items.");
      }
    } catch (e) {
      console.log("No drive_links.json available, using defaults.");
    }

    // 2. Fetch and parse recipes CSV
    loadingText.textContent = "Loading 5,300+ Recipes CSV Database (approx. 9.7MB)...";
    const csvRes = await fetch("nyt_recipes_index.csv");
    if (!csvRes.ok) {
      throw new Error("Could not load recipes database file.");
    }
    
    const csvText = await csvRes.text();
    loadingText.textContent = "Parsing recipes...";
    
    // Parse using PapaParse client-side
    Papa.parse(csvText, {
      header: true,
      skipEmptyLines: true,
      complete: function(results) {
        processParsedData(results.data);
        hideLoadingOverlay();
        loadSavedPreferences();
      },
      error: function(err) {
        alert("Failed to parse recipe database: " + err.message);
      }
    });

  } catch (err) {
    console.error(err);
    loadingText.textContent = "Error: " + err.message;
  }
}

function hideLoadingOverlay() {
  loadingOverlay.style.opacity = 0;
  setTimeout(() => {
    loadingOverlay.style.display = "none";
  }, 500);
}

// Normalize and prepare parsed recipes
function processParsedData(rawRows) {
  recipes = [];
  rawRows.forEach(row => {
    const title = row['Title'] ? row['Title'].trim() : '';
    const ingredients = row['Ingredients'] ? row['Ingredients'].trim() : '';
    const method = row['Method'] ? row['Method'].trim() : '';
    
    if (!title || !ingredients || method.toLowerCase() === 'n/a' || method === '') return;
    
    const rawList = ingredients.split(';').map(i => i.trim()).filter(i => i);
    if (rawList.length === 0) return;
    
    const normalizedList = [];
    const shoppingList = [];
    
    rawList.forEach(raw => {
      const norm = normalizeIngredient(raw);
      if (norm) {
        normalizedList.push(norm);
        if (!PANTRY_ITEMS.has(norm)) {
          shoppingList.push(norm);
        }
      }
    });
    
    row['parsed_ingredients'] = rawList;
    row['normalized_ingredients'] = normalizedList;
    row['shopping_ingredients'] = [...new Set(shoppingList)];
    row['Rating'] = row['Rating'] ? row['Rating'].trim() : 'N/A';
    row['Reviews'] = row['Reviews'] ? row['Reviews'].trim() : 'N/A';
    
    recipes.push(row);
  });
  console.log("Processed recipes count:", recipes.length);
}

// Clean and normalize ingredient names
function normalizeIngredient(rawText) {
  let clean = rawText.toLowerCase();
  
  clean = clean.replace(/^\s*\d+[\d\/\s\.\-¼½¾⅓⅔⅛]*\s*(cups?|tbsp|tablespoons?|tsps?|teaspoons?|pounds?|lbs?|ounces?|oz|grams?|cloves?|cans?|jars?|tins?|bottles?|pinches?|slices?|pieces?|bunches?|sprigs?|heads?|bags?|containers?|halves|quarter|inch|inch-thick)\s*(of)?\s*/i, '');
  clean = clean.replace(/,\s*(peeled|chopped|sliced|diced|minced|melted|grated|slivered|crushed|to taste|for serving|optional|divided|cold|room temperature|finely|coarsely|beaten|drained|rinsed).*$/gi, '');
  clean = clean.replace(/\s*\(.*?\)/g, '');
  
  clean = clean.trim();
  if (clean.endsWith('s') && !clean.endsWith('less') && !clean.endsWith('cress')) {
    clean = clean.slice(0, -1);
  }
  return clean.trim();
}

// Classify ingredient into supermarket category
function classifyIngredient(name) {
  for (const [category, keywords] of Object.entries(CATEGORY_KEYWORDS)) {
    for (const kw of keywords) {
      if (name.includes(kw)) {
        return category;
      }
    }
  }
  return "Other / Miscellaneous";
}

// Check if a recipe matches search filter criteria
function matchCriteria(recipe, category, includeKws, excludeKws, minRating) {
  // Category check
  if (category && category.toLowerCase() !== "all") {
    const rCat = recipe['Category'] ? recipe['Category'].toLowerCase() : '';
    if (rCat !== category.toLowerCase()) {
      const tags = recipe['Tags'] ? recipe['Tags'].split(',').map(t => t.trim().toLowerCase()) : [];
      if (!tags.includes(category.toLowerCase())) {
        return false;
      }
    }
  }
  
  // Rating check
  const rRating = recipe['Rating'] !== 'N/A' ? parseFloat(recipe['Rating']) : 0;
  if (rRating < minRating) return false;
  
  const titleAndIng = (recipe['Title'] + " " + recipe['Ingredients'] + " " + recipe['Tags']).toLowerCase();
  
  // Exclude keywords
  if (excludeKws.length > 0) {
    for (const kw of excludeKws) {
      if (titleAndIng.includes(kw)) return false;
    }
  }
  
  // Include keywords
  if (includeKws.length > 0) {
    let matchFound = false;
    for (const kw of includeKws) {
      if (titleAndIng.includes(kw)) {
        matchFound = true;
        break;
      }
    }
    if (!matchFound) return false;
  }
  
  return true;
}

// plan_meals with popularity utility and diversity penalty
function planMeals(candidates, numMeals, includeKws) {
  if (candidates.length === 0) return [];
  
  function getQualityScore(r) {
    const rating = r['Rating'] !== 'N/A' ? parseFloat(r['Rating']) : 0;
    const reviews = r['Reviews'] !== 'N/A' ? parseInt(r['Reviews']) : 0;
    return { rating, reviews };
  }
  
  const sorted = [...candidates].sort((a, b) => {
    const qa = getQualityScore(a);
    const qb = getQualityScore(b);
    if (qa.rating !== qb.rating) return qb.rating - qa.rating;
    return qb.reviews - qa.reviews;
  });
  
  const selected = [sorted[0]];
  
  while (selected.length < numMeals && selected.length < sorted.length) {
    const currentShoppingUnion = new Set();
    selected.forEach(r => {
      r['shopping_ingredients'].forEach(ing => currentShoppingUnion.add(ing));
    });
    
    let bestNext = null;
    let maxUtility = -Infinity;
    
    for (const r of sorted) {
      if (selected.includes(r)) continue;
      
      const recipeIngredients = new Set(r['shopping_ingredients']);
      let numNew = 0;
      recipeIngredients.forEach(ing => {
        if (!currentShoppingUnion.has(ing)) numNew++;
      });
      
      const q = getQualityScore(r);
      const popularityFactor = Math.log(q.reviews + 1) * (q.rating / 5.0);
      
      let utility = -1.5 * numNew + 1.0 * popularityFactor;
      
      // Diversity penalty
      if (includeKws && includeKws.length > 1) {
        const titleAndIng = (r['Title'] + " " + r['Ingredients'] + " " + r['Tags']).toLowerCase();
        for (const kw of includeKws) {
          if (titleAndIng.includes(kw)) {
            const matchCount = selected.filter(sel => 
              (sel['Title'] + " " + sel['Ingredients'] + " " + sel['Tags']).toLowerCase().includes(kw)
            ).length;
            utility -= 4.0 * matchCount;
          }
        }
      }
      
      if (utility > maxUtility) {
        maxUtility = utility;
        bestNext = r;
      }
    }
    
    if (bestNext) {
      selected.push(bestNext);
    } else {
      break;
    }
  }
  
  return selected;
}

// Generate the shopping list grouped by categories
function generateShoppingList(selectedMeals) {
  const shoppingItems = {};
  
  selectedMeals.forEach(recipe => {
    const title = recipe['Title'];
    const rawList = recipe['parsed_ingredients'];
    const normList = recipe['normalized_ingredients'];
    
    rawList.forEach((raw, idx) => {
      const norm = normList[idx];
      if (!norm || PANTRY_ITEMS.has(norm)) return;
      
      if (!shoppingItems[norm]) {
        shoppingItems[norm] = {
          rawList: [],
          recipes: []
        };
      }
      
      shoppingItems[norm].rawList.push(raw);
      if (!shoppingItems[norm].recipes.includes(title)) {
        shoppingItems[norm].recipes.push(title);
      }
    });
  });
  
  const classified = {};
  for (const [norm, data] of Object.entries(shoppingItems)) {
    const category = classifyIngredient(norm);
    if (!classified[category]) classified[category] = [];
    
    const detailedRaw = data.rawList.reduce((a, b) => a.length >= b.length ? a : b);
    classified[category].push({
      name: norm,
      detail: detailedRaw,
      recipes: data.recipes
    });
  }
  return classified;
}

// Generate weekly plan triggered by UI
function triggerGenerateMealPlan() {
  const mealsCount = parseInt(mealsSlider.value);
  const category = categorySelect.value;
  
  const includeKws = includeInput.value.split(',').map(k => k.trim().toLowerCase()).filter(k => k);
  const excludeKws = excludeInput.value.split(',').map(k => k.trim().toLowerCase()).filter(k => k);
  
  savePreferences();
  
  const candidates = recipes.filter(r => matchCriteria(r, category, includeKws, excludeKws, minRatingSelected));
  
  if (candidates.length === 0) {
    alert("No recipes found matching your exact parameters. Please try adjusting your inclusion/exclusion keywords or lowering your rating requirement.");
    return;
  }
  
  const selectedMeals = planMeals(candidates, mealsCount, includeKws);
  if (selectedMeals.length === 0) {
    alert("Failed to plan meals.");
    return;
  }
  
  const shoppingList = generateShoppingList(selectedMeals);
  renderResultsUI(selectedMeals, shoppingList);
}

// Save generated plan to history
function saveMealPlanToHistory(selectedMeals) {
  try {
    let history = JSON.parse(localStorage.getItem("meal_plan_history") || "[]");
    const now = Date.now();
    
    const entry = {
      timestamp: now,
      recipes: selectedMeals.map(r => r.Title)
    };
    history.push(entry);
    
    // Keep only last 60 days
    const cutoff = now - 60 * 24 * 60 * 60 * 1000;
    history = history.filter(h => h.timestamp > cutoff);
    
    localStorage.setItem("meal_plan_history", JSON.stringify(history));
  } catch (e) {
    console.log("Could not save history:", e);
  }
}

// Get recipe titles planned in the last 14 days
function getRecentRecipesList() {
  try {
    const history = JSON.parse(localStorage.getItem("meal_plan_history") || "[]");
    const now = Date.now();
    const twoWeeksAgo = now - 14 * 24 * 60 * 60 * 1000;
    
    const recent = new Set();
    history.forEach(entry => {
      if (entry.timestamp > twoWeeksAgo) {
        entry.recipes.forEach(r => recent.add(r));
      }
    });
    return [...recent];
  } catch (e) {
    return [];
  }
}

// Render Results layout
function renderResultsUI(selectedMeals, shoppingList) {
  // Save to history on render
  saveMealPlanToHistory(selectedMeals);

  resultsWelcome.style.display = "none";
  planContainer.style.display = "block";
  menuMealsCount.textContent = `${selectedMeals.length} Meals`;
  
  // 1. Render Menu Grid
  menuGrid.innerHTML = "";
  selectedMeals.forEach(r => {
    const pdfFilename = r['PDF Filename'] ? r['PDF Filename'].replace(/ /g, '_') : '';
    let driveLink = '#';
    for (const [key, link] of Object.entries(driveLinks)) {
      if (key.replace(/ /g, '_') === pdfFilename || key === pdfFilename || key.replace('.pdf','') === r['Title']) {
        driveLink = link;
        break;
      }
    }
    
    const imageTag = r['Image URL'] ? `<img src="${r['Image URL']}" alt="${r['Title']}" loading="lazy">` : `<div style="height: 100%; display: flex; justify-content: center; align-items: center; background: #1a1a24; font-size: 2rem;">🥘</div>`;
    
    const card = document.createElement("div");
    card.className = "recipe-card card";
    card.innerHTML = `
      <div class="recipe-image-wrap">
        ${imageTag}
      </div>
      <div class="recipe-info">
        <h3 class="recipe-card-title">${r['Title']}</h3>
        <div class="recipe-card-meta">
          <span class="recipe-card-rating">★ ${r['Rating']}</span>
          <span>⏱️ ${r['Total Time'] || 'n/a'}</span>
        </div>
        <div class="recipe-card-links">
          <a href="${r['URL']}" target="_blank" class="card-link-btn nyt">NYT Cooking</a>
          <a href="${driveLink}" target="_blank" class="card-link-btn drive" ${driveLink === '#' ? 'style="opacity: 0.5; pointer-events: none;"' : ''}>Drive PDF</a>
        </div>
      </div>
    `;
    menuGrid.appendChild(card);
  });
  
  // 2. Render Shopping List Categories
  shoppingListContainer.innerHTML = "";
  const categoriesOrdered = ["Produce", "Meat & Seafood", "Dairy & Eggs", "Canned Goods & Grains", "Pantry & Spices", "Other / Miscellaneous"];
  
  categoriesOrdered.forEach(category => {
    const items = shoppingList[category] || [];
    if (items.length === 0) return;
    
    const block = document.createElement("div");
    block.className = "shopping-category-block";
    block.innerHTML = `
      <h3>${category}</h3>
      <div class="shopping-checklist"></div>
    `;
    
    const checklist = block.querySelector(".shopping-checklist");
    items.sort((a,b) => a.name.localeCompare(b.name)).forEach(item => {
      const label = document.createElement("label");
      label.className = "shopping-label";
      
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.className = "shopping-checkbox";
      
      const span = document.createElement("span");
      const cleanDetail = item.detail.charAt(0).toUpperCase() + item.detail.slice(1);
      span.innerHTML = `<strong>${cleanDetail}</strong> <span class="item-recipe-tags">(for: ${item.recipes.join(', ')})</span>`;
      
      label.appendChild(checkbox);
      label.appendChild(span);
      checklist.appendChild(label);
    });
    
    shoppingListContainer.appendChild(block);
  });
  
  // 3. Render Cooking Instructions
  instructionsContainer.innerHTML = "";
  selectedMeals.forEach((r, idx) => {
    const accordion = document.createElement("div");
    accordion.className = "instruction-accordion";
    
    accordion.innerHTML = `
      <div class="accordion-header">
        <span class="accordion-title">${idx+1}. ${r['Title']}</span>
        <span class="accordion-arrow">▼</span>
      </div>
      <div class="accordion-content">
        <p class="prep-section-title">Ingredients Details</p>
        <ul class="prep-ingredients-list">
          ${r['parsed_ingredients'].map(i => `<li>${i}</li>`).join('')}
        </ul>
        <p class="prep-section-title">Method / Steps</p>
        <p class="prep-method-text">${r['Method']}</p>
      </div>
    `;
    
    const header = accordion.querySelector(".accordion-header");
    const content = accordion.querySelector(".accordion-content");
    header.addEventListener("click", () => {
      const isActive = accordion.classList.contains("active");
      if (isActive) {
        accordion.classList.remove("active");
        content.style.display = "none";
      } else {
        accordion.classList.add("active");
        content.style.display = "block";
      }
    });
    
    instructionsContainer.appendChild(accordion);
  });

  if (window.innerWidth < 900) {
    planContainer.scrollIntoView({ behavior: 'smooth' });
  }
}

// Helper to compile plain text shopping list
function getPlainTextShoppingList() {
  const checkboxes = shoppingListContainer.querySelectorAll(".shopping-label");
  if (checkboxes.length === 0) return "";
  
  let listText = "🛒 Weekly Optimized Shopping List:\n\n";
  const categories = shoppingListContainer.querySelectorAll(".shopping-category-block");
  
  categories.forEach(catBlock => {
    const catName = catBlock.querySelector("h3").textContent;
    listText += `🟢 ${catName}\n`;
    
    const items = catBlock.querySelectorAll(".shopping-label");
    items.forEach(item => {
      const rawText = item.querySelector("span").textContent;
      listText += `- [ ] ${rawText}\n`;
    });
    listText += "\n";
  });
  return listText;
}

// Copy plain text shopping list to clipboard
copyListBtn.addEventListener("click", () => {
  const listText = getPlainTextShoppingList();
  if (!listText) return;
  
  navigator.clipboard.writeText(listText).then(() => {
    const originalText = copyListBtn.textContent;
    copyListBtn.textContent = "Copied! ✓";
    copyListBtn.style.background = "#2ecc71";
    copyListBtn.style.color = "white";
    setTimeout(() => {
      copyListBtn.textContent = originalText;
      copyListBtn.style.background = "";
      copyListBtn.style.color = "";
    }, 2000);
  }).catch(err => {
    alert("Could not copy list to clipboard: " + err);
  });
});

// Setup Mobile Web Share API button if supported (iOS Safari / Android Chrome)
if (navigator.share) {
  shareListBtn.style.display = "inline-block";
  shareListBtn.addEventListener("click", () => {
    const listText = getPlainTextShoppingList();
    if (!listText) return;
    
    navigator.share({
      title: "🛒 Weekly Grocery List",
      text: listText
    }).catch(err => {
      console.log("Web Share failed:", err);
    });
  });
} else {
  shareListBtn.style.display = "none";
}

// Load preferences from localStorage
function loadSavedPreferences() {
  try {
    mealsSlider.value = localStorage.getItem("meals_count") || 5;
    mealsValue.textContent = mealsSlider.value;
    categorySelect.value = localStorage.getItem("category") || "Dinner";
    includeInput.value = localStorage.getItem("include_kws") || "";
    excludeInput.value = localStorage.getItem("exclude_kws") || "";
    
    const savedRating = parseFloat(localStorage.getItem("min_rating") || 4.0);
    ratingButtons.forEach(btn => {
      const val = parseFloat(btn.getAttribute("data-val"));
      if (val === savedRating) {
        ratingButtons.forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        minRatingSelected = val;
      }
    });
  } catch (e) {
    console.log("Could not load preferences from storage.");
  }
}

// Save preferences to localStorage
function savePreferences() {
  try {
    localStorage.setItem("meals_count", mealsSlider.value);
    localStorage.setItem("category", categorySelect.value);
    localStorage.setItem("include_kws", includeInput.value);
    localStorage.setItem("exclude_kws", excludeInput.value);
    localStorage.setItem("min_rating", minRatingSelected);
  } catch (e) {
    console.log("Could not save preferences to storage.");
  }
}

// ==========================================
// AI CHAT CONVERSATIONAL ASSISTANT SYSTEM
// ==========================================

const systemPrompt = `You are a professional culinary assistant. Your task is to plan a weekly menu for the user based on their preferences, using ONLY the recipes provided in the candidates list.
Do not invent any recipe names. Only select from the provided candidates list.

IMPORTANT BEHAVIORAL RULES:
1. Do not recommend or select any recipes listed in the "Recently Planned Recipes (Last 2 Weeks)" block in the prompt, unless the user specifically asks you to repeat them.
2. If the user asks for a mix of proteins, a variety, or mix-and-match ingredients, make sure to select recipes containing different protein types (e.g., mix chicken thighs, ground turkey, beef, vegetarian) instead of repeating the same protein.
3. Exclude any seafood recipes if the user requests it.

Return your response as a JSON object matching this schema:
{
  "reply": "Your friendly conversational reply explaining your recommendations, highlighting how you met their constraints, noting any shared ingredients, and answering any culinary questions they had.",
  "selected_titles": ["Recipe Title 1", "Recipe Title 2", "Recipe Title 3"]
}
`;

// Extract keywords from user prompt to filter candidates locally before sending to Gemini
function searchLocalCandidates(userPrompt) {
  const stopWords = new Set([
    "a", "an", "the", "and", "or", "but", "if", "then", "plan", "meal", "meals", "dinner", "dinners",
    "lunch", "breakfast", "using", "with", "no", "without", "seafood", "exclude", "for", "please", 
    "can", "you", "i", "want", "suggest", "some", "any", "recipe", "recipes", "make", "cook", "week", "this"
  ]);
  
  // Split user prompt into words
  const words = userPrompt.toLowerCase().match(/\b\w+\b/g) || [];
  const searchKws = words.filter(w => w.length > 2 && !stopWords.has(w));
  
  // Match exclusions: look for words after "no", "exclude", "without"
  const excludeKws = [];
  const excludeMatch = userPrompt.toLowerCase().match(/(?:no|exclude|without|excluding)\s+([\w\s,]+?)(?:and|with|for|using|$)/);
  if (excludeMatch) {
    const rawExclude = excludeMatch[1];
    rawExclude.split(',').forEach(part => {
      part.split(' ').map(w => w.trim()).forEach(w => {
        if (w.length > 2 && !stopWords.has(w)) excludeKws.push(w);
      });
    });
  }
  
  // Rank candidates based on how many keywords they match
  const rankedCandidates = recipes.map(r => {
    let score = 0;
    const titleAndIng = (r['Title'] + " " + r['Ingredients'] + " " + r['Tags']).toLowerCase();
    
    // Exclude if it contains exclusions
    if (excludeKws.length > 0) {
      for (const ex of excludeKws) {
        if (titleAndIng.includes(ex)) return { recipe: r, score: -1 };
      }
    }
    
    searchKws.forEach(kw => {
      if (titleAndIng.includes(kw)) score += 1;
      if (r['Title'].toLowerCase().includes(kw)) score += 3; // Boost title matches
    });
    
    return { recipe: r, score: score };
  });
  
  // Filter and sort candidates
  const finalCandidates = rankedCandidates
    .filter(item => item.score > 0)
    .sort((a, b) => b.score - a.score)
    .map(item => item.recipe);
    
  // If no keyword matches, fallback to the top 40 most popular recipes in general
  if (finalCandidates.length === 0) {
    return recipes.slice(0, 40);
  }
  
  // Return top 45 candidates to keep context size manageable
  return finalCandidates.slice(0, 45);
}

// Query Gemini API directly via fetch (Zero-dependency REST)
async function queryGemini(userMessage, candidatesList) {
  const apiKey = localStorage.getItem("gemini_api_key");
  if (!apiKey) throw new Error("API Key not found.");
  
  // Fetch recently planned recipes list (last 14 days)
  const recentRecipes = getRecentRecipesList();
  const recentRecipesText = recentRecipes.length > 0 
    ? `Recently Planned Recipes (Last 2 Weeks - DO NOT select these unless explicitly requested):\n- ${recentRecipes.join('\n- ')}` 
    : 'Recently Planned Recipes (Last 2 Weeks): None.';
  
  // Format candidates list to pass to Gemini
  const candidatesText = candidatesList.map((c, idx) => {
    return `${idx+1}. Title: "${c.Title}" | Rating: ${c.Rating}★ | Reviews: ${c.Reviews} | Time: ${c.TotalTime} | Yield: ${c.Yield}\nIngredients: ${c.parsed_ingredients.slice(0, 15).join(', ')}`;
  }).join('\n\n');
  
  const prompt = `User Request: "${userMessage}"\n\n${recentRecipesText}\n\nHere are the top candidate recipes matching their keywords:\n\n${candidatesText}\n\nSelect the best recipes that fit the user request, organize the meal plan, and explain your choices. Return JSON format.`;
  
  const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${apiKey}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      contents: [
        {
          role: "user",
          parts: [
            { text: systemPrompt },
            { text: prompt }
          ]
        }
      ],
      generationConfig: {
        responseMimeType: "application/json",
        responseSchema: {
          type: "OBJECT",
          properties: {
            reply: { type: "STRING" },
            selected_titles: {
              type: "ARRAY",
              items: { type: "STRING" }
            }
          },
          required: ["reply", "selected_titles"]
        }
      }
    })
  });
  
  if (!response.ok) {
    const errText = await response.text();
    throw new Error(`Gemini API error: ${response.status} - ${errText}`);
  }
  
  const data = await response.json();
  const rawText = data.candidates[0].content.parts[0].text;
  return JSON.parse(rawText);
}

// Add a bubble message to the chat view
function appendChatMessage(sender, text) {
  const msgDiv = document.createElement("div");
  msgDiv.className = `chat-message ${sender}`;
  
  const contentDiv = document.createElement("div");
  contentDiv.className = "message-content";
  contentDiv.textContent = text;
  
  msgDiv.appendChild(contentDiv);
  chatMessagesContainer.appendChild(msgDiv);
  
  // Scroll to bottom
  chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
}

// Add typing loader bubble
let typingIndicatorEl = null;
function showTypingIndicator() {
  if (typingIndicatorEl) return;
  
  typingIndicatorEl = document.createElement("div");
  typingIndicatorEl.className = "chat-message assistant";
  typingIndicatorEl.innerHTML = `
    <div class="message-content">
      <div class="typing-indicator">
        <span></span>
        <span></span>
        <span></span>
      </div>
    </div>
  `;
  chatMessagesContainer.appendChild(typingIndicatorEl);
  chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
}

function removeTypingIndicator() {
  if (typingIndicatorEl) {
    typingIndicatorEl.remove();
    typingIndicatorEl = null;
  }
}

// Trigger chat submit
async function handleChatSubmit() {
  const userText = chatTextInput.value.trim();
  if (!userText) return;
  
  chatTextInput.value = "";
  appendChatMessage("user", userText);
  showTypingIndicator();
  
  try {
    // 1. Search database locally to extract candidates
    const candidates = searchLocalCandidates(userText);
    console.log(`Local search returned ${candidates.length} candidates for Gemini AI evaluation.`);
    
    // 2. Call Gemini API
    const result = await queryGemini(userText, candidates);
    removeTypingIndicator();
    
    // 3. Render Assistant Conversational Reply
    appendChatMessage("assistant", result.reply);
    
    // 4. Update the main UI plan if any recipes were selected by Gemini
    if (result.selected_titles && result.selected_titles.length > 0) {
      const selectedMeals = [];
      result.selected_titles.forEach(title => {
        const matched = recipes.find(r => r['Title'].toLowerCase() === title.toLowerCase() || r['Title'].toLowerCase().includes(title.toLowerCase()));
        if (matched) selectedMeals.push(matched);
      });
      
      if (selectedMeals.length > 0) {
        const shoppingList = generateShoppingList(selectedMeals);
        renderResultsUI(selectedMeals, shoppingList);
      }
    }
    
  } catch (err) {
    removeTypingIndicator();
    console.error("AI Chat failed:", err);
    appendChatMessage("assistant", "⚠️ Sorry, I ran into an error connecting to the AI: " + err.message + ". Please make sure your Gemini API Key is valid and active.");
  }
}

chatSendBtn.addEventListener("click", handleChatSubmit);
chatTextInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    handleChatSubmit();
  }
});

// Fire plan generation on button click
generateBtn.addEventListener("click", triggerGenerateMealPlan);

// Run initialization
initializeApp();
