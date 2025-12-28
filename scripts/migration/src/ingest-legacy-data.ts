#!/usr/bin/env npx ts-node
/**
 * Admiral Legacy Data Ingestor
 * ============================
 *
 * Ingests JSON data exported from Admiral via Browser Console
 * Validates, normalizes, and saves to migration_data/
 *
 * Usage:
 *   npx ts-node src/ingest-legacy-data.ts <input_json_file>
 *   npx ts-node src/ingest-legacy-data.ts admiral_contracts_dump.json
 */

import * as fs from 'fs';
import * as path from 'path';
import {
  AdmiralDataDump,
  AdmiralRawContract,
  AdmiralRawProject,
  AdmiralRawInvoice,
  AdmiralRawClient,
  NormalizedContract,
  NormalizedProject,
  NormalizedInvoice,
  NormalizedClient,
  NormalizedDataOutput,
} from './types';
import {
  normalizeContract,
  normalizeProject,
  normalizeInvoice,
  normalizeClient,
  validateContract,
  validateProject,
  validateInvoice,
  validateClient,
} from './utils/dataCleaners';

// =============================================================================
// CONFIGURATION
// =============================================================================

const OUTPUT_DIR = path.join(__dirname, '..', 'migration_data');

const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m',
};

function log(message: string, type: 'info' | 'success' | 'warning' | 'error' = 'info') {
  const prefix = {
    info: `${colors.blue}[INFO]${colors.reset}`,
    success: `${colors.green}[SUCCESS]${colors.reset}`,
    warning: `${colors.yellow}[WARNING]${colors.reset}`,
    error: `${colors.red}[ERROR]${colors.reset}`,
  };
  console.log(`${prefix[type]} ${message}`);
}

// =============================================================================
// MAIN INGESTOR
// =============================================================================

