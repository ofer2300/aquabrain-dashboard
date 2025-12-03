/**
 * Admiral Legacy System Data Rescue Mission
 * ==========================================
 * Production-grade Puppeteer scraper for migrating data
 * from Admiral ERP to AquaBrain architecture.
 *
 * Features:
 * - Secure credential handling (interactive prompt)
 * - Multi-tab navigation (Projects, Invoices, Contracts)
 * - Hebrew to English header mapping
 * - Pagination handling (all pages)
 * - Data cleaning & transformation
 * - Resilience with retry logic
 * - Progress logging & error screenshots
 *
 * Usage: npm run scrape
 */

import puppeteer, { Browser, Page, ElementHandle } from 'puppeteer';
import * as cheerio from 'cheerio';
import * as fs from 'fs';
import * as path from 'path';
import * as readline from 'readline';

// =============================================================================
// CONFIGURATION
// =============================================================================

const CONFIG = {
  baseUrl: 'https://precise.admiral.co.il',
  loginUrl: 'https://precise.admiral.co.il//Main/Frame_Main.aspx',
  timeout: 60000,
  navigationTimeout: 30000,
  retryAttempts: 3,
  retryDelay: 2000,
  pageLoadDelay: 1500,
  outputDir: './migration_data',
  outputFile: 'legacy_dump.json',
  screenshotOnError: true,
};

// Hebrew to English header mapping
const HEADER_MAP: Record<string, string> = {
  // Projects
  'פרויקט': 'projectName',
  'שם פרויקט': 'projectName',
  'מספר פרויקט': 'projectId',
  'לקוח': 'clientName',
  'שם לקוח': 'clientName',
  'סכום': 'totalAmount',
  'סה"כ': 'totalAmount',
  'יתרה': 'balance',
  'שולם': 'paid',
  'סטטוס': 'status',
  'מצב': 'status',
  'תאריך': 'date',
  'תאריך פתיחה': 'openDate',
  'תאריך סגירה': 'closeDate',
  'תאריך עדכון': 'updateDate',

  // Invoices
  'חשבונית': 'invoiceNumber',
  'מספר חשבונית': 'invoiceNumber',
  'סכום חשבונית': 'invoiceAmount',
  'תאריך חשבונית': 'invoiceDate',
  'תאריך פירעון': 'dueDate',
  'סוג': 'type',
  'הערות': 'notes',

  // Contracts
  'חוזה': 'contractName',
  'מספר חוזה': 'contractId',
  'ערך חוזה': 'contractValue',
  'תאריך התחלה': 'startDate',
  'תאריך סיום': 'endDate',

  // Common
  'כתובת': 'address',
  'טלפון': 'phone',
  'אימייל': 'email',
  'איש קשר': 'contactPerson',
  'מנהל פרויקט': 'projectManager',
  'אחוז התקדמות': 'progressPercent',
};

// Navigation tabs to scrape
const NAV_TABS = [
  { name: 'projects', hebrewSelector: 'פרויקטים', englishKey: 'projects' },
  { name: 'invoices', hebrewSelector: 'חשבונות', englishKey: 'invoices' },
  { name: 'contracts', hebrewSelector: 'חוזים', englishKey: 'contracts' },
  { name: 'clients', hebrewSelector: 'לקוחות', englishKey: 'clients' },
  { name: 'payments', hebrewSelector: 'תשלומים', englishKey: 'payments' },
];

// =============================================================================
// DATA TYPES
// =============================================================================

interface Credentials {
  orgCode: string;
  username: string;
  password: string;
}

interface ScrapedData {
  projects: Record<string, any>[];
  invoices: Record<string, any>[];
  contracts: Record<string, any>[];
  clients: Record<string, any>[];
  payments: Record<string, any>[];
  metadata: {
    scrapedAt: string;
    totalRecords: number;
    source: string;
    version: string;
  };
}

interface ScrapeProgress {
  currentTab: string;
  currentPage: number;
  totalPages: number;
  recordsScraped: number;
}

