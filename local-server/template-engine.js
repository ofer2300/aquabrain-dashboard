/**
 * AquaBrain Template Engine v1.0
 * ==============================
 * Automated Document Generation for Engineering Forms
 *
 * Pain Point Solved:
 * Engineers waste hours filling out repetitive forms for every project.
 * This engine takes a template + project data and produces ready-to-sign documents.
 *
 * Supported Document Types:
 * - הצהרת מהנדס (Engineer Declaration)
 * - הצהרת קולטי שמש (Solar Collector Declaration)
 * - התחייבות לתאגיד (Water Authority Commitment)
 * - תצהיר בניה ירוקה (Green Building Affidavit)
 * - הצהרת יועץ אינסטלציה לטופס 4 (Form 4 Consultant Declaration)
 * - And many more...
 *
 * Author: AquaBrain V10.0 Platinum
 */

const fs = require('fs');
const path = require('path');
const PizZip = require('pizzip');
const Docxtemplater = require('docxtemplater');
const { v4: uuidv4 } = require('uuid');

// ============================================================================
// CONFIGURATION
// ============================================================================

const CONFIG = {
  TEMPLATES_DIR: path.join(__dirname, 'templates', 'base'),
  SAMPLES_DIR: path.join(__dirname, 'templates', 'samples'),
  OUTPUT_DIR: path.join(__dirname, '..', 'frontend', 'public', 'uploads', 'generated'),

  // Standard placeholders used across all documents
  PLACEHOLDERS: {
    // Project Info
    '{{PROJECT_NAME}}': 'projectName',
    '{{PROJECT_NUMBER}}': 'projectNumber',
    '{{ADDRESS}}': 'address',
    '{{CITY}}': 'city',
    '{{BLOCK}}': 'block',
    '{{PARCEL}}': 'parcel',
    '{{PERMIT_NUMBER}}': 'permitNumber',

    // Client/Developer Info
    '{{CLIENT_NAME}}': 'clientName',
    '{{DEVELOPER_NAME}}': 'developerName',
    '{{DEVELOPER_ID}}': 'developerId',
    '{{DEVELOPER_ADDRESS}}': 'developerAddress',
    '{{DEVELOPER_PHONE}}': 'developerPhone',

    // Engineer Info (usually pre-filled)
    '{{ENGINEER_NAME}}': 'engineerName',
    '{{ENGINEER_LICENSE}}': 'engineerLicense',
    '{{ENGINEER_ID}}': 'engineerId',
    '{{ENGINEER_ADDRESS}}': 'engineerAddress',
    '{{ENGINEER_PHONE}}': 'engineerPhone',
    '{{ENGINEER_EMAIL}}': 'engineerEmail',
    '{{COMPANY_NAME}}': 'companyName',

    // Technical Data
    '{{BUILDING_TYPE}}': 'buildingType',
    '{{NUM_UNITS}}': 'numUnits',
    '{{NUM_FLOORS}}': 'numFloors',
    '{{TOTAL_AREA}}': 'totalArea',
    '{{WATER_DEMAND}}': 'waterDemand',
    '{{SEWAGE_DEMAND}}': 'sewageDemand',

    // Dates
    '{{DATE}}': 'date',
    '{{DATE_HEBREW}}': 'dateHebrew',
    '{{PERMIT_DATE}}': 'permitDate',
    '{{COMPLETION_DATE}}': 'completionDate',

    // Water Authority
    '{{WATER_AUTHORITY}}': 'waterAuthority',
    '{{CONNECTION_NUMBER}}': 'connectionNumber',
    '{{METER_SIZE}}': 'meterSize',
  },

  // Default engineer details
  DEFAULT_ENGINEER: {
    engineerName: 'נימרוד עופר',
    engineerLicense: '68465',
    engineerId: '012345678',
    engineerAddress: 'תל אביב',
    engineerPhone: '054-1234567',
    engineerEmail: 'nimrod@aquabrain.io',
    companyName: 'אושר דוד תכנון אינסטלציה בע"מ',
  },

  // Document type templates and their specific fields
  DOCUMENT_TYPES: {
    'הצהרת_מהנדס': {
      name: 'הצהרת מהנדס',
      category: 'declarations',
      requiredFields: ['projectName', 'address', 'clientName', 'date'],
      templateFile: 'הצהרת_מהנדס_טמפלייט.docx',
    },
    'הצהרת_קולטי_שמש': {
      name: 'הצהרת קולטי שמש',
      category: 'declarations',
      requiredFields: ['projectName', 'address', 'numUnits', 'date'],
      templateFile: 'הצהרת_קולטי_שמש_טמפלייט.docx',
    },
    'התחייבות_לתאגיד': {
      name: 'התחייבות לתאגיד',
      category: 'commitments',
      requiredFields: ['projectName', 'address', 'waterAuthority', 'date'],
      templateFile: 'התחייבות_לתאגיד_טמפלייט.docx',
    },
    'תצהיר_בניה_ירוקה': {
      name: 'תצהיר בניה ירוקה',
      category: 'affidavits',
      requiredFields: ['projectName', 'address', 'totalArea', 'date'],
      templateFile: 'תצהיר_בניה_ירוקה_טמפלייט.docx',
    },
    'הצהרת_יועץ_טופס_4': {
      name: 'הצהרת יועץ אינסטלציה לטופס 4',
      category: 'form4',
      requiredFields: ['projectName', 'address', 'permitNumber', 'date'],
      templateFile: 'הצהרת_יועץ_טופס_4_טמפלייט.docx',
    },
    'אישור_מתכנן_לגמר': {
      name: 'אישור מתכנן אינסטלציה לגמר',
      category: 'completion',
      requiredFields: ['projectName', 'address', 'permitNumber', 'completionDate'],
      templateFile: 'אישור_מתכנן_לגמר_טמפלייט.docx',
    },
  },
};

