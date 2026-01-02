/**
 * Admiral Data Rescue - Playwright Edition
 * =========================================
 * Using Playwright for better WSL2 compatibility
 */

import { chromium, Browser, Page } from 'playwright';
import * as cheerio from 'cheerio';
import * as fs from 'fs';
import * as path from 'path';

// =============================================================================
// CONFIGURATION
// =============================================================================

const CONFIG = {
  baseUrl: 'https://precise.admiral.co.il',
  loginUrl: 'https://precise.admiral.co.il//Main/Frame_Main.aspx',
  timeout: 60000,
  navigationTimeout: 30000,
  pageLoadDelay: 2000,
  outputDir: './migration_data',
};

// Hebrew to English header mapping - EXACT from Admiral screenshots
const HEADER_MAP: Record<string, string> = {
  'מנהל פרויקט': 'projectManager',
  "מס'": 'projectId',
  'מס': 'projectId',
  'פרויקט': 'projectName',
  'לקוח': 'clientName',
  'בסיס התקשרות': 'contractBase',
  'סכום': 'contractAmount',
  'שולם': 'totalPaid',
  'יתרה': 'balance',
  'אחוז התקדמות': 'progressPercentage',
  '% התקדמות': 'progressPercentage',
  'חשבון הבא': 'nextInvoiceMilestone',
  'רווח': 'profitability',
  'רווחיות': 'profitability',
  'שם פרויקט': 'projectName',
  'מספר פרויקט': 'projectId',
  'שם לקוח': 'clientName',
  'סה"כ': 'totalAmount',
  'סטטוס': 'status',
  'מצב': 'status',
  'תאריך': 'date',
  'תאריך פתיחה': 'openDate',
  'תאריך סגירה': 'closeDate',
  'חשבונית': 'invoiceNumber',
  'מספר חשבונית': 'invoiceNumber',
  'סכום חשבונית': 'invoiceAmount',
  'תאריך חשבונית': 'invoiceDate',
  'תאריך פירעון': 'dueDate',
  'סוג': 'type',
  'הערות': 'notes',
  'חוזה': 'contractName',
  'מספר חוזה': 'contractId',
  'ערך חוזה': 'contractValue',
  'תאריך התחלה': 'startDate',
  'תאריך סיום': 'endDate',
  'כתובת': 'address',
  'טלפון': 'phone',
  'אימייל': 'email',
  'איש קשר': 'contactPerson',
  'תיאור': 'description',
  'עיר': 'city',
  'ח.פ': 'companyId',
};

const NAV_TABS = [
  { name: 'contractsBalance', hebrewSelector: 'יתרות חוזים', directUrl: '/Projects/ContractsBudgetList.aspx' },
  { name: 'projects', hebrewSelector: 'פרויקטים', directUrl: '/Projects/ProjectsList.aspx' },
  { name: 'invoices', hebrewSelector: 'חשבונות', directUrl: '/Invoices/InvoicesList.aspx' },
  { name: 'contracts', hebrewSelector: 'חוזים', directUrl: '/Contracts/ContractsList.aspx' },
  { name: 'clients', hebrewSelector: 'לקוחות', directUrl: '/Clients/ClientsList.aspx' },
  { name: 'payments', hebrewSelector: 'תשלומים', directUrl: '/Payments/PaymentsList.aspx' },
];

// =============================================================================
// DATA TYPES
// =============================================================================

interface ScrapedData {
  [key: string]: any[];
  metadata?: any;
}

// =============================================================================
// UTILITIES
// =============================================================================

const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
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

function cleanCurrency(value: string): number {
  if (!value) return 0;
  const cleaned = value.replace(/[₪$€,\s-]/g, '').trim();
  return parseFloat(cleaned) || 0;
}

function parseHebrewDate(dateStr: string): string {
  if (!dateStr) return '';
  const match = dateStr.match(/(\d{1,2})\/(\d{1,2})\/(\d{4})/);
  if (match) {
    const [, day, month, year] = match;
    return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
  }
  return dateStr;
}

function cleanText(value: string): string {
  if (!value) return '';
  return value.trim().replace(/\s+/g, ' ').replace(/[\u200F\u200E]/g, '');
}

function mapHeaders(hebrewHeaders: string[]): string[] {
  return hebrewHeaders.map((header) => {
    const cleaned = cleanText(header);
    return HEADER_MAP[cleaned] || cleaned.replace(/\s+/g, '_').toLowerCase();
  });
}

function transformValue(key: string, value: string): any {
  const lowerKey = key.toLowerCase();
  if (['totalamount', 'balance', 'paid', 'totalpaid', 'contractamount', 'invoiceamount'].includes(lowerKey)) {
    return cleanCurrency(value);
  }
  if (lowerKey.includes('date')) {
    return parseHebrewDate(value);
  }
  if (lowerKey.includes('percent') || lowerKey.includes('progress')) {
    return parseFloat(value.replace(/%/g, '')) || 0;
  }
  return cleanText(value);
}

