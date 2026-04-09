from flask import Flask, request, jsonify, Response
import mysql.connector
import requests
import time
from html.parser import HTMLParser

app = Flask(__name__)

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

def get_db_connection():
    retries = 5
    while retries > 0:
        try:
            conn = mysql.connector.connect(
                host="db",
                user="labuser",
                password="labpassword",
                database="ssrflab"
            )
            return conn
        except mysql.connector.Error as err:
            retries -= 1
            time.sleep(2)
    return None

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, password))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return jsonify({"message": "Login successful", "username": user['username']}), 200
    return jsonify({"error": "Invalid credentials"}), 401

@app.route('/api/posts', methods=['GET', 'POST'])
def manage_posts():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        data = request.json
        cursor.execute(
            "INSERT INTO posts (username, title, content, url) VALUES (%s, %s, %s, %s)",
            (data['username'], data['title'], data['content'], data.get('url', ''))
        )
        conn.commit()
        conn.close()
        return jsonify({"message": "Post created successfully"}), 201

    if request.method == 'GET':
        cursor.execute("SELECT * FROM posts ORDER BY id DESC")
        posts = cursor.fetchall()
        conn.close()
        return jsonify(posts), 200

@app.route('/api/preview', methods=['GET'])
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

        return jsonify({"title": title[:120], "description": description[:300], "image": image, "site_name": site_name, "domain": domain, "url": url, "content":resp.text})
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    
@app.route('/internal/admin')
def internal_admin():
    try:
        response = requests.get("http://admin-panel:8080/")
        return Response(response.content, status=response.status_code)
    except Exception as e:
        return str(e), 500

# @app.route('/api/preview', methods=['GET'])
# def preview_url():
#     url = request.args.get('url')
#     if not url:
#         return "URL is required", 400
    
#     # VULNERABILITY: Fetching external resources without validation
#     try:
#         response = requests.get(url, timeout=5)
#         # We return the raw content and headers so the iframe can render it as a webpage
#         return Response(
#             response.content, 
#             status=response.status_code, 
#             content_type=response.headers.get('Content-Type', 'text/html')
#         )
#     except Exception as e:
#         return str(e), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)