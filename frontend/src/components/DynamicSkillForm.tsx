"use client";

import React, { useState, useEffect } from 'react';
import {
  Play,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Upload,
  Calendar,
  Hash,
  Mail,
  Type,
  ToggleLeft,
  List,
  FileJson,
  Palette,
  Sliders,
  X,
} from 'lucide-react';

// ============================================================================
// TYPES (matching backend schema)
// ============================================================================

type FieldType =
  | 'text'
  | 'number'
  | 'email'
  | 'file'
  | 'date'
  | 'datetime'
  | 'select'
  | 'multiselect'
  | 'boolean'
  | 'textarea'
  | 'json'
  | 'color'
  | 'range';

interface InputField {
  name: string;
  label: string;
  type: FieldType;
  required: boolean;
  default?: any;
  placeholder?: string;
  description?: string;
  options?: { value: string; label: string }[];
  min?: number;
  max?: number;
  step?: number;
  accept?: string;
  multiple?: boolean;
  pattern?: string;
  min_length?: number;
  max_length?: number;
}

interface InputSchema {
  fields: InputField[];
}

interface SkillMetadata {
  id: string;
  name: string;
  description: string;
  category: string;
  icon: string;
  color: string;
  version: string;
  author: string;
  tags: string[];
  is_async: boolean;
  estimated_duration_sec?: number;
  requires_revit?: boolean;
  requires_autocad?: boolean;
}

interface SkillDefinition {
  metadata: SkillMetadata;
  input_schema: InputSchema;
}

interface ExecutionResult {
  status: 'pending' | 'running' | 'success' | 'failed' | 'cancelled';
  skill_id: string;
  run_id: string;
  message: string;
  output?: any;
  error?: string;
  duration_ms?: number;
  metrics?: Record<string, any>;
}

// ============================================================================
// FIELD ICON MAP
// ============================================================================

const FIELD_ICONS: Record<FieldType, React.ElementType> = {
  text: Type,
  number: Hash,
  email: Mail,
  file: Upload,
  date: Calendar,
  datetime: Calendar,
  select: List,
  multiselect: List,
  boolean: ToggleLeft,
  textarea: Type,
  json: FileJson,
  color: Palette,
  range: Sliders,
};

// ============================================================================
// DYNAMIC FIELD COMPONENT
// ============================================================================

interface DynamicFieldProps {
  field: InputField;
  value: any;
  onChange: (value: any) => void;
  error?: string;
}

