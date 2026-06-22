from dotenv import load_dotenv
import os

load_dotenv()

NYT_API_KEY = os.getenv("NYT_API_KEY")
if not NYT_API_KEY:
    raise EnvironmentError("NYT_API_KEY is not set. Add it to your .env file.")
