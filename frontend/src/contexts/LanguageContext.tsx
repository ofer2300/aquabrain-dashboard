"use client";

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';

// ============================================================================
// TYPES
// ============================================================================

export type Language = 'he' | 'en' | 'ru';
export type Direction = 'rtl' | 'ltr';

interface LanguageConfig {
  code: Language;
  name: string;
  nativeName: string;
  flag: string;
  direction: Direction;
}

export const LANGUAGES: Record<Language, LanguageConfig> = {
  he: { code: 'he', name: 'Hebrew', nativeName: 'עברית', flag: '🇮🇱', direction: 'rtl' },
  en: { code: 'en', name: 'English', nativeName: 'English', flag: '🇺🇸', direction: 'ltr' },
  ru: { code: 'ru', name: 'Russian', nativeName: 'Русский', flag: '🇷🇺', direction: 'ltr' },
};

// ============================================================================
// DICTIONARY TYPE
// ============================================================================

interface Dictionary {
  // Common UI
  common: {
    save: string;
    cancel: string;
    close: string;
    loading: string;
    error: string;
    success: string;
    confirm: string;
    delete: string;
    edit: string;
    create: string;
    search: string;
    filter: string;
    refresh: string;
    back: string;
    next: string;
    previous: string;
    submit: string;
    reset: string;
  };
  // Navigation
  nav: {
    dashboard: string;
    projects: string;
    skills: string;
    settings: string;
    help: string;
    autopilot: string;
    calculation: string;
    communication: string;
  };
  // Dashboard
  dashboard: {
    title: string;
    subtitle: string;
    systemActive: string;
    systemOffline: string;
    openClashes: string;
    resolvedToday: string;
    aiActivity: string;
    avgResponseTime: string;
    activeResolution: string;
    recentActivity: string;
    performanceMetrics: string;
    systemStatus: string;
    skillFactory: string;
    createSkill: string;
  };
  // Engineering Terms
  engineering: {
    sprinklerHead: string;
    pipeNetwork: string;
    pressureLoss: string;
    flowRate: string;
    velocity: string;
    hydraulicCalc: string;
    clashDetection: string;
    mepSystem: string;
    fireProtection: string;
    hvac: string;
    plumbing: string;
    nfpa13: string;
    hazenWilliams: string;
    cFactor: string;
    psi: string;
    gpm: string;
    fps: string;
  };
  // Skill Factory
  skills: {
    title: string;
    createNew: string;
    generating: string;
    validating: string;
    deployed: string;
    activate: string;
    description: string;
    hydraulicCalc: string;
    revitExtract: string;
    reportGen: string;
  };
  // Messages
  messages: {
    skillCreated: string;
    skillActivated: string;
    processingComplete: string;
    validationPassed: string;
    validationFailed: string;
    connectionError: string;
  };
}

// ============================================================================
// DICTIONARIES
// ============================================================================

