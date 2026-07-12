---
name: meal-planner
description: Generates an optimized weekly meal plan and shopping list by selecting recipes with maximum ingredient overlap from your NYT Cooking database.
---

# Meal Planner Skill

This skill allows the agent to automatically generate weekly meal plans and shopping lists using your local database of over 5,300 NYT Cooking recipes, optimized to group similar ingredients and minimize shopping list size.

## When to Activate
Activate this skill when the user requests:
- A weekly meal plan or recipe selection.
- A shopping list based on your recipe database.
- An optimization of recipes to share ingredients.

## Instructions
1. Navigate to the project directory: `C:\Users\clark\Documents\nyt_recipes`
2. Determine user preferences:
   - Category: (e.g. Dinner, Lunch, Breakfast, Desserts, or "all")
   - Number of meals: (default is 3, but can be customized)
   - Ingredients/keywords to include: (e.g. "chicken", "spinach", "vegetarian")
   - Ingredients/keywords to exclude: (e.g. "pork", "cilantro", "nuts")
3. Run the python meal planner script using the `run_command` tool:
   ```bash
   python meal_planner.py --meals <number> --category <category> --include "<keywords>" --exclude "<keywords>"
   ```
4. Read the generated plan `C:\Users\clark\Documents\nyt_recipes\weekly_meal_plan.md` using the `view_file` tool to inspect the selected recipes and shopping list.
5. Present the summary to the user:
   - List the selected recipe titles, ratings, and cook times.
   - Summarize the shopping list categories.
   - Provide a clickable markdown link to the full plan file: [weekly_meal_plan.md](file:///C:/Users/clark/Documents/nyt_recipes/weekly_meal_plan.md).
