/**
 * Admiral Connection Test
 * =======================
 * Tests connectivity to Admiral legacy system login page.
 * Run before the full scrape to verify access.
 *
 * Usage: npm run test:connection
 */

import puppeteer from 'puppeteer';
import * as fs from 'fs';
import * as path from 'path';

const CONFIG = {
  loginUrl: 'https://precise.admiral.co.il//Main/Frame_Main.aspx',
  outputDir: './migration_data',
};

async function testConnection(): Promise<void> {
  console.log('\n' + '='.repeat(50));
  console.log('   ADMIRAL CONNECTION TEST');
  console.log('='.repeat(50) + '\n');

  let browser = null;

  try {
    console.log('[INFO] Launching browser...');

    browser = await puppeteer.launch({
      headless: 'new',
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--window-size=1920,1080',
      ],
      defaultViewport: {
        width: 1920,
        height: 1080,
      },
    });

    const page = await browser.newPage();
    page.setDefaultTimeout(30000);

    console.log(`[INFO] Navigating to: ${CONFIG.loginUrl}`);

    const response = await page.goto(CONFIG.loginUrl, {
      waitUntil: 'networkidle2',
      timeout: 30000,
    });

    // Check response
    const status = response?.status();
    console.log(`[INFO] HTTP Status: ${status}`);

    if (status !== 200) {
      throw new Error(`Unexpected HTTP status: ${status}`);
    }

    // Get page title
    const title = await page.title();
    console.log(`[INFO] Page Title: ${title}`);

    // Get page URL
    const currentUrl = page.url();
    console.log(`[INFO] Current URL: ${currentUrl}`);

    // Check for login form elements
    const formElements = await page.evaluate(() => {
      const inputs = document.querySelectorAll('input');
      const buttons = document.querySelectorAll('button, input[type="submit"]');
      const forms = document.querySelectorAll('form');

      return {
        inputCount: inputs.length,
        buttonCount: buttons.length,
        formCount: forms.length,
        hasPasswordField: document.querySelector('input[type="password"]') !== null,
        inputTypes: Array.from(inputs).map((i) => ({
          type: i.type,
          name: i.name,
          id: i.id,
          placeholder: i.placeholder,
        })),
      };
    });

    console.log('\n[INFO] Form Analysis:');
    console.log(`  - Forms found: ${formElements.formCount}`);
    console.log(`  - Input fields: ${formElements.inputCount}`);
    console.log(`  - Buttons: ${formElements.buttonCount}`);
    console.log(`  - Has password field: ${formElements.hasPasswordField}`);

    if (formElements.inputTypes.length > 0) {
      console.log('\n[INFO] Input Fields:');
      formElements.inputTypes.forEach((input, i) => {
        console.log(`  ${i + 1}. type="${input.type}" name="${input.name}" id="${input.id}"`);
      });
    }

    // Ensure output directory exists
    if (!fs.existsSync(CONFIG.outputDir)) {
      fs.mkdirSync(CONFIG.outputDir, { recursive: true });
    }

    // Take screenshot
    const screenshotPath = path.join(CONFIG.outputDir, 'connection_test.png');
    await page.screenshot({ path: screenshotPath, fullPage: true });
    console.log(`\n[INFO] Screenshot saved: ${screenshotPath}`);

    // Save HTML for inspection
    const html = await page.content();
    const htmlPath = path.join(CONFIG.outputDir, 'login_page.html');
    fs.writeFileSync(htmlPath, html);
    console.log(`[INFO] HTML saved: ${htmlPath}`);

    console.log('\n' + '='.repeat(50));
    console.log('   CONNECTION TEST: SUCCESS');
    console.log('='.repeat(50));
    console.log('\nThe Admiral login page is accessible.');
    console.log('You can now run the full scraper with: npm run scrape\n');

  } catch (error: any) {
    console.error('\n[ERROR] Connection test failed:', error.message);

    console.log('\n' + '='.repeat(50));
    console.log('   CONNECTION TEST: FAILED');
    console.log('='.repeat(50));
    console.log('\nPossible issues:');
    console.log('  1. Network/firewall blocking access');
    console.log('  2. Invalid URL');
    console.log('  3. Site requires VPN');
    console.log('  4. SSL certificate issues\n');

    process.exit(1);

  } finally {
    if (browser) {
      await browser.close();
    }
  }
}

testConnection().catch(console.error);
