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

// Initialize Application and load databases
async function initializeApp() {
  try {
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
    // Basic verification
    const title = row['Title'] ? row['Title'].trim() : '';
    const ingredients = row['Ingredients'] ? row['Ingredients'].trim() : '';
    const method = row['Method'] ? row['Method'].trim() : '';
    
    if (!title || !ingredients || method.toLowerCase() === 'n/a' || method === '') return;
    
    // Parse raw ingredients
    const rawList = ingredients.split(';').map(i => i.trim()).filter(i => i);
    if (rawList.length === 0) return;
    
    // Normalize list for comparison
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
  
  // Strip measurements, fractions, and indicators
  clean = clean.replace(/^\s*\d+[\d\/\s\.\-¼½¾⅓⅔⅛]*\s*(cups?|tbsp|tablespoons?|tsps?|teaspoons?|pounds?|lbs?|ounces?|oz|grams?|cloves?|cans?|jars?|tins?|bottles?|pinches?|slices?|pieces?|bunches?|sprigs?|heads?|bags?|containers?|halves|quarter|inch|inch-thick)\s*(of)?\s*/i, '');
  clean = clean.replace(/,\s*(peeled|chopped|sliced|diced|minced|melted|grated|slivered|crushed|to taste|for serving|optional|divided|cold|room temperature|finely|coarsely|beaten|drained|rinsed).*$/gi, '');
  clean = clean.replace(/\s*\(.*?\)/g, ''); // strip parentheses
  
  // Strip plural 's' at the end
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
      // Tags fallback check
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
  
  // Exclude keywords (must exclude all)
  if (excludeKws.length > 0) {
    for (const kw of excludeKws) {
      if (titleAndIng.includes(kw)) return false;
    }
  }
  
  // Include keywords (OR match: must include at least one)
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
  
  // Calculate recipe baseline quality score
  function getQualityScore(r) {
    const rating = r['Rating'] !== 'N/A' ? parseFloat(r['Rating']) : 0;
    const reviews = r['Reviews'] !== 'N/A' ? parseInt(r['Reviews']) : 0;
    return { rating, reviews };
  }
  
  // Initial sort by quality descending
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
      
      // Balance: -1.5 utility per new ingredient, +1.0 utility per log popularity
      let utility = -1.5 * numNew + 1.0 * popularityFactor;
      
      // Diversity penalty
      if (includeKws && includeKws.length > 1) {
        const titleAndIng = (r['Title'] + " " + r['Ingredients'] + " " + r['Tags']).toLowerCase();
        for (const kw of includeKws) {
          if (titleAndIng.includes(kw)) {
            const matchCount = selected.filter(sel => 
              (sel['Title'] + " " + sel['Ingredients'] + " " + sel['Tags']).toLowerCase().includes(kw)
            ).length;
            
            // Subtract 4.0 points per already represented keyword
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
    
    // Select the longest (most descriptive) raw text to show
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
  
  // Filter matches
  const candidates = recipes.filter(r => matchCriteria(r, category, includeKws, excludeKws, minRatingSelected));
  console.log(`Found ${candidates.length} candidate recipes.`);
  
  if (candidates.length === 0) {
    alert("No recipes found matching your exact parameters. Please try adjusting your inclusion/exclusion keywords or lowering your rating requirement.");
    return;
  }
  
  const selectedMeals = planMeals(candidates, mealsCount, includeKws);
  if (selectedMeals.length === 0) {
    alert("Failed to plan meals.");
    return;
  }
  
  // Generate shopping list
  const shoppingList = generateShoppingList(selectedMeals);
  
  // Render results UI
  renderResultsUI(selectedMeals, shoppingList);
}

// Render Results layout
function renderResultsUI(selectedMeals, shoppingList) {
  resultsWelcome.style.display = "none";
  planContainer.style.display = "block";
  menuMealsCount.textContent = `${selectedMeals.length} Meals`;
  
  // 1. Render Menu Grid
  menuGrid.innerHTML = "";
  selectedMeals.forEach(r => {
    // Determine Google Drive link
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
    
    // Toggle accordion functionality
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

  // Smooth scroll down to results on mobile devices
  if (window.innerWidth < 900) {
    planContainer.scrollIntoView({ behavior: 'smooth' });
  }
}

// Copy plain text shopping list to clipboard
copyListBtn.addEventListener("click", () => {
  const checkboxes = shoppingListContainer.querySelectorAll(".shopping-label");
  if (checkboxes.length === 0) return;
  
  let listText = "🛒 Weekly Optimized Shopping List:\n\n";
  const categories = shoppingListContainer.querySelectorAll(".shopping-category-block");
  
  categories.forEach(catBlock => {
    const catName = catBlock.querySelector("h3").textContent;
    listText += `🟢 ${catName}\n`;
    
    const items = catBlock.querySelectorAll(".shopping-label");
    items.forEach(item => {
      // Clean up text
      const rawText = item.querySelector("span").textContent;
      listText += `- [ ] ${rawText}\n`;
    });
    listText += "\n";
  });
  
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

// Fire plan generation on button click
generateBtn.addEventListener("click", triggerGenerateMealPlan);

// Run initialization
initializeApp();
