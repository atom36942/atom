#All imports
from core.route import *
from google import genai
import aiohttp,json
from fastapi import Request
from bs4 import BeautifulSoup

#All config
CONFIG_SEARCH_URL="https://www.searchapi.io/api/v1/search"
CONFIG_SEARCH_ENGINE="google"
CONFIG_MAX_URLS=5
CONFIG_LLM_MODEL="gemini-2.0-flash"
CONFIG_HTML_LIMIT=6000

CONFIG_PROMPT_SIGNAL="""From the text below, extract up to 10 distinct factual statements about:
"{query}"

Rules:
- Each fact must be a separate bullet starting with "-"
- Do NOT merge facts into one sentence
- Do NOT repeat the same fact twice
- Copy only what is explicitly stated

Text:
{html}"""


CONFIG_PROMPT_SUMMARY="""You are given factual bullet points from multiple sources about:
"{query}"

Group them into 5-10 short paragraphs.
Use only the facts. No inference, no filler.
Dont start with here is the summary type of text.

Facts:
{merged}"""

#All pure/helper functions
async def func_searchapi_urls(query):
   async with aiohttp.ClientSession() as s:
      async with s.get(CONFIG_SEARCH_URL,params={"engine":CONFIG_SEARCH_ENGINE,"q":query,"api_key":config_searchapi_key}) as r:
         j=await r.json()
         return [x["link"] for x in j.get("organic_results",[])[:CONFIG_MAX_URLS]]

async def func_http_fetch(url):
   async with aiohttp.ClientSession() as s:
      async with s.get(url,headers={"User-Agent":"Mozilla/5.0"}) as r:
         raw=await r.read()
         try:return raw.decode("utf-8","ignore")
         except:return raw.decode("latin1","ignore")

async def func_clean_text(html):
   soup=BeautifulSoup(html,"html.parser")
   for t in soup(["script","style","noscript"]):t.decompose()
   return " ".join(soup.stripped_strings)

async def func_llm_signal(html,query):
   client=genai.Client(api_key=config_gemini_key)
   prompt=CONFIG_PROMPT_SIGNAL.format(query=query,html=html[:CONFIG_HTML_LIMIT])
   r=client.models.generate_content(model=CONFIG_LLM_MODEL,contents=prompt)
   return r.text.strip()

async def func_llm_summarize(fragments,query):
   client=genai.Client(api_key=config_gemini_key)
   merged="\n".join([f for f in fragments if f])
   prompt=CONFIG_PROMPT_SUMMARY.format(query=query,merged=merged)
   r=client.models.generate_content(model=CONFIG_LLM_MODEL,contents=prompt)
   return {"summary":r.text.strip(),"sources":len(fragments)}

#All API routes
@router.get("/public/person-intel")
async def func_api_5aa65182abea4af6bd266efc05ac611f(request:Request,q:str):
   urls=await func_searchapi_urls(q);fragments=[];used=[]
   for u in urls:
      html=await func_http_fetch(u)
      clean=await func_clean_text(html)
      frag=await func_llm_signal(clean,q)
      if frag:fragments.append(frag);used.append(u)
   output=await func_llm_summarize(fragments,q)
   output["urls"]=used
   return {"status":1,"message":output}

