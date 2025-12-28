/**
 * AquaBrain Local Bridge Server v2.0
 * ===================================
 * WebSocket bridge between Next.js frontend and Windows/WSL kernel
 *
 * NEW: Gemini (Brain) + Claude Code CLI (Hands) Architecture
 *
 * Features:
 * - Real-time streaming output via WebSockets
 * - PowerShell and Bash (WSL) command execution
 * - Claude Code CLI integration (the "Hands")
 * - Process management (start, stop, list)
 * - File system operations
 * - pyRevit integration
 * - AutoCAD/Revit COM automation
 *
 * WARNING: This server has FULL SYSTEM ACCESS when run as Administrator
 *
 * Author: AquaBrain V10.0 Platinum
 */

const WebSocket = require('ws');
const { spawn, exec, execSync } = require('child_process');
const os = require('os');
const path = require('path');
const fs = require('fs');

// =============================================================================
// SOFTWARE CONTROLLER: Revit & AutoCAD Management
// =============================================================================
const { SoftwareController, SOFTWARE_CATALOG } = require('./software/controller');
const softwareController = new SoftwareController();

// Configuration
const PORT = process.env.BRIDGE_PORT || 8085;  // Changed from 8080 (Airflow uses 8080)
const MAX_LOG_LINES = 1000;

// =============================================================================
// NEURAL LINK: Python Engineering Core Configuration
// =============================================================================
const PYTHON_CORE_NAME = 'AquaBrain_Terminal';
const POETRY_PATH = path.join(os.homedir(), '.local', 'bin', 'poetry');
const CONDA_ACTIVATE = `source ${path.join(os.homedir(), 'miniconda3', 'bin', 'activate')} py311`;

// Find the Python engineering core directory
function findPythonCore() {
  const searchPaths = [
    path.join(__dirname, '..', '..', PYTHON_CORE_NAME),  // Sibling folder
    path.join(__dirname, '..', PYTHON_CORE_NAME),        // Parent folder
    path.join(os.homedir(), PYTHON_CORE_NAME),           // Home directory
    path.join(os.homedir(), 'AquaProjects', PYTHON_CORE_NAME), // AquaProjects
  ];

  for (const searchPath of searchPaths) {
    if (fs.existsSync(searchPath) && fs.existsSync(path.join(searchPath, 'pyproject.toml'))) {
      console.log(`🧠 Found Python Core at: ${searchPath}`);
      return searchPath;
    }
  }

  console.warn('⚠️ Python Core not found. Skill execution will be unavailable.');
  return null;
}

// Verify poetry environment
function verifyPoetryEnvironment(pythonCorePath) {
  if (!pythonCorePath) return { valid: false, error: 'Python core not found' };

  try {
    // Check if poetry exists
    if (!fs.existsSync(POETRY_PATH)) {
      return { valid: false, error: `Poetry not found at ${POETRY_PATH}` };
    }

    return { valid: true, path: pythonCorePath };
  } catch (error) {
    return { valid: false, error: error.message };
  }
}

// Initialize Python Core
const PYTHON_CORE_PATH = findPythonCore();
const POETRY_ENV = verifyPoetryEnvironment(PYTHON_CORE_PATH);

// Active processes registry
const activeProcesses = new Map();

// Create WebSocket server
const wss = new WebSocket.Server({
  port: PORT,
  // Allow connections from localhost only for security
  verifyClient: (info) => {
    const origin = info.origin || info.req.headers.origin;
    return !origin || origin.includes('localhost') || origin.includes('127.0.0.1');
  }
});