const dictionaries: Record<Language, Dictionary> = {
  he: {
    common: {
      save: 'שמור',
      cancel: 'בטל',
      close: 'סגור',
      loading: 'טוען...',
      error: 'שגיאה',
      success: 'הצלחה',
      confirm: 'אישור',
      delete: 'מחק',
      edit: 'ערוך',
      create: 'צור',
      search: 'חפש',
      filter: 'סנן',
      refresh: 'רענן',
      back: 'חזור',
      next: 'הבא',
      previous: 'הקודם',
      submit: 'שלח',
      reset: 'אפס',
    },
    nav: {
      dashboard: 'לוח בקרה',
      projects: 'פרויקטים',
      skills: 'יכולות',
      settings: 'הגדרות',
      help: 'עזרה',
      autopilot: 'טייס אוטומטי',
      calculation: 'חישובים',
      communication: 'תקשורת',
    },
    dashboard: {
      title: 'לוח בקרה הנדסי',
      subtitle: 'מערכת AI לזיהוי וניהול התנגשויות MEP',
      systemActive: 'מערכת פעילה',
      systemOffline: 'מערכת לא זמינה',
      openClashes: 'התנגשויות פתוחות',
      resolvedToday: 'נפתרו היום',
      aiActivity: 'פעילות AI',
      avgResponseTime: 'זמן תגובה ממוצע',
      activeResolution: 'פתרון התנגשות פעיל',
      recentActivity: 'פעילות אחרונה',
      performanceMetrics: 'מדדי ביצועים',
      systemStatus: 'סטטוס מערכת',
      skillFactory: 'מפעל יכולות',
      createSkill: 'צור Skill חדש',
    },
    engineering: {
      sprinklerHead: 'ראש מתז',
      pipeNetwork: 'רשת צנרת',
      pressureLoss: 'אובדן לחץ',
      flowRate: 'ספיקה',
      velocity: 'מהירות זרימה',
      hydraulicCalc: 'חישוב הידראולי',
      clashDetection: 'זיהוי התנגשויות',
      mepSystem: 'מערכות MEP',
      fireProtection: 'כיבוי אש',
      hvac: 'מיזוג אוויר',
      plumbing: 'אינסטלציה',
      nfpa13: 'תקן NFPA 13',
      hazenWilliams: 'נוסחת הייזן-וויליאמס',
      cFactor: 'מקדם חיכוך C',
      psi: 'PSI (ליש"ר)',
      gpm: 'GPM (גלון/דקה)',
      fps: 'FPS (רגל/שניה)',
    },
    skills: {
      title: 'מפעל יכולות',
      createNew: 'צור יכולת חדשה',
      generating: 'מייצר לוגיקה...',
      validating: 'מאמת בסביבת Sandbox...',
      deployed: 'הופעל',
      activate: 'הפעל',
      description: 'תאר את האוטומציה שאתה צריך',
      hydraulicCalc: 'חישוב הידראולי',
      revitExtract: 'שליפת Revit',
      reportGen: 'יצירת דוחות',
    },
    messages: {
      skillCreated: 'Skill נוצר בהצלחה!',
      skillActivated: 'Skill הופעל והתווסף לספריה!',
      processingComplete: 'העיבוד הושלם',
      validationPassed: 'אימות עבר בהצלחה',
      validationFailed: 'אימות נכשל',
      connectionError: 'שגיאת חיבור לשרת',
    },
  },
  en: {
    common: {
      save: 'Save',
      cancel: 'Cancel',
      close: 'Close',
      loading: 'Loading...',
      error: 'Error',
      success: 'Success',
      confirm: 'Confirm',
      delete: 'Delete',
      edit: 'Edit',
      create: 'Create',
      search: 'Search',
      filter: 'Filter',
      refresh: 'Refresh',
      back: 'Back',
      next: 'Next',
      previous: 'Previous',
      submit: 'Submit',
      reset: 'Reset',
    },
    nav: {
      dashboard: 'Dashboard',
      projects: 'Projects',
      skills: 'Skills',
      settings: 'Settings',
      help: 'Help',
      autopilot: 'Auto-Pilot',
      calculation: 'Calculation',
      communication: 'Communication',
    },
    dashboard: {
      title: 'Engineering Dashboard',
      subtitle: 'AI-powered MEP Clash Detection System',
      systemActive: 'System Active',
      systemOffline: 'System Offline',
      openClashes: 'Open Clashes',
      resolvedToday: 'Resolved Today',
      aiActivity: 'AI Activity',
      avgResponseTime: 'Avg Response Time',
      activeResolution: 'Active Clash Resolution',
      recentActivity: 'Recent Activity',
      performanceMetrics: 'Performance Metrics',
      systemStatus: 'System Status',
      skillFactory: 'Skill Factory',
      createSkill: 'Create New Skill',
    },
    engineering: {
      sprinklerHead: 'Sprinkler Head',
      pipeNetwork: 'Pipe Network',
      pressureLoss: 'Pressure Loss',
      flowRate: 'Flow Rate',
      velocity: 'Velocity',
      hydraulicCalc: 'Hydraulic Calculation',
      clashDetection: 'Clash Detection',
      mepSystem: 'MEP Systems',
      fireProtection: 'Fire Protection',
      hvac: 'HVAC',
      plumbing: 'Plumbing',
      nfpa13: 'NFPA 13 Standard',
      hazenWilliams: 'Hazen-Williams Formula',
      cFactor: 'C-Factor',
      psi: 'PSI',
      gpm: 'GPM',
      fps: 'FPS',
    },
    skills: {
      title: 'Skill Factory',
      createNew: 'Create New Skill',
      generating: 'Generating logic...',
      validating: 'Validating in Sandbox...',
      deployed: 'Deployed',
      activate: 'Activate',
      description: 'Describe the automation you need',
      hydraulicCalc: 'Hydraulic Calculator',
      revitExtract: 'Revit Extractor',
      reportGen: 'Report Generator',
    },
    messages: {
      skillCreated: 'Skill created successfully!',
      skillActivated: 'Skill activated and added to library!',
      processingComplete: 'Processing complete',
      validationPassed: 'Validation passed',
      validationFailed: 'Validation failed',
      connectionError: 'Connection error',
    },
  },
  ru: {
    common: {
      save: 'Сохранить',
      cancel: 'Отмена',
      close: 'Закрыть',
      loading: 'Загрузка...',
      error: 'Ошибка',
      success: 'Успех',
      confirm: 'Подтвердить',
      delete: 'Удалить',
      edit: 'Редактировать',
      create: 'Создать',
      search: 'Поиск',
      filter: 'Фильтр',
      refresh: 'Обновить',
      back: 'Назад',
      next: 'Далее',
      previous: 'Предыдущий',
      submit: 'Отправить',
      reset: 'Сброс',
    },
    nav: {
      dashboard: 'Панель управления',
      projects: 'Проекты',
      skills: 'Навыки',
      settings: 'Настройки',
      help: 'Помощь',
      autopilot: 'Автопилот',
      calculation: 'Расчёты',
      communication: 'Связь',
    },
    dashboard: {
      title: 'Инженерная панель',
      subtitle: 'AI-система обнаружения коллизий MEP',
      systemActive: 'Система активна',
      systemOffline: 'Система недоступна',
      openClashes: 'Открытые коллизии',
      resolvedToday: 'Решено сегодня',
      aiActivity: 'Активность AI',
      avgResponseTime: 'Среднее время отклика',
      activeResolution: 'Активное разрешение коллизии',
      recentActivity: 'Недавняя активность',
      performanceMetrics: 'Показатели производительности',
      systemStatus: 'Статус системы',
      skillFactory: 'Фабрика навыков',
      createSkill: 'Создать новый навык',
    },
    engineering: {
      sprinklerHead: 'Спринклерная головка',
      pipeNetwork: 'Трубопроводная сеть',
      pressureLoss: 'Потеря давления',
      flowRate: 'Расход',
      velocity: 'Скорость потока',
      hydraulicCalc: 'Гидравлический расчёт',
      clashDetection: 'Обнаружение коллизий',
      mepSystem: 'Системы MEP',
      fireProtection: 'Пожаротушение',
      hvac: 'HVAC (ОВиК)',
      plumbing: 'Водоснабжение',
      nfpa13: 'Стандарт NFPA 13',
      hazenWilliams: 'Формула Хазена-Вильямса',
      cFactor: 'Коэффициент C',
      psi: 'PSI (фунт/кв.дюйм)',
      gpm: 'GPM (галлон/мин)',
      fps: 'FPS (фут/сек)',
    },
    skills: {
      title: 'Фабрика навыков',
      createNew: 'Создать новый навык',
      generating: 'Генерация логики...',
      validating: 'Проверка в Sandbox...',
      deployed: 'Развёрнуто',
      activate: 'Активировать',
      description: 'Опишите нужную автоматизацию',
      hydraulicCalc: 'Гидравлический калькулятор',
      revitExtract: 'Извлечение из Revit',
      reportGen: 'Генератор отчётов',
    },
    messages: {
      skillCreated: 'Навык успешно создан!',
      skillActivated: 'Навык активирован и добавлен в библиотеку!',
      processingComplete: 'Обработка завершена',
      validationPassed: 'Проверка пройдена',
      validationFailed: 'Проверка не пройдена',
      connectionError: 'Ошибка подключения',
    },
  },
};

