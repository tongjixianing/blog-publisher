# Blog Publisher

A lightweight, multi-site blog publisher with a rich text editor. Runs locally in your browser — no extra dependencies beyond Python 3.

## Features

- 📝 WYSIWYG rich text editor (bold, italic, headings, lists, code blocks)
- 📷 Insert images — drag & drop or file picker, auto-extracted to static assets
- 🌐 Multi-site support — auto-detects Next.js website projects in your workspace
- 🚀 One-click publish — saves, builds, commits, and pushes to deploy
- 💾 Save drafts without publishing
- 📂 Load and edit existing posts

## How It Works

1. Scans your project folder for Next.js sites with `content/blog/`
2. Opens a rich text editor in your browser at `http://localhost:4444`
3. Select which site to publish to
4. Write your post with formatting and images
5. Click Publish → builds, commits, pushes → Vercel auto-deploys

## Requirements

- Python 3.6+
- Node.js & npm (for building the website)
- Git (for committing and pushing)
- A browser

No pip packages needed. Zero dependencies.

## Usage

```bash
python3 blog-publisher.py
```

The app opens in your browser automatically.

## Site Detection

The publisher auto-detects websites by scanning the parent directory for folders that contain:
- `next.config.ts` (or `.js`/`.mjs`) — confirms it's a Next.js project
- `content/blog/` directory — confirms it has a blog

## Project Structure Expected

```
your-workspace/
├── blog-publisher/          ← this tool
├── personal-website/        ← auto-detected
│   ├── next.config.ts
│   └── content/blog/
├── another-website/         ← auto-detected
│   ├── next.config.ts
│   └── content/blog/
└── some-other-project/      ← ignored (no blog)
```

## License

MIT
