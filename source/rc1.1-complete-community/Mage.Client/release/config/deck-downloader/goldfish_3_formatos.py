#!/usr/bin/env python3
"""Descarga 25 mazos 60+15 de MTGGoldfish en Forge y XMage."""
import os,re,sys,time,shutil,subprocess,importlib.util
from urllib.parse import urljoin
try:
 import requests
 from bs4 import BeautifulSoup
except ImportError:
 subprocess.check_call([sys.executable,"-m","pip","install","requests","beautifulsoup4"])
 import requests
 from bs4 import BeautifulSoup
if importlib.util.find_spec("selenium") is None or importlib.util.find_spec("undetected_chromedriver") is None:
 subprocess.check_call([sys.executable,"-m","pip","install","selenium","undetected-chromedriver"])
from selenium.webdriver.chrome.options import Options
import undetected_chromedriver as uc

BASE="https://www.mtggoldfish.com"
FORMATS={"Standard":"standard","Pioneer":"pioneer","Modern":"modern"}
TOP_N=25
HERE=os.path.dirname(os.path.abspath(__file__))
ROOT=os.path.join(HERE,"MTGGoldfish")
LOG=os.path.join(HERE,"goldfish_3_formatos.log")
SESSION=requests.Session()
SESSION.headers.update({"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/150 Safari/537.36","Accept-Language":"en-US,en;q=0.9"})

class Tee:
 def __init__(self,*streams): self.streams=streams
 def write(self,text):
  for s in self.streams: s.write(text); s.flush()
 def flush(self):
  for s in self.streams: s.flush()

def get_soup(url):
 print("GET",url,flush=True)
 r=SESSION.get(url,timeout=30)
 r.raise_for_status()
 return BeautifulSoup(r.text,"html.parser")

def clean_output():
 if os.path.isdir(ROOT): shutil.rmtree(ROOT,ignore_errors=True)
 for engine in ("Forge","XMage"):
  for fmt in FORMATS: os.makedirs(os.path.join(ROOT,engine,fmt),exist_ok=True)
 print("LIMPIANDO",ROOT,flush=True)

def tournament_urls(fmt):
 soup=get_soup(f"{BASE}/tournaments/{fmt}#paper")
 out=[]; seen=set()
 for a in soup.select('a[href^="/tournament/"]'):
  u=urljoin(BASE,a.get("href","").split("#",1)[0])
  if u not in seen: seen.add(u); out.append(u)
 return out

def deck_links(event_url):
 soup=get_soup(event_url); out=[]; seen=set()
 for a in soup.select('a[href*="/deck/"]'):
  m=re.search(r"/deck/(\d+)",a.get("href", ""))
  if not m or m.group(1) in seen: continue
  did=m.group(1); seen.add(did)
  out.append((did,urljoin(BASE,a.get("href").split("#",1)[0]),a.get_text(" ",strip=True)))
 return out

def make_driver():
 def new_options():
  o=Options(); o.add_argument("--disable-blink-features=AutomationControlled"); o.add_argument("--no-first-run"); o.add_argument("--no-default-browser-check"); return o
 try: return uc.Chrome(options=new_options())
 except Exception as e:
  m=re.search(r"Current browser version is\s*(\d+)",str(e),re.I)
  if not m: raise
  return uc.Chrome(options=new_options(),version_main=int(m.group(1)))

def unlock(driver):
 driver.get(f"{BASE}/tournaments/standard#paper")
 print("Chrome está abierto. Resuelve Cloudflare si aparece y pulsa ENTER aquí.",flush=True)
 input()