console.log(`
╔══════════════════════════════════════════════════════════════╗
║      🧠 AquaBrain Local Bridge v3.0 - Neural Link Edition    ║
║══════════════════════════════════════════════════════════════║
║  Status: ONLINE                                              ║
║  Port: ${PORT}                                                   ║
║  Platform: ${os.platform()} (${os.arch()})                              ║
║  Node: ${process.version}                                          ║
╠══════════════════════════════════════════════════════════════╣
║  🧠 Gemini = Brain (Reasoning & Planning)                    ║
║  🤖 Claude CLI = Hands (Execution & Code)                    ║
║  🐍 Python Core = ${POETRY_ENV.valid ? '✅ CONNECTED' : '❌ NOT FOUND'}                             ║
${POETRY_ENV.valid ? `║     Path: ${PYTHON_CORE_PATH.substring(0, 45)}...` : `║     Error: ${POETRY_ENV.error}`}
╠══════════════════════════════════════════════════════════════╣
║  ⚠️  WARNING: This server has FULL SYSTEM ACCESS             ║
║  🔒 Only accepting connections from localhost                ║
╚══════════════════════════════════════════════════════════════╝
`);

// Connection handler
wss.on('connection', (ws, req) => {
  const clientIP = req.socket.remoteAddress;
  console.log(`✅ Client connected from ${clientIP}`);

  // Send connection confirmation
  ws.send(JSON.stringify({
    type: 'connected',
    message: 'Connected to AquaBrain Local Bridge v3.0 - Neural Link',
    platform: os.platform(),
    hostname: os.hostname(),
    capabilities: ['powershell', 'bash', 'python', 'pyrevit', 'file-ops', 'claude-agent', 'skills', 'software'],
    software: softwareController.getAvailableSoftware(),
    pythonCore: {
      connected: POETRY_ENV.valid,
      path: PYTHON_CORE_PATH,
      error: POETRY_ENV.error
    }
  }));

  // Message handler
  ws.on('message', async (message) => {
    try {
      const request = JSON.parse(message.toString());
      console.log(`📨 Received: ${request.action || request.type} - ${request.command?.substring(0, 50) || ''}`);

      switch (request.action || request.type) {
        case 'execute':
        case 'powershell':
        case 'bash':
          await executeCommand(ws, request);
          break;
        case 'claude_agent':
        case 'claude-agent':
          await executeClaudeAgent(ws, request);
          break;
        case 'python':
          await executePython(ws, request);
          break;
        case 'pyrevit':
          await executePyRevit(ws, request);
          break;
        case 'file-read':
          await readFile(ws, request);
          break;
        case 'file-write':
          await writeFile(ws, request);
          break;
        case 'file-list':
          await listFiles(ws, request);
          break;
        case 'process-list':
          await listProcesses(ws, request);
          break;
        case 'process-kill':
          await killProcess(ws, request);
          break;
        case 'system-info':
          await getSystemInfo(ws);
          break;
        case 'ping':
          ws.send(JSON.stringify({ type: 'pong', timestamp: Date.now() }));
          break;
        // =============================================================
        // NEURAL LINK: Python Skill Execution
        // =============================================================
        case 'EXECUTE_SKILL':
        case 'execute-skill':
          await executeSkill(ws, request);
          break;
        case 'list-skills':
          await listAvailableSkills(ws);
          break;
        // =============================================================
        // SOFTWARE CONTROL: Revit & AutoCAD Management
        // =============================================================
        case 'software-list':
          await handleSoftwareList(ws);
          break;
        case 'software-status':
          await handleSoftwareStatus(ws, request);
          break;
        case 'software-open':
          await handleSoftwareOpen(ws, request);
          break;
        case 'software-close':
          await handleSoftwareClose(ws, request);
          break;
        case 'software-restart':
          await handleSoftwareRestart(ws, request);
          break;
        case 'software-status-all':
          await handleSoftwareStatusAll(ws);
          break;
        default:
          ws.send(JSON.stringify({
            type: 'error',
            error: `Unknown action: ${request.action || request.type}`
          }));
      }
    } catch (error) {
      console.error('❌ Error processing message:', error);
      ws.send(JSON.stringify({
        type: 'error',
        error: error.message
      }));
    }
  });

  ws.on('close', () => {
    console.log(`❌ Client disconnected from ${clientIP}`);
  });

  ws.on('error', (error) => {
    console.error(`❌ WebSocket error:`, error);
  });
});