// ============================================================================
// TEMPLATE ENGINE CLASS
// ============================================================================

class TemplateEngine {
  constructor() {
    this.ensureDirectories();
  }

  ensureDirectories() {
    [CONFIG.TEMPLATES_DIR, CONFIG.SAMPLES_DIR, CONFIG.OUTPUT_DIR].forEach(dir => {
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
      }
    });
  }

  /**
   * List all available templates
   */
  listTemplates() {
    const templates = [];

    // Check base templates
    if (fs.existsSync(CONFIG.TEMPLATES_DIR)) {
      fs.readdirSync(CONFIG.TEMPLATES_DIR).forEach(file => {
        if (file.endsWith('.docx')) {
          templates.push({
            id: path.basename(file, '.docx'),
            name: file,
            path: path.join(CONFIG.TEMPLATES_DIR, file),
            type: 'base',
          });
        }
      });
    }

    // Check samples
    if (fs.existsSync(CONFIG.SAMPLES_DIR)) {
      fs.readdirSync(CONFIG.SAMPLES_DIR).forEach(file => {
        if (file.endsWith('.docx')) {
          templates.push({
            id: path.basename(file, '.docx'),
            name: file,
            path: path.join(CONFIG.SAMPLES_DIR, file),
            type: 'sample',
          });
        }
      });
    }

    return templates;
  }

  /**
   * Analyze a DOCX template to find placeholders
   */
  analyzeTemplate(templatePath) {
    try {
      const content = fs.readFileSync(templatePath, 'binary');
      const zip = new PizZip(content);
      const doc = new Docxtemplater(zip, {
        paragraphLoop: true,
        linebreaks: true,
        delimiters: { start: '{{', end: '}}' },
      });

      // Get the XML content to find placeholders
      const text = doc.getFullText();

      // Find all placeholders (both {{}} and standard patterns)
      const placeholderPatterns = [
        /\{\{([^}]+)\}\}/g,  // {{PLACEHOLDER}}
        /__([A-Z_]+)__/g,     // __PLACEHOLDER__
        /\[([A-Z_]+)\]/g,     // [PLACEHOLDER]
      ];

      const foundPlaceholders = new Set();
      placeholderPatterns.forEach(pattern => {
        let match;
        while ((match = pattern.exec(text)) !== null) {
          foundPlaceholders.add(match[1]);
        }
      });

      // Also look for common Hebrew field patterns
      const hebrewFields = [
        'שם הפרויקט', 'כתובת', 'גוש', 'חלקה', 'תאריך',
        'שם המזמין', 'שם היזם', 'מספר היתר', 'שם המהנדס'
      ];

      return {
        success: true,
        templatePath,
        placeholders: Array.from(foundPlaceholders),
        fullText: text.substring(0, 1000) + '...', // Preview
        suggestedFields: this.suggestFieldMappings(Array.from(foundPlaceholders)),
      };

    } catch (error) {
      return {
        success: false,
        error: error.message,
      };
    }
  }

  /**
   * Suggest field mappings based on placeholder names
   */
  suggestFieldMappings(placeholders) {
    const suggestions = {};

    placeholders.forEach(placeholder => {
      const upper = placeholder.toUpperCase();

      if (upper.includes('PROJECT') || upper.includes('פרויקט')) {
        suggestions[placeholder] = 'projectName';
      } else if (upper.includes('ADDRESS') || upper.includes('כתובת')) {
        suggestions[placeholder] = 'address';
      } else if (upper.includes('DATE') || upper.includes('תאריך')) {
        suggestions[placeholder] = 'date';
      } else if (upper.includes('NAME') || upper.includes('שם')) {
        suggestions[placeholder] = 'clientName';
      } else if (upper.includes('LICENSE') || upper.includes('רישיון')) {
        suggestions[placeholder] = 'engineerLicense';
      } else if (upper.includes('ENGINEER') || upper.includes('מהנדס')) {
        suggestions[placeholder] = 'engineerName';
      }
    });

    return suggestions;
  }

  /**
   * Fill a DOCX template with project data
   */
  fillTemplate(templatePath, projectData, outputFileName = null) {
    try {
      // Merge with default engineer data
      const data = {
        ...CONFIG.DEFAULT_ENGINEER,
        date: new Date().toLocaleDateString('he-IL'),
        dateHebrew: this.getHebrewDate(),
        ...projectData,
      };

      // Read template
      const content = fs.readFileSync(templatePath, 'binary');
      const zip = new PizZip(content);

      // Create docxtemplater instance
      const doc = new Docxtemplater(zip, {
        paragraphLoop: true,
        linebreaks: true,
        delimiters: { start: '{{', end: '}}' },
      });

      // Set the data
      doc.setData(data);

      // Render the document
      doc.render();

      // Generate output
      const buf = doc.getZip().generate({
        type: 'nodebuffer',
        compression: 'DEFLATE',
      });

      // Save to output directory
      const fileName = outputFileName ||
        `${data.projectName || 'document'}_${uuidv4().substring(0, 8)}.docx`;
      const outputPath = path.join(CONFIG.OUTPUT_DIR, fileName);

      fs.writeFileSync(outputPath, buf);

      return {
        success: true,
        outputPath,
        fileName,
        data,
      };

    } catch (error) {
      return {
        success: false,
        error: error.message,
      };
    }
  }

  /**
   * Batch fill multiple templates for a project
   */
  batchFillForProject(projectData, documentTypes = []) {
    const results = [];

    // If no specific types, generate all standard documents
    const typesToGenerate = documentTypes.length > 0
      ? documentTypes
      : Object.keys(CONFIG.DOCUMENT_TYPES);

    typesToGenerate.forEach(docType => {
      const typeConfig = CONFIG.DOCUMENT_TYPES[docType];
      if (!typeConfig) {
        results.push({
          docType,
          success: false,
          error: `Unknown document type: ${docType}`,
        });
        return;
      }

      const templatePath = path.join(CONFIG.TEMPLATES_DIR, typeConfig.templateFile);

      // Check for template in samples if not in base
      let actualTemplatePath = templatePath;
      if (!fs.existsSync(templatePath)) {
        // Try to find a matching sample
        const samples = this.listTemplates().filter(t => t.type === 'sample');
        const matchingSample = samples.find(s =>
          s.name.includes(typeConfig.name) ||
          s.name.includes(docType.replace(/_/g, ' '))
        );
        if (matchingSample) {
          actualTemplatePath = matchingSample.path;
        } else {
          results.push({
            docType,
            name: typeConfig.name,
            success: false,
            error: `Template not found: ${typeConfig.templateFile}`,
          });
          return;
        }
      }

      const result = this.fillTemplate(
        actualTemplatePath,
        projectData,
        `${projectData.projectName || 'project'}_${docType}.docx`
      );

      results.push({
        docType,
        name: typeConfig.name,
        ...result,
      });
    });

    return results;
  }

  /**
   * Get current Hebrew date
   */
  getHebrewDate() {
    const date = new Date();
    const options = {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    };
    return date.toLocaleDateString('he-IL-u-ca-hebrew', options);
  }

  /**
   * Create a template from an existing document
   * (Replaces specific values with placeholders)
   */
  createTemplateFromDocument(sourcePath, mappings) {
    try {
      const content = fs.readFileSync(sourcePath, 'binary');
      const zip = new PizZip(content);
      let xmlContent = zip.file('word/document.xml').asText();

      // Replace specific values with placeholders
      Object.entries(mappings).forEach(([value, placeholder]) => {
        xmlContent = xmlContent.replace(new RegExp(value, 'g'), `{{${placeholder}}}`);
      });

      zip.file('word/document.xml', xmlContent);

      const baseName = path.basename(sourcePath, '.docx');
      const templateFileName = `${baseName}_template.docx`;
      const templatePath = path.join(CONFIG.TEMPLATES_DIR, templateFileName);

      const buf = zip.generate({ type: 'nodebuffer' });
      fs.writeFileSync(templatePath, buf);

      return {
        success: true,
        templatePath,
        templateFileName,
      };

    } catch (error) {
      return {
        success: false,
        error: error.message,
      };
    }
  }

  /**
   * Get document type configuration
   */
  getDocumentTypes() {
    return CONFIG.DOCUMENT_TYPES;
  }

  /**
   * Get all placeholder definitions
   */
  getPlaceholders() {
    return CONFIG.PLACEHOLDERS;
  }
}

