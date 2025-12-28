'use client';

/**
 * Document Generator - Batch Document Production
 * ================================================
 * Enter project data ONCE, generate ALL required documents
 *
 * Pain Point Solved:
 * Instead of manually filling 10+ documents per project,
 * enter data once and click "Generate All"
 *
 * Flow:
 * 1. Enter project details
 * 2. Select document types
 * 3. Click "Generate"
 * 4. Review and send to Signature Flow
 */

import React, { useState, useEffect } from 'react';
import {
  FileText, Building2, User, Calendar, MapPin, Hash, Briefcase,
  CheckSquare, Square, Loader2, Download, FileSignature, Zap,
  ChevronRight, ChevronDown, AlertCircle, CheckCircle2, Sparkles
} from 'lucide-react';

// ============================================================================
// TYPES
// ============================================================================

interface ProjectData {
  // Project Info
  projectName: string;
  projectNumber: string;
  address: string;
  city: string;
  block: string;
  parcel: string;
  permitNumber: string;

  // Client Info
  clientName: string;
  developerName: string;
  developerId: string;
  developerPhone: string;

  // Technical Data
  buildingType: string;
  numUnits: string;
  numFloors: string;
  totalArea: string;

  // Water Authority
  waterAuthority: string;
  connectionNumber: string;
}

interface DocumentType {
  id: string;
  name: string;
  category: string;
  description: string;
  selected: boolean;
}

// ============================================================================
// CONSTANTS
// ============================================================================

const INITIAL_PROJECT_DATA: ProjectData = {
  projectName: '',
  projectNumber: '',
  address: '',
  city: '',
  block: '',
  parcel: '',
  permitNumber: '',
  clientName: '',
  developerName: '',
  developerId: '',
  developerPhone: '',
  buildingType: 'מגורים',
  numUnits: '',
  numFloors: '',
  totalArea: '',
  waterAuthority: 'מי אביבים',
  connectionNumber: '',
};

const DOCUMENT_TYPES: DocumentType[] = [
  { id: 'הצהרת_מהנדס', name: 'הצהרת מהנדס', category: 'הצהרות', description: 'הצהרת מהנדס מים וביוב', selected: true },
  { id: 'הצהרת_יועץ_טופס_4', name: 'הצהרת יועץ לטופס 4', category: 'טופס 4', description: 'הצהרת יועץ אינסטלציה לאישור אכלוס', selected: true },
  { id: 'אישור_מתכנן_לגמר', name: 'אישור מתכנן לגמר', category: 'גמר', description: 'אישור מתכנן אינסטלציה לגמר', selected: true },
  { id: 'התחייבות_לתאגיד', name: 'התחייבות לתאגיד', category: 'תאגיד', description: 'מכתב התחייבות לתאגיד המים', selected: true },
  { id: 'הצהרת_קולטי_שמש', name: 'הצהרת קולטי שמש', category: 'סולארי', description: 'הצהרה על התקנת קולטי שמש', selected: false },
  { id: 'תצהיר_בניה_ירוקה', name: 'תצהיר בניה ירוקה', category: 'ירוק', description: 'תצהיר עפ"י תקן 5281', selected: false },
  { id: 'הצהרת_מתזים', name: 'הצהרת מתזים', category: 'כיבוי אש', description: 'הצהרה על מערכת ספרינקלרים', selected: false },
  { id: 'אישור_ציוד_אינסטלציה', name: 'אישור ציוד אינסטלציה', category: 'ציוד', description: 'אישור תקינות ציוד', selected: false },
];

const WATER_AUTHORITIES = [
  'מי אביבים', 'מי רמת גן', 'מקורות', 'מי הרצליה', 'מי נתניה',
  'מי כרמל', 'מי באר שבע', 'מי ראשון', 'יובלים', 'מי גבעתיים'
];