/**
 * Execute shell command (PowerShell or Bash)
 */
async function executeCommand(ws, request) {
  const { command, type = 'powershell', cwd, env = {} } = request;
  const processId = `proc_${Date.now()}`;

  let shellCmd, shellArgs;

  if (type === 'bash' || type === 'wsl') {
    // WSL/Bash execution
    shellCmd = 'wsl.exe';
    shellArgs = ['bash', '-c', command];
  } else {
    // PowerShell execution (default)
    shellCmd = 'powershell.exe';
    shellArgs = [
      '-NoProfile',
      '-ExecutionPolicy', 'Bypass',
      '-Command', command
    ];
  }

  // Spawn process
  const processOptions = {
    cwd: cwd || process.cwd(),
    env: { ...process.env, ...env },
    shell: false
  };

  const proc = spawn(shellCmd, shellArgs, processOptions);
  activeProcesses.set(processId, proc);

  // Send process started notification
  ws.send(JSON.stringify({
    type: 'process-started',
    processId,
    command: command.substring(0, 100),
    shell: type
  }));

  let outputBuffer = '';

  // Stream stdout
  proc.stdout.on('data', (data) => {
    const output = data.toString();
    outputBuffer += output;
    ws.send(JSON.stringify({
      type: 'stdout',
      processId,
      output,
      timestamp: Date.now()
    }));
  });

  // Stream stderr
  proc.stderr.on('data', (data) => {
    const output = data.toString();
    ws.send(JSON.stringify({
      type: 'stderr',
      processId,
      output,
      timestamp: Date.now()
    }));
  });

  // Process completed
  proc.on('close', (code) => {
    activeProcesses.delete(processId);
    ws.send(JSON.stringify({
      type: 'process-completed',
      processId,
      exitCode: code,
      success: code === 0,
      fullOutput: outputBuffer
    }));
  });

  // Process error
  proc.on('error', (error) => {
    activeProcesses.delete(processId);
    ws.send(JSON.stringify({
      type: 'process-error',
      processId,
      error: error.message
    }));
  });
}

/**
 * Execute Python script
 */
async function executePython(ws, request) {
  const { script, args = [], cwd } = request;

  const command = `python3 -c "${script.replace(/"/g, '\\"')}"`;
  await executeCommand(ws, { command, type: 'bash', cwd });
}

/**
 * Execute pyRevit command
 */
async function executePyRevit(ws, request) {
  const { action, script, revitVersion = '2025' } = request;

  let command;

  switch (action) {
    case 'run':
      command = `pyrevit run "${script}" --revit=${revitVersion}`;
      break;
    case 'attach':
      command = `pyrevit attach master default --installed`;
      break;
    case 'env':
      command = `pyrevit env`;
      break;
    case 'routes':
      command = `pyrevit configs routes`;
      break;
    default:
      command = `pyrevit ${action}`;
  }

  await executeCommand(ws, { command, type: 'powershell' });
}

/**
 * Execute Claude Code CLI Agent - The "Hands" of AquaBrain
 * =========================================================
 * This function spawns the Claude Code CLI with a prompt from Gemini (the "Brain")
 * and streams the output back to the frontend in real-time.
 *
 * Architecture:
 * - Gemini (Brain) creates the prompt/instructions
 * - Claude Code CLI (Hands) executes the actual code/commands
 * - Results stream back through WebSocket
 */
