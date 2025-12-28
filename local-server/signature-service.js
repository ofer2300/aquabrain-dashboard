/**
 * AquaBrain Signature Pipeline Service v1.0
 * ==========================================
 * Isolated "Logical Container" for Engineering Document Signatures
 *
 * Architecture:
 * - Completely separate from bridge.js (no conflicts)
 * - Self-contained WebSocket server on port 8081
 * - JSON-based persistent storage
 * - IMAP email harvester
 * - PDF auto-stamping engine
 *
 * Safety Features:
 * - Never overwrites original documents
 * - Rollback capability
 * - Auto-recovery on connection drops
 * - Comprehensive logging
 *
 * Author: AquaBrain V10.0 Platinum
 */

const WebSocket = require('ws');
const fs = require('fs');
const path = require('path');
const { v4: uuidv4 } = require('uuid');
const { PDFDocument, rgb, StandardFonts } = require('pdf-lib');
const nodemailer = require('nodemailer');

// ============================================================================
// CONFIGURATION
// ============================================================================

const CONFIG = {
  PORT: 8081,

  // Paths (relative to this file)
  PATHS: {
    DATA_DIR: path.join(__dirname, 'data'),
    STACK_INDEX: path.join(__dirname, 'data', 'signatures_db.json'),
    PENDING_DIR: path.join(__dirname, '..', 'frontend', 'public', 'uploads', 'pending_signatures'),
    SIGNED_DIR: path.join(__dirname, '..', 'frontend', 'public', 'uploads', 'signed_documents'),
    ARCHIVE_DIR: path.join(__dirname, '..', 'frontend', 'public', 'uploads', 'archive'),
    ASSETS_DIR: path.join(__dirname, 'assets', 'signatures'),
    LOGS_DIR: path.join(__dirname, 'data', 'logs'),
  },

  // Email keywords for harvesting (Hebrew + English)
  HARVEST_KEYWORDS: [
    'חתימה', 'טופס 4', 'אישור', 'תצהיר', 'בניה ירוקה',
    'signature', 'form 4', 'approval', 'declaration', 'green building',
    'אינסטלציה', 'מכבי אש', 'plumbing', 'fire department'
  ],

  // Document type classification patterns
  DOC_TYPES: {
    'טופס 4': ['טופס 4', 'form 4', 'טופס4'],
    'תצהיר אינסטלציה': ['תצהיר', 'אינסטלציה', 'plumbing declaration'],
    'בניה ירוקה': ['בניה ירוקה', 'green building', 'תקן 5281'],
    'אישור מכבי אש': ['מכבי אש', 'fire department', 'כיבוי אש'],
    'אישור כללי': [] // Fallback
  },

  // Engineer details for stamping
  ENGINEER: {
    name: 'נימרוד עופר',
    licenseNumber: '68465',
    title: 'מהנדס מים וביוב מוסמך',
    company: 'אושר דוד תכנון אינסטלציה בע"מ',
    email: 'nimrod@aquabrain.io'
  },

  // Signature placement defaults (can be adjusted per document)
  SIGNATURE_DEFAULTS: {
    x: 400,
    y: 100,
    width: 150,
    height: 60
  }
};

// ============================================================================
// STACK INDEX DATABASE
// ============================================================================

class StackIndex {
  constructor() {
    this.dbPath = CONFIG.PATHS.STACK_INDEX;
    this.data = { signatures: [], lastUpdated: null };
    this.load();
  }

  load() {
    try {
      if (fs.existsSync(this.dbPath)) {
        const raw = fs.readFileSync(this.dbPath, 'utf-8');
        this.data = JSON.parse(raw);
        log('INFO', `Loaded ${this.data.signatures.length} signatures from database`);
      } else {
        this.save();
        log('INFO', 'Created new signatures database');
      }
    } catch (error) {
      log('ERROR', `Failed to load database: ${error.message}`);
      this.data = { signatures: [], lastUpdated: null };
    }
  }

  save() {
    try {
      this.data.lastUpdated = new Date().toISOString();
      fs.writeFileSync(this.dbPath, JSON.stringify(this.data, null, 2));
    } catch (error) {
      log('ERROR', `Failed to save database: ${error.message}`);
    }
  }

