import os
import requests
import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from upsonic import Agent, Task, ObjectResponse
from upsonic.client.tools import Search
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize the agent
news_agent = Agent("Company News Analyst", model="azure/gpt-4o")

# Define FastAPI app
app = FastAPI()

# Input Model: Company Name
class CompanyInput(BaseModel):
    company_name: str

# Response Format
class News(ObjectResponse):
    title: str
    url: str
    snippet: str

class NewsResponse(ObjectResponse):
    articles: list[News]

# ✅ SerpAPI Tool for Company News Search
class SerpAPITool:
    def search(query: str) -> list:
        """Fetch latest news articles using SerpAPI."""
        api_key = os.getenv("SERPAPI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="SerpAPI API Key not found!")

        url = "https://google.serper.dev/search"
        headers = {
            'X-API-KEY': api_key,
            'Content-Type': 'application/json'
        }
        payload = json.dumps({"q": query})

        response = requests.post(url, headers=headers, data=payload)
        if response.status_code == 200:
            data = response.json()
            search_results = data.get("organic", [])

            return [
                News(
                    title=result.get("title", "No Title"),
                    url=result.get("link", "#"),
                    snippet=result.get("snippet", "No Description")
                )
                for result in search_results[:10]
            ]
        else:
            raise HTTPException(status_code=500, detail=f"SerpAPI Request Failed: {response.text}")

# ✅ Define News Search Task
@app.post("/get-company-news/")
async def get_company_news(input_data: CompanyInput):
    """Fetches the latest news articles about the given company."""
    search_query = f"Latest news about {input_data.company_name}"

    news_task = Task(
        description=f"Fetch the latest news about {input_data.company_name}.",
        tools=[Search, SerpAPITool],
        response_format=NewsResponse
    )

    news_agent.do(news_task)
    news_data = news_task.response

    if not news_data:
        raise HTTPException(status_code=500, detail="Failed to fetch company news.")

    return {
        "company_name": input_data.company_name,
        "articles": news_data.articles
    }

# ✅ Web UI for Company News Search
@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Company News Search</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; margin: 50px; }
            input { padding: 10px; margin: 10px; width: 300px; }
            button { padding: 10px; background: blue; color: white; border: none; cursor: pointer; }
            #results { margin-top: 20px; text-align: left; }
            footer { margin-top: 30px; font-size: 0.9em; color: #555; }
            footer a { color: #007BFF; text-decoration: none; }
            footer a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <h1>Company News Search</h1>
        <input type="text" id="company" placeholder="Enter company name">
        <button onclick="fetchCompanyNews()">Search</button>
        <div id="results"></div>
        <footer>
            Powered by <a href="https://upsonic.ai" target="_blank">UpsonicAI</a>
        </footer>
        <script>
            async function fetchCompanyNews() {
                const company = document.getElementById('company').value;
                const response = await fetch('/get-company-news/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ company_name: company })
                });
                const data = await response.json();

                let resultsHTML = "<h2>Latest Articles:</h2>";
                data.articles.forEach(article => {
                    resultsHTML += `<p><strong>${article.title}</strong><br>`;
                    resultsHTML += `<a href="${article.url}" target="_blank">Read More</a></p>`;
                });

                document.getElementById('results').innerHTML = resultsHTML;
            }
        </script>
    </body>
    </html>
    """
