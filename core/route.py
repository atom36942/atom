#import
from core.config import *
from core.function import *
from datetime import datetime
from pathlib import Path
from starlette.background import BackgroundTask
from fastapi import Request, WebSocket, WebSocketDisconnect, responses
from bs4 import BeautifulSoup
from google import genai
import asyncio
import aiohttp
import hashlib
import json
import os
import time
import uuid

#router
from fastapi import APIRouter
router=APIRouter()