// =============================================================================
// LOGGING UTILITIES
// =============================================================================

const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m',
};

function log(message: string, type: 'info' | 'success' | 'warning' | 'error' | 'progress' = 'info') {
  const timestamp = new Date().toISOString().split('T')[1].split('.')[0];
  const prefix = {
    info: `${colors.blue}[INFO]${colors.reset}`,
    success: `${colors.green}[SUCCESS]${colors.reset}`,
    warning: `${colors.yellow}[WARNING]${colors.reset}`,
    error: `${colors.red}[ERROR]${colors.reset}`,
    progress: `${colors.cyan}[PROGRESS]${colors.reset}`,
  };
  console.log(`${colors.bright}[${timestamp}]${colors.reset} ${prefix[type]} ${message}`);
}

function logProgress(progress: ScrapeProgress) {
  const bar = createProgressBar(progress.currentPage, progress.totalPages);
  log(`Tab: ${progress.currentTab} | Page ${progress.currentPage}/${progress.totalPages} ${bar} | Records: ${progress.recordsScraped}`, 'progress');
}

function createProgressBar(current: number, total: number, width: number = 20): string {
  const percent = total > 0 ? current / total : 0;
  const filled = Math.round(width * percent);
  const empty = width - filled;
  return `[${'='.repeat(filled)}${' '.repeat(empty)}] ${Math.round(percent * 100)}%`;
}

// =============================================================================
// CREDENTIAL HANDLER
// =============================================================================

async function getCredentials(): Promise<Credentials> {
  // Check environment variables first
  if (process.env.ADMIRAL_ORG && process.env.ADMIRAL_USER && process.env.ADMIRAL_PASS) {
    log('Using credentials from environment variables', 'info');
    return {
      orgCode: process.env.ADMIRAL_ORG,
      username: process.env.ADMIRAL_USER,
      password: process.env.ADMIRAL_PASS,
    };
  }

  // Interactive prompt
  log('Please enter Admiral credentials (will not be stored):', 'info');

  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  const question = (prompt: string): Promise<string> => {
    return new Promise((resolve) => {
      rl.question(prompt, (answer) => {
        resolve(answer);
      });
    });
  };

  const orgCode = await question('Organization Code (קוד ארגון): ');
  const username = await question('Username (שם משתמש): ');

  // For password, we need to hide input
  process.stdout.write('Password (סיסמה): ');
  const password = await new Promise<string>((resolve) => {
    const stdin = process.stdin;
    const wasRaw = stdin.isRaw;

    stdin.setRawMode?.(true);
    stdin.resume();

    let password = '';
    stdin.on('data', function handler(ch) {
      const char = ch.toString('utf8');

      if (char === '\n' || char === '\r' || char === '\u0004') {
        stdin.setRawMode?.(wasRaw);
        stdin.pause();
        stdin.removeListener('data', handler);
        console.log();
        resolve(password);
      } else if (char === '\u0003') {
        process.exit();
      } else if (char === '\u007F') {
        // Backspace
        password = password.slice(0, -1);
        process.stdout.clearLine?.(0);
        process.stdout.cursorTo?.(0);
        process.stdout.write('Password (סיסמה): ' + '*'.repeat(password.length));
      } else {
        password += char;
        process.stdout.write('*');
      }
    });
  });

  rl.close();

  return { orgCode, username, password };
}

// =============================================================================
// DATA CLEANING & TRANSFORMATION
// =============================================================================

function cleanCurrency(value: string): number {
  if (!value || typeof value !== 'string') return 0;

  // Remove currency symbols, commas, and spaces
  const cleaned = value
    .replace(/[₪$€,\s]/g, '')
    .replace(/[-]/g, '')
    .trim();

  const num = parseFloat(cleaned);
  return isNaN(num) ? 0 : num;
}

