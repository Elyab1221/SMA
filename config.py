import os
from dotenv import load_dotenv 

load_dotenv()
SECRET_KEY=os.environ["SECRET_KEY"]
DATABASE=os.environ.get("DATABASE","sma.db")
DAILY_LIMIT=5
#there is a limit for msgs per day because no one knows what will happen when u give ppl too much freedom 
