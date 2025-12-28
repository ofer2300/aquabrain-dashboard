"use client";

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { DashboardShell } from '@/components/DashboardShell';
import { useLanguage } from '@/contexts/LanguageContext';
import {
  UserCog,
  Save,
  Edit3,
  Lock,
  Upload,
  Check,
  X,
  Mail,
  Phone,
  CreditCard,
  Building,
  Key,
  Cloud,
  FileText,
  AlertCircle,
  CheckCircle,
  Loader2,
} from 'lucide-react';

// ============================================================================
// TYPES
// ============================================================================

interface EngineerProfile {
  id?: string;
  full_name: string;
  id_number: string;
  engineer_license?: string;
  email: string;
  email_provider: 'gmail' | 'outlook' | 'icloud' | 'other';
  custom_email?: string;
  phone: string;
  stamp_signature_url?: string;
  // Future fields
  api_keys?: {
    openai?: string;
    claude?: string;
    gemini?: string;
    grok?: string;
    deepseek?: string;
  };
  adobe_license?: string;
  cloud_storage?: {
    sharepoint?: string;
    onedrive?: string;
    google_drive?: string;
  };
  is_locked: boolean;
  created_at?: string;
  updated_at?: string;
}

const INITIAL_PROFILE: EngineerProfile = {
  full_name: '',
  id_number: '',
  engineer_license: '',
  email: '',
  email_provider: 'gmail',
  custom_email: '',
  phone: '',
  stamp_signature_url: '',
  api_keys: {},
  adobe_license: '',
  cloud_storage: {},
  is_locked: false,
};

// ============================================================================
// TRANSLATIONS
// ============================================================================

const translations = {
  he: {
    title: 'פרטים אישיים',
    subtitle: 'פרטי המהנדס שישמשו לחתימה אוטומטית על מסמכים',
    fullName: 'שם מלא',
    fullNamePlaceholder: 'לדוגמה: נימרוד עופר',
    idNumber: 'תעודת זהות',
    idNumberPlaceholder: '9 ספרות',
    engineerLicense: 'מספר רישיון מהנדס',
    engineerLicensePlaceholder: 'אופציונלי',
    email: 'כתובת אימייל עיקרית',
    emailProvider: 'ספק אימייל',
    customEmail: 'כתובת אימייל מותאמת',
    customEmailPlaceholder: 'לדוגמה: nimrod@company.com',
    phone: 'מספר טלפון נייד',
    phonePlaceholder: '05X-XXXXXXX',
    stampSignature: 'חותמת וחתימה אישית',
    uploadStamp: 'העלה תמונת חותמת וחתימה',
    uploadHint: 'מומלץ PNG שקוף, עד 2MB',
    apiKeys: 'מפתחות API (עתידי)',
    adobeLicense: 'רשיון Adobe Acrobat',
    cloudStorage: 'חיבור לאחסון ענן',
    saveAndLock: 'שמור פרטים ונעל טופס',
    edit: 'ערוך מחדש',
    saving: 'שומר...',
    saved: 'נשמר בהצלחה!',
    error: 'שגיאה בשמירה',
    locked: 'הטופס נעול',
    lockedHint: 'לחץ על "ערוך מחדש" לעדכון',
    required: 'שדה חובה',
    invalidId: 'תעודת זהות חייבת להכיל 9 ספרות',
    invalidPhone: 'מספר טלפון לא תקין',
    invalidEmail: 'כתובת אימייל לא תקינה',
    previewStamp: 'תצוגה מקדימה',
    removeStamp: 'הסר',
    futureFeature: 'יהיה זמין בקרוב',
    gmail: 'Gmail',
    outlook: 'Outlook',
    icloud: 'iCloud',
    other: 'אחר',
  },
  en: {
    title: 'Personal Details',
    subtitle: 'Engineer details for automatic document signing',
    fullName: 'Full Name',
    fullNamePlaceholder: 'e.g., John Doe',
    idNumber: 'ID Number',
    idNumberPlaceholder: '9 digits',
    engineerLicense: 'Engineer License Number',
    engineerLicensePlaceholder: 'Optional',
    email: 'Primary Email Address',
    emailProvider: 'Email Provider',
    customEmail: 'Custom Email Address',
    customEmailPlaceholder: 'e.g., john@company.com',
    phone: 'Mobile Phone Number',
    phonePlaceholder: '05X-XXXXXXX',
    stampSignature: 'Stamp & Personal Signature',
    uploadStamp: 'Upload Stamp & Signature Image',
    uploadHint: 'Recommended: Transparent PNG, max 2MB',
    apiKeys: 'API Keys (Future)',
    adobeLicense: 'Adobe Acrobat License',
    cloudStorage: 'Cloud Storage Connection',
    saveAndLock: 'Save Details & Lock Form',
    edit: 'Edit',
    saving: 'Saving...',
    saved: 'Saved successfully!',
    error: 'Error saving',
    locked: 'Form Locked',
    lockedHint: 'Click "Edit" to update',
    required: 'Required field',
    invalidId: 'ID must contain 9 digits',
    invalidPhone: 'Invalid phone number',
    invalidEmail: 'Invalid email address',
    previewStamp: 'Preview',
    removeStamp: 'Remove',
    futureFeature: 'Coming soon',
    gmail: 'Gmail',
    outlook: 'Outlook',
    icloud: 'iCloud',
    other: 'Other',
  },
  ru: {
    title: 'Личные данные',
    subtitle: 'Данные инженера для автоматической подписи документов',
    fullName: 'Полное имя',
    fullNamePlaceholder: 'например: Иван Иванов',
    idNumber: 'Номер удостоверения',
    idNumberPlaceholder: '9 цифр',
    engineerLicense: 'Номер лицензии инженера',
    engineerLicensePlaceholder: 'Необязательно',
    email: 'Основной email',
    emailProvider: 'Провайдер email',
    customEmail: 'Пользовательский email',
    customEmailPlaceholder: 'например: ivan@company.com',
    phone: 'Мобильный телефон',
    phonePlaceholder: '05X-XXXXXXX',
    stampSignature: 'Печать и личная подпись',
    uploadStamp: 'Загрузить изображение печати и подписи',
    uploadHint: 'Рекомендуется: прозрачный PNG, макс. 2MB',
    apiKeys: 'API ключи (будущее)',
    adobeLicense: 'Лицензия Adobe Acrobat',
    cloudStorage: 'Подключение облачного хранилища',
    saveAndLock: 'Сохранить и заблокировать форму',
    edit: 'Редактировать',
    saving: 'Сохранение...',
    saved: 'Успешно сохранено!',
    error: 'Ошибка сохранения',
    locked: 'Форма заблокирована',
    lockedHint: 'Нажмите "Редактировать" для изменения',
    required: 'Обязательное поле',
    invalidId: 'ID должен содержать 9 цифр',
    invalidPhone: 'Неверный номер телефона',
    invalidEmail: 'Неверный email',
    previewStamp: 'Предпросмотр',
    removeStamp: 'Удалить',
    futureFeature: 'Скоро будет доступно',
    gmail: 'Gmail',
    outlook: 'Outlook',
    icloud: 'iCloud',
    other: 'Другой',
  },
};