// ============================================================================
// CONTEXT
// ============================================================================

interface LanguageContextType {
  lang: Language;
  direction: Direction;
  config: LanguageConfig;
  t: Dictionary;
  setLanguage: (lang: Language) => void;
  formatNumber: (num: number) => string;
  formatDate: (date: Date) => string;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

// ============================================================================
// PROVIDER
// ============================================================================

interface LanguageProviderProps {
  children: ReactNode;
  defaultLang?: Language;
}

export function LanguageProvider({ children, defaultLang = 'he' }: LanguageProviderProps) {
  const [lang, setLangState] = useState<Language>(defaultLang);

  // Load saved language from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('aquabrain_lang') as Language;
    if (saved && LANGUAGES[saved]) {
      setLangState(saved);
    }
  }, []);

  // Update document direction when language changes
  useEffect(() => {
    const dir = LANGUAGES[lang].direction;
    document.documentElement.dir = dir;
    document.documentElement.lang = lang;
    document.body.style.direction = dir;
  }, [lang]);

  const setLanguage = useCallback((newLang: Language) => {
    setLangState(newLang);
    localStorage.setItem('aquabrain_lang', newLang);
  }, []);

  const formatNumber = useCallback((num: number) => {
    return new Intl.NumberFormat(lang === 'he' ? 'he-IL' : lang === 'ru' ? 'ru-RU' : 'en-US').format(num);
  }, [lang]);

  const formatDate = useCallback((date: Date) => {
    return new Intl.DateTimeFormat(lang === 'he' ? 'he-IL' : lang === 'ru' ? 'ru-RU' : 'en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    }).format(date);
  }, [lang]);

  const value: LanguageContextType = {
    lang,
    direction: LANGUAGES[lang].direction,
    config: LANGUAGES[lang],
    t: dictionaries[lang],
    setLanguage,
    formatNumber,
    formatDate,
  };

  return (
    <LanguageContext.Provider value={value}>
      {children}
    </LanguageContext.Provider>
  );
}

