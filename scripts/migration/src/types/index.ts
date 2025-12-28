/**
 * Admiral Legacy System Type Definitions
 * ======================================
 * Types for data extracted from Admiral ERP system
 */

// Raw Admiral contract record (Hebrew field names from browser console dump)
export interface AdmiralRawContract {
  'מנהל פרויקט'?: string;
  "מס'"?: string | number;
  'מס'?: string | number;
  'פרויקט'?: string;
  'לקוח'?: string;
  'בסיס התקשרות'?: string;
  'סכום'?: string | number;
  'שולם'?: string | number;
  'יתרה'?: string | number;
  'אחוז התקדמות'?: string | number;
  '% התקדמות'?: string | number;
  'חשבון הבא'?: string;
  'רווח'?: string | number;
  'רווחיות'?: string | number;
  [key: string]: any;  // Allow additional fields
}

// Normalized contract record (English field names)
export interface NormalizedContract {
  projectId: string;
  projectName: string;
  projectManager: string;
  clientName: string;
  contractBase: string;
  contractAmount: number;
  totalPaid: number;
  balance: number;
  progressPercentage: number;
  nextInvoiceMilestone: string;
  profitability: number;
  // Metadata
  _sourceSystem: 'admiral';
  _importedAt: string;
  _rawData?: AdmiralRawContract;
}

// Admiral project record
export interface AdmiralRawProject {
  'מספר פרויקט'?: string | number;
  'שם פרויקט'?: string;
  'לקוח'?: string;
  'שם לקוח'?: string;
  'סה"כ'?: string | number;
  'סטטוס'?: string;
  'מצב'?: string;
  'תאריך פתיחה'?: string;
  'תאריך סגירה'?: string;
  [key: string]: any;
}

export interface NormalizedProject {
  projectId: string;
  projectName: string;
  clientName: string;
  totalAmount: number;
  status: string;
  openDate: string;
  closeDate: string;
  _sourceSystem: 'admiral';
  _importedAt: string;
}

// Admiral invoice record
export interface AdmiralRawInvoice {
  'מספר חשבונית'?: string | number;
  'חשבונית'?: string | number;
  'פרויקט'?: string;
  'לקוח'?: string;
  'סכום חשבונית'?: string | number;
  'סכום'?: string | number;
  'תאריך חשבונית'?: string;
  'תאריך פירעון'?: string;
  'סטטוס'?: string;
  [key: string]: any;
}

export interface NormalizedInvoice {
  invoiceNumber: string;
  projectName: string;
  clientName: string;
  invoiceAmount: number;
  invoiceDate: string;
  dueDate: string;
  status: string;
  _sourceSystem: 'admiral';
  _importedAt: string;
}

// Admiral client record
export interface AdmiralRawClient {
  'שם לקוח'?: string;
  'לקוח'?: string;
  'כתובת'?: string;
  'עיר'?: string;
  'טלפון'?: string;
  'אימייל'?: string;
  'איש קשר'?: string;
  'ח.פ'?: string | number;
  'עוסק מורשה'?: string | number;
  [key: string]: any;
}

export interface NormalizedClient {
  clientName: string;
  address: string;
  city: string;
  phone: string;
  email: string;
  contactPerson: string;
  companyId: string;
  vatNumber: string;
  _sourceSystem: 'admiral';
  _importedAt: string;
}

// Full Admiral data dump structure
export interface AdmiralDataDump {
  contracts?: AdmiralRawContract[];
  contractsBalance?: AdmiralRawContract[];
  projects?: AdmiralRawProject[];
  invoices?: AdmiralRawInvoice[];
  clients?: AdmiralRawClient[];
  payments?: any[];
  metadata?: {
    exportedAt?: string;
    source?: string;
    version?: string;
    totalRecords?: number;
  };
}

// Normalized output structure
export interface NormalizedDataOutput {
  contracts: NormalizedContract[];
  projects: NormalizedProject[];
  invoices: NormalizedInvoice[];
  clients: NormalizedClient[];
  metadata: {
    importedAt: string;
    sourceSystem: 'admiral';
    totalContracts: number;
    totalProjects: number;
    totalInvoices: number;
    totalClients: number;
    validationErrors: string[];
  };
}
