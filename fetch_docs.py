import urllib.request, re, html

url = 'https://source.coop/ftw/global-data'
resp = urllib.request.urlopen(url).read().decode('utf-8')

# Extract the rendered README div hidden id="S:9"
m = re.search(r'<div hidden id="S:9">(.*?)</div>\s*<script>', resp, re.DOTALL)
if m:
    text = m.group(1)
    # Strip HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)
    text = html.unescape(text)
    # Clean up extra whitespace
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines:
        print(line)
else:
    print('Div S:9 not found')

