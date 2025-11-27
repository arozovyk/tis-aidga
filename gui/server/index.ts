import express from 'express';
import cors from 'cors';
import { spawn, execSync } from 'child_process';
import path from 'path';
import fs from 'fs';
import { randomUUID } from 'crypto';

const app = express();
const PORT = 3001;

app.use(cors());
app.use(express.json());

// Get the parent directory where tisaidga is installed
const PROJECT_ROOT = path.resolve(process.cwd(), '..');

// Simple file upload handling (for compile_commands.json)
app.post('/api/upload-compile-db', express.raw({ type: 'multipart/form-data', limit: '10mb' }), (req, res) => {
  // Parse multipart form data manually (simple approach)
  const boundary = req.headers['content-type']?.split('boundary=')[1];
  if (!boundary) {
    return res.status(400).json({ error: 'No boundary found' });
  }

  const body = req.body.toString();
  const parts = body.split(`--${boundary}`);

  for (const part of parts) {
    if (part.includes('filename=')) {
      // Extract filename
      const filenameMatch = part.match(/filename="([^"]+)"/);
      const filename = filenameMatch ? filenameMatch[1] : 'compile_commands.json';

      // Extract content (after double newline)
      const contentStart = part.indexOf('\r\n\r\n');
      if (contentStart === -1) continue;

      let content = part.slice(contentStart + 4);
      // Remove trailing boundary markers
      content = content.replace(/\r\n--$/, '').replace(/--\r\n$/, '').trim();

      // Save to temp location
      const uploadDir = path.join(PROJECT_ROOT, '.tisaidga', 'uploads');
      if (!fs.existsSync(uploadDir)) {
        fs.mkdirSync(uploadDir, { recursive: true });
      }

      const savedPath = path.join(uploadDir, `${randomUUID()}_${filename}`);
      fs.writeFileSync(savedPath, content);

      return res.json({ path: savedPath, filename });
    }
  }

  res.status(400).json({ error: 'No file found in request' });
});

// Local source root mapping (set via env var if remote paths differ from local)
// e.g., LOCAL_SOURCE_ROOT=/Users/artemiyrozovyk/work maps /home/arozovyk/work/... to local
const LOCAL_SOURCE_ROOT = process.env.LOCAL_SOURCE_ROOT || '';

// Try to resolve a remote path to a local path
function resolveSourcePath(remotePath: string, filename: string): string | null {
  // 1. Try the path as-is (works if local)
  if (fs.existsSync(remotePath)) {
    return remotePath;
  }

  // 2. Try with LOCAL_SOURCE_ROOT mapping
  if (LOCAL_SOURCE_ROOT) {
    // Extract relative path from common patterns like /home/user/work/project/file.c
    const workMatch = remotePath.match(/\/work\/(.+)$/);
    if (workMatch) {
      const localPath = path.join(LOCAL_SOURCE_ROOT, workMatch[1]);
      if (fs.existsSync(localPath)) {
        return localPath;
      }
    }
  }

  // 3. Try to find by filename in PROJECT_ROOT
  const searchPaths = [
    path.join(PROJECT_ROOT, filename),
    path.join(PROJECT_ROOT, 'src', filename),
  ];

  for (const searchPath of searchPaths) {
    if (fs.existsSync(searchPath)) {
      return searchPath;
    }
  }

  // 4. Try recursive search in PROJECT_ROOT (limited depth)
  try {
    const findResult = execSync(
      `find "${PROJECT_ROOT}" -maxdepth 5 -name "${filename}" -type f 2>/dev/null | head -1`,
      { encoding: 'utf-8' }
    ).trim();
    if (findResult && fs.existsSync(findResult)) {
      return findResult;
    }
  } catch {
    // ignore find errors
  }

  return null;
}

interface Project {
  name: string;
  fileCount: number;
  remoteDir: string;
}

interface FileInfo {
  name: string;
  path: string;
}

// Initialize project from compile_commands.json
app.post('/api/init', async (req, res) => {
  const { compilationDbPath, projectName } = req.body;

  if (!compilationDbPath) {
    return res.status(400).json({ error: 'compilationDbPath is required' });
  }

  try {
    const args = ['init', compilationDbPath];
    if (projectName) {
      args.push('--name', projectName);
    }
    args.push('-v');

    const result = execSync(`tisaidga ${args.join(' ')}`, {
      cwd: PROJECT_ROOT,
      encoding: 'utf-8',
    });

    res.json({ success: true, output: result });
  } catch (error: any) {
    res.status(500).json({ error: error.message, stderr: error.stderr });
  }
});