  add(signature) {
    const entry = {
      id: uuidv4(),
      projectName: signature.projectName || 'Unknown Project',
      docType: signature.docType || 'אישור כללי',
      requestDate: new Date().toISOString(),
      status: 'pending', // pending | processing | approved | rejected | sent
      originalFilePath: signature.originalFilePath,
      processedFilePath: null,
      senderEmail: signature.senderEmail || null,
      senderName: signature.senderName || null,
      subject: signature.subject || null,
      signaturePosition: { ...CONFIG.SIGNATURE_DEFAULTS },
      notes: signature.notes || '',
      history: [{
        action: 'created',
        timestamp: new Date().toISOString(),
        details: 'Document added to signature queue'
      }]
    };

    this.data.signatures.unshift(entry); // Add to top of stack
    this.save();
    log('INFO', `Added signature request: ${entry.id} - ${entry.projectName}`);
    return entry;
  }

  update(id, updates) {
    const index = this.data.signatures.findIndex(s => s.id === id);
    if (index === -1) return null;

    // Add history entry
    if (!this.data.signatures[index].history) {
      this.data.signatures[index].history = [];
    }
    this.data.signatures[index].history.push({
      action: 'updated',
      timestamp: new Date().toISOString(),
      details: JSON.stringify(updates)
    });

    Object.assign(this.data.signatures[index], updates);
    this.save();
    return this.data.signatures[index];
  }

  get(id) {
    return this.data.signatures.find(s => s.id === id);
  }

  getAll(filter = {}) {
    let results = [...this.data.signatures];

    if (filter.status) {
      results = results.filter(s => s.status === filter.status);
    }
    if (filter.docType) {
      results = results.filter(s => s.docType === filter.docType);
    }

    return results;
  }

  getPending() {
    return this.getAll({ status: 'pending' });
  }

  delete(id) {
    const index = this.data.signatures.findIndex(s => s.id === id);
    if (index === -1) return false;

    this.data.signatures.splice(index, 1);
    this.save();
    return true;
  }

  getStats() {
    const signatures = this.data.signatures;
    return {
      total: signatures.length,
      pending: signatures.filter(s => s.status === 'pending').length,
      processing: signatures.filter(s => s.status === 'processing').length,
      approved: signatures.filter(s => s.status === 'approved').length,
      rejected: signatures.filter(s => s.status === 'rejected').length,
      sent: signatures.filter(s => s.status === 'sent').length
    };
  }
}

// ============================================================================
// LOGGING SYSTEM
// ============================================================================

const LOG_BUFFER = [];
const MAX_LOG_BUFFER = 500;

function log(level, message, data = null) {
  const timestamp = new Date().toISOString();
  const entry = { timestamp, level, message, data };

  // Console output with colors
  const colors = {
    INFO: '\x1b[36m',    // Cyan
    WARN: '\x1b[33m',    // Yellow
    ERROR: '\x1b[31m',   // Red
    SUCCESS: '\x1b[32m', // Green
    DEBUG: '\x1b[35m'    // Magenta
  };
  const reset = '\x1b[0m';
  console.log(`${colors[level] || ''}[${timestamp}] [${level}] ${message}${reset}`);

  // Buffer for UI streaming
  LOG_BUFFER.push(entry);
  if (LOG_BUFFER.length > MAX_LOG_BUFFER) {
    LOG_BUFFER.shift();
  }

  // Broadcast to connected clients
  broadcastLog(entry);
}

function broadcastLog(entry) {
  if (wss) {
    wss.clients.forEach(client => {
      if (client.readyState === WebSocket.OPEN) {
        client.send(JSON.stringify({ type: 'log', ...entry }));
      }
    });
  }
}

// ============================================================================
// PDF AUTO-STAMPING ENGINE
// ============================================================================

class StampingEngine {
  constructor() {
    // Engineer's personal stamp/signature
    this.engineerStampPath = path.join(CONFIG.PATHS.ASSETS_DIR, 'engineer_stamp.png');
    // Company stamp
    this.companyStampPath = path.join(CONFIG.PATHS.ASSETS_DIR, 'company_stamp.png');
  }