const BUILDING_TYPES = [
  'מגורים', 'מסחרי', 'משרדים', 'תעשייה', 'ציבורי', 'מעורב'
];

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export default function DocumentGeneratorPage() {
  const [projectData, setProjectData] = useState<ProjectData>(INITIAL_PROJECT_DATA);
  const [documentTypes, setDocumentTypes] = useState<DocumentType[]>(DOCUMENT_TYPES);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedDocs, setGeneratedDocs] = useState<any[]>([]);
  const [expandedCategory, setExpandedCategory] = useState<string | null>('הצהרות');
  const [step, setStep] = useState<'input' | 'select' | 'generate' | 'complete'>('input');

  // Group documents by category
  const categories = documentTypes.reduce((acc, doc) => {
    if (!acc[doc.category]) acc[doc.category] = [];
    acc[doc.category].push(doc);
    return acc;
  }, {} as Record<string, DocumentType[]>);

  const selectedCount = documentTypes.filter(d => d.selected).length;

  // Handle input change
  const handleInputChange = (field: keyof ProjectData, value: string) => {
    setProjectData(prev => ({ ...prev, [field]: value }));
  };

  // Toggle document selection
  const toggleDocument = (id: string) => {
    setDocumentTypes(prev =>
      prev.map(d => d.id === id ? { ...d, selected: !d.selected } : d)
    );
  };

  // Select/Deselect all in category
  const toggleCategory = (category: string, selected: boolean) => {
    setDocumentTypes(prev =>
      prev.map(d => d.category === category ? { ...d, selected } : d)
    );
  };

  // Generate documents (simulation for now)
  const handleGenerate = async () => {
    setIsGenerating(true);
    setStep('generate');

    // Simulate generation
    const selectedDocs = documentTypes.filter(d => d.selected);
    const results: any[] = [];

    for (const doc of selectedDocs) {
      await new Promise(resolve => setTimeout(resolve, 500)); // Simulate processing
      results.push({
        ...doc,
        status: 'success',
        fileName: `${projectData.projectName}_${doc.id}.docx`,
        generatedAt: new Date().toISOString(),
      });
      setGeneratedDocs([...results]);
    }

    setIsGenerating(false);
    setStep('complete');
  };

  // Send to signature flow
  const sendToSignatureFlow = async () => {
    // In production, this would send the documents to the signature service
    window.location.href = '/signature-flow';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-white p-6" dir="rtl">

      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-gradient-to-br from-blue-600 to-cyan-600 rounded-xl">
            <Sparkles size={28} />
          </div>
          <div>
            <h1 className="text-2xl font-bold">מחולל מסמכים</h1>
            <p className="text-sm text-slate-400">הזן פעם אחת, ייצר הכל</p>
          </div>
        </div>

        {/* Progress Steps */}
        <div className="flex items-center gap-2">
          {['input', 'select', 'generate', 'complete'].map((s, i) => (
            <React.Fragment key={s}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                step === s ? 'bg-blue-600' :
                ['input', 'select', 'generate', 'complete'].indexOf(step) > i
                  ? 'bg-green-600' : 'bg-slate-700'
              }`}>
                {i + 1}
              </div>
              {i < 3 && <div className={`w-8 h-0.5 ${
                ['input', 'select', 'generate', 'complete'].indexOf(step) > i
                  ? 'bg-green-600' : 'bg-slate-700'
              }`} />}
            </React.Fragment>
          ))}
        </div>
      </div>

      <div className="max-w-6xl mx-auto">

        {/* Step 1: Project Data Input */}
        {step === 'input' && (
          <div className="bg-slate-900/80 backdrop-blur-xl rounded-2xl border border-white/10 p-6">
            <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
              <Building2 size={24} />
              פרטי הפרויקט
            </h2>

            <div className="grid grid-cols-3 gap-6">

              {/* Project Info */}
              <div className="space-y-4">
                <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider">מידע בסיסי</h3>

                <div>
                  <label className="text-xs text-slate-400">שם הפרויקט *</label>
                  <input
                    type="text"
                    value={projectData.projectName}
                    onChange={(e) => handleInputChange('projectName', e.target.value)}
                    placeholder="למשל: ארלוזורוב 20"
                    className="w-full mt-1 px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="text-xs text-slate-400">כתובת מלאה *</label>
                  <input
                    type="text"
                    value={projectData.address}
                    onChange={(e) => handleInputChange('address', e.target.value)}
                    placeholder="רחוב, מספר"
                    className="w-full mt-1 px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="text-xs text-slate-400">עיר *</label>
                  <input
                    type="text"
                    value={projectData.city}
                    onChange={(e) => handleInputChange('city', e.target.value)}
                    placeholder="תל אביב"
                    className="w-full mt-1 px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-blue-500"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-slate-400">גוש</label>
                    <input
                      type="text"
                      value={projectData.block}
                      onChange={(e) => handleInputChange('block', e.target.value)}
                      className="w-full mt-1 px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-blue-500"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-slate-400">חלקה</label>
                    <input
                      type="text"
                      value={projectData.parcel}
                      onChange={(e) => handleInputChange('parcel', e.target.value)}
                      className="w-full mt-1 px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-blue-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="text-xs text-slate-400">מספר היתר</label>
                  <input
                    type="text"
                    value={projectData.permitNumber}
                    onChange={(e) => handleInputChange('permitNumber', e.target.value)}
                    className="w-full mt-1 px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-blue-500"
                  />
                </div>
              </div>

              {/* Client Info */}
              <div className="space-y-4">
                <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider">פרטי הלקוח</h3>

                <div>
                  <label className="text-xs text-slate-400">שם המזמין/יזם *</label>
                  <input
                    type="text"
                    value={projectData.clientName}
                    onChange={(e) => handleInputChange('clientName', e.target.value)}
                    className="w-full mt-1 px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="text-xs text-slate-400">שם החברה/קבלן</label>
                  <input
                    type="text"
                    value={projectData.developerName}
                    onChange={(e) => handleInputChange('developerName', e.target.value)}
                    className="w-full mt-1 px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="text-xs text-slate-400">ח.פ./ת.ז.</label>
                  <input
                    type="text"
                    value={projectData.developerId}
                    onChange={(e) => handleInputChange('developerId', e.target.value)}
                    className="w-full mt-1 px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="text-xs text-slate-400">טלפון</label>
                  <input
                    type="text"
                    value={projectData.developerPhone}
                    onChange={(e) => handleInputChange('developerPhone', e.target.value)}
                    className="w-full mt-1 px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-blue-500"
                  />
                </div>
              </div>

              {/* Technical Info */}
              <div className="space-y-4">
                <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider">נתונים טכניים</h3>

                <div>
                  <label className="text-xs text-slate-400">סוג מבנה</label>
                  <select
                    value={projectData.buildingType}
                    onChange={(e) => handleInputChange('buildingType', e.target.value)}
                    className="w-full mt-1 px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-blue-500"
                  >
                    {BUILDING_TYPES.map(type => (
                      <option key={type} value={type}>{type}</option>
                    ))}
                  </select>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-slate-400">מס' יח"ד</label>
                    <input
                      type="text"
                      value={projectData.numUnits}
                      onChange={(e) => handleInputChange('numUnits', e.target.value)}
                      className="w-full mt-1 px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-blue-500"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-slate-400">מס' קומות</label>
                    <input
                      type="text"
                      value={projectData.numFloors}
                      onChange={(e) => handleInputChange('numFloors', e.target.value)}
                      className="w-full mt-1 px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-blue-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="text-xs text-slate-400">שטח כולל (מ"ר)</label>
                  <input
                    type="text"
                    value={projectData.totalArea}
                    onChange={(e) => handleInputChange('totalArea', e.target.value)}
                    className="w-full mt-1 px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="text-xs text-slate-400">תאגיד מים</label>
                  <select
                    value={projectData.waterAuthority}
                    onChange={(e) => handleInputChange('waterAuthority', e.target.value)}
                    className="w-full mt-1 px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-blue-500"
                  >
                    {WATER_AUTHORITIES.map(auth => (
                      <option key={auth} value={auth}>{auth}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="text-xs text-slate-400">מס' חיבור</label>
                  <input
                    type="text"
                    value={projectData.connectionNumber}
                    onChange={(e) => handleInputChange('connectionNumber', e.target.value)}
                    className="w-full mt-1 px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-blue-500"
                  />
                </div>
              </div>
            </div>

            {/* Continue Button */}
            <div className="mt-8 flex justify-end">
              <button
                onClick={() => setStep('select')}
                disabled={!projectData.projectName || !projectData.address}
                className="flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed rounded-xl font-bold transition"
              >
                המשך לבחירת מסמכים
                <ChevronRight size={20} />
              </button>
            </div>
          </div>
        )}

        {/* Step 2: Document Selection */}
        {step === 'select' && (
          <div className="bg-slate-900/80 backdrop-blur-xl rounded-2xl border border-white/10 p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold flex items-center gap-2">
                <FileText size={24} />
                בחר מסמכים לייצור
              </h2>
              <span className="text-sm text-slate-400">
                {selectedCount} מסמכים נבחרו
              </span>
            </div>

            <div className="space-y-4">
              {Object.entries(categories).map(([category, docs]) => (
                <div key={category} className="border border-slate-800 rounded-xl overflow-hidden">
                  <div
                    onClick={() => setExpandedCategory(expandedCategory === category ? null : category)}
                    className="flex items-center justify-between p-4 bg-slate-800/50 cursor-pointer hover:bg-slate-800 transition"
                  >
                    <div className="flex items-center gap-3">
                      {expandedCategory === category ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                      <span className="font-medium">{category}</span>
                      <span className="text-xs text-slate-400">({docs.length} מסמכים)</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={(e) => { e.stopPropagation(); toggleCategory(category, true); }}
                        className="text-xs text-blue-400 hover:text-blue-300"
                      >
                        בחר הכל
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); toggleCategory(category, false); }}
                        className="text-xs text-slate-400 hover:text-slate-300"
                      >
                        בטל הכל
                      </button>
                    </div>
                  </div>

                  {expandedCategory === category && (
                    <div className="p-4 space-y-2">
                      {docs.map(doc => (
                        <div
                          key={doc.id}
                          onClick={() => toggleDocument(doc.id)}
                          className={`flex items-center gap-3 p-3 rounded-lg cursor-pointer transition ${
                            doc.selected ? 'bg-blue-500/20 border border-blue-500/30' : 'bg-slate-800/50 hover:bg-slate-800'
                          }`}
                        >
                          {doc.selected ? (
                            <CheckSquare size={20} className="text-blue-400" />
                          ) : (
                            <Square size={20} className="text-slate-500" />
                          )}
                          <div>
                            <div className="font-medium">{doc.name}</div>
                            <div className="text-xs text-slate-400">{doc.description}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Navigation */}
            <div className="mt-8 flex justify-between">
              <button
                onClick={() => setStep('input')}
                className="flex items-center gap-2 px-6 py-3 bg-slate-700 hover:bg-slate-600 rounded-xl transition"
              >
                חזור
              </button>
              <button
                onClick={handleGenerate}
                disabled={selectedCount === 0}
                className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 disabled:opacity-50 disabled:cursor-not-allowed rounded-xl font-bold transition"
              >
                <Zap size={20} />
                ייצר {selectedCount} מסמכים
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Generation Progress */}
        {step === 'generate' && (
          <div className="bg-slate-900/80 backdrop-blur-xl rounded-2xl border border-white/10 p-6">
            <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
              <Loader2 size={24} className="animate-spin" />
              מייצר מסמכים...
            </h2>

            <div className="space-y-3">
              {documentTypes.filter(d => d.selected).map((doc, i) => {
                const generated = generatedDocs.find(g => g.id === doc.id);
                return (
                  <div
                    key={doc.id}
                    className={`flex items-center gap-3 p-4 rounded-xl transition ${
                      generated ? 'bg-green-500/20 border border-green-500/30' : 'bg-slate-800'
                    }`}
                  >
                    {generated ? (
                      <CheckCircle2 size={20} className="text-green-400" />
                    ) : isGenerating && i === generatedDocs.length ? (
                      <Loader2 size={20} className="animate-spin text-blue-400" />
                    ) : (
                      <div className="w-5 h-5 rounded-full border-2 border-slate-600" />
                    )}
                    <div>
                      <div className="font-medium">{doc.name}</div>
                      {generated && (
                        <div className="text-xs text-green-400">{generated.fileName}</div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Step 4: Complete */}
        {step === 'complete' && (
          <div className="bg-slate-900/80 backdrop-blur-xl rounded-2xl border border-white/10 p-6">
            <div className="text-center py-8">
              <CheckCircle2 size={64} className="mx-auto mb-4 text-green-400" />
              <h2 className="text-2xl font-bold mb-2">הושלם!</h2>
              <p className="text-slate-400 mb-8">
                {generatedDocs.length} מסמכים נוצרו בהצלחה עבור {projectData.projectName}
              </p>

              <div className="grid grid-cols-2 gap-4 max-w-md mx-auto">
                <button
                  onClick={() => {/* Download all */}}
                  className="flex items-center justify-center gap-2 px-6 py-3 bg-slate-700 hover:bg-slate-600 rounded-xl transition"
                >
                  <Download size={20} />
                  הורד הכל
                </button>
                <button
                  onClick={sendToSignatureFlow}
                  className="flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 rounded-xl font-bold transition"
                >
                  <FileSignature size={20} />
                  המשך לחתימה
                </button>
              </div>
            </div>

            {/* Generated Documents List */}
            <div className="mt-8 border-t border-slate-800 pt-6">
              <h3 className="font-bold mb-4">מסמכים שנוצרו:</h3>
              <div className="grid grid-cols-2 gap-3">
                {generatedDocs.map(doc => (
                  <div
                    key={doc.id}
                    className="flex items-center gap-3 p-3 bg-slate-800 rounded-lg"
                  >
                    <FileText size={18} className="text-green-400" />
                    <div className="flex-1 min-w-0">
                      <div className="font-medium truncate">{doc.name}</div>
                      <div className="text-xs text-slate-400 truncate">{doc.fileName}</div>
                    </div>
                    <button className="p-1.5 hover:bg-slate-700 rounded">
                      <Download size={16} />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
