'use client';

/**
 * PDFViewer Component - Client-side only PDF rendering
 * Uses react-pdf with complete SSR guard
 */

import React, { useEffect, useState, useRef } from 'react';

interface PDFViewerProps {
  file: string;
  pageNumber: number;
  width?: number;
  onLoadSuccess?: (data: { numPages: number }) => void;
  onLoadError?: (error: Error) => void;
  className?: string;
}

// These will be set after dynamic import
let Document: any = null;
let Page: any = null;

export const PDFViewer: React.FC<PDFViewerProps> = ({
  file,
  pageNumber,
  width = 595,
  onLoadSuccess,
  onLoadError,
  className,
}) => {
  const [isReady, setIsReady] = useState(false);
  const [numPages, setNumPages] = useState<number | null>(null);
  const initRef = useRef(false);

  useEffect(() => {
    // Only run on client side, only once
    if (typeof window === 'undefined' || initRef.current) return;
    initRef.current = true;

    // Dynamic import of react-pdf (client-side only)
    Promise.all([
      import('react-pdf'),
      import('react-pdf/dist/Page/AnnotationLayer.css'),
      import('react-pdf/dist/Page/TextLayer.css'),
    ]).then(([pdfModule]) => {
      // Set up worker
      pdfModule.pdfjs.GlobalWorkerOptions.workerSrc =
        `//unpkg.com/pdfjs-dist@${pdfModule.pdfjs.version}/build/pdf.worker.min.mjs`;

      Document = pdfModule.Document;
      Page = pdfModule.Page;
      setIsReady(true);
    }).catch(err => {
      console.error('Failed to load react-pdf:', err);
      onLoadError?.(err);
    });
  }, []);

  const handleLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    onLoadSuccess?.({ numPages });
  };

  if (!isReady || !Document || !Page) {
    return (
      <div
        className={`flex items-center justify-center bg-slate-800 ${className || ''}`}
        style={{ width, minHeight: 842 }}
      >
        <div className="text-slate-400 animate-pulse">טוען PDF...</div>
      </div>
    );
  }

  return (
    <Document
      file={file}
      onLoadSuccess={handleLoadSuccess}
      onLoadError={onLoadError}
      className={className}
      loading={
        <div className="flex items-center justify-center bg-slate-800" style={{ width, minHeight: 842 }}>
          <div className="text-slate-400 animate-pulse">טוען מסמך...</div>
        </div>
      }
    >
      <Page
        pageNumber={pageNumber}
        width={width}
        renderTextLayer={true}
        renderAnnotationLayer={true}
      />
    </Document>
  );
};

export default PDFViewer;
