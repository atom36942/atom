#import
import os
import uvicorn
from core.app import app

#main
if __name__ == "__main__":
    print("🚀 starting atom server...")
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))