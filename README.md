## 📦 Lite Backend (FastAPI)

This is the FastAPI-powered backend for **Stears Lite**, an economic data insights platform. It provides company data for African companies.
---

### 🚀 Features

* 📈 Company data, including income, funding, competitors, e.t.c
* 🔁 JSON API ready for frontend consumption (Next.js)

---

### 🛠️ Tech Stack

* **Python 3.10+**
* **FastAPI**
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
├── README.md
└── vercel.json
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
  "company": "Tesla",
  "company_info_fixed": {"total funding": "$10B", ...},
  "company_info": {"industry": "Automotive", ...},
  "description": "Tesla, Inc. is an American electric vehicle and clean energy company.",
  "country": "USA",
  "articles": [
    {
      "id": "article_id_1", 
      "title": "Tesla's New Car Model Announced", 
      "sentiment_score": 0.8, 
      ...
    },
    ...
    ],
  "competitors": {
    "company1": {...}, 
    "company2": {...}},
  "funding": {
    "round_1": {"amount": "2B", ...}, 
    ...
    }
}

```