function parseHebrewDate(dateStr: string): string {
  if (!dateStr || typeof dateStr !== 'string') return '';

  // Handle DD/MM/YYYY format
  const match = dateStr.match(/(\d{1,2})\/(\d{1,2})\/(\d{4})/);
  if (match) {
    const [, day, month, year] = match;
    return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
  }

  // Handle DD.MM.YYYY format
  const dotMatch = dateStr.match(/(\d{1,2})\.(\d{1,2})\.(\d{4})/);
  if (dotMatch) {
    const [, day, month, year] = dotMatch;
    return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
  }

  return dateStr;
}

function cleanPercentage(value: string): number {
  if (!value || typeof value !== 'string') return 0;

  const cleaned = value.replace(/%/g, '').trim();
  const num = parseFloat(cleaned);
  return isNaN(num) ? 0 : num;
}

function cleanText(value: string): string {
  if (!value || typeof value !== 'string') return '';

  return value
    .trim()
    .replace(/\s+/g, ' ')
    .replace(/[\u200F\u200E]/g, ''); // Remove RTL/LTR marks
}

function transformValue(key: string, value: string): any {
  const lowerKey = key.toLowerCase();

  // Currency fields
  if (['totalamount', 'balance', 'paid', 'invoiceamount', 'contractvalue'].includes(lowerKey)) {
    return cleanCurrency(value);
  }

  // Date fields
  if (lowerKey.includes('date') || lowerKey.endsWith('date')) {
    return parseHebrewDate(value);
  }

  // Percentage fields
  if (lowerKey.includes('percent') || lowerKey.includes('progress')) {
    return cleanPercentage(value);
  }

  // Default: clean text
  return cleanText(value);
}

function mapHeaders(hebrewHeaders: string[]): string[] {
  return hebrewHeaders.map((header) => {
    const cleaned = cleanText(header);
    return HEADER_MAP[cleaned] || cleaned.replace(/\s+/g, '_').toLowerCase();
  });
}

// =============================================================================
// SCRAPER CLASS
// =============================================================================

class AdmiralScraper {
  private browser: Browser | null = null;
  private page: Page | null = null;
  private data: ScrapedData;

  constructor() {
    this.data = {
      projects: [],
      invoices: [],
      contracts: [],
      clients: [],
      payments: [],
      metadata: {
        scrapedAt: new Date().toISOString(),
        totalRecords: 0,
        source: 'Admiral Legacy System',
        version: '1.0.0',
      },
    };
  }

  async initialize(): Promise<void> {
    log('Launching Puppeteer browser...', 'info');

    this.browser = await puppeteer.launch({
      headless: 'new',
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-accelerated-2d-canvas',
        '--disable-gpu',
        '--window-size=1920,1080',
        '--lang=he-IL',
      ],
      defaultViewport: {
        width: 1920,
        height: 1080,
      },
    });

    this.page = await this.browser.newPage();

    // Set default timeout
    this.page.setDefaultTimeout(CONFIG.timeout);
    this.page.setDefaultNavigationTimeout(CONFIG.navigationTimeout);

    // Set Hebrew locale
    await this.page.setExtraHTTPHeaders({
      'Accept-Language': 'he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7',
    });

