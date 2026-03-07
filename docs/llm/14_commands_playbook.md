# 14. Commands Playbook (PowerShell, Windows)

Authoritative, copy-paste ready commands for our development workflow. Shell: PowerShell (pwsh.exe). For broader context on features, see ARCHITECTURE.md → “What’s where?” and cross-links inside 13. API Reference.

Note: Always activate the venv in terminal sessions:

```powershell
& C:/noc_project/UNOC/unoc/.venv/Scripts/Activate.ps1
```

## Run tests

- Full suite (SQLite test DB):

```powershell
${env:PYTHONIOENCODING} = 'utf-8'; C:/noc_project/UNOC/unoc/.venv/Scripts/python.exe -m pytest -q
```

- Single file:

```powershell
C:/noc_project/UNOC/unoc/.venv/Scripts/python.exe -m pytest -q backend/tests/test_traffic_engine_v2.py
```

- Single test:

```powershell
C:/noc_project/UNOC/unoc/.venv/Scripts/python.exe -m pytest -q backend/tests/test_traffic_engine_v2.py::test_end_to_end_aggregation_on_devices_and_links
```

## Performance harness (pytest -m perf)

- Small scale with profiling and tagged output directory:

```powershell
${env:UNOC_PERF_PROFILE} = '1'; ${env:PERF_SCALE} = 'small'; ${env:UNOC_PERF_OUTDIR} = 'perf_reports'; ${env:UNOC_PERF_TAG} = 'before'; C:/noc_project/UNOC/unoc/.venv/Scripts/python.exe -m pytest -q -m perf backend/tests/perf/test_large_scale.py
```

- Verify pyinstrument availability:

```powershell
C:/noc_project/UNOC/unoc/.venv/Scripts/python.exe - <<'PY'
import importlib.util, sys
print('python:', sys.executable)
print('pyinstrument found:', bool(importlib.util.find_spec('pyinstrument')))
PY
```

## Kill stuck dev servers (uvicorn/watchfiles)

```powershell
$procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'run.py|uvicorn|watchfiles' };
$cnt = ($procs | Measure-Object).Count;
if($cnt -gt 0){ $procs | ForEach-Object { try { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue } catch {} } };
Write-Output ("Stopped {0} processes" -f $cnt)
```

## Inline Python from PowerShell (robust)

Piping a here-string to python.exe is brittle. Prefer writing to a temp file and executing it:

```powershell
$py = 'C:/noc_project/UNOC/unoc/.venv/Scripts/python.exe'
$tmp = New-TemporaryFile; Set-Content -LiteralPath $tmp -Encoding UTF8 @'
import asyncio
from httpx import AsyncClient
from backend.main import app

async def main():
    async with AsyncClient(app=app, base_url='http://test') as client:
        r = await client.get('/api/health')
        print('health:', r.status_code)

asyncio.run(main())
'@
& $py $tmp; Remove-Item $tmp -Force
```

## Start backend (task)

Use VS Code tasks (recommended):

- backend: run
- backend: run (no reload)
- backend: run inmemory (no reload)

Or run directly:

```powershell
${env:UNOC_ASYNC_MODE} = 'threading'; ${env:UNOC_PORT} = '5001'; ${env:UNOC_DEV_FEATURES} = '1'; ${env:AUTO_ASSIGN_DEFAULT_HARDWARE} = '1'; C:/noc_project/UNOC/unoc/.venv/Scripts/python.exe run.py
```

## Lint/format

```powershell
C:/noc_project/UNOC/unoc/.venv/Scripts/python.exe -m ruff check .
C:/noc_project/UNOC/unoc/.venv/Scripts/python.exe -m isort .
C:/noc_project/UNOC/unoc/.venv/Scripts/python.exe -m black .
```

## Generate TS types

```powershell
C:/noc_project/UNOC/unoc/.venv/Scripts/python.exe tools/gen_ts_types.py
```

## Frontend build

```powershell
cd C:/noc_project/UNOC/unoc/unoc-frontend-v2; npm run -s build
```

## Curl-like requests using Python inline (temp-file pattern)