function DynamicField({ field, value, onChange, error }: DynamicFieldProps) {
  const Icon = FIELD_ICONS[field.type] || Type;

  const baseInputClass = `
    w-full px-4 py-3 rounded-xl
    bg-white/5 border border-white/10
    text-white placeholder:text-white/30
    focus:outline-none focus:border-status-ai/50 focus:ring-1 focus:ring-status-ai/30
    transition-all
    ${error ? 'border-red-500/50' : ''}
  `;

  const renderField = () => {
    switch (field.type) {
      case 'text':
      case 'email':
        return (
          <input
            type={field.type}
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder}
            className={baseInputClass}
            pattern={field.pattern}
            minLength={field.min_length}
            maxLength={field.max_length}
          />
        );

      case 'number':
      case 'range':
        return (
          <input
            type={field.type === 'range' ? 'range' : 'number'}
            value={value ?? field.default ?? ''}
            onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
            placeholder={field.placeholder}
            className={baseInputClass}
            min={field.min}
            max={field.max}
            step={field.step}
          />
        );

      case 'textarea':
        return (
          <textarea
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder}
            className={`${baseInputClass} min-h-[100px] resize-y`}
            minLength={field.min_length}
            maxLength={field.max_length}
          />
        );

      case 'select':
        return (
          <select
            value={value || field.default || ''}
            onChange={(e) => onChange(e.target.value)}
            className={baseInputClass}
          >
            <option value="">Select...</option>
            {field.options?.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        );

      case 'multiselect':
        const selectedValues = Array.isArray(value) ? value : [];
        return (
          <div className="space-y-2">
            {field.options?.map((opt) => (
              <label key={opt.value} className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={selectedValues.includes(opt.value)}
                  onChange={(e) => {
                    if (e.target.checked) {
                      onChange([...selectedValues, opt.value]);
                    } else {
                      onChange(selectedValues.filter((v: string) => v !== opt.value));
                    }
                  }}
                  className="w-5 h-5 rounded bg-white/10 border-white/20 text-status-ai focus:ring-status-ai/50"
                />
                <span className="text-white">{opt.label}</span>
              </label>
            ))}
          </div>
        );

      case 'boolean':
        return (
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={value ?? field.default ?? false}
              onChange={(e) => onChange(e.target.checked)}
              className="w-6 h-6 rounded bg-white/10 border-white/20 text-status-ai focus:ring-status-ai/50"
            />
            <span className="text-white">{field.description || 'Enable'}</span>
          </label>
        );

      case 'date':
      case 'datetime':
        return (
          <input
            type={field.type === 'datetime' ? 'datetime-local' : 'date'}
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            className={baseInputClass}
          />
        );

      case 'file':
        return (
          <div className="space-y-2">
            <input
              type="file"
              accept={field.accept}
              multiple={field.multiple}
              onChange={(e) => {
                const files = e.target.files;
                if (files) {
                  onChange(field.multiple ? Array.from(files) : files[0]);
                }
              }}
              className="hidden"
              id={`file-${field.name}`}
            />
            <label
              htmlFor={`file-${field.name}`}
              className={`
                ${baseInputClass} cursor-pointer flex items-center justify-center gap-3
                hover:bg-white/10 hover:border-status-ai/30
              `}
            >
              <Upload className="w-5 h-5 text-status-ai" />
              <span>{value?.name || 'Choose file...'}</span>
            </label>
            {field.accept && (
              <p className="text-xs text-white/40">Accepted: {field.accept}</p>
            )}
          </div>
        );

      case 'color':
        return (
          <div className="flex items-center gap-3">
            <input
              type="color"
              value={value || field.default || '#BD00FF'}
              onChange={(e) => onChange(e.target.value)}
              className="w-12 h-12 rounded-lg cursor-pointer bg-transparent"
            />
            <input
              type="text"
              value={value || field.default || '#BD00FF'}
              onChange={(e) => onChange(e.target.value)}
              placeholder="#RRGGBB"
              className={`${baseInputClass} flex-1`}
            />
          </div>
        );

      case 'json':
        return (
          <textarea
            value={typeof value === 'string' ? value : JSON.stringify(value || {}, null, 2)}
            onChange={(e) => {
              try {
                onChange(JSON.parse(e.target.value));
              } catch {
                onChange(e.target.value);
              }
            }}
            placeholder={field.placeholder || '{"key": "value"}'}
            className={`${baseInputClass} min-h-[120px] font-mono text-sm`}
          />
        );

      default:
        return (
          <input
            type="text"
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder}
            className={baseInputClass}
          />
        );
    }
  };

  return (
    <div className="space-y-2">
      <label className="flex items-center gap-2 text-sm text-white/80">
        <Icon className="w-4 h-4 text-status-ai" />
        {field.label}
        {field.required && <span className="text-red-400">*</span>}
      </label>
      {renderField()}
      {field.description && field.type !== 'boolean' && (
        <p className="text-xs text-white/40">{field.description}</p>
      )}
      {error && <p className="text-xs text-red-400">{error}</p>}
    </div>
  );
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

interface DynamicSkillFormProps {
  skill: SkillDefinition;
  onExecute: (inputs: Record<string, any>) => Promise<ExecutionResult>;
  onClose?: () => void;
}