// =============================================================================
// MAIN SCRAPER
// =============================================================================

async function main() {
  console.log('\n' + '█'.repeat(60));
  console.log(`${colors.green}${colors.bright}   🚀 ADMIRAL DATA RESCUE - PLAYWRIGHT EDITION${colors.reset}`);
  console.log('█'.repeat(60) + '\n');

  // SECURITY: Credentials MUST be set via environment variables - no fallbacks
  const orgCode = process.env.ADMIRAL_ORG;
  const username = process.env.ADMIRAL_USER;
  const password = process.env.ADMIRAL_PASS;

  if (!orgCode || !username || !password) {
    console.error(`${colors.red}${colors.bright}ERROR: Missing required credentials${colors.reset}`);
    console.error('Please set environment variables: ADMIRAL_ORG, ADMIRAL_USER, ADMIRAL_PASS');
    process.exit(1);
  }

  const credentials = { orgCode, username, password };

  log(`Credentials: Org=${credentials.orgCode}, User=${credentials.username}`, 'info');

  // Ensure output directory exists
  if (!fs.existsSync(CONFIG.outputDir)) {
    fs.mkdirSync(CONFIG.outputDir, { recursive: true });
  }

  let browser: Browser | null = null;
  const allData: ScrapedData = {};
  let totalRecords = 0;

  try {
    log('Launching Playwright Chromium...', 'info');

    // Connect to Windows Chrome via CDP WebSocket
    const cdpUrl = 'http://10.255.255.254:9222';
    log(`Connecting to Chrome at ${cdpUrl}...`, 'info');

    browser = await chromium.connectOverCDP(cdpUrl);
    log('Connected to Chrome!', 'success');

    // Get existing context or create new one
    const contexts = browser.contexts();
    const context = contexts.length > 0 ? contexts[0] : await browser.newContext({
      viewport: { width: 1920, height: 1080 },
      locale: 'he-IL',
    });

    // Get existing page or create new one
    const pages = context.pages();
    const page = pages.length > 0 ? pages[0] : await context.newPage();
    page.setDefaultTimeout(CONFIG.timeout);
    page.setDefaultNavigationTimeout(CONFIG.navigationTimeout);

    log(`Browser launched successfully`, 'success');

    // ========== LOGIN ==========
    log(`Navigating to: ${CONFIG.loginUrl}`, 'info');
    await page.goto(CONFIG.loginUrl, { waitUntil: 'networkidle' });

    await page.screenshot({ path: path.join(CONFIG.outputDir, 'login_page.png') });
    log('Login page loaded', 'success');

    // Find and fill login form
    log('Filling login form...', 'info');

    // Try to find form inputs
    const inputs = await page.$$('input[type="text"], input:not([type])');
    log(`Found ${inputs.length} text inputs`, 'info');

    // Organization code (first input usually)
    const orgInput = await page.$('input[name*="org"], input[id*="org"], input[placeholder*="ארגון"]')
                  || (inputs.length > 0 ? inputs[0] : null);
    if (orgInput) {
      await orgInput.fill(credentials.orgCode);
      log('Filled organization code', 'success');
    }

    // Username
    const userInput = await page.$('input[name*="user"], input[id*="user"], input[placeholder*="משתמש"]')
                   || (inputs.length > 1 ? inputs[1] : null);
    if (userInput) {
      await userInput.fill(credentials.username);
      log('Filled username', 'success');
    }

    // Password
    const passInput = await page.$('input[type="password"]');
    if (passInput) {
      await passInput.fill(credentials.password);
      log('Filled password', 'success');
    }

    await page.screenshot({ path: path.join(CONFIG.outputDir, 'login_filled.png') });

    // Click login button
    const loginButton = await page.$('button[type="submit"], input[type="submit"], button:has-text("כניסה"), input[value*="כניסה"]');
    if (loginButton) {
      await loginButton.click();
      log('Clicked login button', 'info');
    } else {
      // Try pressing Enter
      await page.keyboard.press('Enter');
      log('Pressed Enter to submit', 'info');
    }

    // Wait for navigation
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(CONFIG.pageLoadDelay);

    await page.screenshot({ path: path.join(CONFIG.outputDir, 'after_login.png') });

    const currentUrl = page.url();
    log(`Current URL after login: ${currentUrl}`, 'info');

    if (currentUrl.includes('login') || currentUrl.includes('error')) {
      log('Login may have failed - check screenshots', 'warning');
    } else {
      log('Login appears successful!', 'success');
    }

    // ========== SCRAPE EACH TAB ==========
    console.log('\n' + '█'.repeat(60));
    console.log(`${colors.green}${colors.bright}   🚀 YOLO MODE - SCRAPING ALL TABS${colors.reset}`);
    console.log('█'.repeat(60) + '\n');

    for (const tab of NAV_TABS) {
      log(`\n${'='.repeat(50)}`, 'info');
      log(`SCRAPING: ${tab.name.toUpperCase()} (${tab.hebrewSelector})`, 'info');
      log(`${'='.repeat(50)}`, 'info');

      const records: any[] = [];
      let currentPage = 1;
      let hasNextPage = true;

      try {
        // Navigate to tab
        const fullUrl = `${CONFIG.baseUrl}${tab.directUrl}`;
        log(`Navigating to: ${fullUrl}`, 'info');

        await page.goto(fullUrl, { waitUntil: 'networkidle' });
        await page.waitForTimeout(CONFIG.pageLoadDelay);

        await page.screenshot({ path: path.join(CONFIG.outputDir, `${tab.name}_page_1.png`) });

        // Scrape pages
        while (hasNextPage) {
          log(`Scraping page ${currentPage}...`, 'progress');

          // Get HTML and parse with Cheerio
          const html = await page.content();
          const $ = cheerio.load(html);

          // Find main table
          let mainTable = $('table').first();
          let maxRows = 0;
          $('table').each((_, table) => {
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

          if (hebrewHeaders.length > 0) {
            const englishHeaders = mapHeaders(hebrewHeaders);
            log(`Headers: ${englishHeaders.slice(0, 5).join(', ')}...`, 'info');

            // Extract rows
            const rows = mainTable.find('tbody tr, tr:not(:first-child)');
            rows.each((_, row) => {
              const record: any = {};
              const cells = $(row).find('td');

              cells.each((colIndex, cell) => {
                if (colIndex < englishHeaders.length) {
                  const key = englishHeaders[colIndex];
                  const rawValue = $(cell).text().trim();
                  record[key] = transformValue(key, rawValue);
                }
              });

              if (Object.keys(record).length > 0) {
                record._scrapedAt = new Date().toISOString();
                record._page = currentPage;
                records.push(record);
              }
            });

            log(`Page ${currentPage}: ${rows.length} rows found, ${records.length} total records`, 'progress');
          }

          // Save incremental checkpoint
          const checkpoint = {
            timestamp: new Date().toISOString(),
            tab: tab.name,
            page: currentPage,
            records: records.slice(-50), // Last 50 records
          };
          fs.appendFileSync(
            path.join(CONFIG.outputDir, 'raw_data_dump.jsonl'),
            JSON.stringify(checkpoint) + '\n'
          );

          // Check for next page
          hasNextPage = await page.evaluate(() => {
            const links = document.querySelectorAll('a, button');
            for (const link of links) {
              const text = link.textContent || '';
              if (text.includes('הבא') || text.includes('>>') || text.includes('עמוד הבא')) {
                const el = link as HTMLElement;
                if (!el.hasAttribute('disabled') && !el.classList.contains('disabled')) {
                  el.click();
                  return true;
                }
              }
            }
            return false;
          });

          if (hasNextPage) {
            currentPage++;
            await page.waitForLoadState('networkidle');
            await page.waitForTimeout(CONFIG.pageLoadDelay);
          }
        }

        log(`✅ Completed ${tab.name}: ${records.length} records from ${currentPage} pages`, 'success');
        allData[tab.name] = records;
        totalRecords += records.length;

      } catch (error: any) {
        log(`Error on ${tab.name}: ${error.message}`, 'error');
        await page.screenshot({ path: path.join(CONFIG.outputDir, `error_${tab.name}.png`) });
        allData[tab.name] = records; // Save what we have
        totalRecords += records.length;
      }
    }

    // ========== SAVE FINAL DATA ==========
    allData.metadata = {
      scrapedAt: new Date().toISOString(),
      totalRecords,
      source: 'Admiral Legacy System',
      version: '2.0.0-playwright',
    };

    const outputPath = path.join(CONFIG.outputDir, 'legacy_dump.json');
    fs.writeFileSync(outputPath, JSON.stringify(allData, null, 2), 'utf-8');

    // Print summary
    console.log('\n' + '█'.repeat(60));
    console.log(`${colors.green}${colors.bright}   🎯 DATA RESCUE MISSION COMPLETE${colors.reset}`);
    console.log('█'.repeat(60));
    for (const tab of NAV_TABS) {
      const count = allData[tab.name]?.length || 0;
      console.log(`${tab.name}: ${count} records`);
    }
    console.log('-'.repeat(60));
    console.log(`${colors.green}${colors.bright}TOTAL: ${totalRecords} records${colors.reset}`);
    console.log(`${colors.yellow}Output: ${outputPath}${colors.reset}`);
    console.log('█'.repeat(60) + '\n');

  } catch (error: any) {
    log(`Fatal error: ${error.message}`, 'error');
    console.error(error);
  } finally {
    if (browser) {
      await browser.close();
      log('Browser closed', 'info');
    }
  }
}

main().catch(console.error);
