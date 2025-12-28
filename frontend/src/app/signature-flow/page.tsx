'use client';

/**
 * Signature Flow Cockpit - Mission Control V2.1
 * ==============================================
 * Premium UI for the Engineering Signature Pipeline
 *
 * V2.1: REAL PDF RENDERING in Canvas Editor
 * - Uses react-pdf for actual document display
 * - Stamps overlay on real PDF pages
 * - Proper positioning relative to document
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import dynamic from 'next/dynamic';

// Dynamic import for PDF viewer to avoid SSR issues with DOMMatrix
const PDFViewer = dynamic(() => import('@/components/PDFViewer'), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center bg-slate-800" style={{ width: 595, minHeight: 842 }}>
      <div className="text-slate-400">Loading PDF...</div>
    </div>
  ),
});

import {
  FileSignature, Upload, Check, X, Send, RefreshCw, Eye, Clock,
  AlertTriangle, CheckCircle2, XCircle, Mail, FileText, Loader2,
  GripVertical, ZoomIn, ZoomOut, RotateCcw, Download, Trash2,
  Settings, Activity, ChevronRight, ChevronDown, Move, Maximize2,
  Image, Link, Stamp, MinusCircle, PlusCircle, RotateCw, Save,
  ChevronLeft, ArrowLeft, ArrowRight
} from 'lucide-react';

// PDF.js worker setup - done in useEffect to avoid SSR issues

// ============================================================================
// TYPES
// ============================================================================

interface SignatureEntry {
  id: string;
  projectName: string;
  docType: string;
  requestDate: string;
  status: 'pending' | 'processing' | 'approved' | 'rejected' | 'sent';
  originalFilePath: string;
  processedFilePath: string | null;
  senderEmail: string | null;
  senderName: string | null;
  subject: string | null;
  signaturePosition: { x: number; y: number; width: number; height: number };
  notes: string;
  history: Array<{ action: string; timestamp: string; details: string }>;
}

interface StampConfig {
  id: string;
  type: 'engineer' | 'company';
  name: string;
  imagePath: string;
  x: number;
  y: number;
  width: number;
  height: number;
  rotation: number;
  visible: boolean;
  page: number; // Which page the stamp is on
}

interface Stats {
  total: number;
  pending: number;
  processing: number;
  approved: number;
  rejected: number;
  sent: number;
}

interface LogEntry {
  timestamp: string;
  level: 'INFO' | 'WARN' | 'ERROR' | 'SUCCESS' | 'DEBUG';
  message: string;
}

// ============================================================================
// AVAILABLE STAMPS
// ============================================================================

const AVAILABLE_STAMPS: Omit<StampConfig, 'x' | 'y' | 'page'>[] = [
  {
    id: 'stamp_engineer',
    type: 'engineer',
    name: 'חותמת מהנדס - נימרוד עופר',
    imagePath: '/assets/signatures/engineer_stamp.png',
    width: 120,
    height: 120,
    rotation: 0,
    visible: true
  },
  {
    id: 'stamp_company',
    type: 'company',
    name: 'חותמת חברה - אושר דוד',
    imagePath: '/assets/signatures/company_stamp.png',
    width: 150,
    height: 70,
    rotation: 0,
    visible: true
  }
];

// ============================================================================
// WEBSOCKET HOOK
// ============================================================================

const useSignatureService = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [signatures, setSignatures] = useState<SignatureEntry[]>([]);
  const [stats, setStats] = useState<Stats>({ total: 0, pending: 0, processing: 0, approved: 0, rejected: 0, sent: 0 });
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const ws = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    ws.current = new WebSocket('ws://localhost:8081');

    ws.current.onopen = () => {
      setIsConnected(true);
      console.log('Connected to Signature Pipeline');
    };

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleMessage(data);
    };

    ws.current.onclose = () => {
      setIsConnected(false);
      setTimeout(connect, 3000);
    };

    ws.current.onerror = () => {
      setIsConnected(false);
    };
  }, []);

  const handleMessage = (data: any) => {
    switch (data.type) {
      case 'init':
        setSignatures(data.signatures || []);
        setStats(data.stats);
        setLogs(data.logs || []);
        break;
      case 'signatures':
        setSignatures(data.signatures);
        if (data.stats) setStats(data.stats);
        break;
      case 'signature-added':
      case 'signature-updated':
      case 'signature-approved':
      case 'signature-rejected':
      case 'signature-sent':
      case 'signature-rollback':
        send({ action: 'get-all' });
        break;
      case 'stats':
        setStats(data.stats);
        break;
      case 'log':
        setLogs(prev => [...prev.slice(-499), data]);
        break;
      case 'logs':
        setLogs(data.logs);
        break;
      case 'error':
        console.error('Service error:', data.message);
        break;
    }
  };

  const send = useCallback((message: any) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message));
    }
  }, []);

  useEffect(() => {
    connect();
    return () => {
      ws.current?.close();
    };
  }, [connect]);

  return { isConnected, signatures, stats, logs, send };
};

// ============================================================================
// CANVAS EDITOR COMPONENT WITH REAL PDF
// ============================================================================

interface CanvasEditorProps {
  documentName: string;
  pdfUrl: string;
  stamps: StampConfig[];
  onStampsChange: (stamps: StampConfig[]) => void;
  onConfirm: () => void;
  onCancel: () => void;
}

function CanvasEditor({ documentName, pdfUrl, stamps, onStampsChange, onConfirm, onCancel }: CanvasEditorProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [selectedStampId, setSelectedStampId] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [numPages, setNumPages] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pdfLoading, setPdfLoading] = useState(true);
  const [pdfError, setPdfError] = useState<string | null>(null);
  const [pageSize, setPageSize] = useState({ width: 595, height: 842 }); // A4 default

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setPdfLoading(false);
    setPdfError(null);
  };

  const onDocumentLoadError = (error: Error) => {
    console.error('PDF load error:', error);
    setPdfError('שגיאה בטעינת המסמך');
    setPdfLoading(false);
  };

  const onPageLoadSuccess = (page: any) => {
    setPageSize({
      width: page.width,
      height: page.height
    });
  };

  const updateStamp = (id: string, updates: Partial<StampConfig>) => {
    onStampsChange(stamps.map(s => s.id === id ? { ...s, ...updates } : s));
  };

  const handleMouseDown = (e: React.MouseEvent, stampId: string) => {
    e.preventDefault();
    e.stopPropagation();
    setSelectedStampId(stampId);
    setIsDragging(true);
    setDragStart({ x: e.clientX, y: e.clientY });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging || !selectedStampId) return;

    const stamp = stamps.find(s => s.id === selectedStampId);
    if (!stamp) return;

    const dx = (e.clientX - dragStart.x) / zoom;
    const dy = (e.clientY - dragStart.y) / zoom;

    updateStamp(selectedStampId, {
      x: Math.max(0, stamp.x + dx),
      y: Math.max(0, stamp.y + dy)
    });

    setDragStart({ x: e.clientX, y: e.clientY });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleResize = (stampId: string, delta: number) => {
    const stamp = stamps.find(s => s.id === stampId);
    if (!stamp) return;
    const scale = 1 + delta * 0.1;
    updateStamp(stampId, {
      width: Math.max(30, Math.min(300, stamp.width * scale)),
      height: Math.max(30, Math.min(300, stamp.height * scale))
    });
  };

  const handleRotate = (stampId: string, delta: number) => {
    const stamp = stamps.find(s => s.id === stampId);
    if (!stamp) return;
    updateStamp(stampId, { rotation: (stamp.rotation + delta + 360) % 360 });
  };

  const toggleVisibility = (stampId: string) => {
    const stamp = stamps.find(s => s.id === stampId);
    if (!stamp) return;
    updateStamp(stampId, { visible: !stamp.visible });
  };

  const deleteStamp = (stampId: string) => {
    onStampsChange(stamps.filter(s => s.id !== stampId));
    if (selectedStampId === stampId) setSelectedStampId(null);
  };

  const moveStampToPage = (stampId: string, page: number) => {
    updateStamp(stampId, { page });
  };

  // Get stamps for current page
  const currentPageStamps = stamps.filter(s => s.page === currentPage);

  return (
    <div className="fixed inset-0 bg-black/90 flex flex-col z-50" dir="rtl">
      {/* Header */}
      <div className="bg-slate-900 border-b border-white/10 p-3 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-4">
          <Maximize2 className="text-purple-400" size={20} />
          <div>
            <h2 className="font-bold text-sm">עורך חותמות - תצוגה מקדימה</h2>
            <p className="text-xs text-slate-400">{documentName}</p>
          </div>
        </div>

        {/* Page Navigation */}
        {numPages > 1 && (
          <div className="flex items-center gap-2 bg-slate-800 rounded-lg px-3 py-1.5">
            <button
              onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
              disabled={currentPage <= 1}
              className="p-1 hover:bg-white/10 rounded disabled:opacity-30"
            >
              <ArrowRight size={16} />
            </button>
            <span className="text-sm min-w-[80px] text-center">
              עמוד {currentPage} / {numPages}
            </span>
            <button
              onClick={() => setCurrentPage(p => Math.min(numPages, p + 1))}
              disabled={currentPage >= numPages}
              className="p-1 hover:bg-white/10 rounded disabled:opacity-30"
            >
              <ArrowLeft size={16} />
            </button>
          </div>
        )}

        {/* Zoom Controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setZoom(z => Math.max(0.5, z - 0.1))}
            className="p-1.5 hover:bg-white/10 rounded-lg transition"
          >
            <ZoomOut size={16} />
          </button>
          <span className="text-xs w-12 text-center">{Math.round(zoom * 100)}%</span>
          <button
            onClick={() => setZoom(z => Math.min(2, z + 0.1))}
            className="p-1.5 hover:bg-white/10 rounded-lg transition"
          >
            <ZoomIn size={16} />
          </button>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={onCancel}
            className="px-4 py-1.5 bg-slate-700 hover:bg-slate-600 rounded-lg transition text-sm"
          >
            ביטול
          </button>
          <button
            onClick={onConfirm}
            className="px-4 py-1.5 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 rounded-lg font-bold transition flex items-center gap-2 text-sm"
          >
            <Check size={16} />
            אישור סופי וחתימה
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Stamps Panel */}
        <div className="w-64 bg-slate-900/95 border-l border-white/10 p-3 overflow-y-auto flex-shrink-0">
          <h3 className="font-bold mb-3 flex items-center gap-2 text-sm">
            <Stamp size={16} />
            חותמות
          </h3>

          {/* Stamps List */}
          <div className="space-y-2">
            {stamps.map(stamp => (
              <div
                key={stamp.id}
                onClick={() => setSelectedStampId(stamp.id)}
                className={`p-2 rounded-lg border cursor-pointer transition text-sm ${
                  selectedStampId === stamp.id
                    ? 'border-purple-500 bg-purple-500/20'
                    : 'border-white/10 bg-slate-800/50 hover:bg-slate-800'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-medium truncate flex-1">{stamp.name}</span>
                  <button
                    onClick={(e) => { e.stopPropagation(); toggleVisibility(stamp.id); }}
                    className={`p-1 rounded ${stamp.visible ? 'text-green-400' : 'text-slate-500'}`}
                  >
                    <Eye size={12} />
                  </button>
                </div>

                {/* Preview */}
                <div className="h-12 bg-slate-700 rounded flex items-center justify-center mb-1 overflow-hidden">
                  <img
                    src={stamp.imagePath}
                    alt={stamp.name}
                    className="max-h-full max-w-full object-contain"
                    style={{ opacity: stamp.visible ? 1 : 0.3 }}
                  />
                </div>

                {/* Page indicator */}
                <div className="text-[10px] text-slate-500 text-center">
                  עמוד {stamp.page}
                </div>

                {/* Controls for selected stamp */}
                {selectedStampId === stamp.id && (
                  <div className="space-y-1.5 pt-2 border-t border-white/10 mt-2">
                    {/* Size */}
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] text-slate-400">גודל</span>
                      <div className="flex items-center gap-1">
                        <button
                          onClick={(e) => { e.stopPropagation(); handleResize(stamp.id, -1); }}
                          className="p-0.5 hover:bg-white/10 rounded"
                        >
                          <MinusCircle size={12} />
                        </button>
                        <span className="text-[10px] w-14 text-center">
                          {Math.round(stamp.width)}x{Math.round(stamp.height)}
                        </span>
                        <button
                          onClick={(e) => { e.stopPropagation(); handleResize(stamp.id, 1); }}
                          className="p-0.5 hover:bg-white/10 rounded"
                        >
                          <PlusCircle size={12} />
                        </button>
                      </div>
                    </div>

                    {/* Rotation */}
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] text-slate-400">סיבוב</span>
                      <div className="flex items-center gap-1">
                        <button
                          onClick={(e) => { e.stopPropagation(); handleRotate(stamp.id, -15); }}
                          className="p-0.5 hover:bg-white/10 rounded"
                        >
                          <RotateCcw size={12} />
                        </button>
                        <span className="text-[10px] w-8 text-center">{stamp.rotation}°</span>
                        <button
                          onClick={(e) => { e.stopPropagation(); handleRotate(stamp.id, 15); }}
                          className="p-0.5 hover:bg-white/10 rounded"
                        >
                          <RotateCw size={12} />
                        </button>
                      </div>
                    </div>

                    {/* Page selector */}
                    {numPages > 1 && (
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] text-slate-400">עמוד</span>
                        <select
                          value={stamp.page}
                          onChange={(e) => { e.stopPropagation(); moveStampToPage(stamp.id, parseInt(e.target.value)); }}
                          className="bg-slate-700 rounded px-1 py-0.5 text-[10px]"
                          onClick={e => e.stopPropagation()}
                        >
                          {Array.from({ length: numPages }, (_, i) => (
                            <option key={i + 1} value={i + 1}>עמוד {i + 1}</option>
                          ))}
                        </select>
                      </div>
                    )}

                    {/* Delete */}
                    <button
                      onClick={(e) => { e.stopPropagation(); deleteStamp(stamp.id); }}
                      className="w-full mt-1 px-2 py-1 bg-red-500/20 text-red-400 hover:bg-red-500/30 rounded text-[10px] flex items-center justify-center gap-1"
                    >
                      <Trash2 size={10} />
                      הסר
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Add Stamp */}
          <div className="mt-3 pt-3 border-t border-white/10">
            <p className="text-[10px] text-slate-400 mb-1">הוסף חותמת:</p>
            <div className="space-y-1">
              {AVAILABLE_STAMPS.filter(as => !stamps.find(s => s.id === as.id)).map(stamp => (
                <button
                  key={stamp.id}
                  onClick={() => onStampsChange([...stamps, { ...stamp, x: 50, y: 50, page: currentPage }])}
                  className="w-full px-2 py-1.5 bg-slate-800 hover:bg-slate-700 rounded text-[11px] text-right transition"
                >
                  + {stamp.name}
                </button>
              ))}
              {AVAILABLE_STAMPS.filter(as => !stamps.find(s => s.id === as.id)).length === 0 && (
                <p className="text-[10px] text-slate-500 text-center">כל החותמות בשימוש</p>
              )}
            </div>
          </div>
        </div>

        {/* PDF Canvas Area */}
        <div
          ref={containerRef}
          className="flex-1 bg-slate-800 overflow-auto p-4"
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
        >
          <div className="flex justify-center">
            {/* PDF Document with Stamps Overlay */}
            <div
              className="relative shadow-2xl"
              style={{ transform: `scale(${zoom})`, transformOrigin: 'top center' }}
            >
              {pdfLoading && (
                <div className="absolute inset-0 flex items-center justify-center bg-slate-900 rounded-lg" style={{ width: 595, height: 842 }}>
                  <div className="text-center">
                    <Loader2 size={32} className="animate-spin mx-auto mb-2 text-purple-400" />
                    <p className="text-sm text-slate-400">טוען מסמך...</p>
                  </div>
                </div>
              )}

              {pdfError && (
                <div className="flex items-center justify-center bg-slate-900 rounded-lg" style={{ width: 595, height: 842 }}>
                  <div className="text-center text-red-400">
                    <AlertTriangle size={32} className="mx-auto mb-2" />
                    <p className="text-sm">{pdfError}</p>
                    <p className="text-xs text-slate-500 mt-2">נסה לפתוח את המסמך בחלון חדש</p>
                  </div>
                </div>
              )}

              <PDFViewer
                file={pdfUrl}
                pageNumber={currentPage}
                onLoadSuccess={onDocumentLoadSuccess}
                onLoadError={onDocumentLoadError}
                className="pdf-document"
              />

              {/* Stamps Overlay - only for current page */}
              {!pdfLoading && !pdfError && currentPageStamps.filter(s => s.visible).map(stamp => (
                <div
                  key={stamp.id}
                  className={`absolute cursor-move transition-shadow bg-transparent ${
                    selectedStampId === stamp.id ? 'ring-2 ring-purple-500 ring-offset-2 ring-offset-transparent shadow-lg z-10' : 'z-5'
                  }`}
                  style={{
                    left: stamp.x,
                    top: stamp.y,
                    width: stamp.width,
                    height: stamp.height,
                    transform: `rotate(${stamp.rotation}deg)`,
                    background: 'transparent',
                  }}
                  onMouseDown={(e) => handleMouseDown(e, stamp.id)}
                >
                  <img
                    src={stamp.imagePath}
                    alt={stamp.name}
                    className="w-full h-full object-contain pointer-events-none"
                    draggable={false}
                    style={{
                      mixBlendMode: 'multiply',
                      background: 'transparent',
                    }}
                  />
                  {selectedStampId === stamp.id && (
                    <>
                      <div className="absolute -top-1 -left-1 w-2 h-2 bg-purple-500 rounded-full" />
                      <div className="absolute -top-1 -right-1 w-2 h-2 bg-purple-500 rounded-full" />
                      <div className="absolute -bottom-1 -left-1 w-2 h-2 bg-purple-500 rounded-full" />
                      <div className="absolute -bottom-1 -right-1 w-2 h-2 bg-purple-500 rounded-full" />
                      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-none">
                        <Move size={16} className="text-purple-500 opacity-50" />
                      </div>
                    </>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Instructions Footer */}
      <div className="bg-slate-900 border-t border-white/10 p-2 text-center text-[10px] text-slate-400 flex-shrink-0">
        <span className="mx-3">גרור חותמות למיקום הרצוי</span>
        <span className="mx-3">|</span>
        <span className="mx-3">השתמש בפאנל השמאלי לשינוי גודל וסיבוב</span>
        <span className="mx-3">|</span>
        <span className="mx-3">לחץ "אישור סופי" כשהתוצאה מושלמת</span>
      </div>
    </div>
  );
}

// ============================================================================
// STAMP PREVIEW MODAL
// ============================================================================

interface StampPreviewModalProps {
  stamp: Omit<StampConfig, 'x' | 'y' | 'page'>;
  onClose: () => void;
}

function StampPreviewModal({ stamp, onClose }: StampPreviewModalProps) {
  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-slate-900 rounded-2xl p-6 max-w-md border border-white/10" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-bold">{stamp.name}</h3>
          <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-lg">
            <X size={18} />
          </button>
        </div>
        <div className="bg-white rounded-xl p-4">
          <img
            src={stamp.imagePath}
            alt={stamp.name}
            className="max-w-full max-h-64 mx-auto"
          />
        </div>
        <p className="text-xs text-slate-400 text-center mt-4">
          {stamp.type === 'engineer' ? 'חותמת מהנדס רשום' : 'חותמת חברה'}
        </p>
      </div>
    </div>
  );
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export default function SignatureFlowPage() {
  const { isConnected, signatures, stats, logs, send } = useSignatureService();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showLogs, setShowLogs] = useState(false);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [recipientEmail, setRecipientEmail] = useState('');
  const [showSendModal, setShowSendModal] = useState(false);

  // Canvas Editor State
  const [showCanvasEditor, setShowCanvasEditor] = useState(false);
  const [editorStamps, setEditorStamps] = useState<StampConfig[]>([]);
  const [pendingApprovalId, setPendingApprovalId] = useState<string | null>(null);
  const [editorPdfUrl, setEditorPdfUrl] = useState<string>('');

  // Stamp Preview State
  const [previewStamp, setPreviewStamp] = useState<Omit<StampConfig, 'x' | 'y' | 'page'> | null>(null);

  const selectedSignature = signatures.find(s => s.id === selectedId);

  // Build PDF URL from file path
  const getPdfUrl = (filePath: string) => {
    const fileName = filePath.split('/').pop();
    return `/uploads/pending_signatures/${encodeURIComponent(fileName || '')}`;
  };

  // Initialize stamps for editor
  const initializeStampsForEditor = (signatureId: string) => {
    const sig = signatures.find(s => s.id === signatureId);
    if (!sig) return;

    // Start with both stamps at default positions on page 1
    const initialStamps: StampConfig[] = AVAILABLE_STAMPS.map((stamp, idx) => ({
      ...stamp,
      x: 50 + idx * 30,
      y: 650 + idx * 40, // Near bottom of page
      page: 1
    }));

    setEditorStamps(initialStamps);
    setPendingApprovalId(signatureId);
    setEditorPdfUrl(getPdfUrl(sig.originalFilePath));
    setShowCanvasEditor(true);
  };

  // Handle canvas editor confirm
  const handleCanvasConfirm = () => {
    if (pendingApprovalId) {
      send({
        action: 'approve-signature',
        data: {
          id: pendingApprovalId,
          stamps: editorStamps.filter(s => s.visible).map(s => ({
            type: s.type,
            x: s.x,
            y: s.y,
            width: s.width,
            height: s.height,
            rotation: s.rotation,
            page: s.page
          }))
        }
      });
    }
    setShowCanvasEditor(false);
    setPendingApprovalId(null);
  };

  // Actions
  const handleOpenCanvasEditor = (id: string) => {
    initializeStampsForEditor(id);
  };

  const handleReject = (id: string, reason?: string) => {
    send({ action: 'reject-signature', data: { id, reason } });
  };

  const handleSend = (id: string, email: string) => {
    send({ action: 'send-signed', data: { id, recipientEmail: email } });
    setShowSendModal(false);
  };

  const handleRollback = (id: string) => {
    send({ action: 'rollback', data: { id } });
  };

  const handleUpload = (file: File, projectName: string, docType: string) => {
    const reader = new FileReader();
    reader.onload = () => {
      const base64 = (reader.result as string).split(',')[1];
      send({
        action: 'upload-document',
        data: { fileName: file.name, fileContent: base64, projectName, docType }
      });
      setUploadModalOpen(false);
    };
    reader.readAsDataURL(file);
  };

  // Status Helpers
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending': return 'text-yellow-400 bg-yellow-500/20';
      case 'processing': return 'text-purple-400 bg-purple-500/20';
      case 'approved': return 'text-green-400 bg-green-500/20';
      case 'rejected': return 'text-red-400 bg-red-500/20';
      case 'sent': return 'text-blue-400 bg-blue-500/20';
      default: return 'text-slate-400 bg-slate-500/20';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pending': return <Clock size={14} />;
      case 'processing': return <Loader2 size={14} className="animate-spin" />;
      case 'approved': return <CheckCircle2 size={14} />;
      case 'rejected': return <XCircle size={14} />;
      case 'sent': return <Send size={14} />;
      default: return <FileText size={14} />;
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'pending': return 'ממתין לחתימה';
      case 'processing': return 'מעבד...';
      case 'approved': return 'אושר';
      case 'rejected': return 'נדחה';
      case 'sent': return 'נשלח';
      default: return status;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-white p-6" dir="rtl">

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-gradient-to-br from-purple-600 to-pink-600 rounded-xl">
            <FileSignature size={28} />
          </div>
          <div>
            <h1 className="text-2xl font-bold">מרכז חתימות</h1>
            <p className="text-sm text-slate-400">Signature Pipeline - Mission Control</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium ${
            isConnected ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
          }`}>
            <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
            {isConnected ? 'מחובר' : 'מנותק'}
          </div>

          <button
            onClick={() => setUploadModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-500 rounded-lg transition"
          >
            <Upload size={16} />
            העלה מסמך
          </button>

          <button
            onClick={() => setShowLogs(!showLogs)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg transition ${
              showLogs ? 'bg-slate-700 text-white' : 'bg-slate-800 text-slate-400 hover:text-white'
            }`}
          >
            <Activity size={16} />
            לוגים
          </button>
        </div>
      </div>

      {/* Stats Bar */}
      <div className="grid grid-cols-6 gap-4 mb-6">
        {[
          { label: 'סה"כ', value: stats.total, color: 'bg-slate-700' },
          { label: 'ממתינים', value: stats.pending, color: 'bg-yellow-500/20 text-yellow-400' },
          { label: 'בעיבוד', value: stats.processing, color: 'bg-purple-500/20 text-purple-400' },
          { label: 'אושרו', value: stats.approved, color: 'bg-green-500/20 text-green-400' },
          { label: 'נדחו', value: stats.rejected, color: 'bg-red-500/20 text-red-400' },
          { label: 'נשלחו', value: stats.sent, color: 'bg-blue-500/20 text-blue-400' },
        ].map((stat, i) => (
          <div key={i} className={`p-4 rounded-xl ${stat.color} backdrop-blur-xl border border-white/10`}>
            <div className="text-2xl font-bold">{stat.value}</div>
            <div className="text-xs text-slate-400">{stat.label}</div>
          </div>
        ))}
      </div>

      {/* Main Content */}
      <div className="flex gap-6">

        {/* Queue Table */}
        <div className={`${selectedId ? 'w-1/3' : 'w-full'} transition-all duration-300`}>
          <div className="bg-slate-900/80 backdrop-blur-xl rounded-2xl border border-white/10 overflow-hidden">
            <div className="p-4 border-b border-white/10 flex items-center justify-between">
              <h2 className="font-bold flex items-center gap-2">
                <FileText size={18} />
                תור חתימות
              </h2>
              <span className="text-xs text-slate-400">{signatures.length} מסמכים</span>
            </div>

            <div className="max-h-[calc(100vh-350px)] overflow-y-auto">
              {signatures.length === 0 ? (
                <div className="p-8 text-center text-slate-500">
                  <FileSignature size={48} className="mx-auto mb-4 opacity-30" />
                  <p>אין מסמכים בתור</p>
                  <p className="text-xs mt-2">העלה מסמך או הפעל את ה-Harvester</p>
                </div>
              ) : (
                signatures.map(sig => (
                  <div
                    key={sig.id}
                    onClick={() => setSelectedId(sig.id === selectedId ? null : sig.id)}
                    className={`p-4 border-b border-white/5 cursor-pointer transition hover:bg-white/5 ${
                      selectedId === sig.id ? 'bg-purple-500/10 border-r-2 border-r-purple-500' : ''
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="font-medium text-sm">{sig.projectName}</div>
                        <div className="text-xs text-slate-400 mt-1">{sig.docType}</div>
                        {sig.senderEmail && (
                          <div className="text-xs text-slate-500 mt-1 flex items-center gap-1">
                            <Mail size={10} />
                            {sig.senderEmail}
                          </div>
                        )}
                      </div>
                      <div className="flex flex-col items-end gap-1">
                        <span className={`px-2 py-0.5 rounded-full text-xs flex items-center gap-1 ${getStatusColor(sig.status)}`}>
                          {getStatusIcon(sig.status)}
                          {getStatusText(sig.status)}
                        </span>
                        <span className="text-[10px] text-slate-500">
                          {new Date(sig.requestDate).toLocaleDateString('he-IL')}
                        </span>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Workspace */}
        {selectedId && selectedSignature && (
          <div className="flex-1 bg-slate-900/80 backdrop-blur-xl rounded-2xl border border-white/10 overflow-hidden">
            <div className="h-full flex flex-col">

              <div className="p-4 border-b border-white/10 flex items-center justify-between">
                <div>
                  <h2 className="font-bold">{selectedSignature.projectName}</h2>
                  <p className="text-xs text-slate-400">{selectedSignature.docType}</p>
                </div>
                <button
                  onClick={() => setSelectedId(null)}
                  className="p-2 hover:bg-white/10 rounded-lg transition"
                >
                  <X size={18} />
                </button>
              </div>

              <div className="flex-1 flex">
                {/* PDF Preview */}
                <div className="flex-1 border-l border-white/10 p-4">
                  <div className="h-full bg-slate-800 rounded-xl flex items-center justify-center relative overflow-hidden">
                    {selectedSignature.originalFilePath ? (
                      <iframe
                        src={getPdfUrl(selectedSignature.originalFilePath)}
                        className="w-full h-full rounded-xl"
                        title="PDF Preview"
                      />
                    ) : (
                      <p className="text-slate-500">אין קובץ</p>
                    )}
                  </div>
                </div>

                {/* Action Panel */}
                <div className="w-80 p-4 flex flex-col gap-4">
                  <div className={`p-3 rounded-xl ${getStatusColor(selectedSignature.status)}`}>
                    <div className="flex items-center gap-2">
                      {getStatusIcon(selectedSignature.status)}
                      <span className="font-medium">{getStatusText(selectedSignature.status)}</span>
                    </div>
                  </div>

                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-slate-400">תאריך בקשה:</span>
                      <span>{new Date(selectedSignature.requestDate).toLocaleString('he-IL')}</span>
                    </div>
                    {selectedSignature.notes && (
                      <div>
                        <span className="text-slate-400">הערות:</span>
                        <p className="text-xs mt-1 text-slate-300">{selectedSignature.notes}</p>
                      </div>
                    )}
                  </div>

                  {/* Stamp Preview Links */}
                  {selectedSignature.status === 'pending' && (
                    <div className="border border-white/10 rounded-xl p-3 bg-slate-800/50">
                      <p className="text-xs text-slate-400 mb-2 flex items-center gap-2">
                        <Stamp size={14} />
                        חותמות לאישור:
                      </p>
                      <div className="space-y-2">
                        {AVAILABLE_STAMPS.map(stamp => (
                          <button
                            key={stamp.id}
                            onClick={() => setPreviewStamp(stamp)}
                            className="w-full flex items-center gap-3 px-3 py-2 bg-slate-700/50 hover:bg-slate-700 rounded-lg transition text-right"
                          >
                            <div className="w-10 h-10 bg-white rounded flex items-center justify-center flex-shrink-0">
                              <img
                                src={stamp.imagePath}
                                alt={stamp.name}
                                className="max-w-full max-h-full object-contain"
                              />
                            </div>
                            <div className="flex-1">
                              <p className="text-xs font-medium">{stamp.name}</p>
                              <p className="text-[10px] text-slate-500">
                                {stamp.type === 'engineer' ? 'חותמת מהנדס' : 'חותמת חברה'}
                              </p>
                            </div>
                            <Link size={14} className="text-purple-400" />
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="flex-1" />

                  {selectedSignature.status === 'pending' && (
                    <>
                      <button
                        onClick={() => handleOpenCanvasEditor(selectedSignature.id)}
                        className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 rounded-xl font-bold transition"
                      >
                        <Check size={20} />
                        אשר וחתום
                      </button>
                      <p className="text-[10px] text-center text-slate-500">
                        לחיצה תפתח עורך למיקום החותמות על המסמך
                      </p>
                      <button
                        onClick={() => handleReject(selectedSignature.id)}
                        className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-slate-700 hover:bg-slate-600 rounded-xl transition"
                      >
                        <X size={20} />
                        דחה
                      </button>
                    </>
                  )}

                  {selectedSignature.status === 'approved' && (
                    <>
                      <button
                        onClick={() => {
                          setRecipientEmail(selectedSignature.senderEmail || '');
                          setShowSendModal(true);
                        }}
                        className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 rounded-xl font-bold transition"
                      >
                        <Send size={20} />
                        שלח במייל
                      </button>
                      <button
                        onClick={() => handleRollback(selectedSignature.id)}
                        className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-slate-700 hover:bg-slate-600 rounded-xl transition"
                      >
                        <RotateCcw size={16} />
                        בטל חתימה
                      </button>
                    </>
                  )}

                  {selectedSignature.status === 'sent' && (
                    <div className="text-center text-green-400 py-4">
                      <CheckCircle2 size={32} className="mx-auto mb-2" />
                      <p className="font-medium">המסמך נשלח בהצלחה!</p>
                    </div>
                  )}

                  {/* History */}
                  {selectedSignature.history && selectedSignature.history.length > 0 && (
                    <div className="mt-4">
                      <details className="group">
                        <summary className="flex items-center gap-2 text-xs text-slate-400 cursor-pointer">
                          <ChevronRight size={14} className="group-open:rotate-90 transition" />
                          היסטוריה ({selectedSignature.history.length})
                        </summary>
                        <div className="mt-2 space-y-1 text-xs">
                          {selectedSignature.history.map((h, i) => (
                            <div key={i} className="flex justify-between text-slate-500">
                              <span>{h.action}</span>
                              <span>{new Date(h.timestamp).toLocaleTimeString('he-IL')}</span>
                            </div>
                          ))}
                        </div>
                      </details>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Logs Panel */}
      {showLogs && (
        <div className="fixed bottom-0 left-0 right-0 h-64 bg-slate-950/95 backdrop-blur-xl border-t border-white/10 z-40">
          <div className="h-full flex flex-col">
            <div className="p-2 border-b border-white/10 flex items-center justify-between">
              <span className="text-xs text-slate-400 font-mono flex items-center gap-2">
                <Activity size={12} />
                Operation Logs
              </span>
              <button onClick={() => setShowLogs(false)} className="p-1 hover:bg-white/10 rounded">
                <X size={14} />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-2 font-mono text-xs space-y-0.5">
              {logs.map((log, i) => (
                <div key={i} className={`flex gap-2 ${
                  log.level === 'ERROR' ? 'text-red-400' :
                  log.level === 'WARN' ? 'text-yellow-400' :
                  log.level === 'SUCCESS' ? 'text-green-400' :
                  log.level === 'DEBUG' ? 'text-purple-400' : 'text-slate-400'
                }`}>
                  <span className="text-slate-600">{new Date(log.timestamp).toLocaleTimeString('he-IL')}</span>
                  <span className="w-16">[{log.level}]</span>
                  <span>{log.message}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Canvas Editor Modal */}
      {showCanvasEditor && pendingApprovalId && (
        <CanvasEditor
          documentName={signatures.find(s => s.id === pendingApprovalId)?.originalFilePath?.split('/').pop() || 'Document'}
          pdfUrl={editorPdfUrl}
          stamps={editorStamps}
          onStampsChange={setEditorStamps}
          onConfirm={handleCanvasConfirm}
          onCancel={() => { setShowCanvasEditor(false); setPendingApprovalId(null); }}
        />
      )}

      {/* Stamp Preview Modal */}
      {previewStamp && (
        <StampPreviewModal
          stamp={previewStamp}
          onClose={() => setPreviewStamp(null)}
        />
      )}

      {/* Upload Modal */}
      {uploadModalOpen && (
        <UploadModal
          onClose={() => setUploadModalOpen(false)}
          onUpload={handleUpload}
        />
      )}

      {/* Send Modal */}
      {showSendModal && selectedSignature && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-900 rounded-2xl p-6 w-96 border border-white/10">
            <h3 className="text-lg font-bold mb-4">שלח מסמך חתום</h3>
            <div className="space-y-4">
              <div>
                <label className="text-sm text-slate-400">כתובת מייל</label>
                <input
                  type="email"
                  value={recipientEmail}
                  onChange={(e) => setRecipientEmail(e.target.value)}
                  placeholder="email@example.com"
                  className="w-full mt-1 px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-purple-500"
                />
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setShowSendModal(false)}
                  className="flex-1 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition"
                >
                  ביטול
                </button>
                <button
                  onClick={() => handleSend(selectedSignature.id, recipientEmail)}
                  disabled={!recipientEmail}
                  className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-lg transition flex items-center justify-center gap-2"
                >
                  <Send size={16} />
                  שלח
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// UPLOAD MODAL
// ============================================================================

function UploadModal({ onClose, onUpload }: { onClose: () => void; onUpload: (file: File, projectName: string, docType: string) => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [projectName, setProjectName] = useState('');
  const [docType, setDocType] = useState('אישור כללי');
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile?.type === 'application/pdf') {
      setFile(droppedFile);
    }
  };

  const handleSubmit = () => {
    if (file && projectName) {
      onUpload(file, projectName, docType);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-slate-900 rounded-2xl p-6 w-[500px] border border-white/10" dir="rtl">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-bold">העלה מסמך לחתימה</h3>
          <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-lg">
            <X size={18} />
          </button>
        </div>

        <div
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition ${
            isDragging ? 'border-purple-500 bg-purple-500/10' : 'border-slate-700 hover:border-slate-600'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            className="hidden"
          />
          {file ? (
            <div className="flex items-center justify-center gap-3">
              <FileText size={24} className="text-purple-400" />
              <span>{file.name}</span>
            </div>
          ) : (
            <>
              <Upload size={32} className="mx-auto mb-3 text-slate-500" />
              <p className="text-slate-400">גרור קובץ PDF לכאן</p>
              <p className="text-xs text-slate-500 mt-1">או לחץ לבחירת קובץ</p>
            </>
          )}
        </div>

        <div className="space-y-4 mt-6">
          <div>
            <label className="text-sm text-slate-400">שם הפרויקט *</label>
            <input
              type="text"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              placeholder="למשל: ארלוזורוב 20"
              className="w-full mt-1 px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-purple-500"
            />
          </div>
          <div>
            <label className="text-sm text-slate-400">סוג מסמך</label>
            <select
              value={docType}
              onChange={(e) => setDocType(e.target.value)}
              className="w-full mt-1 px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:outline-none focus:border-purple-500"
            >
              <option value="אישור כללי">אישור כללי</option>
              <option value="טופס 4">טופס 4</option>
              <option value="תצהיר אינסטלציה">תצהיר אינסטלציה</option>
              <option value="בניה ירוקה">בניה ירוקה</option>
              <option value="אישור מכבי אש">אישור מכבי אש</option>
            </select>
          </div>
        </div>

        <div className="flex gap-2 mt-6">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition"
          >
            ביטול
          </button>
          <button
            onClick={handleSubmit}
            disabled={!file || !projectName}
            className="flex-1 px-4 py-2 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition flex items-center justify-center gap-2"
          >
            <Upload size={16} />
            העלה
          </button>
        </div>
      </div>
    </div>
  );
}
