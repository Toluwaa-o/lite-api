## 📦 Lite Backend (FastAPI)

This is the FastAPI-powered backend for **Stears Lite**, an economic data insights platform. It provides macroeconomic indicator data for African countries, including trends, volatility analysis, and comparisons to regional averages.

---

### 🚀 Features

* 📈 Macroeconomic indicators grouped by category (GDP, Inflation, Trade, etc.)
* 🔍 Trend data for the past 5 years
* 🧮 Volatility classification (Stable, Moderately Volatile, Volatile)
* 📊 Regional vs national comparisons
* 🔁 JSON API ready for frontend consumption (Next.js)

---

### 🛠️ Tech Stack

* **Python 3.10+**
* **FastAPI**
* **Pandas** for data processing
* **Uvicorn** for ASGI server

---

### 📁 Project Structure

```
.
├── main.py               # FastAPI app entry point
├── scrapper_functions/
│   └── scrapper.py          # Scrapes for data and returns the information in a useful format
|   └── data
|       └── data.py       # Contains various lists and dictionaries used in the data collection process
|   └── functions
|       └── functions.py   # Contains all the functions that handle the scraping and processing logic
├── .gitignore             # Gitignore file
├── requirements.text       # Contains the required libraries and specifications for the api to work
└── README.md
```

---

### 🧪 Running Locally

1. **Clone the repo**

```bash
git clone https://github.com/Toluwaa-o/lite-api.git
cd lite-api
```

2. **Create and activate a virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Run the server**

```bash
uvicorn main:app --reload
```

Visit `http://localhost:8000/docs` to access the interactive API docs.

---

### 📌 Endpoints

* `GET /information/{company}` – Returns processed data for a company

Example:

```
GET /information/Opay
```

---

### 📄 Output Format

```json
{
  "GDP & Growth": {
    "NY.GDP.MKTP.CD": {
      "current_value": 500000000000,
      "description": "GDP (current US$)",
      "trend": [...],
      "comparison": {...},
      "percentage_difference": 0.12,
      "volatility_label": "Moderately Volatile"
    }
  },
  ...
}
```