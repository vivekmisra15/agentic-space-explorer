import os                          # Lets us read environment variables (your keys)
from dotenv import load_dotenv     # Reads .env file and loads keys into memory
from google import genai           # The Gemini SDK

load_dotenv()                      # Executes: read `.env` → set OS variables
api_key = os.getenv("GEMINI_API_KEY")  # Fetch the key you pasted

print(f"Key loaded: {'Yes' if api_key else 'No'}")  # Sanity check: did we find it?

client = genai.Client(api_key=api_key)  # Create a Gemini client with YOUR key
response = client.models.generate_content(
    model="gemini-2.5-flash-lite",
    contents="Say 'Engines ready' if you can hear me."
)
print(f"Gemini response: {response.text}")      # Print what Gemini says back