import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from googleapiclient.discovery import build

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

# --- Helper Function for Google Search ---
def perform_google_search(query: str, lang_code: str):
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
            num=5  # Fetch top 5 results
        ).execute()

        # Extract and format the search results
        if 'items' in result:
            formatted_results = [
                {
                    "title": item.get('title'),
                    "link": item.get('link'),
                    "snippet": item.get('snippet')
                }
                for item in result['items']
            ]
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

    search_results = perform_google_search(query=request.query, lang_code=request.lang_code)
    
    if not search_results:
        return {"message": "No results found.", "results": []}
        
    return {"results": search_results}

@app.get("/")
def read_root():
    return {"message": "Google Search MCP Server is running. Send a POST request to /search/ to perform a search."}