async function executeClaudeAgent(ws, request) {
  const { command: prompt, workingDirectory, allowedTools = [] } = request;
  const processId = `claude_${Date.now()}`;

  console.log(`🤖 Claude Agent Triggered: ${prompt.substring(0, 80)}...`);

  // Send process started notification
  ws.send(JSON.stringify({
    type: 'claude-agent-started',
    processId,
    prompt: prompt.substring(0, 200),
    source: 'Claude CLI'
  }));

  // Determine the shell and command based on platform
  // On Windows: use cmd.exe /c claude
  // On WSL/Linux: use claude directly
  const isWindows = os.platform() === 'win32';

  let shellCmd, shellArgs;

  if (isWindows) {
    // Windows: Run claude through cmd.exe
    shellCmd = 'cmd.exe';
    shellArgs = ['/c', 'claude', '-p', prompt];
  } else {
    // WSL/Linux: Try to run claude through Windows if we're in WSL
    // Check if we're in WSL by looking for /mnt/c
    const isWSL = fs.existsSync('/mnt/c');

    if (isWSL) {
      // Run claude.exe through Windows from WSL
      shellCmd = 'cmd.exe';
      shellArgs = ['/c', 'claude', '-p', prompt];
    } else {
      // Pure Linux: run claude directly (assumes it's in PATH)
      shellCmd = 'claude';
      shellArgs = ['-p', prompt];
    }
  }

  // If working directory specified, add it
  const processOptions = {
    cwd: workingDirectory || process.cwd(),
    env: { ...process.env },
    shell: false
  };

  try {
    const proc = spawn(shellCmd, shellArgs, processOptions);
    activeProcesses.set(processId, proc);

    let outputBuffer = '';
    let errorBuffer = '';

    // Stream stdout
    proc.stdout.on('data', (data) => {
      const output = data.toString();
      outputBuffer += output;
      ws.send(JSON.stringify({
        type: 'claude-stdout',
        processId,
        output,
        source: 'Claude CLI',
        timestamp: Date.now()
      }));
    });

    // Stream stderr
    proc.stderr.on('data', (data) => {
      const output = data.toString();
      errorBuffer += output;
      ws.send(JSON.stringify({
        type: 'claude-stderr',
        processId,
        output,
        source: 'Claude CLI',
        timestamp: Date.now()
      }));
    });

    // Process completed
    proc.on('close', (code) => {
      activeProcesses.delete(processId);
      ws.send(JSON.stringify({
        type: 'claude-agent-completed',
        processId,
        exitCode: code,
        success: code === 0,
        fullOutput: outputBuffer,
        errors: errorBuffer,
        source: 'Claude CLI'
      }));
      console.log(`🤖 Claude Agent completed (exit code: ${code})`);
    });

    // Process error
    proc.on('error', (error) => {
      activeProcesses.delete(processId);
      ws.send(JSON.stringify({
        type: 'claude-agent-error',
        processId,
        error: error.message,
        source: 'Claude CLI',
        hint: 'Make sure Claude Code CLI is installed: npm install -g @anthropic-ai/claude-code'
      }));
      console.error(`🤖 Claude Agent error: ${error.message}`);
    });

  } catch (error) {
    ws.send(JSON.stringify({
      type: 'claude-agent-error',
      processId,
      error: error.message,
      source: 'Claude CLI',
      hint: 'Make sure Claude Code CLI is installed and accessible in PATH'
    }));
  }
}

/**
 * Read file contents
 */
async function readFile(ws, request) {
  const { path: filePath, encoding = 'utf-8' } = request;

  try {
    const content = fs.readFileSync(filePath, encoding);
    ws.send(JSON.stringify({
      type: 'file-content',
      path: filePath,
      content,
      size: Buffer.byteLength(content, encoding)
    }));
  } catch (error) {
    ws.send(JSON.stringify({
      type: 'error',
      error: `Failed to read file: ${error.message}`
    }));
  }
}

/**
 * Write file contents
 */
async function writeFile(ws, request) {
  const { path: filePath, content, encoding = 'utf-8' } = request;

  try {
    // Ensure directory exists
    const dir = path.dirname(filePath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }

    fs.writeFileSync(filePath, content, encoding);
    ws.send(JSON.stringify({
      type: 'file-written',
      path: filePath,
      size: Buffer.byteLength(content, encoding)
    }));
  } catch (error) {
    ws.send(JSON.stringify({
      type: 'error',
      error: `Failed to write file: ${error.message}`
    }));
  }
}