// ============================================================================
// HOOK
// ============================================================================

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
}

// ============================================================================
// LANGUAGE SWITCHER COMPONENT
// ============================================================================

interface LanguageSwitcherProps {
  variant?: 'flags' | 'dropdown' | 'minimal';
  className?: string;
}

export function LanguageSwitcher({ variant = 'flags', className = '' }: LanguageSwitcherProps) {
  const { lang, setLanguage } = useLanguage();
  const [isOpen, setIsOpen] = useState(false);

  if (variant === 'flags') {
    return (
      <div className={`flex items-center gap-1 ${className}`}>
        {(Object.keys(LANGUAGES) as Language[]).map((code) => (
          <button
            key={code}
            onClick={() => setLanguage(code)}
            className={`
              w-9 h-9 rounded-lg flex items-center justify-center text-xl
              transition-all duration-200
              ${lang === code
                ? 'bg-white/20 ring-2 ring-purple-500/50 scale-110'
                : 'bg-white/5 hover:bg-white/10 opacity-60 hover:opacity-100'}
            `}
            title={LANGUAGES[code].nativeName}
          >
            {LANGUAGES[code].flag}
          </button>
        ))}
      </div>
    );
  }

  if (variant === 'dropdown') {
    return (
      <div className={`relative ${className}`}>
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 transition-colors"
        >
          <span className="text-xl">{LANGUAGES[lang].flag}</span>
          <span className="text-sm text-white/80">{LANGUAGES[lang].nativeName}</span>
        </button>
        {isOpen && (
          <div className="absolute top-full mt-2 right-0 z-50 glass-heavy rounded-xl overflow-hidden min-w-[150px]">
            {(Object.keys(LANGUAGES) as Language[]).map((code) => (
              <button
                key={code}
                onClick={() => {
                  setLanguage(code);
                  setIsOpen(false);
                }}
                className={`
                  w-full flex items-center gap-3 px-4 py-3 text-right
                  hover:bg-white/10 transition-colors
                  ${lang === code ? 'bg-purple-500/20' : ''}
                `}
              >
                <span className="text-xl">{LANGUAGES[code].flag}</span>
                <span className="text-sm text-white/80">{LANGUAGES[code].nativeName}</span>
              </button>
            ))}
          </div>
        )}
      </div>
    );
  }

  // Minimal variant - just current flag
  return (
    <button
      onClick={() => {
        const langs = Object.keys(LANGUAGES) as Language[];
        const currentIndex = langs.indexOf(lang);
        const nextIndex = (currentIndex + 1) % langs.length;
        setLanguage(langs[nextIndex]);
      }}
      className={`w-10 h-10 rounded-lg flex items-center justify-center text-2xl bg-white/5 hover:bg-white/10 transition-colors ${className}`}
      title="Switch language"
    >
      {LANGUAGES[lang].flag}
    </button>
  );
}

export default LanguageContext;
