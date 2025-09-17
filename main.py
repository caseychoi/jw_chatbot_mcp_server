import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from googleapiclient.discovery import build
import requests
from bs4 import BeautifulSoup

# Load environment variables from .env file
load_dotenv()

# Get API key and CSE ID from environment
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")

# Initialize FastAPI app
app = FastAPI(
    title="Google Search MCP Server",
    description="A server to perform Google Custom Searches, scoped to a specific website.",
    version="1.0.0",
)

# Define the request body model using Pydantic
# This ensures that any request to our endpoint has a 'query' and an optional 'lang_code'
class SearchRequest(BaseModel):
    query: str
    lang_code: str = 'en' # Default to English if not provided
    num: int = Field(..., ge=1, le=10, description="Number of results to return (1-10)")
    full_text: bool  # Optional: fetch full page text

# --- Helper Function for Google Search ---
def perform_google_search(query: str, lang_code: str, num: int, full_text: bool):
    """
    Performs a Google Custom Search with a specified query and language.
    """
    try:
        # Build the service object
        service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)
        
        # Perform the search
        result = service.cse().list(
            q=query,
            cx=GOOGLE_CSE_ID,
            lr=f"lang_{lang_code}", # Language restriction
            num=num  # Use the provided count
        ).execute()

        # Extract and format the search results
        if 'items' in result:
            formatted_results = []
            for item in result['items']:
                result_dict = {
                    "title": item.get('title'),
                    "link": item.get('link'),
                    "snippet": item.get('snippet')
                }
                if full_text:
                    try:
                        response = requests.get(item.get('link'), timeout=5)
                        soup = BeautifulSoup(response.content, 'html.parser')
                        # Extract text from <p> tags or body, limit to ~1000 chars
                        paragraphs = soup.find_all('p')
                        full_content = ' '.join([p.get_text() for p in paragraphs])[:1000]
                        result_dict["full_text"] = full_content
                    except Exception as e:
                        result_dict["full_text"] = f"Error fetching text: {str(e)}"
                formatted_results.append(result_dict)
            return formatted_results
        else:
            return []
            
    except Exception as e:
        print(f"An error occurred during Google search: {e}")
        # In a real server, you'd have more robust error logging
        raise HTTPException(status_code=500, detail=f"Google Search API error: {str(e)}")


# --- API Endpoint for Search ---
@app.post("/search/")
def search(request: SearchRequest):
    """
    Receives a search query and language code, performs the search,
    and returns the results.
    """
    print(f"Received search request: Query='{request.query}', Language='{request.lang_code}'")
    
    if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
        raise HTTPException(status_code=500, detail="Server is not configured with Google API credentials.")

    search_results = perform_google_search(query=request.query, lang_code=request.lang_code, num=request.num, full_text=request.full_text)
    
    if not search_results:
        return {"message": "No results found.", "results": []}
        
    return {"results": search_results}

@app.get("/")
def read_root():
    return {"message": "Google Search MCP Server is running. Send a POST request to /search/ to perform a search."}