  async stampDocument(signatureEntry) {
    log('INFO', `Starting auto-stamp for: ${signatureEntry.id}`);

    try {
      // Load the original PDF
      const originalPath = signatureEntry.originalFilePath;
      if (!fs.existsSync(originalPath)) {
        throw new Error(`Original file not found: ${originalPath}`);
      }

      const pdfBytes = fs.readFileSync(originalPath);
      const pdfDoc = await PDFDocument.load(pdfBytes);
      const pages = pdfDoc.getPages();
      const lastPage = pages[pages.length - 1];
      const { width, height } = lastPage.getSize();

      // Load fonts
      const helveticaFont = await pdfDoc.embedFont(StandardFonts.Helvetica);
      const helveticaBold = await pdfDoc.embedFont(StandardFonts.HelveticaBold);

      // Signature position
      const pos = signatureEntry.signaturePosition || CONFIG.SIGNATURE_DEFAULTS;

      // Draw signature box background
      lastPage.drawRectangle({
        x: pos.x - 10,
        y: pos.y - 10,
        width: pos.width + 20,
        height: pos.height + 80,
        color: rgb(0.98, 0.98, 0.98),
        borderColor: rgb(0.7, 0.7, 0.7),
        borderWidth: 1,
      });

      // Draw ENGINEER STAMP (personal) if exists
      if (fs.existsSync(this.engineerStampPath)) {
        const engineerImage = fs.readFileSync(this.engineerStampPath);
        const embeddedEngineer = await pdfDoc.embedPng(engineerImage);

        // Engineer stamp on the right side
        lastPage.drawImage(embeddedEngineer, {
          x: pos.x,
          y: pos.y + 20,
          width: 80,
          height: 80,
        });

        log('INFO', 'Engineer stamp applied');
      } else {
        // Placeholder signature line
        lastPage.drawLine({
          start: { x: pos.x, y: pos.y + 50 },
          end: { x: pos.x + pos.width, y: pos.y + 50 },
          thickness: 1,
          color: rgb(0, 0, 0),
        });
        log('WARN', 'Engineer stamp not found - using placeholder line');
      }

      // Draw COMPANY STAMP if exists
      if (fs.existsSync(this.companyStampPath)) {
        const companyImage = fs.readFileSync(this.companyStampPath);
        const embeddedCompany = await pdfDoc.embedPng(companyImage);

        // Company stamp next to engineer stamp
        lastPage.drawImage(embeddedCompany, {
          x: pos.x + 90,
          y: pos.y + 20,
          width: 80,
          height: 80,
        });

        log('INFO', 'Company stamp applied');
      } else {
        log('WARN', 'Company stamp not found');
      }

      // Draw engineer details
      const textY = pos.y + 10;
      const textSize = 8;

      lastPage.drawText(CONFIG.ENGINEER.name, {
        x: pos.x,
        y: textY,
        size: textSize + 2,
        font: helveticaBold,
        color: rgb(0, 0, 0),
      });

      lastPage.drawText(`מס' רישיון: ${CONFIG.ENGINEER.licenseNumber}`, {
        x: pos.x,
        y: textY - 12,
        size: textSize,
        font: helveticaFont,
        color: rgb(0, 0, 0),
      });

      lastPage.drawText(CONFIG.ENGINEER.title, {
        x: pos.x,
        y: textY - 24,
        size: textSize,
        font: helveticaFont,
        color: rgb(0.3, 0.3, 0.3),
      });

      // Draw date
      const dateStr = new Date().toLocaleDateString('he-IL');
      lastPage.drawText(`תאריך: ${dateStr}`, {
        x: pos.x,
        y: textY - 36,
        size: textSize,
        font: helveticaFont,
        color: rgb(0.3, 0.3, 0.3),
      });

      // Save the signed PDF (never overwrite original!)
      const signedFileName = path.basename(originalPath, '.pdf') + '_signed.pdf';
      const signedPath = path.join(CONFIG.PATHS.SIGNED_DIR, signedFileName);

      const signedPdfBytes = await pdfDoc.save();
      fs.writeFileSync(signedPath, signedPdfBytes);

      log('SUCCESS', `Document stamped successfully: ${signedPath}`);

      return {
        success: true,
        signedPath,
        signedFileName
      };

    } catch (error) {
      log('ERROR', `Stamping failed: ${error.message}`);
      return {
        success: false,
        error: error.message
      };
    }
  }

  async previewStamp(signatureEntry) {
    // Same as stampDocument but returns base64 for preview
    // This allows the UI to show how the document will look before final approval
    try {
      const result = await this.stampDocument(signatureEntry);
      if (result.success) {
        const pdfBytes = fs.readFileSync(result.signedPath);
        return {
          success: true,
          preview: pdfBytes.toString('base64'),
          path: result.signedPath
        };
      }
      return result;
    } catch (error) {
      return { success: false, error: error.message };
    }
  }
}

