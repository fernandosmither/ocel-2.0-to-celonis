<div align="center">
  <img src="ocelonis.png" alt="Ocelonis Logo" width="120" height="120">

  # Ocelonis

  **OCEL 2.0 to Celonis Uploader**

  Upload your OCEL 2.0 files to Celonis in seconds, not weeks.

  [🚀 **Use Now** → ocelonis.fdosmith.dev](https://ocelonis.fdosmith.dev)
</div>

---

## Why Ocelonis?

The original Python script for uploading [OCEL 2.0 files](https://www.ocel-standard.org/) to Celonis was deprecated, forcing researchers to use a [manual provisional procedure](https://ocel-standard.org/provisional_celonis_upload_procedure.pdf) that can take **weeks** for larger projects.

**Ocelonis solves this** by providing an automated, web-based solution that uploads your files in **seconds**.

## 🎯 Quick Start

**Simply visit**: [**ocelonis.fdosmith.dev**](https://ocelonis.fdosmith.dev)

1. Upload your `.jsonocel` file
2. Login to your Celonis account
3. Done! Your object types and events are created automatically 
>(TO-DO: support for uploading Objects, Events and relations)

No installation. No setup.

## 🛠️ Local Development

Want to run locally? Quick setup:

### Backend
```bash
cd backend
uv sync && source .venv/bin/activate
# Set environment variables (see backend/.env.template)
just dev
```

### Frontend
```bash
cd frontend
pnpm install && pnpm start
```

📖 **Detailed setup**: See [backend/README.md](backend/README.md) and [frontend/README.md](frontend/README.md)

## 🤝 Contributing

We welcome contributions! Please:
- 🐛 **Report issues** with detailed descriptions
- 🔧 **Submit PRs** following existing code patterns
- 📖 **Improve docs** where helpful

## 🏆 Credits

Created in collaboration with [**HapLab**](https://www.haplab.org/) to accelerate OCEL research and save researchers valuable time.

---

<div align="center">
  <strong>Stop waiting weeks. Start uploading in seconds.</strong>
  <br><br>
  <a href="https://ocelonis.fdosmith.dev">Try Ocelonis Now →</a>
</div>
