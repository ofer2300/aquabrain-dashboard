/**
 * Admiral Data Cleaners & Normalizers
 * ====================================
 * Utilities for cleaning and normalizing Admiral legacy data
 */

import {
  AdmiralRawContract,
  NormalizedContract,
  AdmiralRawProject,
  NormalizedProject,
  AdmiralRawInvoice,
  NormalizedInvoice,
  AdmiralRawClient,
  NormalizedClient,
} from '../types';

// =============================================================================
// PRIMITIVE CLEANERS
// =============================================================================

/**
 * Clean currency string and convert to number
 * Handles: ₪1,234.56, $1,234.56, 1,234.56, -1,234.56
 */
export function cleanCurrency(value: string | number | undefined): number {
  if (value === undefined || value === null || value === '') return 0;
  if (typeof value === 'number') return value;

  const cleaned = String(value)
    .replace(/[₪$€,\s]/g, '')
    .replace(/[-−–]/g, '-')  // Normalize different dash types
    .trim();

  const num = parseFloat(cleaned);
  return isNaN(num) ? 0 : num;
}

/**
 * Clean percentage string and convert to number
 * Handles: 85%, 85.5%, 85
 */
export function cleanPercentage(value: string | number | undefined): number {
  if (value === undefined || value === null || value === '') return 0;
  if (typeof value === 'number') return value;

  const cleaned = String(value).replace(/%/g, '').trim();
  const num = parseFloat(cleaned);
  return isNaN(num) ? 0 : num;
}

/**
 * Parse Hebrew date format (DD/MM/YYYY) to ISO 8601
 */
export function parseHebrewDate(dateStr: string | undefined): string {
  if (!dateStr) return '';

  // Handle DD/MM/YYYY format
  const slashMatch = dateStr.match(/(\d{1,2})\/(\d{1,2})\/(\d{4})/);
  if (slashMatch) {
    const [, day, month, year] = slashMatch;
    return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
  }

  // Handle DD.MM.YYYY format
  const dotMatch = dateStr.match(/(\d{1,2})\.(\d{1,2})\.(\d{4})/);
  if (dotMatch) {
    const [, day, month, year] = dotMatch;
    return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
  }

  // Handle YYYY-MM-DD format (already ISO)
  const isoMatch = dateStr.match(/(\d{4})-(\d{2})-(\d{2})/);
  if (isoMatch) {
    return dateStr;
  }

  return dateStr; // Return as-is if no pattern matches
}

/**
 * Clean text - remove RTL marks, normalize whitespace
 */
export function cleanText(value: string | undefined): string {
  if (!value) return '';

  return String(value)
    .trim()
    .replace(/\s+/g, ' ')
    .replace(/[\u200F\u200E\u202A\u202B\u202C]/g, ''); // Remove RTL/LTR marks
}

/**
 * Convert any value to string ID
 */
export function toStringId(value: string | number | undefined): string {
  if (value === undefined || value === null) return '';
  return String(value).trim();
}

// =============================================================================
// RECORD NORMALIZERS
// =============================================================================

/**
 * Normalize a raw Admiral contract record
 */
export function normalizeContract(raw: AdmiralRawContract): NormalizedContract {
  return {
    projectId: toStringId(raw["מס'"] || raw['מס']),
    projectName: cleanText(raw['פרויקט']),
    projectManager: cleanText(raw['מנהל פרויקט']),
    clientName: cleanText(raw['לקוח']),
    contractBase: cleanText(raw['בסיס התקשרות']),
    contractAmount: cleanCurrency(raw['סכום']),
    totalPaid: cleanCurrency(raw['שולם']),
    balance: cleanCurrency(raw['יתרה']),
    progressPercentage: cleanPercentage(raw['אחוז התקדמות'] || raw['% התקדמות']),
    nextInvoiceMilestone: cleanText(raw['חשבון הבא']),
    profitability: cleanCurrency(raw['רווח'] || raw['רווחיות']),
    _sourceSystem: 'admiral',
    _importedAt: new Date().toISOString(),
  };
}

/**
 * Normalize a raw Admiral project record
 */
export function normalizeProject(raw: AdmiralRawProject): NormalizedProject {
  return {
    projectId: toStringId(raw['מספר פרויקט']),
    projectName: cleanText(raw['שם פרויקט']),
    clientName: cleanText(raw['לקוח'] || raw['שם לקוח']),
    totalAmount: cleanCurrency(raw['סה"כ']),
    status: cleanText(raw['סטטוס'] || raw['מצב']),
    openDate: parseHebrewDate(raw['תאריך פתיחה']),
    closeDate: parseHebrewDate(raw['תאריך סגירה']),
    _sourceSystem: 'admiral',
    _importedAt: new Date().toISOString(),
  };
}

/**
 * Normalize a raw Admiral invoice record
 */
export function normalizeInvoice(raw: AdmiralRawInvoice): NormalizedInvoice {
  return {
    invoiceNumber: toStringId(raw['מספר חשבונית'] || raw['חשבונית']),
    projectName: cleanText(raw['פרויקט']),
    clientName: cleanText(raw['לקוח']),
    invoiceAmount: cleanCurrency(raw['סכום חשבונית'] || raw['סכום']),
    invoiceDate: parseHebrewDate(raw['תאריך חשבונית']),
    dueDate: parseHebrewDate(raw['תאריך פירעון']),
    status: cleanText(raw['סטטוס']),
    _sourceSystem: 'admiral',
    _importedAt: new Date().toISOString(),
  };
}

/**
 * Normalize a raw Admiral client record
 */
export function normalizeClient(raw: AdmiralRawClient): NormalizedClient {
  return {
    clientName: cleanText(raw['שם לקוח'] || raw['לקוח']),
    address: cleanText(raw['כתובת']),
    city: cleanText(raw['עיר']),
    phone: cleanText(raw['טלפון']),
    email: cleanText(raw['אימייל']),
    contactPerson: cleanText(raw['איש קשר']),
    companyId: toStringId(raw['ח.פ']),
    vatNumber: toStringId(raw['עוסק מורשה']),
    _sourceSystem: 'admiral',
    _importedAt: new Date().toISOString(),
  };
}

// =============================================================================
// VALIDATION
// =============================================================================

/**
 * Validate a normalized contract has required fields
 */
export function validateContract(contract: NormalizedContract): string[] {
  const errors: string[] = [];

  if (!contract.projectId) {
    errors.push(`Contract missing projectId`);
  }
  if (!contract.projectName) {
    errors.push(`Contract ${contract.projectId} missing projectName`);
  }
  if (contract.contractAmount < 0) {
    errors.push(`Contract ${contract.projectId} has negative contractAmount`);
  }

  return errors;
}

/**
 * Validate a normalized project
 */
export function validateProject(project: NormalizedProject): string[] {
  const errors: string[] = [];

  if (!project.projectId) {
    errors.push(`Project missing projectId`);
  }
  if (!project.projectName) {
    errors.push(`Project ${project.projectId} missing projectName`);
  }

  return errors;
}

/**
 * Validate a normalized invoice
 */
export function validateInvoice(invoice: NormalizedInvoice): string[] {
  const errors: string[] = [];

  if (!invoice.invoiceNumber) {
    errors.push(`Invoice missing invoiceNumber`);
  }
  if (invoice.invoiceAmount <= 0) {
    errors.push(`Invoice ${invoice.invoiceNumber} has invalid amount`);
  }

  return errors;
}

/**
 * Validate a normalized client
 */
export function validateClient(client: NormalizedClient): string[] {
  const errors: string[] = [];

  if (!client.clientName) {
    errors.push(`Client missing clientName`);
  }

  return errors;
}
