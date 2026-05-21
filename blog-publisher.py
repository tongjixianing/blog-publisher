#!/usr/bin/env python3
"""Blog Publisher — Multi-site web app with rich text editor."""

import http.server
import json
import os
import re
import subprocess
import base64
from datetime import date
from urllib.parse import parse_qs, urlparse
import webbrowser

# Auto-detect website projects in the parent folder
# Looks for directories containing a next.config.ts/js and content/blog/
PROJECTS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def detect_sites():
    """Scan parent folder for Next.js website projects with a blog."""
    sites = []
    if not os.path.isdir(PROJECTS_ROOT):
        return sites
    for name in sorted(os.listdir(PROJECTS_ROOT)):
        project_path = os.path.join(PROJECTS_ROOT, name)
        if not os.path.isdir(project_path):
            continue
        # Detect Next.js project with blog content
        has_next = os.path.exists(os.path.join(project_path, "next.config.ts")) or \
                   os.path.exists(os.path.join(project_path, "next.config.js")) or \
                   os.path.exists(os.path.join(project_path, "next.config.mjs"))
        has_blog = os.path.isdir(os.path.join(project_path, "content", "blog"))
        if has_next and has_blog:
            # Try to get git remote for repo info
            repo = ""
            try:
                result = subprocess.run(['git', 'remote', 'get-url', 'origin'],
                                        cwd=project_path, capture_output=True, text=True)
                if result.returncode == 0:
                    url = result.stdout.strip()
                    # Extract user/repo from https or ssh URL
                    m = re.search(r'github\.com[:/](.+?)(?:\.git)?$', url)
                    if m:
                        repo = m.group(1)
            except Exception:
                pass
            sites.append({
                "id": name,
                "name": name.replace('-', ' ').title(),
                "path": project_path,
                "repo": repo
            })
    return sites