// ============================================================================
// PROJECT DATA STORE
// ============================================================================

class ProjectStore {
  constructor() {
    this.dbPath = path.join(__dirname, 'data', 'projects_db.json');
    this.data = { projects: [] };
    this.load();
  }

  load() {
    try {
      if (fs.existsSync(this.dbPath)) {
        const raw = fs.readFileSync(this.dbPath, 'utf-8');
        this.data = JSON.parse(raw);
      }
    } catch (error) {
      console.error('Failed to load projects database:', error.message);
    }
  }

  save() {
    try {
      fs.writeFileSync(this.dbPath, JSON.stringify(this.data, null, 2));
    } catch (error) {
      console.error('Failed to save projects database:', error.message);
    }
  }

  addProject(projectData) {
    const project = {
      id: uuidv4(),
      createdAt: new Date().toISOString(),
      ...projectData,
    };
    this.data.projects.push(project);
    this.save();
    return project;
  }

  getProject(id) {
    return this.data.projects.find(p => p.id === id);
  }

  getAllProjects() {
    return this.data.projects;
  }

  updateProject(id, updates) {
    const index = this.data.projects.findIndex(p => p.id === id);
    if (index === -1) return null;

    this.data.projects[index] = {
      ...this.data.projects[index],
      ...updates,
      updatedAt: new Date().toISOString(),
    };
    this.save();
    return this.data.projects[index];
  }

  deleteProject(id) {
    const index = this.data.projects.findIndex(p => p.id === id);
    if (index === -1) return false;

    this.data.projects.splice(index, 1);
    this.save();
    return true;
  }
}

// ============================================================================
// EXPORTS
// ============================================================================

module.exports = {
  TemplateEngine,
  ProjectStore,
  CONFIG,
};

// ============================================================================
// CLI USAGE (if run directly)
// ============================================================================

if (require.main === module) {
  const engine = new TemplateEngine();

  console.log('📝 AquaBrain Template Engine v1.0');
  console.log('='.repeat(50));

  // List available templates
  const templates = engine.listTemplates();
  console.log(`\n📁 Found ${templates.length} templates:`);
  templates.forEach((t, i) => {
    console.log(`   ${i + 1}. [${t.type}] ${t.name}`);
  });

  // Analyze first sample if exists
  if (templates.length > 0) {
    console.log('\n🔍 Analyzing first template...');
    const analysis = engine.analyzeTemplate(templates[0].path);
    if (analysis.success) {
      console.log(`   Placeholders found: ${analysis.placeholders.length}`);
      console.log(`   Suggestions:`, analysis.suggestedFields);
    }
  }

  console.log('\n✅ Template Engine ready');
}