// List all projects
app.get('/api/projects', (req, res) => {
  try {
    const result = execSync('tisaidga list', {
      cwd: PROJECT_ROOT,
      encoding: 'utf-8',
    });

    // Parse the output to extract project names
    const projects: Project[] = [];
    const lines = result.split('\n');

    for (const line of lines) {
      // Match lines like "  project-name (N files)"
      const match = line.match(/^\s+(\S+)\s+\((\d+)\s+files?\)/);
      if (match) {
        projects.push({
          name: match[1],
          fileCount: parseInt(match[2]),
          remoteDir: '',
        });
      }
    }

    res.json({ projects });
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

// List files in a project
app.get('/api/projects/:project/files', (req, res) => {
  const { project } = req.params;

  try {
    const result = execSync(`tisaidga list ${project} -v`, {
      cwd: PROJECT_ROOT,
      encoding: 'utf-8',
    });

    // Parse output to get files
    // Format: "  filename.c" (2 spaces indent)
    const files: FileInfo[] = [];
    const lines = result.split('\n');

    for (const line of lines) {
      // Match lines like "  filename.c" (2 spaces + filename ending in .c)
      const match = line.match(/^  (\S+\.c)\s*$/);
      if (match) {
        files.push({
          name: match[1],
          path: match[1],
        });
      }
    }

    res.json({ files });
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

// Get functions from a file (extract from source)
app.get('/api/projects/:project/files/:filename/functions', async (req, res) => {
  const { project, filename } = req.params;

  try {
    // Read the project config to get file path
    const projectDir = path.join(PROJECT_ROOT, '.tisaidga', 'projects', project);
    const fileInfoPath = path.join(projectDir, 'files', `${filename}.json`);

    if (!fs.existsSync(fileInfoPath)) {
      return res.status(404).json({ error: 'File not found in project' });
    }

    const fileInfo = JSON.parse(fs.readFileSync(fileInfoPath, 'utf-8'));
    const remotePath = fileInfo.path;

    // Try to resolve the remote path to a local path
    const sourcePath = resolveSourcePath(remotePath, filename);

    if (!sourcePath) {
      return res.status(404).json({
        error: `Source file not found locally. Remote path: ${remotePath}. Set LOCAL_SOURCE_ROOT env var to map paths.`
      });
    }

    console.log(`Reading functions from: ${sourcePath}`);
    const sourceCode = fs.readFileSync(sourcePath, 'utf-8');

    // Simple regex to extract function definitions
    // Matches: return_type function_name(params) {
    const functionRegex = /^[\w\s\*]+\s+(\w+)\s*\([^)]*\)\s*\{/gm;
    const functions: string[] = [];
    let match;

    while ((match = functionRegex.exec(sourceCode)) !== null) {
      const funcName = match[1];
      // Filter out common non-functions
      if (!['if', 'while', 'for', 'switch', 'else'].includes(funcName)) {
        functions.push(funcName);
      }
    }

    res.json({ functions: [...new Set(functions)] });
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

// Generate driver with streaming progress
app.get('/api/generate', (req, res) => {
  const { project, filename, functionName, model = 'gpt-4o-mini', maxIterations = '3' } = req.query;

  if (!project || !filename || !functionName) {
    return res.status(400).json({ error: 'project, filename, and functionName are required' });
  }

  // Set up SSE headers
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');

  const sendEvent = (type: string, data: any) => {
    res.write(`data: ${JSON.stringify({ type, ...data })}\n\n`);
  };

  sendEvent('status', { message: `Starting driver generation for ${functionName}...` });

  const outputFile = `drivers/gui_${functionName}.c`;
  const args = [
    'gen',
    project as string,
    filename as string,
    functionName as string,
    '--model', model as string,
    '--max-iterations', maxIterations as string,
    '--output', outputFile,
    '--with-logs',
    '--context', 'function',
    '-v',
  ];

  const child = spawn('tisaidga', args, {
    cwd: PROJECT_ROOT,
  });

  let fullOutput = '';
  let driverCode = '';

  child.stdout.on('data', (data: Buffer) => {
    const text = data.toString();
    fullOutput += text;

    // Parse progress from output
    const lines = text.split('\n');
    for (const line of lines) {
      if (line.includes('Generating driver')) {
        sendEvent('status', { message: 'Generating initial driver code...' });
      } else if (line.includes('Running TIS')) {
        sendEvent('status', { message: 'Validating with TIS Analyzer...' });
      } else if (line.includes('Iteration')) {
        const iterMatch = line.match(/Iteration\s+(\d+)/i);
        if (iterMatch) {
          sendEvent('status', { message: `Refinement iteration ${iterMatch[1]}...` });
        }
      } else if (line.includes('SUCCESS')) {
        sendEvent('status', { message: 'Driver generation successful!' });
      } else if (line.includes('FAILED')) {
        sendEvent('status', { message: 'Driver generation failed' });
      } else if (line.trim()) {
        sendEvent('log', { message: line.trim() });
      }
    }
  });

  child.stderr.on('data', (data: Buffer) => {
    const text = data.toString();
    sendEvent('log', { message: text, isError: true });
  });

  child.on('close', (code: number) => {
    // Try to read the generated driver file
    const outputPath = path.join(PROJECT_ROOT, outputFile);
    if (fs.existsSync(outputPath)) {
      driverCode = fs.readFileSync(outputPath, 'utf-8');
    }

    sendEvent('complete', {
      success: code === 0,
      exitCode: code,
      driverCode,
      outputFile,
    });

    res.end();
  });

  child.on('error', (error: Error) => {
    sendEvent('error', { message: error.message });
    res.end();
  });

  // Handle client disconnect
  req.on('close', () => {
    child.kill();
  });
});

// Read a generated driver file
app.get('/api/driver/:filename', (req, res) => {
  const { filename } = req.params;
  const driverPath = path.join(PROJECT_ROOT, 'drivers', filename);

  if (!fs.existsSync(driverPath)) {
    return res.status(404).json({ error: 'Driver file not found' });
  }

  const content = fs.readFileSync(driverPath, 'utf-8');
  res.json({ content, filename });
});

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
  console.log(`Project root: ${PROJECT_ROOT}`);
});
