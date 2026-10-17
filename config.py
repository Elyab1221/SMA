import os
from datetime import timedelta
from dotenv import load_dotenv 

load_dotenv()
SECRET_KEY=os.environ["SECRET_KEY"]
CLUB_CODE=os.environ["CLUB_CODE"]
DATABASE=os.environ.get("DATABASE","sma.db")
DAILY_LIMIT=5
#there is a limit for msgs per day because no one knows what will happen when u give ppl too much freedom 
MAX_FAILS=5          #wrong password
LOCK_SECONDS=600     #lockout length seconds so prob 10 min ig 
SESSION_LIFETIME=timedelta(hours=8)  
HTTPS=os.environ.get("HTTPS")=="1"        
DEBUG= os.environ.get("FLASK_DEBUG")=="1"
