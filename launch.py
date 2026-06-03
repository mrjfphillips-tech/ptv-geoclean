"""
GeoClean Launcher — avoids Windows Firewall prompts by running
Streamlit in-process rather than spawning a new python.exe subprocess.
"""
import os
import sys
import time
import threading
import webbrowser

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Set Streamlit config via environment before importing streamlit
os.environ['STREAMLIT_SERVER_ADDRESS'] = '127.0.0.1'
os.environ['STREAMLIT_SERVER_PORT'] = '8501'
os.environ['STREAMLIT_SERVER_HEADLESS'] = 'true'
os.environ['STREAMLIT_BROWSER_GATHER_USAGE_STATS'] = 'false'
os.environ['STREAMLIT_SERVER_ENABLE_CORS'] = 'false'
os.environ['STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION'] = 'false'

# Open browser after a short delay
def open_browser():
    time.sleep(4)
    webbrowser.open('http://127.0.0.1:8501')

threading.Thread(target=open_browser, daemon=True).start()

# Run Streamlit in-process (no subprocess = no new firewall check)
from streamlit.web import cli as stcli

sys.argv = [
    'streamlit', 'run', 'app.py',
    '--server.address', '127.0.0.1',
    '--server.port', '8501',
    '--server.headless', 'true',
    '--server.enableCORS', 'false',
    '--server.enableXsrfProtection', 'false',
    '--browser.gatherUsageStats', 'false',
]
stcli.main()