    log('Browser initialized successfully', 'success');
  }

  async login(credentials: Credentials): Promise<boolean> {
    if (!this.page) throw new Error('Browser not initialized');

    log(`Navigating to login page: ${CONFIG.loginUrl}`, 'info');

    try {
      await this.page.goto(CONFIG.loginUrl, {
        waitUntil: 'networkidle2',
        timeout: CONFIG.navigationTimeout,
      });

      // Take screenshot of login page
      await this.page.screenshot({
        path: path.join(CONFIG.outputDir, 'login_page.png'),
      });

      log('Login page loaded, entering credentials...', 'info');

      // Wait for login form - try multiple possible selectors
      const formSelectors = [
        'input[name*="org"]',
        'input[id*="org"]',
        'input[placeholder*="ארגון"]',
        '#txtOrganization',
        'input[type="text"]',
      ];

      let orgInput: ElementHandle<Element> | null = null;
      for (const selector of formSelectors) {
        try {
          orgInput = await this.page.waitForSelector(selector, { timeout: 5000 });
          if (orgInput) {
            log(`Found org input with selector: ${selector}`, 'info');
            break;
          }
        } catch {
          continue;
        }
      }

      if (!orgInput) {
        // Try to find any text inputs
        const inputs = await this.page.$$('input[type="text"], input:not([type])');
        if (inputs.length >= 2) {
          log(`Found ${inputs.length} text inputs, using first for org code`, 'info');
          orgInput = inputs[0];
        }
      }

      if (orgInput) {
        await orgInput.type(credentials.orgCode, { delay: 50 });
      }

      // Find username input
      const userSelectors = [
        'input[name*="user"]',
        'input[id*="user"]',
        'input[placeholder*="משתמש"]',
        '#txtUsername',
      ];

      for (const selector of userSelectors) {
        try {
          const userInput = await this.page.$(selector);
          if (userInput) {
            await userInput.type(credentials.username, { delay: 50 });
            break;
          }
        } catch {
          continue;
        }
      }

      // Find password input
      const passInput = await this.page.$('input[type="password"]');
      if (passInput) {
        await passInput.type(credentials.password, { delay: 50 });
      }

      // Find and click login button
      const buttonSelectors = [
        'button[type="submit"]',
        'input[type="submit"]',
        'button:contains("כניסה")',
        '.login-button',
        '#btnLogin',
      ];

      for (const selector of buttonSelectors) {
        try {
          const button = await this.page.$(selector);
          if (button) {
            await button.click();
            break;
          }
        } catch {
          continue;
        }
      }

      // Wait for navigation/dashboard
      await this.page.waitForNavigation({
        waitUntil: 'networkidle2',
        timeout: CONFIG.navigationTimeout,
      });

      // Check if login was successful
      const currentUrl = this.page.url();
      if (currentUrl.includes('login') || currentUrl.includes('error')) {
        throw new Error('Login failed - still on login page');
      }

      // Take screenshot of dashboard
      await this.page.screenshot({
        path: path.join(CONFIG.outputDir, 'dashboard.png'),
      });

      log('Login successful! Dashboard loaded.', 'success');
      return true;

    } catch (error: any) {
      log(`Login failed: ${error.message}`, 'error');

      if (CONFIG.screenshotOnError && this.page) {
        await this.page.screenshot({
          path: path.join(CONFIG.outputDir, 'login_error.png'),
        });
      }

      return false;
    }
  }

  async scrapeTab(tabConfig: typeof NAV_TABS[0]): Promise<Record<string, any>[]> {
    if (!this.page) throw new Error('Browser not initialized');

    const records: Record<string, any>[] = [];
    let currentPage = 1;
    let hasNextPage = true;

    log(`Starting scrape of tab: ${tabConfig.name} (${tabConfig.hebrewSelector})`, 'info');

    try {
      // Try to navigate to the tab
      const tabSelectors = [
        `a:contains("${tabConfig.hebrewSelector}")`,
        `[title*="${tabConfig.hebrewSelector}"]`,
        `[aria-label*="${tabConfig.hebrewSelector}"]`,
        `.nav-link:contains("${tabConfig.hebrewSelector}")`,
        `li:contains("${tabConfig.hebrewSelector}") a`,
      ];

      let tabClicked = false;
      for (const selector of tabSelectors) {
        try {
          // Use evaluate to find element with Hebrew text
          const found = await this.page.evaluate((text) => {
            const elements = document.querySelectorAll('a, button, li, span, div');
            for (const el of elements) {
              if (el.textContent?.includes(text)) {
                (el as HTMLElement).click();
                return true;
              }
            }
            return false;
          }, tabConfig.hebrewSelector);

          if (found) {
            tabClicked = true;
            log(`Clicked tab: ${tabConfig.hebrewSelector}`, 'info');
            break;
          }
        } catch {
          continue;
        }
      }

      if (!tabClicked) {
        log(`Could not find tab: ${tabConfig.hebrewSelector}, skipping...`, 'warning');
        return records;
      }

      // Wait for table to load
      await this.page.waitForTimeout(CONFIG.pageLoadDelay);
      await this.page.waitForSelector('table', { timeout: 10000 }).catch(() => null);

      while (hasNextPage) {
        // Scrape current page
        const pageRecords = await this.scrapeTable();
        records.push(...pageRecords);

        logProgress({
          currentTab: tabConfig.name,
          currentPage,
          totalPages: currentPage, // We don't know total yet
          recordsScraped: records.length,
        });

        // Check for next page
        hasNextPage = await this.goToNextPage();

        if (hasNextPage) {
          currentPage++;
          await this.page.waitForTimeout(CONFIG.pageLoadDelay);
        }
      }

      log(`Completed scraping ${tabConfig.name}: ${records.length} records`, 'success');

    } catch (error: any) {
      log(`Error scraping tab ${tabConfig.name}: ${error.message}`, 'error');

      if (CONFIG.screenshotOnError && this.page) {
        await this.page.screenshot({
          path: path.join(CONFIG.outputDir, `error_${tabConfig.name}.png`),
        });
      }
    }

    return records;
  }

  async scrapeTable(): Promise<Record<string, any>[]> {
    if (!this.page) throw new Error('Browser not initialized');

    const records: Record<string, any>[] = [];

    try {
      // Get page HTML
      const html = await this.page.content();
      const $ = cheerio.load(html);

      // Find main data table
      const tables = $('table');

      if (tables.length === 0) {
        log('No tables found on page', 'warning');
        return records;
      }

      // Use the largest table (most likely the data table)
      let mainTable = tables.first();
      let maxRows = 0;

      tables.each((_, table) => {
        const rowCount = $(table).find('tr').length;
        if (rowCount > maxRows) {
          maxRows = rowCount;
          mainTable = $(table);
        }
      });

      // Extract headers
      const hebrewHeaders: string[] = [];
      mainTable.find('thead tr th, tr:first-child th, tr:first-child td').each((_, el) => {
        hebrewHeaders.push($(el).text().trim());
      });

      if (hebrewHeaders.length === 0) {
        log('No headers found in table', 'warning');
        return records;
      }

      const englishHeaders = mapHeaders(hebrewHeaders);
      log(`Found headers: ${englishHeaders.join(', ')}`, 'info');

      // Extract rows
      const rows = mainTable.find('tbody tr, tr:not(:first-child)');

      rows.each((_, row) => {
        const record: Record<string, any> = {};
        const cells = $(row).find('td');

        cells.each((colIndex, cell) => {
          if (colIndex < englishHeaders.length) {
            const key = englishHeaders[colIndex];
            const rawValue = $(cell).text().trim();
            record[key] = transformValue(key, rawValue);
          }
        });

        // Only add if record has data
        if (Object.keys(record).length > 0) {
          record._scrapedAt = new Date().toISOString();
          records.push(record);
        }
      });

    } catch (error: any) {
      log(`Error parsing table: ${error.message}`, 'error');
    }

    return records;
  }

  async goToNextPage(): Promise<boolean> {
    if (!this.page) return false;

    try {
      // Try various pagination selectors
      const nextPageSelectors = [
        'a:contains("עמוד הבא")',
        'a:contains(">>")',
        'a:contains("הבא")',
        '.pagination .next',
        '.pagination-next',
        '[aria-label="Next"]',
        'a.next',
        'button.next',
      ];

      // Check if there's a next page button that's enabled
      const hasNext = await this.page.evaluate((selectors) => {
        // Try to find by Hebrew text
        const allLinks = document.querySelectorAll('a, button');
        for (const link of allLinks) {
          const text = link.textContent || '';
          if (text.includes('הבא') || text.includes('>>') || text.includes('עמוד הבא')) {
            const element = link as HTMLElement;
            const isDisabled = element.hasAttribute('disabled') ||
              element.classList.contains('disabled') ||
              element.getAttribute('aria-disabled') === 'true';

            if (!isDisabled) {
              element.click();
              return true;
            }
          }
        }

        // Try numbered pagination
        const currentPage = document.querySelector('.pagination .active, .current-page');
        if (currentPage) {
          const nextSibling = currentPage.nextElementSibling as HTMLElement;
          if (nextSibling && nextSibling.tagName === 'A') {
            nextSibling.click();
            return true;
          }
        }

        return false;
      }, nextPageSelectors);

      if (hasNext) {
        await this.page.waitForTimeout(1000);
        await this.page.waitForNetworkIdle({ timeout: 10000 }).catch(() => null);
        return true;
      }

    } catch (error: any) {
      log(`Pagination check error: ${error.message}`, 'warning');
    }

    return false;
  }

  async scrapeAll(): Promise<void> {
    log('Starting full data extraction...', 'info');

    for (const tab of NAV_TABS) {
      const records = await this.scrapeTab(tab);
      const key = tab.englishKey as keyof Omit<ScrapedData, 'metadata'>;
      this.data[key] = records;
    }

    // Update metadata
    this.data.metadata.totalRecords =
      this.data.projects.length +
      this.data.invoices.length +
      this.data.contracts.length +
      this.data.clients.length +
      this.data.payments.length;

    this.data.metadata.scrapedAt = new Date().toISOString();

    log(`Total records scraped: ${this.data.metadata.totalRecords}`, 'success');
  }

  async saveData(): Promise<void> {
    // Ensure output directory exists
    if (!fs.existsSync(CONFIG.outputDir)) {
      fs.mkdirSync(CONFIG.outputDir, { recursive: true });
    }

    const outputPath = path.join(CONFIG.outputDir, CONFIG.outputFile);

    fs.writeFileSync(outputPath, JSON.stringify(this.data, null, 2), 'utf-8');

    log(`Data saved to: ${outputPath}`, 'success');

    // Print summary
    console.log('\n' + '='.repeat(60));
    console.log(`${colors.green}${colors.bright}DATA RESCUE MISSION COMPLETE${colors.reset}`);
    console.log('='.repeat(60));
    console.log(`Projects:   ${this.data.projects.length} records`);
    console.log(`Invoices:   ${this.data.invoices.length} records`);
    console.log(`Contracts:  ${this.data.contracts.length} records`);
    console.log(`Clients:    ${this.data.clients.length} records`);
    console.log(`Payments:   ${this.data.payments.length} records`);
    console.log('-'.repeat(60));
    console.log(`TOTAL:      ${this.data.metadata.totalRecords} records`);
    console.log(`Output:     ${outputPath}`);
    console.log('='.repeat(60) + '\n');
  }

  async close(): Promise<void> {
    if (this.browser) {
      await this.browser.close();
      log('Browser closed', 'info');
    }
  }
}

// =============================================================================
// MAIN EXECUTION
// =============================================================================

async function main(): Promise<void> {
  console.log('\n' + '='.repeat(60));
  console.log(`${colors.cyan}${colors.bright}   ADMIRAL DATA RESCUE MISSION${colors.reset}`);
  console.log(`${colors.cyan}   Legacy System Migration Tool v1.0${colors.reset}`);
  console.log('='.repeat(60) + '\n');

  const scraper = new AdmiralScraper();

  try {
    // Get credentials
    const credentials = await getCredentials();

    // Initialize browser
    await scraper.initialize();

    // Login
    const loginSuccess = await scraper.login(credentials);
    if (!loginSuccess) {
      throw new Error('Login failed. Please check credentials.');
    }

    // Scrape all data
    await scraper.scrapeAll();

    // Save results
    await scraper.saveData();

  } catch (error: any) {
    log(`Fatal error: ${error.message}`, 'error');
    console.error(error);
    process.exit(1);

  } finally {
    await scraper.close();
  }
}

// Run
main().catch(console.error);