// ============================================================================
// EMAIL HARVESTER (IMAP Watcher)
// ============================================================================

class EmailHarvester {
  constructor(stackIndex) {
    this.stackIndex = stackIndex;
    this.imapConfig = null;
    this.isWatching = false;
    this.watchInterval = null;
  }

  configure(config) {
    this.imapConfig = {
      imap: {
        user: config.user,
        password: config.password,
        host: config.host || 'imap.gmail.com',
        port: config.port || 993,
        tls: true,
        tlsOptions: { rejectUnauthorized: false }
      }
    };
    log('INFO', `Email harvester configured for: ${config.user}`);
  }

  async startWatching(intervalMs = 60000) {
    if (!this.imapConfig) {
      log('ERROR', 'Email harvester not configured');
      return false;
    }

    this.isWatching = true;
    log('INFO', `Starting email watch (interval: ${intervalMs}ms)`);

    // Initial scan
    await this.scanInbox();

    // Set up interval
    this.watchInterval = setInterval(async () => {
      if (this.isWatching) {
        await this.scanInbox();
      }
    }, intervalMs);

    return true;
  }

  stopWatching() {
    this.isWatching = false;
    if (this.watchInterval) {
      clearInterval(this.watchInterval);
      this.watchInterval = null;
    }
    log('INFO', 'Email watching stopped');
  }

  async scanInbox() {
    // Note: Full IMAP implementation requires imap-simple
    // For now, this is a placeholder that can be extended
    log('INFO', 'Scanning inbox for signature requests...');

    // In production, this would:
    // 1. Connect to IMAP
    // 2. Search for unread emails with keywords
    // 3. Extract attachments
    // 4. Classify and add to stack

    // Placeholder for manual testing
    log('DEBUG', 'Email scan complete (IMAP integration pending)');
  }

  classifyDocument(subject, body) {
    const text = `${subject} ${body}`.toLowerCase();

    for (const [docType, keywords] of Object.entries(CONFIG.DOC_TYPES)) {
      for (const keyword of keywords) {
        if (text.includes(keyword.toLowerCase())) {
          return docType;
        }
      }
    }

    return 'אישור כללי';
  }

  extractProjectName(subject, body) {
    // Try to extract project name from common patterns
    const patterns = [
      /פרויקט[:\s]+([^\n,]+)/i,
      /project[:\s]+([^\n,]+)/i,
      /כתובת[:\s]+([^\n,]+)/i,
      /address[:\s]+([^\n,]+)/i,
      /רחוב[:\s]+([^\n,]+)/i,
    ];

    const text = `${subject} ${body}`;

    for (const pattern of patterns) {
      const match = text.match(pattern);
      if (match) {
        return match[1].trim();
      }
    }

    // Fallback: use subject
    return subject.substring(0, 50);
  }
}

// ============================================================================
// EMAIL SENDER (for approved documents)
// ============================================================================

class EmailSender {
  constructor() {
    this.transporter = null;
  }

  configure(config) {
    this.transporter = nodemailer.createTransport({
      host: config.host || 'smtp.gmail.com',
      port: config.port || 587,
      secure: false,
      auth: {
        user: config.user,
        pass: config.password
      }
    });
    log('INFO', 'Email sender configured');
  }

  async sendSignedDocument(signatureEntry, recipientEmail) {
    if (!this.transporter) {
      log('ERROR', 'Email sender not configured');
      return { success: false, error: 'Email not configured' };
    }

    try {
      const signedPath = signatureEntry.processedFilePath;
      if (!signedPath || !fs.existsSync(signedPath)) {
        throw new Error('Signed document not found');
      }

      const mailOptions = {
        from: CONFIG.ENGINEER.email,
        to: recipientEmail,
        subject: `מסמך חתום: ${signatureEntry.projectName} - ${signatureEntry.docType}`,
        html: `
          <div dir="rtl" style="font-family: Arial, sans-serif;">
            <h2>מסמך חתום מצורף</h2>
            <p>שלום רב,</p>
            <p>מצורף המסמך החתום עבור:</p>
            <ul>
              <li><strong>פרויקט:</strong> ${signatureEntry.projectName}</li>
              <li><strong>סוג מסמך:</strong> ${signatureEntry.docType}</li>
              <li><strong>תאריך חתימה:</strong> ${new Date().toLocaleDateString('he-IL')}</li>
            </ul>
            <p>בברכה,<br>${CONFIG.ENGINEER.name}<br>${CONFIG.ENGINEER.title}</p>
          </div>
        `,
        attachments: [{
          filename: path.basename(signedPath),
          path: signedPath
        }]
      };

      const result = await this.transporter.sendMail(mailOptions);
      log('SUCCESS', `Email sent to: ${recipientEmail}`);
      return { success: true, messageId: result.messageId };

    } catch (error) {
      log('ERROR', `Failed to send email: ${error.message}`);
      return { success: false, error: error.message };
    }
  }
}

