#!/usr/bin/env python3
from pathlib import Path
import shutil, zipfile, hashlib

HERE=Path(__file__).resolve().parent
ROOT=HERE/'migration-workspace'/'port-1.4.61V1'
OUT=ROOT/'candidate-output-v4'
ZIP=OUT/'XMage_1.4.61V1_CommunityPatch_DeckDownloader_SMOKE_CANDIDATE_V4.zip'
TEST=ROOT/'gui-smoke-v1'
EXPECTED='02ee830c0e06c28c966032cccd019e000a593fa0b0b746ab7e0d85316c35cf54'

def sha256(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()

def main():
 print('=== XMage Community Patch - ISOLATED GUI SMOKE PREP V1 ===')
 print('SAFE MODE: active XMage is NEVER modified.\n')
 if not ZIP.is_file(): raise RuntimeError(f'V4 candidate not found: {ZIP}')
 got=sha256(ZIP)
 print(f'[OK] Candidate SHA-256: {got}')
 if got.lower()!=EXPECTED: raise RuntimeError('Candidate hash differs from the V4 package that passed static smoke.')
 if TEST.exists():
  print('[STEP] Removing previous isolated GUI test folder...')
  shutil.rmtree(TEST)
 TEST.mkdir(parents=True)
 print('[STEP] Extracting candidate to isolated GUI test folder...')
 with zipfile.ZipFile(ZIP) as z: z.extractall(TEST)
 client=TEST/'lib'/'mage-client-1.4.61.jar'
 if not client.is_file(): raise RuntimeError('Expected lib\\mage-client-1.4.61.jar missing after extraction.')
 runtime=TEST/'config'/'deck-downloader'
 if not runtime.is_dir(): raise RuntimeError('Deck Downloader runtime missing after extraction.')
 launchers=[]
 for pat in ('*.bat','*.cmd'):
  launchers += list(TEST.glob(pat))
 print('[OK] Isolated candidate extracted and verified.')
 print(f'[OK] Test folder: {TEST}')
 print(f'[OK] Patched client: {client}')
 print(f'[OK] Runtime: {runtime}')
 if launchers:
  print('[INFO] Root launchers found:')
  for p in launchers: print('       '+p.name)
 else:
  print('[WARN] No root BAT/CMD launcher found. Do NOT improvise a launch command yet.')
 print('\n=== GUI SMOKE PREPARATION PASSED ===')
 print('Nothing was copied into active XMage.')
 print('1.4.61V1 remains BLOCKED.')
 print('Next: inspect the isolated folder/launcher and launch ONLY this test copy.')
 return 0

if __name__=='__main__':
 try: raise SystemExit(main())
 except Exception as e:
  print(f'\nERROR: {e}')
  print('Active XMage was NOT modified. 1.4.61V1 remains BLOCKED.')
  input('Press Enter to close...')
  raise SystemExit(1)
