import urllib.request
url = 'https://freelance.habr.com/tasks'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req, timeout=10) as resp:
    html = resp.read().decode('utf-8', errors='ignore')
    print("Title:", html[html.find('<title>'):html.find('</title>')+8])
    print("Sample:", html[:600])