Example: create OLT+ODF, PON port, and link via httpx client bound to FastAPI app (no network):

```powershell
$py = 'C:/noc_project/UNOC/unoc/.venv/Scripts/python.exe'
$tmp = New-TemporaryFile; Set-Content -LiteralPath $tmp -Encoding UTF8 @'
import asyncio
from httpx import AsyncClient
from backend.main import app

async def main():
    async with AsyncClient(app=app, base_url='http://test') as client:
        await client.post('/api/devices', json={'id':'olt1','name':'olt1','type':'OLT','status':'UP'})
        await client.post('/api/devices', json={'id':'odf1','name':'odf1','type':'ODF','status':'UP'})
        r = await client.post('/api/devices/olt1/interfaces', json={'name':'pon0','port_role':'PON'})
        print('create pon0:', r.status_code, r.text)
        r2 = await client.post('/api/links', json={'id':'odf1__olt1','a_interface_id':'olt1-if0','b_interface_id':'odf1-if0','status':'UP'})
        print('create link:', r2.status_code, r2.text)

asyncio.run(main())
'@
& $py $tmp; Remove-Item $tmp -Force
```

Tip: prefer this temp-file approach for any non-trivial inline script. It avoids quoting/escaping pitfalls with here-strings and stdin piping.

## Deterministic L3 setup (VRF, address, default route)

The snippet below sets up a minimal L3 environment using the in-process FastAPI app via httpx.AsyncClient:

- Creates a device edge1 (ROUTER)
- Creates an interface if0 and assigns IPv4 192.0.2.2/30
- Creates a VRF named "default" and uses its id to create resources
- Creates a default route 0.0.0.0/0 via next-hop 192.0.2.1 on edge1-if0

It exercises API validations documented in 13. API Reference → "Default Route Validations".

```powershell
$py = 'C:/noc_project/UNOC/unoc/.venv/Scripts/python.exe'
$tmp = New-TemporaryFile; Set-Content -LiteralPath $tmp -Encoding UTF8 @'
import asyncio
from httpx import AsyncClient
from backend.main import app

async def main():
    async with AsyncClient(app=app, base_url='http://test') as client:
        # Create device
        r = await client.post('/api/devices', json={'id':'edge1','name':'edge1','type':'ROUTER','status':'UP'})
        print('create device:', r.status_code, r.json() if r.status_code==201 else r.text)

        # Create interface and assign address
        r = await client.post('/api/devices/edge1/interfaces', json={'name':'if0','port_role':'ROUTER_PORT'})
        print('create if0:', r.status_code)
        if_id = r.json().get('id') if r.status_code == 201 else 'edge1-if0'

        # Create a VRF and seed a /30 prefix within it
        r = await client.post('/api/ipam/vrfs', json={'name': 'default'})
        assert r.status_code == 201, r.text
        vrf = r.json()
        vrf_id = vrf['id']
        print('create vrf:', r.status_code, vrf_id)

        r = await client.post('/api/ipam/prefixes', json={'vrf_id': vrf_id, 'prefix':'192.0.2.0/30'})
        print('seed /30 prefix:', r.status_code)

        # Assign interface address
        r = await client.post(f'/api/interfaces/{if_id}/addresses', json={'ip':'192.0.2.2','prefix_len':30})
        print('assign address:', r.status_code, r.text)

        # Create default route in that VRF (validations require next_hop + interface_id)
        r = await client.post(f'/api/devices/edge1/routing/vrfs/{vrf_id}/routes', json={'prefix':'0.0.0.0/0','next_hop':'192.0.2.1','interface_id': if_id})
        print('create default route:', r.status_code, r.json() if r.status_code==201 else r.text)

asyncio.run(main())
'@
& $py $tmp; Remove-Item $tmp -Force
```

Notes

- Errors are returned with HTTP 400 and English detail messages for validation failures, e.g., "Default route requires next_hop" or "Interface does not belong to device".
- For deterministic status tests that depend on L3 reachability, set these env vars before starting the backend or running tests:

```powershell
${env:UNOC_L3_STATUS_STRICT} = '1'
${env:WS_SEND_HELLO_ON_CONNECT} = '1'
```