async function ingestLegacyData(inputPath: string): Promise<void> {
  console.log('\n' + '█'.repeat(60));
  console.log(`${colors.green}${colors.bright}   🚀 ADMIRAL LEGACY DATA INGESTOR${colors.reset}`);
  console.log('█'.repeat(60) + '\n');

  // Resolve input path
  const resolvedPath = path.isAbsolute(inputPath)
    ? inputPath
    : path.join(process.cwd(), inputPath);

  log(`Input file: ${resolvedPath}`, 'info');

  // Check file exists
  if (!fs.existsSync(resolvedPath)) {
    log(`File not found: ${resolvedPath}`, 'error');
    process.exit(1);
  }

  // Read and parse JSON
  log('Reading JSON file...', 'info');
  let rawData: AdmiralDataDump | AdmiralRawContract[];

  try {
    const fileContent = fs.readFileSync(resolvedPath, 'utf-8');
    rawData = JSON.parse(fileContent);
    log('JSON parsed successfully', 'success');
  } catch (error: any) {
    log(`Failed to parse JSON: ${error.message}`, 'error');
    process.exit(1);
  }

  // Determine data structure
  let contracts: AdmiralRawContract[] = [];
  let projects: AdmiralRawProject[] = [];
  let invoices: AdmiralRawInvoice[] = [];
  let clients: AdmiralRawClient[] = [];

  if (Array.isArray(rawData)) {
    // Direct array of contracts
    log('Detected: Array of contracts', 'info');
    contracts = rawData;
  } else {
    // Object with multiple sections
    log('Detected: Full data dump object', 'info');
    contracts = rawData.contracts || rawData.contractsBalance || [];
    projects = rawData.projects || [];
    invoices = rawData.invoices || [];
    clients = rawData.clients || [];
  }

  log(`Raw counts - Contracts: ${contracts.length}, Projects: ${projects.length}, Invoices: ${invoices.length}, Clients: ${clients.length}`, 'info');

  // Normalize data
  log('\nNormalizing data...', 'info');

  const allValidationErrors: string[] = [];

  // Normalize contracts
  const normalizedContracts: NormalizedContract[] = [];
  for (const raw of contracts) {
    const normalized = normalizeContract(raw);
    const errors = validateContract(normalized);
    allValidationErrors.push(...errors);
    normalizedContracts.push(normalized);
  }
  log(`Normalized ${normalizedContracts.length} contracts`, 'success');

  // Normalize projects
  const normalizedProjects: NormalizedProject[] = [];
  for (const raw of projects) {
    const normalized = normalizeProject(raw);
    const errors = validateProject(normalized);
    allValidationErrors.push(...errors);
    normalizedProjects.push(normalized);
  }
  if (projects.length > 0) {
    log(`Normalized ${normalizedProjects.length} projects`, 'success');
  }

  // Normalize invoices
  const normalizedInvoices: NormalizedInvoice[] = [];
  for (const raw of invoices) {
    const normalized = normalizeInvoice(raw);
    const errors = validateInvoice(normalized);
    allValidationErrors.push(...errors);
    normalizedInvoices.push(normalized);
  }
  if (invoices.length > 0) {
    log(`Normalized ${normalizedInvoices.length} invoices`, 'success');
  }

  // Normalize clients
  const normalizedClients: NormalizedClient[] = [];
  for (const raw of clients) {
    const normalized = normalizeClient(raw);
    const errors = validateClient(normalized);
    allValidationErrors.push(...errors);
    normalizedClients.push(normalized);
  }
  if (clients.length > 0) {
    log(`Normalized ${normalizedClients.length} clients`, 'success');
  }

  // Report validation errors
  if (allValidationErrors.length > 0) {
    log(`\n${allValidationErrors.length} validation warnings:`, 'warning');
    allValidationErrors.slice(0, 10).forEach((err) => {
      console.log(`  - ${err}`);
    });
    if (allValidationErrors.length > 10) {
      console.log(`  ... and ${allValidationErrors.length - 10} more`);
    }
  }

  // Prepare output
  const output: NormalizedDataOutput = {
    contracts: normalizedContracts,
    projects: normalizedProjects,
    invoices: normalizedInvoices,
    clients: normalizedClients,
    metadata: {
      importedAt: new Date().toISOString(),
      sourceSystem: 'admiral',
      totalContracts: normalizedContracts.length,
      totalProjects: normalizedProjects.length,
      totalInvoices: normalizedInvoices.length,
      totalClients: normalizedClients.length,
      validationErrors: allValidationErrors,
    },
  };

  // Ensure output directory exists
  if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  }

  // Save normalized data
  log('\nSaving normalized data...', 'info');

  // Save all-in-one file
  const allDataPath = path.join(OUTPUT_DIR, 'admiral_normalized.json');
  fs.writeFileSync(allDataPath, JSON.stringify(output, null, 2), 'utf-8');
  log(`All data: ${allDataPath}`, 'success');

  // Save separate files for each type
  if (normalizedContracts.length > 0) {
    const contractsPath = path.join(OUTPUT_DIR, 'contracts.json');
    fs.writeFileSync(contractsPath, JSON.stringify(normalizedContracts, null, 2), 'utf-8');
    log(`Contracts: ${contractsPath}`, 'success');
  }

  if (normalizedProjects.length > 0) {
    const projectsPath = path.join(OUTPUT_DIR, 'projects.json');
    fs.writeFileSync(projectsPath, JSON.stringify(normalizedProjects, null, 2), 'utf-8');
    log(`Projects: ${projectsPath}`, 'success');
  }

  if (normalizedInvoices.length > 0) {
    const invoicesPath = path.join(OUTPUT_DIR, 'invoices.json');
    fs.writeFileSync(invoicesPath, JSON.stringify(normalizedInvoices, null, 2), 'utf-8');
    log(`Invoices: ${invoicesPath}`, 'success');
  }

  if (normalizedClients.length > 0) {
    const clientsPath = path.join(OUTPUT_DIR, 'clients.json');
    fs.writeFileSync(clientsPath, JSON.stringify(normalizedClients, null, 2), 'utf-8');
    log(`Clients: ${clientsPath}`, 'success');
  }

  // Print summary
  console.log('\n' + '█'.repeat(60));
  console.log(`${colors.green}${colors.bright}   🎯 DATA INGESTION COMPLETE${colors.reset}`);
  console.log('█'.repeat(60));
  console.log(`Contracts:  ${normalizedContracts.length}`);
  console.log(`Projects:   ${normalizedProjects.length}`);
  console.log(`Invoices:   ${normalizedInvoices.length}`);
  console.log(`Clients:    ${normalizedClients.length}`);
  console.log('-'.repeat(60));
  console.log(`${colors.green}TOTAL:      ${normalizedContracts.length + normalizedProjects.length + normalizedInvoices.length + normalizedClients.length} records${colors.reset}`);
  console.log(`${colors.yellow}Output:     ${OUTPUT_DIR}${colors.reset}`);
  if (allValidationErrors.length > 0) {
    console.log(`${colors.yellow}Warnings:   ${allValidationErrors.length}${colors.reset}`);
  }
  console.log('█'.repeat(60) + '\n');
}

// =============================================================================
// CLI ENTRY POINT
// =============================================================================

const args = process.argv.slice(2);

if (args.length === 0) {
  console.log(`
${colors.cyan}Admiral Legacy Data Ingestor${colors.reset}

Usage:
  npx ts-node src/ingest-legacy-data.ts <input_json_file>

Examples:
  npx ts-node src/ingest-legacy-data.ts admiral_contracts_dump.json
  npx ts-node src/ingest-legacy-data.ts /path/to/exported_data.json

Input Format:
  The input JSON can be either:
  1. An array of contract objects (direct browser console dump)
  2. A full data dump object with { contracts, projects, invoices, clients }

Output:
  - migration_data/admiral_normalized.json  (all data combined)
  - migration_data/contracts.json           (normalized contracts)
  - migration_data/projects.json            (normalized projects)
  - migration_data/invoices.json            (normalized invoices)
  - migration_data/clients.json             (normalized clients)
`);
  process.exit(0);
}

ingestLegacyData(args[0]).catch((error) => {
  log(`Fatal error: ${error.message}`, 'error');
  console.error(error);
  process.exit(1);
});