PORT = 4444

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Blog Publisher</title>
  <link href="https://cdn.quilljs.com/1.3.7/quill.snow.css" rel="stylesheet">
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { background: #0a0a1a; color: #e0e0e0; font-family: 'Segoe UI', system-ui, sans-serif; }
    .container { max-width: 900px; margin: 0 auto; padding: 20px; }
    h1 { color: #0ff; font-size: 24px; margin-bottom: 20px; }
    .form-group { margin-bottom: 15px; }
    label { display: block; color: #888; font-size: 12px; text-transform: uppercase; margin-bottom: 5px; }
    input[type="text"], input[type="date"], select {
      width: 100%; padding: 10px 12px; background: #12121a; border: 1px solid #333;
      border-radius: 6px; color: #fff; font-size: 14px; outline: none;
    }
    input:focus, select:focus { border-color: #0ff; }
    select option { background: #12121a; color: #fff; }
    .row { display: flex; gap: 15px; }
    .row .form-group { flex: 1; }
    .site-selector { background: #1a1a2e; border: 1px solid #333; border-radius: 8px; padding: 15px; margin-bottom: 20px; }
    .site-selector label { color: #0ff; font-size: 13px; }
    .site-info { font-size: 12px; color: #666; margin-top: 5px; font-family: monospace; }
    .editor-container { margin: 15px 0; border-radius: 8px; overflow: hidden; border: 1px solid #333; }
    .ql-toolbar.ql-snow { background: #1a1a2e; border: none; border-bottom: 1px solid #333; }
    .ql-container.ql-snow { background: #12121a; border: none; min-height: 350px; font-size: 14px; color: #e0e0e0; }
    .ql-editor { min-height: 350px; }
    .ql-editor img { max-width: 100%; border-radius: 8px; margin: 10px 0; }
    .ql-snow .ql-stroke { stroke: #888; }
    .ql-snow .ql-fill { fill: #888; }
    .ql-snow .ql-picker-label { color: #888; }
    .ql-snow .ql-picker-options { background: #1a1a2e; border-color: #333; }
    .btn-row { display: flex; gap: 10px; margin-top: 15px; }
    button {
      padding: 10px 20px; border: none; border-radius: 6px; font-size: 14px;
      cursor: pointer; font-weight: 600; transition: all 0.2s;
    }
    .btn-publish { background: #0ff; color: #0a0a0f; margin-left: auto; }
    .btn-publish:hover { background: #00ccaa; }
    .btn-draft { background: #333; color: #fff; }
    .btn-draft:hover { background: #444; }
    .btn-load { background: #333; color: #fff; }
    .btn-load:hover { background: #444; }
    .status { margin-top: 15px; padding: 10px; border-radius: 6px; font-size: 13px; font-family: monospace; display: none; }
    .status.show { display: block; }
    .status.success { background: #0f2f0f; color: #4ade80; border: 1px solid #22c55e33; }
    .status.error { background: #2f0f0f; color: #f87171; border: 1px solid #ef444433; }
    .status.info { background: #0f0f2f; color: #60a5fa; border: 1px solid #3b82f633; }
    .image-btn { background: #1a1a2e; color: #0ff; border: 1px solid #0ff; padding: 6px 12px; font-size: 12px; border-radius: 4px; margin-bottom: 10px; }
    .image-btn:hover { background: #0ff; color: #0a0a0f; }
  </style>
</head>
<body>
  <div class="container">
    <h1>📝 Blog Publisher</h1>

    <div class="site-selector">
      <label>Publish To</label>
      <select id="site" onchange="updateSiteInfo()">
        SITE_OPTIONS
      </select>
      <div class="site-info" id="siteInfo"></div>
    </div>

    <div class="form-group">
      <label>Title</label>
      <input type="text" id="title" placeholder="My Awesome Blog Post">
    </div>

    <div class="form-group">
      <label>Excerpt</label>
      <input type="text" id="excerpt" placeholder="A short description for the listing page">
    </div>

    <div class="row">
      <div class="form-group">
        <label>Tags (comma-separated)</label>
        <input type="text" id="tags" placeholder="AI, Spark, Migration">
      </div>
      <div class="form-group" style="max-width:180px">
        <label>Date</label>
        <input type="date" id="date" value="">
      </div>
    </div>

    <label>Content</label>
    <button class="image-btn" onclick="insertImage()">📷 Insert Image</button>
    <div class="editor-container">
      <div id="editor"></div>
    </div>

    <div class="btn-row">
      <button class="btn-load" onclick="loadPost()">📂 Load Existing</button>
      <button class="btn-draft" onclick="saveDraft()">💾 Save Draft</button>
      <button class="btn-publish" onclick="publish()">🚀 Publish</button>
    </div>

    <div class="status" id="status"></div>
  </div>

  <input type="file" id="imageInput" accept="image/*" style="display:none" onchange="handleImage(event)">
  <input type="file" id="loadInput" accept=".mdx,.md" style="display:none" onchange="handleLoad(event)">

  <script src="https://cdn.quilljs.com/1.3.7/quill.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/turndown@7.1.2/dist/turndown.js"></script>
  <script>
    const sites = SITES_JSON;

    const quill = new Quill('#editor', {
      theme: 'snow',
      modules: {
        toolbar: [
          [{ header: [1, 2, 3, false] }],
          ['bold', 'italic', 'underline', 'strike'],
          ['blockquote', 'code-block'],
          [{ list: 'ordered' }, { list: 'bullet' }],
          ['link', 'image'],
          ['clean']
        ]
      },
      placeholder: 'Write your blog post here...'
    });

    document.getElementById('date').value = new Date().toISOString().split('T')[0];
    updateSiteInfo();

    function updateSiteInfo() {
      const site = sites.find(s => s.id === document.getElementById('site').value);
      if (site) {
        document.getElementById('siteInfo').textContent = site.path + '  →  github.com/' + site.repo;
      }
    }

    function showStatus(msg, type) {
      const el = document.getElementById('status');
      el.textContent = msg;
      el.className = 'status show ' + type;
    }

    function insertImage() { document.getElementById('imageInput').click(); }

    function handleImage(event) {
      const file = event.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = function(e) {
        const range = quill.getSelection(true);
        quill.insertEmbed(range.index, 'image', e.target.result);
        quill.setSelection(range.index + 1);
      };
      reader.readAsDataURL(file);
      event.target.value = '';
    }

    function getSlug() {
      return document.getElementById('title').value
        .toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
    }

    function getMarkdown() {
      const turndownService = new TurndownService({ headingStyle: 'atx', codeBlockStyle: 'fenced' });
      return turndownService.turndown(quill.root.innerHTML);
    }

    function getPayload() {
      return {
        site: document.getElementById('site').value,
        title: document.getElementById('title').value,
        slug: getSlug(),
        excerpt: document.getElementById('excerpt').value,
        tags: document.getElementById('tags').value,
        date: document.getElementById('date').value,
        content: getMarkdown(),
        html: quill.root.innerHTML
      };
    }

    async function saveDraft() {
      if (!document.getElementById('title').value) { showStatus('Please enter a title', 'error'); return; }
      showStatus('Saving draft...', 'info');
      const resp = await fetch('/api/save', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(getPayload()) });
      const data = await resp.json();
      showStatus(data.message, data.success ? 'success' : 'error');
    }

    async function publish() {
      if (!document.getElementById('title').value) { showStatus('Please enter a title', 'error'); return; }
      const site = sites.find(s => s.id === document.getElementById('site').value);
      if (!confirm('Publish to ' + site.name + '?\\n\\nThis will save, build, commit, and push.')) return;
      showStatus('Publishing to ' + site.name + '...', 'info');
      const resp = await fetch('/api/publish', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(getPayload()) });
      const data = await resp.json();
      showStatus(data.message, data.success ? 'success' : 'error');
    }

    function loadPost() { document.getElementById('loadInput').click(); }

    function handleLoad(event) {
      const file = event.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = function(e) {
        const raw = e.target.result;
        const match = raw.match(/^---[\\r\\n]+([\\s\\S]*?)[\\r\\n]+---[\\r\\n]+([\\s\\S]*)/);
        if (match) {
          const [, frontmatter, content] = match;
          frontmatter.split(/\\r?\\n/).forEach(line => {
            if (line.startsWith('title:')) document.getElementById('title').value = line.split(':').slice(1).join(':').trim().replace(/"/g, '');
            if (line.startsWith('excerpt:')) document.getElementById('excerpt').value = line.split(':').slice(1).join(':').trim().replace(/"/g, '');
            if (line.startsWith('date:')) document.getElementById('date').value = line.split(':').slice(1).join(':').trim().replace(/"/g, '');
            if (line.startsWith('tags:')) document.getElementById('tags').value = (line.match(/"([^"]+)"/g) || []).map(t => t.replace(/"/g, '')).join(', ');
          });
          quill.root.innerHTML = content.replace(/^#\\s+.+\\n?/, '');
        }
        showStatus('Loaded: ' + file.name, 'success');
      };
      reader.readAsText(file);
      event.target.value = '';
    }
  </script>
</body>
</html>"""


def get_site_by_id(site_id):
    return next((s for s in detect_sites() if s['id'] == site_id), None)


class BlogHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            sites = detect_sites()
            options = ''.join(f'<option value="{s["id"]}">{s["name"]} ({s["id"]})</option>' for s in sites)
            html = HTML.replace('SITE_OPTIONS', options).replace('SITES_JSON', json.dumps(sites))
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(html.encode())
        elif self.path == '/api/sites':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(detect_sites()).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        body = json.loads(self.rfile.read(content_length))

        if self.path == '/api/save':
            result = self.save_post(body)
        elif self.path == '/api/publish':
            result = self.publish_post(body)
        else:
            result = {'success': False, 'message': 'Unknown endpoint'}

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())

    def save_post(self, data):
        try:
            site = get_site_by_id(data['site'])
            if not site:
                return {'success': False, 'message': f'❌ Unknown site: {data["site"]}'}

            project_dir = site['path']
            blog_dir = os.path.join(project_dir, "content", "blog")
            public_blog_dir = os.path.join(project_dir, "public", "blog")
            slug = data['slug']

            os.makedirs(blog_dir, exist_ok=True)
            os.makedirs(public_blog_dir, exist_ok=True)

            # Extract base64 images
            content = data['content']
            img_count = 0

            def replace_image(match):
                nonlocal img_count
                img_count += 1
                alt = match.group(1)
                ext = match.group(3).replace('jpeg', 'jpg')
                img_data = match.group(4)
                filename = f"{slug}-img{img_count}.{ext}"
                filepath = os.path.join(public_blog_dir, filename)
                with open(filepath, 'wb') as f:
                    f.write(base64.b64decode(img_data))
                return f'![{alt}](/blog/{filename})'

            content = re.sub(r'!\[([^\]]*)\]\((data:image/([^;]+);base64,([^)]+))\)', replace_image, content)

            def replace_html_img(match):
                nonlocal img_count
                img_count += 1
                src = match.group(1)
                ext_match = re.match(r'data:image/([^;]+);base64,(.*)', src)
                if ext_match:
                    ext = ext_match.group(1).replace('jpeg', 'jpg')
                    img_data = ext_match.group(2)
                    filename = f"{slug}-img{img_count}.{ext}"
                    filepath = os.path.join(public_blog_dir, filename)
                    with open(filepath, 'wb') as f:
                        f.write(base64.b64decode(img_data))
                    return f'![image](/blog/{filename})'
                return match.group(0)

            content = re.sub(r'<img[^>]*src="(data:image/[^"]+)"[^>]*/?>',  replace_html_img, content)

            # Build MDX
            tags = [t.strip() for t in data['tags'].split(',') if t.strip()]
            tags_yaml = ', '.join(f'"{t}"' for t in tags)

            mdx = f"""---
title: "{data['title']}"
date: "{data['date']}"
excerpt: "{data['excerpt']}"
tags: [{tags_yaml}]
---

# {data['title']}

{content}
"""
            filepath = os.path.join(blog_dir, f"{slug}.mdx")
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(mdx)

            return {'success': True, 'message': f'✅ Saved to {site["name"]}: content/blog/{slug}.mdx ({img_count} images)'}
        except Exception as e:
            return {'success': False, 'message': f'❌ Error: {str(e)}'}

    def publish_post(self, data):
        result = self.save_post(data)
        if not result['success']:
            return result

        site = get_site_by_id(data['site'])
        project_dir = site['path']

        try:
            # Build
            proc = subprocess.run(['npm', 'run', 'build'], cwd=project_dir,
                                  capture_output=True, text=True, shell=(os.name == 'nt'))
            if proc.returncode != 0:
                return {'success': False, 'message': f'❌ Build failed: {proc.stderr[:200]}'}

            # Git commit & push
            subprocess.run(['git', 'add', '-A'], cwd=project_dir, check=True)
            subprocess.run(['git', 'commit', '-m', f"Add blog post: {data['title']}"],
                           cwd=project_dir, check=True)
            proc = subprocess.run(['git', 'push'], cwd=project_dir, capture_output=True, text=True)
            if proc.returncode != 0:
                return {'success': False, 'message': f'❌ Push failed: {proc.stderr[:200]}'}

            return {'success': True, 'message': f"🚀 Published to {site['name']}! /blog/{data['slug']} — Vercel deploying..."}
        except Exception as e:
            return {'success': False, 'message': f'❌ Error: {str(e)}'}


if __name__ == '__main__':
    sites = detect_sites()
    print("📝 Blog Publisher — Multi-Site (Auto-Detect)")
    print(f"   Scanning: {PROJECTS_ROOT}")
    print(f"   Sites found:")
    if sites:
        for s in sites:
            print(f"   • {s['name']} → {s['path']} (repo: {s['repo'] or 'unknown'})")
    else:
        print("   ⚠️  No sites found. Make sure projects have next.config.ts and content/blog/")
    print(f"\n🚀 Running at http://localhost:{PORT}")
    print("   Press Ctrl+C to stop\n")

    server = http.server.HTTPServer(('127.0.0.1', PORT), BlogHandler)
    webbrowser.open(f'http://localhost:{PORT}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Stopped.")
        server.shutdown()
