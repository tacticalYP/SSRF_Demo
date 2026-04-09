from flask import Flask, request, jsonify, Response, send_from_directory
import requests
import os
from html.parser import HTMLParser

app = Flask(__name__)

USERS = [
    {"id": 1, "username": "admin", "password": "admin123", "role": "admin"},
    {"id": 2, "username": "alice", "password": "alice123", "role": "user"},
    {"id": 3, "username": "bob",   "password": "bob123",   "role": "user"},
]
POSTS = []

class OGParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.og = {}
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta":
            prop = attrs.get("property", attrs.get("name", ""))
            content = attrs.get("content", "")
            candidates = ("og:title","og:description","og:image","og:site_name","twitter:title","twitter:description","twitter:image")
            if prop in candidates:
                key = prop.replace("twitter:", "og:") if prop.startswith("twitter:") else prop
                if key not in self.og:
                    self.og[key] = content
        if tag == "title":
            self._in_title = True

    def handle_data(self, data):
        if self._in_title:
            self.title += data

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False


@app.route('/app')
def frontend():
    return send_from_directory(os.path.dirname(__file__), 'index.html')

# @app.route('/api/login', methods=['POST'])
# def login():
#     data = request.json
#     user = next((u for u in USERS if u['username'] == data.get('username') and u['password'] == data.get('password')), None)
#     if user:
#         return jsonify({"message": "Login successful", "username": user['username']}), 200
#     return jsonify({"error": "Invalid credentials"}), 401

@app.route('/api/login', methods=['POST'])
def login():
    # Ignore what the user types and always return success as admin
    return jsonify({"message": "Login successful", "username": "admin"}), 200

@app.route('/api/posts', methods=['GET', 'POST'])
def manage_posts():
    if request.method == 'POST':
        data = request.json
        post = {"id": len(POSTS)+1, "username": data.get('username','anon'), "title": data['title'], "content": data['content'], "url": data.get('url','')}
        POSTS.append(post)
        return jsonify({"message": "Post created successfully"}), 201
    return jsonify(list(reversed(POSTS))), 200

@app.route('/api/og-preview', methods=['GET'])
def og_preview():
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "URL required"}), 400
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; SSRFDemoBot/1.0)"}
        resp = requests.get(url, timeout=6, headers=headers, allow_redirects=True)
        parser = OGParser()
        parser.feed(resp.text[:50000])

        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc or url

        title = parser.og.get("og:title") or parser.title.strip() or url
        description = parser.og.get("og:description", "")
        image = parser.og.get("og:image", "")
        site_name = parser.og.get("og:site_name", "") or domain

        return jsonify({"title": title[:120], "description": description[:300], "image": image, "site_name": site_name, "domain": domain, "url": url,"content":resp.text})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/preview', methods=['GET'])
def preview_url():
    url = request.args.get('url')
    if not url:
        return "URL is required", 400
    try:
        resp = requests.get(url, timeout=5)
        return Response(resp.content, status=resp.status_code, content_type=resp.headers.get('Content-Type', 'text/html'))
    except Exception as e:
        return str(e), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)