// ============================================================================
// WEBSOCKET SERVER
// ============================================================================

let wss = null;
const stackIndex = new StackIndex();
const stampingEngine = new StampingEngine();
const emailHarvester = new EmailHarvester(stackIndex);
const emailSender = new EmailSender();

function startServer() {
  wss = new WebSocket.Server({ port: CONFIG.PORT });

  console.log(`
╔══════════════════════════════════════════════════════════════╗
║     📝 AquaBrain Signature Pipeline v1.0                     ║
║══════════════════════════════════════════════════════════════║
║  Status: ONLINE                                              ║
║  Port: ${CONFIG.PORT}                                                  ║
║  Database: ${stackIndex.data.signatures.length} signatures                                   ║
╠══════════════════════════════════════════════════════════════╣
║  🔒 Isolated Container - No conflict with bridge.js          ║
║  📁 Never overwrites original documents                      ║
║  🔄 Auto-recovery enabled                                    ║
╚══════════════════════════════════════════════════════════════╝
  `);

  wss.on('connection', (ws) => {
    log('INFO', 'Client connected to Signature Pipeline');

    // Send initial state
    ws.send(JSON.stringify({
      type: 'init',
      signatures: stackIndex.getAll(),
      stats: stackIndex.getStats(),
      logs: LOG_BUFFER.slice(-50)
    }));

    ws.on('message', async (message) => {
      try {
        const request = JSON.parse(message.toString());
        await handleRequest(ws, request);
      } catch (error) {
        log('ERROR', `Failed to process request: ${error.message}`);
        ws.send(JSON.stringify({ type: 'error', message: error.message }));
      }
    });

    ws.on('close', () => {
      log('INFO', 'Client disconnected');
    });
  });
}

