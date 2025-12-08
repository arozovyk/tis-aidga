import { useState, useEffect, useRef, useMemo } from 'react'
import hljs from 'highlight.js/lib/core'
import c from 'highlight.js/lib/languages/c'
import 'highlight.js/styles/atom-one-dark.css'

hljs.registerLanguage('c', c)

interface Project {
  name: string
  fileCount: number
}

interface FileInfo {
  name: string
  path: string
}

interface LogEntry {
  message: string
  isError?: boolean
}

type GenerationStatus = 'idle' | 'generating' | 'success' | 'failed'

function App() {
  // Project state
  const [projects, setProjects] = useState<Project[]>([])
  const [selectedProject, setSelectedProject] = useState<string>('')
  const [files, setFiles] = useState<FileInfo[]>([])
  const [selectedFile, setSelectedFile] = useState<string>('')
  const [functions, setFunctions] = useState<string[]>([])
  const [selectedFunction, setSelectedFunction] = useState<string>('')

  // Init state
  const [compilationDbPath, setCompilationDbPath] = useState<string>('')
  const [newProjectName, setNewProjectName] = useState<string>('')
  const [isInitializing, setIsInitializing] = useState(false)

  // Generation state
  const [model, setModel] = useState<string>('gpt-4o-mini')
  const [maxIterations, setMaxIterations] = useState<string>('3')
  const [isGenerating, setIsGenerating] = useState(false)
  const [progressMessage, setProgressMessage] = useState<string>('')
  const [generationStatus, setGenerationStatus] = useState<GenerationStatus>('idle')
  const [driverCode, setDriverCode] = useState<string>('')
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [generationTime, setGenerationTime] = useState<number | null>(null)
  const [startTime, setStartTime] = useState<number | null>(null)

  const logContainerRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Highlight C code
  const highlightedCode = useMemo(() => {
    if (!driverCode) return ''
    try {
      return hljs.highlight(driverCode, { language: 'c' }).value
    } catch {
      return driverCode
    }
  }, [driverCode])

  // Load projects on mount
  useEffect(() => {
    loadProjects()
  }, [])

  // Load files when project changes
  useEffect(() => {
    if (selectedProject) {
      loadFiles(selectedProject)
    } else {
      setFiles([])
      setSelectedFile('')
      setFunctions([])
      setSelectedFunction('')
    }
  }, [selectedProject])

  // Load functions when file changes
  useEffect(() => {
    if (selectedProject && selectedFile) {
      loadFunctions(selectedProject, selectedFile)
    } else {
      setFunctions([])
      setSelectedFunction('')
    }
  }, [selectedProject, selectedFile])

  // Auto-scroll logs
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight
    }
  }, [logs])

  const loadProjects = async () => {
    try {
      const res = await fetch('/api/projects')
      const data = await res.json()
      setProjects(data.projects || [])
    } catch (error) {
      console.error('Failed to load projects:', error)
    }
  }

  const loadFiles = async (project: string) => {
    try {
      const res = await fetch(`/api/projects/${project}/files`)
      const data = await res.json()
      setFiles(data.files || [])
      setSelectedFile('')
      setFunctions([])
      setSelectedFunction('')
    } catch (error) {
      console.error('Failed to load files:', error)
    }
  }

  const loadFunctions = async (project: string, filename: string) => {
    try {
      const res = await fetch(`/api/projects/${project}/files/${filename}/functions`)
      const data = await res.json()
      setFunctions(data.functions || [])
      setSelectedFunction('')
    } catch (error) {
      console.error('Failed to load functions:', error)
    }
  }

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    // Upload file to server and get the saved path
    const formData = new FormData()
    formData.append('file', file)

    try {
      const res = await fetch('/api/upload-compile-db', {
        method: 'POST',
        body: formData,
      })
      const data = await res.json()
      if (data.path) {
        setCompilationDbPath(data.path)
      }
    } catch (error) {
      console.error('Failed to upload file:', error)
    }
  }

  const handleInit = async () => {
    if (!compilationDbPath) return

    setIsInitializing(true)
    try {
      const res = await fetch('/api/init', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          compilationDbPath,
          projectName: newProjectName || undefined,
        }),
      })

      const data = await res.json()
      if (data.success) {
        await loadProjects()
        setCompilationDbPath('')
        setNewProjectName('')
      } else {
        alert('Init failed: ' + (data.error || 'Unknown error'))
      }
    } catch (error) {
      console.error('Init failed:', error)
      alert('Init failed: ' + error)
    } finally {
      setIsInitializing(false)
    }
  }

  const handleGenerate = async () => {
    if (!selectedProject || !selectedFile || !selectedFunction) return

    setIsGenerating(true)
    setGenerationStatus('idle')
    setProgressMessage('Starting generation...')
    setDriverCode('')
    setLogs([])
    setGenerationTime(null)
    const genStartTime = Date.now()
    setStartTime(genStartTime)

    const params = new URLSearchParams({
      project: selectedProject,
      filename: selectedFile,
      functionName: selectedFunction,
      model,
      maxIterations,
    })

    const eventSource = new EventSource(`/api/generate?${params}`)

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data)

      switch (data.type) {
        case 'status':
          setProgressMessage(data.message)
          break
        case 'log':
          setLogs(prev => [...prev.slice(-100), { message: data.message, isError: data.isError }])
          break
        case 'complete':
          setIsGenerating(false)
          setGenerationStatus(data.success ? 'success' : 'failed')
          setGenerationTime(Date.now() - genStartTime)
          setProgressMessage(data.success ? 'Generation complete!' : 'Generation failed')
          if (data.driverCode) {
            setDriverCode(data.driverCode)
          }
          eventSource.close()
          break
        case 'error':
          setIsGenerating(false)
          setGenerationStatus('failed')
          setGenerationTime(Date.now() - genStartTime)
          setProgressMessage('Error: ' + data.message)
          eventSource.close()
          break
      }
    }

    eventSource.onerror = () => {
      setIsGenerating(false)
      setGenerationStatus('failed')
      setProgressMessage('Connection error')
      eventSource.close()
    }
  }

  return (
    <div className="app">
      <header className="header">
        <h1>TIS-Chiron Driver Generator</h1>
      </header>

      <div className="main-content">
        <aside className="sidebar">
          {/* Init Panel */}
          <div className="panel">
            <h2>Initialize Project</h2>
            <div className="init-section">
              <div className="input-group">
                <label>compile_commands.json path</label>
                <div className="file-input-wrapper">
                  <input
                    type="text"
                    value={compilationDbPath}
                    onChange={(e) => setCompilationDbPath(e.target.value)}
                    placeholder="/path/to/compile_commands.json"
                  />
                  <button
                    className="btn btn-secondary btn-browse"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    Browse
                  </button>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".json"
                    onChange={handleFileSelect}
                  />
                </div>
              </div>
              <div className="input-group">
                <label>Project name (optional)</label>
                <input
                  type="text"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  placeholder="my-project"
                />
              </div>
              <button
                className="btn btn-primary"
                onClick={handleInit}
                disabled={!compilationDbPath || isInitializing}
              >
                {isInitializing ? 'Initializing...' : 'Init Project'}
              </button>
            </div>
          </div>

          {/* Project/File Selection */}
          <div className="panel">
            <h2>Select Target</h2>
            <div className="init-section">
              <div className="input-group">
                <label>Project</label>
                <select
                  value={selectedProject}
                  onChange={(e) => setSelectedProject(e.target.value)}
                >
                  <option value="">Select project...</option>
                  {projects.map((p) => (
                    <option key={p.name} value={p.name}>
                      {p.name} ({p.fileCount} files)
                    </option>
                  ))}
                </select>
              </div>
              <div className="input-group">
                <label>Source File</label>
                <select
                  value={selectedFile}
                  onChange={(e) => setSelectedFile(e.target.value)}
                  disabled={!selectedProject}
                >
                  <option value="">Select file...</option>
                  {files.map((f) => (
                    <option key={f.name} value={f.name}>
                      {f.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Function List */}
          <div className="panel function-list">
            <h2>Functions ({functions.length})</h2>
            {functions.length > 0 ? (
              <ul>
                {functions.map((fn) => (
                  <li
                    key={fn}
                    className={selectedFunction === fn ? 'selected' : ''}
                    onClick={() => setSelectedFunction(fn)}
                  >
                    {fn}()
                  </li>
                ))}
              </ul>
            ) : (
              <p style={{ color: '#666', fontSize: '0.875rem' }}>
                {selectedFile ? 'No functions found' : 'Select a file to see functions'}
              </p>
            )}
          </div>

          {/* Generation Settings */}
          <div className="panel">
            <h2>Generation Settings</h2>
            <div className="init-section">
              <div className="row">
                <div className="input-group">
                  <label>Model</label>
                  <select value={model} onChange={(e) => setModel(e.target.value)}>
                    <option value="gpt-4o-mini">gpt-4o-mini</option>
                    <option value="gpt-4o">gpt-4o</option>
                    <option value="gpt-4-turbo">gpt-4-turbo</option>
                  </select>
                </div>
                <div className="input-group">
                  <label>Max Iter</label>
                  <select value={maxIterations} onChange={(e) => setMaxIterations(e.target.value)}>
                    <option value="1">1</option>
                    <option value="2">2</option>
                    <option value="3">3</option>
                    <option value="5">5</option>
                    <option value="10">10</option>
                  </select>
                </div>
              </div>
              <button
                className="btn btn-primary"
                onClick={handleGenerate}
                disabled={!selectedFunction || isGenerating}
              >
                {isGenerating ? 'Generating...' : 'Generate Driver'}
              </button>
            </div>
          </div>
        </aside>

        <main className="main-area">
          {/* Progress Panel */}
          <div className="panel progress-panel">
            <h2>Progress</h2>
            <div className="progress-content">
              {isGenerating ? (
                <>
                  <div className="progress-spinner" />
                  <span className="progress-message">{progressMessage}</span>
                </>
              ) : generationStatus !== 'idle' ? (
                <span className={`progress-message ${generationStatus}`}>
                  {progressMessage}
                </span>
              ) : (
                <span className="progress-idle">
                  Select a function and click Generate to start
                </span>
              )}
            </div>
          </div>

          {/* Result Panel */}
          <div className="panel result-panel">
            <div className="result-header">
              <h2>Driver Result</h2>
              <div className="result-meta">
                {generationTime !== null && (
                  <span className="generation-time">
                    {(generationTime / 1000).toFixed(1)}s
                  </span>
                )}
                {generationStatus !== 'idle' && (
                  <span className={`result-status ${generationStatus}`}>
                    {generationStatus === 'success' ? 'SUCCESS' : generationStatus === 'failed' ? 'FAILED' : ''}
                  </span>
                )}
              </div>
            </div>
            {driverCode ? (
              <pre className="code-container">
                <code dangerouslySetInnerHTML={{ __html: highlightedCode }} />
              </pre>
            ) : (
              <div className="code-container empty">
                Generated driver code will appear here
              </div>
            )}
          </div>

          {/* Log Panel */}
          <div className="panel log-panel">
            <h2>Logs</h2>
            <div className="log-content" ref={logContainerRef}>
              {logs.map((log, i) => (
                <div key={i} className={`log-line ${log.isError ? 'error' : ''}`}>
                  {log.message}
                </div>
              ))}
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}

export default App