// ============================================================================
// VALIDATION
// ============================================================================

interface ValidationErrors {
  full_name?: string;
  id_number?: string;
  email?: string;
  phone?: string;
}

function validateProfile(profile: EngineerProfile, t: typeof translations.he): ValidationErrors {
  const errors: ValidationErrors = {};

  if (!profile.full_name.trim()) {
    errors.full_name = t.required;
  }

  if (!profile.id_number || !/^\d{9}$/.test(profile.id_number)) {
    errors.id_number = t.invalidId;
  }

  if (!profile.email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(profile.email)) {
    errors.email = t.invalidEmail;
  }

  if (!profile.phone || !/^05\d-?\d{7}$/.test(profile.phone.replace(/-/g, ''))) {
    errors.phone = t.invalidPhone;
  }

  return errors;
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export default function ProfilePage() {
  const { lang, direction } = useLanguage();
  const t = translations[lang];

  const [profile, setProfile] = useState<EngineerProfile>(INITIAL_PROFILE);
  const [errors, setErrors] = useState<ValidationErrors>({});
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [stampPreview, setStampPreview] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load profile on mount
  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/engineer-profile');
      if (response.ok) {
        const data = await response.json();
        if (data && data.full_name) {
          setProfile(data);
          if (data.stamp_signature_url) {
            setStampPreview(data.stamp_signature_url);
          }
        }
      }
    } catch (error) {
      console.log('No existing profile found');
    } finally {
      setIsLoading(false);
    }
  };

  const handleInputChange = (field: keyof EngineerProfile, value: string) => {
    setProfile(prev => ({ ...prev, [field]: value }));
    // Clear error when user types
    if (errors[field as keyof ValidationErrors]) {
      setErrors(prev => ({ ...prev, [field]: undefined }));
    }
  };

  const handlePhoneChange = (value: string) => {
    // Format phone number
    let formatted = value.replace(/\D/g, '');
    if (formatted.length > 3) {
      formatted = formatted.slice(0, 3) + '-' + formatted.slice(3);
    }
    if (formatted.length > 11) {
      formatted = formatted.slice(0, 11);
    }
    handleInputChange('phone', formatted);
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file size (2MB max)
    if (file.size > 2 * 1024 * 1024) {
      alert('File size must be less than 2MB');
      return;
    }

    // Create preview
    const reader = new FileReader();
    reader.onload = (e) => {
      setStampPreview(e.target?.result as string);
    };
    reader.readAsDataURL(file);

    // Upload to backend
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('http://localhost:8000/api/engineer-profile/upload-stamp', {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        const data = await response.json();
        setProfile(prev => ({ ...prev, stamp_signature_url: data.url }));
      }
    } catch (error) {
      console.error('Error uploading stamp:', error);
    }
  };

  const handleRemoveStamp = () => {
    setStampPreview(null);
    setProfile(prev => ({ ...prev, stamp_signature_url: '' }));
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleSave = async () => {
    const validationErrors = validateProfile(profile, t);
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }

    setIsSaving(true);
    setSaveStatus('idle');

    try {
      const response = await fetch('http://localhost:8000/api/engineer-profile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...profile, is_locked: true }),
      });

      if (response.ok) {
        const data = await response.json();
        setProfile({ ...profile, ...data, is_locked: true });
        setSaveStatus('success');
        setTimeout(() => setSaveStatus('idle'), 3000);
      } else {
        setSaveStatus('error');
      }
    } catch (error) {
      console.error('Error saving profile:', error);
      setSaveStatus('error');
    } finally {
      setIsSaving(false);
    }
  };

  const handleUnlock = () => {
    setProfile(prev => ({ ...prev, is_locked: false }));
  };

  if (isLoading) {
    return (
      <DashboardShell>
        <div className="flex items-center justify-center h-96">
          <Loader2 className="w-8 h-8 animate-spin text-status-ai" />
        </div>
      </DashboardShell>
    );
  }

  const isLocked = profile.is_locked;

  return (
    <DashboardShell>
      <div className={`max-w-3xl mx-auto ${direction === 'rtl' ? 'text-right' : 'text-left'}`}>
        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <div className="w-14 h-14 rounded-2xl bg-status-ai/20 flex items-center justify-center">
            <UserCog className="w-7 h-7 text-status-ai" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-text-primary">{t.title}</h1>
            <p className="text-text-secondary">{t.subtitle}</p>
          </div>
          {isLocked && (
            <div className={`flex items-center gap-2 px-4 py-2 rounded-xl bg-status-warning/10 border border-status-warning/20 ${direction === 'rtl' ? 'mr-auto' : 'ml-auto'}`}>
              <Lock className="w-4 h-4 text-status-warning" />
              <span className="text-sm text-status-warning font-medium">{t.locked}</span>
            </div>
          )}
        </div>

        {/* Form */}
        <div className="space-y-6">
          {/* Basic Info Section */}
          <div className="glass-panel p-6 space-y-5">
            <h2 className="text-lg font-semibold text-text-primary flex items-center gap-2">
              <CreditCard className="w-5 h-5 text-status-ai" />
              {lang === 'he' ? 'פרטים בסיסיים' : lang === 'ru' ? 'Основная информация' : 'Basic Information'}
            </h2>

            {/* Full Name */}
            <div className="space-y-2">
              <label className="block text-sm font-medium text-text-secondary">{t.fullName} *</label>
              <input
                type="text"
                value={profile.full_name}
                onChange={(e) => handleInputChange('full_name', e.target.value)}
                disabled={isLocked}
                placeholder={t.fullNamePlaceholder}
                className={`w-full px-4 py-3 rounded-xl bg-white/5 border ${errors.full_name ? 'border-status-error' : 'border-white/10'} text-text-primary placeholder-text-secondary/50 focus:outline-none focus:border-status-ai/50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed`}
              />
              {errors.full_name && (
                <p className="text-sm text-status-error flex items-center gap-1">
                  <AlertCircle className="w-4 h-4" />
                  {errors.full_name}
                </p>
              )}
            </div>

            {/* ID Number */}
            <div className="space-y-2">
              <label className="block text-sm font-medium text-text-secondary">{t.idNumber} *</label>
              <input
                type="text"
                value={profile.id_number}
                onChange={(e) => handleInputChange('id_number', e.target.value.replace(/\D/g, '').slice(0, 9))}
                disabled={isLocked}
                placeholder={t.idNumberPlaceholder}
                className={`w-full px-4 py-3 rounded-xl bg-white/5 border ${errors.id_number ? 'border-status-error' : 'border-white/10'} text-text-primary placeholder-text-secondary/50 focus:outline-none focus:border-status-ai/50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed`}
              />
              {errors.id_number && (
                <p className="text-sm text-status-error flex items-center gap-1">
                  <AlertCircle className="w-4 h-4" />
                  {errors.id_number}
                </p>
              )}
            </div>

            {/* Engineer License */}
            <div className="space-y-2">
              <label className="block text-sm font-medium text-text-secondary">{t.engineerLicense}</label>
              <input
                type="text"
                value={profile.engineer_license || ''}
                onChange={(e) => handleInputChange('engineer_license', e.target.value)}
                disabled={isLocked}
                placeholder={t.engineerLicensePlaceholder}
                className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-text-primary placeholder-text-secondary/50 focus:outline-none focus:border-status-ai/50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              />
            </div>
          </div>

          {/* Contact Section */}
          <div className="glass-panel p-6 space-y-5">
            <h2 className="text-lg font-semibold text-text-primary flex items-center gap-2">
              <Mail className="w-5 h-5 text-status-ai" />
              {lang === 'he' ? 'פרטי התקשרות' : lang === 'ru' ? 'Контактная информация' : 'Contact Information'}
            </h2>

            {/* Email */}
            <div className="space-y-2">
              <label className="block text-sm font-medium text-text-secondary">{t.email} *</label>
              <input
                type="email"
                value={profile.email}
                onChange={(e) => handleInputChange('email', e.target.value)}
                disabled={isLocked}
                placeholder="example@gmail.com"
                className={`w-full px-4 py-3 rounded-xl bg-white/5 border ${errors.email ? 'border-status-error' : 'border-white/10'} text-text-primary placeholder-text-secondary/50 focus:outline-none focus:border-status-ai/50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed`}
              />
              {errors.email && (
                <p className="text-sm text-status-error flex items-center gap-1">
                  <AlertCircle className="w-4 h-4" />
                  {errors.email}
                </p>
              )}
            </div>

            {/* Email Provider */}
            <div className="space-y-2">
              <label className="block text-sm font-medium text-text-secondary">{t.emailProvider}</label>
              <select
                value={profile.email_provider}
                onChange={(e) => handleInputChange('email_provider', e.target.value)}
                disabled={isLocked}
                className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-text-primary focus:outline-none focus:border-status-ai/50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <option value="gmail">{t.gmail}</option>
                <option value="outlook">{t.outlook}</option>
                <option value="icloud">{t.icloud}</option>
                <option value="other">{t.other}</option>
              </select>
            </div>

            {/* Custom Email (if Other) */}
            {profile.email_provider === 'other' && (
              <div className="space-y-2">
                <label className="block text-sm font-medium text-text-secondary">{t.customEmail}</label>
                <input
                  type="email"
                  value={profile.custom_email || ''}
                  onChange={(e) => handleInputChange('custom_email', e.target.value)}
                  disabled={isLocked}
                  placeholder={t.customEmailPlaceholder}
                  className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-text-primary placeholder-text-secondary/50 focus:outline-none focus:border-status-ai/50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                />
              </div>
            )}

            {/* Phone */}
            <div className="space-y-2">
              <label className="block text-sm font-medium text-text-secondary">{t.phone} *</label>
              <div className="relative">
                <Phone className={`absolute top-1/2 -translate-y-1/2 w-5 h-5 text-text-secondary ${direction === 'rtl' ? 'right-4' : 'left-4'}`} />
                <input
                  type="tel"
                  value={profile.phone}
                  onChange={(e) => handlePhoneChange(e.target.value)}
                  disabled={isLocked}
                  placeholder={t.phonePlaceholder}
                  className={`w-full ${direction === 'rtl' ? 'pr-12' : 'pl-12'} py-3 rounded-xl bg-white/5 border ${errors.phone ? 'border-status-error' : 'border-white/10'} text-text-primary placeholder-text-secondary/50 focus:outline-none focus:border-status-ai/50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed`}
                />
              </div>
              {errors.phone && (
                <p className="text-sm text-status-error flex items-center gap-1">
                  <AlertCircle className="w-4 h-4" />
                  {errors.phone}
                </p>
              )}
            </div>
          </div>

          {/* Stamp & Signature Section */}
          <div className="glass-panel p-6 space-y-5">
            <h2 className="text-lg font-semibold text-text-primary flex items-center gap-2">
              <FileText className="w-5 h-5 text-status-ai" />
              {t.stampSignature}
            </h2>

            <div className={`flex ${direction === 'rtl' ? 'flex-row-reverse' : ''} gap-6`}>
              {/* Upload Area */}
              <div className="flex-1">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/png,image/jpeg"
                  onChange={handleFileUpload}
                  disabled={isLocked}
                  className="hidden"
                  id="stamp-upload"
                />
                <label
                  htmlFor="stamp-upload"
                  className={`flex flex-col items-center justify-center w-full h-40 border-2 border-dashed rounded-xl transition-colors ${isLocked ? 'opacity-50 cursor-not-allowed border-white/10' : 'border-white/20 hover:border-status-ai/50 cursor-pointer'}`}
                >
                  <Upload className="w-8 h-8 text-text-secondary mb-2" />
                  <span className="text-text-secondary text-sm">{t.uploadStamp}</span>
                  <span className="text-text-secondary/50 text-xs mt-1">{t.uploadHint}</span>
                </label>
              </div>

              {/* Preview Area */}
              {stampPreview && (
                <div className="w-48 relative">
                  <p className="text-sm text-text-secondary mb-2">{t.previewStamp}</p>
                  <div className="relative bg-white/5 rounded-xl p-4 border border-white/10">
                    <img
                      src={stampPreview}
                      alt="Stamp Preview"
                      className="w-full h-auto object-contain"
                    />
                    {!isLocked && (
                      <button
                        onClick={handleRemoveStamp}
                        className="absolute -top-2 -right-2 w-6 h-6 bg-status-error rounded-full flex items-center justify-center"
                      >
                        <X className="w-4 h-4 text-white" />
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Future Features Section */}
          <div className="glass-panel p-6 space-y-5 opacity-60">
            <h2 className="text-lg font-semibold text-text-primary flex items-center gap-2">
              <Key className="w-5 h-5 text-status-ai" />
              {t.apiKeys}
              <span className="text-xs px-2 py-1 rounded-full bg-status-ai/20 text-status-ai">{t.futureFeature}</span>
            </h2>

            <div className="grid grid-cols-2 gap-4">
              {['OpenAI', 'Claude', 'Gemini', 'Grok', 'DeepSeek'].map((provider) => (
                <div key={provider} className="space-y-1">
                  <label className="block text-sm font-medium text-text-secondary">{provider}</label>
                  <input
                    type="password"
                    disabled
                    placeholder="sk-..."
                    className="w-full px-4 py-2 rounded-xl bg-white/5 border border-white/10 text-text-primary placeholder-text-secondary/50 opacity-50 cursor-not-allowed"
                  />
                </div>
              ))}
            </div>
          </div>

          <div className="glass-panel p-6 space-y-5 opacity-60">
            <h2 className="text-lg font-semibold text-text-primary flex items-center gap-2">
              <Cloud className="w-5 h-5 text-status-ai" />
              {t.cloudStorage}
              <span className="text-xs px-2 py-1 rounded-full bg-status-ai/20 text-status-ai">{t.futureFeature}</span>
            </h2>

            <div className="grid grid-cols-3 gap-4">
              {['SharePoint', 'OneDrive', 'Google Drive'].map((service) => (
                <button
                  key={service}
                  disabled
                  className="px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-text-secondary opacity-50 cursor-not-allowed"
                >
                  {service}
                </button>
              ))}
            </div>
          </div>

          {/* Action Buttons */}
          <div className={`flex ${direction === 'rtl' ? 'flex-row-reverse' : ''} gap-4 pt-4`}>
            {isLocked ? (
              <button
                onClick={handleUnlock}
                className="flex items-center gap-2 px-6 py-3 rounded-xl bg-white/10 border border-white/20 text-text-primary hover:bg-white/15 transition-colors"
              >
                <Edit3 className="w-5 h-5" />
                {t.edit}
              </button>
            ) : (
              <button
                onClick={handleSave}
                disabled={isSaving}
                className="flex items-center gap-2 px-8 py-3 rounded-xl bg-status-ai text-white font-semibold hover:bg-status-ai/80 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSaving ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    {t.saving}
                  </>
                ) : (
                  <>
                    <Save className="w-5 h-5" />
                    {t.saveAndLock}
                  </>
                )}
              </button>
            )}

            {saveStatus === 'success' && (
              <div className="flex items-center gap-2 text-status-success">
                <CheckCircle className="w-5 h-5" />
                {t.saved}
              </div>
            )}

            {saveStatus === 'error' && (
              <div className="flex items-center gap-2 text-status-error">
                <AlertCircle className="w-5 h-5" />
                {t.error}
              </div>
            )}
          </div>
        </div>
      </div>
    </DashboardShell>
  );
}