async function handleRequest(ws, request) {
  const { action, data } = request;
  log('DEBUG', `Received action: ${action}`);

  switch (action) {
    // ---- Stack Management ----
    case 'get-all':
      ws.send(JSON.stringify({
        type: 'signatures',
        signatures: stackIndex.getAll(data?.filter),
        stats: stackIndex.getStats()
      }));
      break;

    case 'get-pending':
      ws.send(JSON.stringify({
        type: 'signatures',
        signatures: stackIndex.getPending(),
        stats: stackIndex.getStats()
      }));
      break;

    case 'add-signature':
      const newEntry = stackIndex.add(data);
      broadcast({ type: 'signature-added', signature: newEntry, stats: stackIndex.getStats() });
      break;

    case 'update-signature':
      const updated = stackIndex.update(data.id, data.updates);
      broadcast({ type: 'signature-updated', signature: updated, stats: stackIndex.getStats() });
      break;

    // ---- Stamping Operations ----
    case 'preview-stamp':
      const entry = stackIndex.get(data.id);
      if (entry) {
        stackIndex.update(data.id, { status: 'processing' });
        const preview = await stampingEngine.previewStamp(entry);
        ws.send(JSON.stringify({ type: 'stamp-preview', id: data.id, ...preview }));
      }
      break;

    case 'approve-signature':
      const toApprove = stackIndex.get(data.id);
      if (toApprove) {
        const stampResult = await stampingEngine.stampDocument(toApprove);
        if (stampResult.success) {
          stackIndex.update(data.id, {
            status: 'approved',
            processedFilePath: stampResult.signedPath
          });
          broadcast({ type: 'signature-approved', id: data.id, stats: stackIndex.getStats() });
        } else {
          ws.send(JSON.stringify({ type: 'error', message: stampResult.error }));
        }
      }
      break;

    case 'reject-signature':
      stackIndex.update(data.id, { status: 'rejected', notes: data.reason || 'Rejected by user' });
      broadcast({ type: 'signature-rejected', id: data.id, stats: stackIndex.getStats() });
      break;

    case 'send-signed':
      const toSend = stackIndex.get(data.id);
      if (toSend && toSend.processedFilePath) {
        const sendResult = await emailSender.sendSignedDocument(toSend, data.recipientEmail);
        if (sendResult.success) {
          stackIndex.update(data.id, { status: 'sent' });
          broadcast({ type: 'signature-sent', id: data.id, stats: stackIndex.getStats() });
        } else {
          ws.send(JSON.stringify({ type: 'error', message: sendResult.error }));
        }
      }
      break;

    // ---- Position Adjustment ----
    case 'update-position':
      stackIndex.update(data.id, { signaturePosition: data.position });
      ws.send(JSON.stringify({ type: 'position-updated', id: data.id }));
      break;

    // ---- Rollback / Undo ----
    case 'rollback':
      const toRollback = stackIndex.get(data.id);
      if (toRollback && toRollback.processedFilePath) {
        // Delete the signed file
        if (fs.existsSync(toRollback.processedFilePath)) {
          fs.unlinkSync(toRollback.processedFilePath);
        }
        stackIndex.update(data.id, {
          status: 'pending',
          processedFilePath: null
        });
        broadcast({ type: 'signature-rollback', id: data.id, stats: stackIndex.getStats() });
        log('INFO', `Rolled back signature: ${data.id}`);
      }
      break;

    // ---- File Upload (Manual) ----
    case 'upload-document':
      // data contains: { fileName, fileContent (base64), projectName, docType }
      const uploadPath = path.join(CONFIG.PATHS.PENDING_DIR, data.fileName);
      fs.writeFileSync(uploadPath, Buffer.from(data.fileContent, 'base64'));

      const uploadEntry = stackIndex.add({
        projectName: data.projectName,
        docType: data.docType,
        originalFilePath: uploadPath,
        notes: 'Manually uploaded'
      });
      broadcast({ type: 'signature-added', signature: uploadEntry, stats: stackIndex.getStats() });
      break;

    // ---- Email Configuration ----
    case 'configure-email':
      emailHarvester.configure(data);
      emailSender.configure(data);
      ws.send(JSON.stringify({ type: 'email-configured', success: true }));
      break;

    case 'start-harvester':
      const started = await emailHarvester.startWatching(data.interval || 60000);
      ws.send(JSON.stringify({ type: 'harvester-status', running: started }));
      break;

    case 'stop-harvester':
      emailHarvester.stopWatching();
      ws.send(JSON.stringify({ type: 'harvester-status', running: false }));
      break;

    // ---- Stats ----
    case 'get-stats':
      ws.send(JSON.stringify({ type: 'stats', stats: stackIndex.getStats() }));
      break;

    // ---- Logs ----
    case 'get-logs':
      ws.send(JSON.stringify({ type: 'logs', logs: LOG_BUFFER.slice(-(data.limit || 100)) }));
      break;

    default:
      ws.send(JSON.stringify({ type: 'error', message: `Unknown action: ${action}` }));
  }
}

function broadcast(message) {
  if (wss) {
    wss.clients.forEach(client => {
      if (client.readyState === WebSocket.OPEN) {
        client.send(JSON.stringify(message));
      }
    });
  }
}

// ============================================================================
// ERROR HANDLING & RECOVERY
// ============================================================================

process.on('uncaughtException', (error) => {
  log('ERROR', `Uncaught exception: ${error.message}`);
  // Auto-recovery: restart server after 5 seconds
  setTimeout(() => {
    log('INFO', 'Attempting auto-recovery...');
    startServer();
  }, 5000);
});

process.on('unhandledRejection', (reason) => {
  log('ERROR', `Unhandled rejection: ${reason}`);
});

// Graceful shutdown
process.on('SIGINT', () => {
  log('INFO', 'Shutting down Signature Pipeline...');
  emailHarvester.stopWatching();
  if (wss) {
    wss.close();
  }
  process.exit(0);
});

// ============================================================================
// START THE SERVICE
// ============================================================================

// Ensure directories exist
Object.values(CONFIG.PATHS).forEach(dirPath => {
  if (!dirPath.includes('.json') && !fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
  }
});

startServer();