def parse_deck_page(driver,url):
 print("CHROME",url,flush=True)
 driver.get(url)
 for _ in range(20):
  source=driver.page_source
  if 'deck_input[deck]' in source: break
  time.sleep(1)
 else:
  text=(driver.execute_script("return document.body.innerText;") or "")
  if re.search(r"403|forbidden|just a moment|un momento|verify",text,re.I):
   print("Cloudflare/403 en este mazo. Resuélvelo en Chrome y pulsa ENTER.",flush=True)
   input(); driver.refresh(); time.sleep(3); source=driver.page_source
 soup=BeautifulSoup(source,"html.parser")
 field=soup.select_one('input[name="deck_input[deck]"]')
 if not field: raise ValueError("la página no contiene la lista deck_input[deck]")
 raw=field.get("value","")
 name=(soup.select_one('input[name="deck_input[name]"]') or {}).get("value")
 if not name:
  h=soup.select_one("h1")
  name=h.get_text(" ",strip=True) if h else "MTGGoldfish deck"
 main=[]; side=[]; is_side=False
 for line in raw.splitlines():
  line=line.strip()
  if not line: continue
  if line.lower()=="sideboard" or line.lower().startswith("sideboard"):
   is_side=True; continue
  m=re.match(r"^(\d+)\s+(.+)$",line)
  if not m: continue
  card=re.sub(r"\s*\[[^]]+\].*$","",m.group(2)).strip()
  card=re.sub(r"\s*<[^>]+>\s*$","",card).strip()
  (side if is_side else main).append((int(m.group(1)),card))
 return name,main,side

def safe_stem(name,did,index):
 stem=re.sub(r"[^A-Za-z0-9 _-]","",name).strip().replace(" ","_") or "MTGGoldfish"
 return f"{index:02d}_{stem}_{did}"

def write_deck(fmt,stem,name,main,side):
 fpath=os.path.join(ROOT,"Forge",fmt,stem+".dck")
 xpath=os.path.join(ROOT,"XMage",fmt,stem+".txt")
 with open(fpath,"w",encoding="utf-8") as f:
  f.write(f"[metadata]\nName={name}\n[Main]\n")
  for q,c in main: f.write(f"{q} {c}\n")
  f.write("[Sideboard]\n")
  for q,c in side: f.write(f"{q} {c}\n")
 with open(xpath,"w",encoding="utf-8") as f:
  for q,c in main: f.write(f"{q} {c}\n")
  f.write("\n")
  for q,c in side: f.write(f"{q} {c}\n")

def run():
 clean_output(); total=0; driver=make_driver(); unlock(driver)
 for fmt,slug in FORMATS.items():
  ok=0; processed=set()
  try: events=tournament_urls(slug)
  except Exception as e:
   print(f"[{fmt}] error listando torneos: {e}",flush=True); continue
  for event in events:
   if ok>=TOP_N: break
   try: links=deck_links(event)
   except Exception as e:
    print(f"[{fmt}] evento omitido {event}: {e}",flush=True); continue
   for did,url,link_name in links:
    if ok>=TOP_N: break
    if did in processed: continue
    processed.add(did)
    try:
     name,main,side=parse_deck_page(driver,url)
     mq=sum(q for q,_ in main); sq=sum(q for q,_ in side)
     print(f"[{fmt}] {did}: {mq}+{sq} ({name})",flush=True)
     if mq!=60 or sq!=15:
      print(f"[{fmt}] omitido {did}: no es 60+15",flush=True); continue
     write_deck(fmt,safe_stem(name,did,ok+1),name,main,side)
     ok+=1; total+=1; print(f"[{fmt}] OK {ok}/{TOP_N}",flush=True)
    except Exception as e:
     print(f"[{fmt}] omitido {did}: {e}",flush=True)
    time.sleep(.25)
  print(f"{fmt}: {ok} exportados",flush=True)
 print("TOTAL",total,flush=True)
 driver.quit()

if __name__=="__main__":
 old=sys.stdout
 with open(LOG,"w",encoding="utf-8") as log:
  sys.stdout=Tee(old,log)
  try: run()
  except Exception as e: print("ERROR GLOBAL",repr(e),flush=True)
  finally: print("LOG",LOG,flush=True); sys.stdout=old