/**
 * List files in directory
 */
async function listFiles(ws, request) {
  const { path: dirPath, recursive = false } = request;

  try {
    const files = fs.readdirSync(dirPath, { withFileTypes: true });
    const result = files.map(file => ({
      name: file.name,
      isDirectory: file.isDirectory(),
      isFile: file.isFile(),
      path: path.join(dirPath, file.name)
    }));

    ws.send(JSON.stringify({
      type: 'file-list',
      path: dirPath,
      files: result
    }));
  } catch (error) {
    ws.send(JSON.stringify({
      type: 'error',
      error: `Failed to list directory: ${error.message}`
    }));
  }
}

/**
 * List active processes
 */
async function listProcesses(ws, request) {
  const processList = [];
  for (const [id, proc] of activeProcesses) {
    processList.push({
      id,
      pid: proc.pid,
      killed: proc.killed
    });
  }

  ws.send(JSON.stringify({
    type: 'process-list',
    processes: processList
  }));
}

/**
 * Kill a process
 */
async function killProcess(ws, request) {
  const { processId } = request;

  if (activeProcesses.has(processId)) {
    const proc = activeProcesses.get(processId);
    proc.kill('SIGTERM');
    activeProcesses.delete(processId);

    ws.send(JSON.stringify({
      type: 'process-killed',
      processId
    }));
  } else {
    ws.send(JSON.stringify({
      type: 'error',
      error: `Process not found: ${processId}`
    }));
  }
}

/**
 * Get system information
 */
async function getSystemInfo(ws) {
  const info = {
    type: 'system-info',
    platform: os.platform(),
    arch: os.arch(),
    hostname: os.hostname(),
    cpus: os.cpus().length,
    totalMemory: os.totalmem(),
    freeMemory: os.freemem(),
    uptime: os.uptime(),
    nodeVersion: process.version,
    cwd: process.cwd(),
    activeProcesses: activeProcesses.size
  };

  ws.send(JSON.stringify(info));
}

// =============================================================================
// NEURAL LINK: Python Skill Execution Functions
// =============================================================================

/**
 * Execute a Python engineering skill via Poetry
 * This is the core of the Neural Link - connecting Node.js to Python
 */
