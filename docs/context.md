# Project Context: AI-Powered Restaurant Recommendation System

> **Source:** `problemStatement.txt`  
> **Use case:** Zomato-inspired restaurant recommendation service

---

## Overview

Build an **AI-powered restaurant recommendation service** inspired by Zomato. The system intelligently suggests restaurants based on user preferences by combining **structured data** with a **Large Language Model (LLM)**.

---

## Objective

Design and implement an application that:

- Takes user preferences (such as location, budget, cuisine, and ratings)
- Uses a real-world dataset of restaurants
- Leverages an LLM to generate personalized, human-like recommendations
- Displays clear and useful results to the user

---

## System Workflow

### 1. Data Ingestion

- Load and preprocess the Zomato dataset from Hugging Face  
  **Dataset URL:** https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation
- Extract relevant fields such as:
  - Restaurant name
  - Location
  - Cuisine
  - Cost
  - Rating
  - (Other applicable fields from the dataset)

### 2. User Input

Collect user preferences:

| Preference | Examples / Notes |
|------------|------------------|
| **Location** | Delhi, Bangalore |
| **Budget** | low, medium, high |
| **Cuisine** | Italian, Chinese |
| **Minimum rating** | Numeric threshold |
| **Additional preferences** | family-friendly, quick service, etc. |

### 3. Integration Layer

- Filter and prepare relevant restaurant data based on user input
- Pass structured results into an LLM prompt
- Design a prompt that helps the LLM **reason** and **rank** options

### 4. Recommendation Engine

Use the LLM to:

- **Rank** restaurants
- **Provide explanations** (why each recommendation fits the user)
- **Optionally summarize** choices

### 5. Output Display

Present top recommendations in a user-friendly format:

| Field | Description |
|-------|-------------|
| Restaurant Name | Name of the recommended restaurant |
| Cuisine | Type of cuisine offered |
| Rating | Restaurant rating |
| Estimated Cost | Cost estimate for the user |
| AI-generated explanation | Why this restaurant was recommended |

---

## Key Technical Components

```
User Preferences → Data Filtering → LLM Prompt → Ranked Recommendations → UI Display
        ↑                    ↑
   Zomato Dataset (Hugging Face)
```

| Component | Role |
|-----------|------|
| **Dataset** | Real-world Zomato restaurant data (Hugging Face) |
| **Filter layer** | Narrow candidates by location, budget, cuisine, rating |
| **LLM** | Rank, explain, and optionally summarize recommendations |
| **Presentation layer** | Show structured results with AI explanations |

---

## Success Criteria

1. User can specify preferences (location, budget, cuisine, rating, extras).
2. System loads and uses the Hugging Face Zomato dataset.
3. Filtered data is passed to an LLM with a well-designed prompt.
4. Output includes ranked restaurants with name, cuisine, rating, cost, and explanations.
5. Results are presented clearly to the end user.

---

## External Resources

- **Dataset:** [ManikaSaini/zomato-restaurant-recommendation](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation) on Hugging Face
