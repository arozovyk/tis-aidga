# TIS-AIDGA GUI

A TypeScript web GUI for the TIS-AIDGA driver generation tool.

## Prerequisites

- Node.js 18+
- The `tisaidga` Python CLI must be installed and available in PATH
- `OPENAI_API_KEY` environment variable set (for OpenAI models)

## Installation

```bash
cd gui
npm install
```

## Running

Start both the backend server and frontend dev server:

```bash
npm run dev
```

This will start:
- Backend API server on http://localhost:3001
- Frontend dev server on http://localhost:5173

Open http://localhost:5173 in your browser.

## Usage

1. **Initialize a Project**:
   - Enter the path to your `compile_commands.json` file
   - Optionally specify a project name
   - Click "Init Project"

2. **Select Target**:
   - Choose a project from the dropdown
   - Select a source file
   - Click on a function from the list

3. **Generate Driver**:
   - Choose model (gpt-4o-mini is default and cheapest)
   - Set max iterations (refinement attempts)
   - Click "Generate Driver"

4. **View Progress**:
   - Watch the progress panel for current status
   - See detailed logs at the bottom
   - Generated driver code appears in the main panel

## Architecture

```
gui/
├── server/           # Express backend
│   └── index.ts      # API endpoints that shell to Python CLI
├── src/              # React frontend
│   ├── App.tsx       # Main application component
│   ├── styles.css    # Application styles
│   └── main.tsx      # Entry point
├── package.json
└── vite.config.ts
```

## API Endpoints

- `POST /api/init` - Initialize project from compile_commands.json
- `GET /api/projects` - List all projects
- `GET /api/projects/:project/files` - List files in a project
- `GET /api/projects/:project/files/:filename/functions` - Get functions from a file
- `GET /api/generate` - Generate driver (SSE stream)
- `GET /api/driver/:filename` - Read generated driver file