async function executeSkill(ws, request) {
  const { skill, params = {}, command, args = [] } = request;
  const processId = `skill_${Date.now()}`;

  // Validate environment
  if (!POETRY_ENV.valid) {
    ws.send(JSON.stringify({
      type: 'SKILL_ERROR',
      processId,
      skill,
      error: POETRY_ENV.error,
      hint: 'Ensure AquaBrain_Terminal is cloned and poetry is installed'
    }));
    return;
  }

  console.log(`🐍 Executing Skill: ${skill || command} with params:`, params);

  // Build the aquabrain command
  // Format: poetry run aquabrain <command> [args...]
  const skillCommand = skill || command || 'info';
  const skillArgs = args.length > 0 ? args : Object.entries(params)
    .map(([key, value]) => `--${key}=${value}`)
    .join(' ');

  // Build the full command with conda activation and poetry
  const fullCommand = `${CONDA_ACTIVATE} && cd "${PYTHON_CORE_PATH}" && ${POETRY_PATH} run aquabrain ${skillCommand} ${skillArgs}`.trim();

  // Send skill started notification
  ws.send(JSON.stringify({
    type: 'SKILL_STARTED',
    processId,
    skill: skillCommand,
    params,
    pythonCore: PYTHON_CORE_PATH,
    timestamp: Date.now()
  }));

  // Spawn the process
  const proc = spawn('bash', ['-c', fullCommand], {
    cwd: PYTHON_CORE_PATH,
    env: { ...process.env, PYTHONUNBUFFERED: '1' },
    shell: false
  });

  activeProcesses.set(processId, proc);

  let outputBuffer = '';
  let errorBuffer = '';

  // Stream stdout - skill output
  proc.stdout.on('data', (data) => {
    const output = data.toString();
    outputBuffer += output;

    // Try to parse as JSON for structured output
    let parsedData = null;
    try {
      parsedData = JSON.parse(output.trim());
    } catch (e) {
      // Not JSON, that's fine
    }

    ws.send(JSON.stringify({
      type: 'SKILL_OUTPUT',
      processId,
      skill: skillCommand,
      output,
      parsed: parsedData,
      stream: 'stdout',
      timestamp: Date.now()
    }));
  });

  // Stream stderr - errors or warnings
  proc.stderr.on('data', (data) => {
    const output = data.toString();
    errorBuffer += output;

    ws.send(JSON.stringify({
      type: 'SKILL_OUTPUT',
      processId,
      skill: skillCommand,
      output,
      stream: 'stderr',
      timestamp: Date.now()
    }));
  });

  // Process completed
  proc.on('close', (code) => {
    activeProcesses.delete(processId);

    // Try to parse final output as JSON
    let result = null;
    try {
      result = JSON.parse(outputBuffer.trim());
    } catch (e) {
      result = outputBuffer.trim();
    }

    ws.send(JSON.stringify({
      type: 'SKILL_COMPLETED',
      processId,
      skill: skillCommand,
      exitCode: code,
      success: code === 0,
      result,
      fullOutput: outputBuffer,
      errors: errorBuffer,
      timestamp: Date.now()
    }));

    console.log(`🐍 Skill ${skillCommand} completed (exit code: ${code})`);
  });

  // Process error
  proc.on('error', (error) => {
    activeProcesses.delete(processId);

    ws.send(JSON.stringify({
      type: 'SKILL_ERROR',
      processId,
      skill: skillCommand,
      error: error.message,
      hint: 'Check that poetry and Python 3.11 environment are properly configured'
    }));

    console.error(`🐍 Skill error: ${error.message}`);
  });
}

/**
 * List available skills from the Python core
 */
async function listAvailableSkills(ws) {
  if (!POETRY_ENV.valid) {
    ws.send(JSON.stringify({
      type: 'skills-list',
      available: false,
      error: POETRY_ENV.error,
      skills: []
    }));
    return;
  }

  // Execute aquabrain --help to get available commands
  const fullCommand = `${CONDA_ACTIVATE} && cd "${PYTHON_CORE_PATH}" && ${POETRY_PATH} run aquabrain --help`;

  exec(`bash -c '${fullCommand}'`, (error, stdout, stderr) => {
    if (error) {
      ws.send(JSON.stringify({
        type: 'skills-list',
        available: false,
        error: error.message,
        skills: []
      }));
      return;
    }

    // Parse the help output to extract commands
    const skills = [];
    const lines = stdout.split('\n');
    let inCommands = false;

    for (const line of lines) {
      if (line.includes('Commands')) {
        inCommands = true;
        continue;
      }
      if (inCommands && line.trim()) {
        const match = line.match(/^\s+(\w+)\s+(.*)$/);
        if (match) {
          skills.push({
            id: match[1],
            name: match[1],
            description: match[2].trim()
          });
        }
      }
    }

    ws.send(JSON.stringify({
      type: 'skills-list',
      available: true,
      pythonCore: PYTHON_CORE_PATH,
      skills
    }));
  });
}

// =============================================================================
// SOFTWARE CONTROL HANDLERS
// =============================================================================

/**
 * List available software
 */
async function handleSoftwareList(ws) {
  const software = softwareController.getAvailableSoftware();
  ws.send(JSON.stringify({
    type: 'software-list',
    software,
    timestamp: Date.now()
  }));
}

/**
 * Get status of specific software
 */
