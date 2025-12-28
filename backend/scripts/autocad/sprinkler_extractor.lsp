;;; ============================================================================
;;; AQUABRAIN SPRINKLER EXTRACTOR - AutoLISP Script
;;; ============================================================================
;;; Version: 2.0 - Full XDATA Extraction
;;; Compatible: AutoCAD 2024-2026, accoreconsole.exe
;;; Output: JSON format for AquaBrain pipeline
;;; ============================================================================

;;; -----------------------------------------------------------------------------
;;; CONFIGURATION - הגדרות
;;; -----------------------------------------------------------------------------

;; Sprinkler block name patterns (case-insensitive)
(setq *SPRINKLER-PATTERNS* '(
  "SPK" "SPRINKLER" "SPRINK" "HEAD" "FIRE"
  "K5.6" "K8.0" "K11.2" "K14.0" "K16.8" "K25.2"
  "PEND" "UPRT" "SIDE" "CONC"
))

;; XDATA application names to search
(setq *XDATA-APPS* '("AQUABRAIN" "SPRINKLER" "HYDRO" "FIRE" "MEP"))

;; Output file path (will be set dynamically)
(setq *OUTPUT-FILE* nil)

;;; -----------------------------------------------------------------------------
;;; UTILITY FUNCTIONS - פונקציות עזר
;;; -----------------------------------------------------------------------------

;; Check if string contains pattern (case-insensitive)
(defun str-contains (str pattern / str-up pat-up)
  (if (and str pattern)
    (progn
      (setq str-up (strcase str))
      (setq pat-up (strcase pattern))
      (vl-string-search pat-up str-up)
    )
    nil
  )
)

;; Check if block name matches sprinkler patterns
(defun is-sprinkler-block (block-name / found)
  (setq found nil)
  (foreach pattern *SPRINKLER-PATTERNS*
    (if (str-contains block-name pattern)
      (setq found T)
    )
  )
  found
)

;; Get XDATA from entity for all registered applications
(defun get-entity-xdata (ent / ed app-data xdata-list)
  (setq xdata-list '())
  (foreach app *XDATA-APPS*
    (setq ed (entget ent (list app)))
    (if ed
      (progn
        (setq app-data (assoc -3 ed))
        (if app-data
          (setq xdata-list (append xdata-list (list (cdr app-data))))
        )
      )
    )
  )
  xdata-list
)

;; Parse XDATA to extract key-value pairs
(defun parse-xdata (xdata-list / result pair key val)
  (setq result '())
  (foreach app-xdata xdata-list
    (if (listp app-xdata)
      (foreach item app-xdata
        (if (listp item)
          (foreach sub-item item
            (cond
              ;; String value (1000)
              ((and (listp sub-item) (= (car sub-item) 1000))
               (setq result (cons (cons "xdata_str" (cdr sub-item)) result))
              )
              ;; Integer value (1070)
              ((and (listp sub-item) (= (car sub-item) 1070))
               (setq result (cons (cons "xdata_int" (cdr sub-item)) result))
              )
              ;; Real value (1040)
              ((and (listp sub-item) (= (car sub-item) 1040))
               (setq result (cons (cons "xdata_real" (cdr sub-item)) result))
              )
            )
          )
        )
      )
    )
  )
  result
)

;; Extract attributes from block reference
(defun get-block-attributes (ent / attribs att-list att-name att-val)
  (setq attribs (vlax-invoke (vlax-ename->vla-object ent) 'GetAttributes))
  (setq att-list '())
  (foreach att (vlax-safearray->list (vlax-variant-value attribs))
    (setq att-name (vla-get-TagString att))
    (setq att-val (vla-get-TextString att))
    (setq att-list (cons (cons att-name att-val) att-list))
  )
  att-list
)

;; Convert to JSON string
(defun to-json-string (str)
  (if str
    (progn
      ;; Escape special characters
      (setq str (vl-string-subst "\\\"" "\"" str))
      (setq str (vl-string-subst "\\\\" "\\" str))
      (strcat "\"" str "\"")
    )
    "null"
  )
)

;; Convert number to string
(defun num-to-str (num)
  (if num
    (rtos num 2 6)
    "0"
  )
)

;;; -----------------------------------------------------------------------------
;;; MAIN EXTRACTION FUNCTIONS - פונקציות חילוץ ראשיות
;;; -----------------------------------------------------------------------------

;; Extract single sprinkler data
(defun extract-sprinkler (ent / ed block-name ins-pt layer obj xdata attribs result)
  (setq ed (entget ent))
  (setq block-name (cdr (assoc 2 ed)))
  (setq ins-pt (cdr (assoc 10 ed)))
  (setq layer (cdr (assoc 8 ed)))

  ;; Get VLA object for more properties
  (setq obj (vlax-ename->vla-object ent))

  ;; Get XDATA
  (setq xdata (get-entity-xdata ent))
  (setq xdata-parsed (parse-xdata xdata))

  ;; Get attributes
  (setq attribs (get-block-attributes ent))

  ;; Build result alist
  (list
    (cons "ID" (vl-princ-to-string (vla-get-Handle obj)))
    (cons "BlockName" block-name)
    (cons "Layer" layer)
    (cons "X" (car ins-pt))
    (cons "Y" (cadr ins-pt))
    (cons "Z" (if (caddr ins-pt) (caddr ins-pt) 0.0))
    (cons "Rotation" (cdr (assoc 50 ed)))
    (cons "ScaleX" (cdr (assoc 41 ed)))
    (cons "ScaleY" (cdr (assoc 42 ed)))
    (cons "ScaleZ" (cdr (assoc 43 ed)))
    ;; Try to extract K-Factor from block name or attributes
    (cons "KFactor" (extract-k-factor block-name attribs))
    ;; Try to extract flow from attributes
    (cons "FlowLpm" (extract-flow attribs xdata-parsed))
    ;; Coverage area
    (cons "CoverageM2" (extract-coverage attribs xdata-parsed))
    ;; Zone ID
    (cons "ZoneId" (extract-zone layer attribs))
    ;; Raw attributes
    (cons "Attributes" attribs)
    ;; Raw XDATA
    (cons "XData" xdata-parsed)
  )
)

;; Extract K-Factor from block name or attributes
(defun extract-k-factor (block-name attribs / k-val)
  (setq k-val 5.6)  ;; Default K-Factor

  ;; Try to extract from block name
  (cond
    ((str-contains block-name "K5.6") (setq k-val 5.6))
    ((str-contains block-name "K8.0") (setq k-val 8.0))
    ((str-contains block-name "K11.2") (setq k-val 11.2))
    ((str-contains block-name "K14.0") (setq k-val 14.0))
    ((str-contains block-name "K16.8") (setq k-val 16.8))
    ((str-contains block-name "K25.2") (setq k-val 25.2))
  )

  ;; Try from attributes
  (foreach att attribs
    (if (str-contains (car att) "K-FACTOR")
      (setq k-val (atof (cdr att)))
    )
    (if (str-contains (car att) "KFACTOR")
      (setq k-val (atof (cdr att)))
    )
  )

  k-val
)

;; Extract flow rate from attributes
(defun extract-flow (attribs xdata / flow)
  (setq flow 0.0)

  ;; Try from attributes
  (foreach att attribs
    (if (or (str-contains (car att) "FLOW")
            (str-contains (car att) "GPM")
            (str-contains (car att) "LPM"))
      (setq flow (atof (cdr att)))
    )
  )

  ;; Try from XDATA
  (foreach xd xdata
    (if (str-contains (car xd) "real")
      (if (> (cdr xd) 0)
        (setq flow (cdr xd))
      )
    )
  )

  flow
)

;; Extract coverage area
(defun extract-coverage (attribs xdata / coverage)
  (setq coverage 12.0)  ;; Default 12 m² (130 ft²)

  (foreach att attribs
    (if (or (str-contains (car att) "COVERAGE")
            (str-contains (car att) "AREA"))
      (setq coverage (atof (cdr att)))
    )
  )

  coverage
)

;; Extract zone from layer name or attributes
(defun extract-zone (layer attribs / zone)
  (setq zone "ZONE-1")  ;; Default zone

  ;; Try to parse zone from layer
  (cond
    ((str-contains layer "ZONE-1") (setq zone "ZONE-1"))
    ((str-contains layer "ZONE-2") (setq zone "ZONE-2"))
    ((str-contains layer "ZONE-3") (setq zone "ZONE-3"))
    ((str-contains layer "Z1") (setq zone "ZONE-1"))
    ((str-contains layer "Z2") (setq zone "ZONE-2"))
    ((str-contains layer "Z3") (setq zone "ZONE-3"))
  )

  ;; Try from attributes
  (foreach att attribs
    (if (str-contains (car att) "ZONE")
      (setq zone (cdr att))
    )
  )

  zone
)

;; Convert sprinkler data to JSON object
(defun sprinkler-to-json (spk-data / json-str)
  (setq json-str "{")

  (setq json-str (strcat json-str "\"ID\":" (to-json-string (cdr (assoc "ID" spk-data))) ","))
  (setq json-str (strcat json-str "\"BlockName\":" (to-json-string (cdr (assoc "BlockName" spk-data))) ","))
  (setq json-str (strcat json-str "\"Layer\":" (to-json-string (cdr (assoc "Layer" spk-data))) ","))
  (setq json-str (strcat json-str "\"X\":" (num-to-str (cdr (assoc "X" spk-data))) ","))
  (setq json-str (strcat json-str "\"Y\":" (num-to-str (cdr (assoc "Y" spk-data))) ","))
  (setq json-str (strcat json-str "\"Z\":" (num-to-str (cdr (assoc "Z" spk-data))) ","))
  (setq json-str (strcat json-str "\"KFactor\":" (num-to-str (cdr (assoc "KFactor" spk-data))) ","))
  (setq json-str (strcat json-str "\"FlowLpm\":" (num-to-str (cdr (assoc "FlowLpm" spk-data))) ","))
  (setq json-str (strcat json-str "\"CoverageM2\":" (num-to-str (cdr (assoc "CoverageM2" spk-data))) ","))
  (setq json-str (strcat json-str "\"ZoneId\":" (to-json-string (cdr (assoc "ZoneId" spk-data)))))

  (setq json-str (strcat json-str "}"))
  json-str
)

;;; -----------------------------------------------------------------------------
;;; MAIN EXTRACTION COMMAND
;;; -----------------------------------------------------------------------------

(defun c:EXTRACTSPRINKLERS (/ ss i ent block-name sprinklers json-output file)
  (vl-load-com)

  (princ "\n")
  (princ "\n╔══════════════════════════════════════════════════════════════╗")
  (princ "\n║     AQUABRAIN SPRINKLER EXTRACTOR v2.0                       ║")
  (princ "\n╚══════════════════════════════════════════════════════════════╝")
  (princ "\n")

  ;; Get all block references
  (setq ss (ssget "X" '((0 . "INSERT"))))

  (if (not ss)
    (progn
      (princ "\n[ERROR] No blocks found in drawing")
      (princ)
      (exit)
    )
  )

  (princ (strcat "\nScanning " (itoa (sslength ss)) " blocks..."))

  ;; Extract sprinklers
  (setq sprinklers '())
  (setq i 0)

  (repeat (sslength ss)
    (setq ent (ssname ss i))
    (setq block-name (cdr (assoc 2 (entget ent))))

    (if (is-sprinkler-block block-name)
      (progn
        (setq spk-data (extract-sprinkler ent))
        (setq sprinklers (cons spk-data sprinklers))
        (princ (strcat "\n  Found: " block-name))
      )
    )

    (setq i (1+ i))
  )

  (princ (strcat "\n\nExtracted " (itoa (length sprinklers)) " sprinklers"))

  ;; Build JSON output
  (setq json-output "[")
  (setq first-item T)

  (foreach spk sprinklers
    (if first-item
      (setq first-item nil)
      (setq json-output (strcat json-output ","))
    )
    (setq json-output (strcat json-output (sprinkler-to-json spk)))
  )

  (setq json-output (strcat json-output "]"))

  ;; Write to file
  (setq *OUTPUT-FILE* (strcat (getvar "DWGPREFIX") "sprinkler_data.json"))
  (setq file (open *OUTPUT-FILE* "w"))
  (write-line json-output file)
  (close file)

  (princ (strcat "\n\n✓ JSON written to: " *OUTPUT-FILE*))
  (princ "\n")

  ;; Return the JSON for immediate use
  json-output
)

;; Short command alias
(defun c:EXSPK ()
  (c:EXTRACTSPRINKLERS)
)

;;; -----------------------------------------------------------------------------
;;; AUTO-LOAD MESSAGE
;;; -----------------------------------------------------------------------------

(princ "\n")
(princ "\n╔══════════════════════════════════════════════════════════════╗")
(princ "\n║     AQUABRAIN SPRINKLER EXTRACTOR - Loaded                   ║")
(princ "\n╠══════════════════════════════════════════════════════════════╣")
(princ "\n║  Commands:                                                   ║")
(princ "\n║    EXTRACTSPRINKLERS (or EXSPK) - Extract all sprinklers    ║")
(princ "\n╚══════════════════════════════════════════════════════════════╝")
(princ "\n")
(princ)