export function DynamicSkillForm({ skill, onExecute, onClose }: DynamicSkillFormProps) {
  const [values, setValues] = useState<Record<string, any>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isExecuting, setIsExecuting] = useState(false);
  const [result, setResult] = useState<ExecutionResult | null>(null);

  // Initialize default values
  useEffect(() => {
    const defaults: Record<string, any> = {};
    skill.input_schema.fields.forEach((field) => {
      if (field.default !== undefined) {
        defaults[field.name] = field.default;
      }
    });
    setValues(defaults);
  }, [skill]);

  const handleChange = (fieldName: string, value: any) => {
    setValues((prev) => ({ ...prev, [fieldName]: value }));
    // Clear error when value changes
    if (errors[fieldName]) {
      setErrors((prev) => {
        const next = { ...prev };
        delete next[fieldName];
        return next;
      });
    }
  };

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};

    skill.input_schema.fields.forEach((field) => {
      const value = values[field.name];

      if (field.required && (value === undefined || value === null || value === '')) {
        newErrors[field.name] = `${field.label} is required`;
      }

      if (field.type === 'number' && value !== undefined && value !== '') {
        const num = parseFloat(value);
        if (field.min !== undefined && num < field.min) {
          newErrors[field.name] = `Minimum value is ${field.min}`;
        }
        if (field.max !== undefined && num > field.max) {
          newErrors[field.name] = `Maximum value is ${field.max}`;
        }
      }

      if (field.type === 'email' && value && !value.includes('@')) {
        newErrors[field.name] = 'Invalid email address';
      }
    });

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validate()) return;

    setIsExecuting(true);
    setResult(null);

    try {
      const result = await onExecute(values);
      setResult(result);
    } catch (error) {
      setResult({
        status: 'failed',
        skill_id: skill.metadata.id,
        run_id: '',
        message: 'Execution failed',
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    } finally {
      setIsExecuting(false);
    }
  };

  return (
    <div className="glass-heavy rounded-2xl overflow-hidden">
      {/* Header */}
      <div
        className="px-6 py-4 border-b border-white/10 flex items-center justify-between"
        style={{ background: `linear-gradient(135deg, ${skill.metadata.color}20, transparent)` }}
      >
        <div className="flex items-center gap-4">
          <div
            className="w-12 h-12 rounded-xl flex items-center justify-center"
            style={{ backgroundColor: `${skill.metadata.color}30` }}
          >
            <span className="text-2xl" style={{ color: skill.metadata.color }}>
              {skill.metadata.icon === 'Droplets' ? '💧' :
               skill.metadata.icon === 'Building2' ? '🏗️' :
               skill.metadata.icon === 'FileBarChart' ? '📊' : '⚙️'}
            </span>
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">{skill.metadata.name}</h2>
            <p className="text-sm text-white/60">{skill.metadata.description}</p>
          </div>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-white/10 transition-colors"
          >
            <X className="w-5 h-5 text-white/60" />
          </button>
        )}
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="p-6 space-y-6">
        {skill.input_schema.fields.map((field) => (
          <DynamicField
            key={field.name}
            field={field}
            value={values[field.name]}
            onChange={(value) => handleChange(field.name, value)}
            error={errors[field.name]}
          />
        ))}

        {/* Result Display */}
        {result && (
          <div
            className={`
              p-4 rounded-xl border transition-all
              ${result.status === 'success'
                ? 'bg-green-500/10 border-green-500/30'
                : 'bg-red-500/10 border-red-500/30'}
            `}
          >
            <div className="flex items-center gap-3 mb-2">
              {result.status === 'success' ? (
                <CheckCircle2 className="w-5 h-5 text-green-400" />
              ) : (
                <AlertCircle className="w-5 h-5 text-red-400" />
              )}
              <span
                className={`font-medium ${
                  result.status === 'success' ? 'text-green-400' : 'text-red-400'
                }`}
              >
                {result.message}
              </span>
            </div>
            {result.duration_ms && (
              <p className="text-xs text-white/40">Completed in {result.duration_ms}ms</p>
            )}
            {result.error && (
              <p className="text-sm text-red-300 mt-2">{result.error}</p>
            )}
            {result.output && (
              <details className="mt-3">
                <summary className="text-xs text-white/50 cursor-pointer hover:text-white/70">
                  View Output
                </summary>
                <pre className="mt-2 p-3 rounded-lg bg-black/30 text-xs text-white/70 overflow-auto max-h-48">
                  {JSON.stringify(result.output, null, 2)}
                </pre>
              </details>
            )}
          </div>
        )}

        {/* Submit Button */}
        <button
          type="submit"
          disabled={isExecuting}
          className={`
            w-full py-4 rounded-xl font-bold text-lg transition-all
            flex items-center justify-center gap-3
            ${isExecuting
              ? 'bg-white/10 text-white/50 cursor-not-allowed'
              : 'bg-status-ai/20 hover:bg-status-ai/30 border border-status-ai/50 text-status-ai'}
          `}
          style={!isExecuting ? { borderColor: `${skill.metadata.color}80` } : {}}
        >
          {isExecuting ? (
            <>
              <Loader2 className="w-6 h-6 animate-spin" />
              Executing...
            </>
          ) : (
            <>
              <Play className="w-6 h-6" />
              Execute Skill
            </>
          )}
        </button>

        {/* Metadata Footer */}
        <div className="flex items-center justify-between text-xs text-white/30 pt-4 border-t border-white/10">
          <span>v{skill.metadata.version} by {skill.metadata.author}</span>
          <div className="flex gap-2">
            {skill.metadata.tags.slice(0, 3).map((tag) => (
              <span key={tag} className="px-2 py-1 rounded-full bg-white/5">
                {tag}
              </span>
            ))}
          </div>
        </div>
      </form>
    </div>
  );
}

export default DynamicSkillForm;