async function handleSoftwareStatus(ws, request) {
  const { softwareId } = request;

  try {
    const status = await softwareController.getStatus(softwareId);
    ws.send(JSON.stringify({
      type: 'software-status',
      softwareId,
      ...status,
      timestamp: Date.now()
    }));
  } catch (error) {
    ws.send(JSON.stringify({
      type: 'software-error',
      softwareId,
      error: error.message
    }));
  }
}

/**
 * Get status of all software
 */
async function handleSoftwareStatusAll(ws) {
  try {
    const statuses = await softwareController.getAllStatus();
    ws.send(JSON.stringify({
      type: 'software-status-all',
      statuses,
      timestamp: Date.now()
    }));
  } catch (error) {
    ws.send(JSON.stringify({
      type: 'software-error',
      error: error.message
    }));
  }
}

/**
 * Open software
 */
async function handleSoftwareOpen(ws, request) {
  const { softwareId, filePath = '' } = request;

  console.log(`🖥️ Opening software: ${softwareId}${filePath ? ` with file: ${filePath}` : ''}`);

  ws.send(JSON.stringify({
    type: 'software-opening',
    softwareId,
    message: `Starting ${SOFTWARE_CATALOG[softwareId]?.name || softwareId}...`,
    timestamp: Date.now()
  }));

  try {
    const result = await softwareController.open(softwareId, filePath);
    ws.send(JSON.stringify({
      type: 'software-opened',
      softwareId,
      ...result,
      timestamp: Date.now()
    }));
    console.log(`✅ Software opened: ${softwareId}`);
  } catch (error) {
    ws.send(JSON.stringify({
      type: 'software-error',
      softwareId,
      action: 'open',
      error: error.message
    }));
    console.error(`❌ Failed to open ${softwareId}: ${error.message}`);
  }
}

/**
 * Close software
 */
async function handleSoftwareClose(ws, request) {
  const { softwareId } = request;

  console.log(`🖥️ Closing software: ${softwareId}`);

  ws.send(JSON.stringify({
    type: 'software-closing',
    softwareId,
    message: `Closing ${SOFTWARE_CATALOG[softwareId]?.name || softwareId}...`,
    timestamp: Date.now()
  }));

  try {
    const result = await softwareController.close(softwareId);
    ws.send(JSON.stringify({
      type: 'software-closed',
      softwareId,
      ...result,
      timestamp: Date.now()
    }));
    console.log(`✅ Software closed: ${softwareId}`);
  } catch (error) {
    ws.send(JSON.stringify({
      type: 'software-error',
      softwareId,
      action: 'close',
      error: error.message
    }));
    console.error(`❌ Failed to close ${softwareId}: ${error.message}`);
  }
}

/**
 * Restart software
 */
async function handleSoftwareRestart(ws, request) {
  const { softwareId, filePath = '' } = request;

  console.log(`🖥️ Restarting software: ${softwareId}`);

  ws.send(JSON.stringify({
    type: 'software-restarting',
    softwareId,
    message: `Restarting ${SOFTWARE_CATALOG[softwareId]?.name || softwareId}...`,
    timestamp: Date.now()
  }));

  try {
    const result = await softwareController.restart(softwareId, filePath);
    ws.send(JSON.stringify({
      type: 'software-restarted',
      softwareId,
      ...result,
      timestamp: Date.now()
    }));
    console.log(`✅ Software restarted: ${softwareId}`);
  } catch (error) {
    ws.send(JSON.stringify({
      type: 'software-error',
      softwareId,
      action: 'restart',
      error: error.message
    }));
    console.error(`❌ Failed to restart ${softwareId}: ${error.message}`);
  }
}

// Graceful shutdown
process.on('SIGINT', () => {
  console.log('\n🛑 Shutting down bridge server...');

  // Kill all active processes
  for (const [id, proc] of activeProcesses) {
    proc.kill('SIGTERM');
  }

  wss.close(() => {
    console.log('✅ Server closed');
    process.exit(0);
  });
});

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
  console.error('❌ Uncaught exception:', error);
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('❌ Unhandled rejection:', reason);
});
