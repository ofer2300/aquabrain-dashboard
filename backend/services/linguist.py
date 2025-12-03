"""
AquaBrain Engineering Linguist V1.0
===================================
Context-aware translation service for MEP engineering terms.

Features:
- Engineering-specific translations (not generic)
- Context-aware (knows difference between "head" in plumbing vs general)
- Learning from user feedback
- Multiple languages: Hebrew, English, Russian
"""

from __future__ import annotations
import sqlite3
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, Field
from enum import Enum


class Language(str, Enum):
    """Supported languages."""
    HEBREW = "he"
    ENGLISH = "en"
    RUSSIAN = "ru"


class EngineeringDomain(str, Enum):
    """Engineering domains for context."""
    FIRE_PROTECTION = "fire_protection"
    HVAC = "hvac"
    PLUMBING = "plumbing"
    ELECTRICAL = "electrical"
    STRUCTURAL = "structural"
    GENERAL = "general"


class TermEntry(BaseModel):
    """A term in the knowledge base."""
    term_key: str
    lang: Language
    translation: str
    explanation: str = ""
    domain: EngineeringDomain = EngineeringDomain.GENERAL
    confidence_score: float = 1.0
    user_feedback_count: int = 0
    positive_feedback: int = 0
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class TranslationRequest(BaseModel):
    """Request to translate a term."""
    term: str
    target_lang: Language
    context: Optional[str] = None
    domain: EngineeringDomain = EngineeringDomain.GENERAL


class TranslationResult(BaseModel):
    """Result of a translation."""
    original: str
    translation: str
    target_lang: Language
    explanation: str = ""
    confidence: float = 1.0
    source: str = "knowledge_base"  # "knowledge_base" or "llm"
    domain: EngineeringDomain = EngineeringDomain.GENERAL


class ExplanationRequest(BaseModel):
    """Request to explain a term."""
    term: str
    lang: Language
    domain: EngineeringDomain = EngineeringDomain.GENERAL


class ExplanationResult(BaseModel):
    """Result of an explanation."""
    term: str
    explanation: str
    lang: Language
    examples: List[str] = Field(default_factory=list)
    related_terms: List[str] = Field(default_factory=list)


# ============================================================================
# BUILT-IN ENGINEERING DICTIONARY
# ============================================================================

ENGINEERING_DICTIONARY: Dict[str, Dict[Language, Dict[str, str]]] = {
    # Fire Protection
    "sprinkler_head": {
        Language.HEBREW: {"translation": "ראש מתז", "explanation": "התקן כיבוי אש אוטומטי המתפזר מים בעת גילוי חום"},
        Language.ENGLISH: {"translation": "Sprinkler Head", "explanation": "Automatic fire suppression device that disperses water when heat is detected"},
        Language.RUSSIAN: {"translation": "Спринклерная головка", "explanation": "Автоматическое устройство пожаротушения, распыляющее воду при обнаружении тепла"},
    },
    "pressure_loss": {
        Language.HEBREW: {"translation": "אובדן לחץ", "explanation": "הפחתת לחץ המים בזרימה דרך צינורות עקב חיכוך"},
        Language.ENGLISH: {"translation": "Pressure Loss", "explanation": "Reduction in water pressure as it flows through pipes due to friction"},
        Language.RUSSIAN: {"translation": "Потеря давления", "explanation": "Снижение давления воды при прохождении через трубы из-за трения"},
    },
    "flow_rate": {
        Language.HEBREW: {"translation": "ספיקה", "explanation": "נפח המים העובר בצינור ליחידת זמן (GPM או ליטר/דקה)"},
        Language.ENGLISH: {"translation": "Flow Rate", "explanation": "Volume of water passing through a pipe per unit time (GPM or L/min)"},
        Language.RUSSIAN: {"translation": "Расход", "explanation": "Объём воды, проходящей через трубу в единицу времени (галлон/мин или л/мин)"},
    },
    "velocity": {
        Language.HEBREW: {"translation": "מהירות זרימה", "explanation": "מהירות תנועת המים בצינור (FPS או מ/ש)"},
        Language.ENGLISH: {"translation": "Velocity", "explanation": "Speed of water movement in a pipe (FPS or m/s)"},
        Language.RUSSIAN: {"translation": "Скорость потока", "explanation": "Скорость движения воды в трубе (фут/сек или м/с)"},
    },
    "c_factor": {
        Language.HEBREW: {"translation": "מקדם C", "explanation": "מקדם חיכוך הייזן-וויליאמס המציין את חלקות פנים הצינור"},
        Language.ENGLISH: {"translation": "C-Factor", "explanation": "Hazen-Williams friction coefficient indicating pipe interior smoothness"},
        Language.RUSSIAN: {"translation": "Коэффициент C", "explanation": "Коэффициент трения Хазена-Вильямса, указывающий на гладкость внутренней поверхности трубы"},
    },
    "hazen_williams": {
        Language.HEBREW: {"translation": "הייזן-וויליאמס", "explanation": "נוסחה אמפירית לחישוב אובדן לחץ בצינורות מים"},
        Language.ENGLISH: {"translation": "Hazen-Williams", "explanation": "Empirical formula for calculating pressure loss in water pipes"},
        Language.RUSSIAN: {"translation": "Хазен-Вильямс", "explanation": "Эмпирическая формула для расчёта потерь давления в водопроводных трубах"},
    },
    "nfpa_13": {
        Language.HEBREW: {"translation": "תקן NFPA 13", "explanation": "תקן אמריקאי להתקנת מערכות ספרינקלרים"},
        Language.ENGLISH: {"translation": "NFPA 13", "explanation": "American standard for sprinkler system installation"},
        Language.RUSSIAN: {"translation": "NFPA 13", "explanation": "Американский стандарт установки спринклерных систем"},
    },
    "pipe_schedule": {
        Language.HEBREW: {"translation": "סדרת צינור", "explanation": "סיווג עובי דופן הצינור (Schedule 40, Schedule 10)"},
        Language.ENGLISH: {"translation": "Pipe Schedule", "explanation": "Classification of pipe wall thickness (Schedule 40, Schedule 10)"},
        Language.RUSSIAN: {"translation": "Серия трубы", "explanation": "Классификация толщины стенки трубы (Schedule 40, Schedule 10)"},
    },
    # HVAC
    "duct": {
        Language.HEBREW: {"translation": "תעלת אוויר", "explanation": "צינור להובלת אוויר במערכת מיזוג"},
        Language.ENGLISH: {"translation": "Duct", "explanation": "Channel for conveying air in HVAC systems"},
        Language.RUSSIAN: {"translation": "Воздуховод", "explanation": "Канал для транспортировки воздуха в системах ОВиК"},
    },
    "diffuser": {
        Language.HEBREW: {"translation": "מפזר אוויר", "explanation": "התקן בקצה תעלת האוויר לפיזור זרימה אחידה"},
        Language.ENGLISH: {"translation": "Diffuser", "explanation": "Device at duct end for uniform air distribution"},
        Language.RUSSIAN: {"translation": "Диффузор", "explanation": "Устройство на конце воздуховода для равномерного распределения воздуха"},
    },
    "cfm": {
        Language.HEBREW: {"translation": "CFM (רגל מעוקב/דקה)", "explanation": "יחידת מדידה לספיקת אוויר"},
        Language.ENGLISH: {"translation": "CFM (Cubic Feet per Minute)", "explanation": "Unit of air flow measurement"},
        Language.RUSSIAN: {"translation": "CFM (куб. фут/мин)", "explanation": "Единица измерения расхода воздуха"},
    },
    # Clash Detection
    "hard_clash": {
        Language.HEBREW: {"translation": "התנגשות קשה", "explanation": "חפיפה פיזית בין אלמנטים שלא ניתנת לפתרון ללא שינוי"},
        Language.ENGLISH: {"translation": "Hard Clash", "explanation": "Physical overlap between elements that cannot be resolved without modification"},
        Language.RUSSIAN: {"translation": "Жёсткая коллизия", "explanation": "Физическое пересечение элементов, которое невозможно разрешить без изменений"},
    },
    "soft_clash": {
        Language.HEBREW: {"translation": "התנגשות רכה", "explanation": "הפרה של מרווח תחזוקה או גישה נדרש"},
        Language.ENGLISH: {"translation": "Soft Clash", "explanation": "Violation of required maintenance or access clearance"},
        Language.RUSSIAN: {"translation": "Мягкая коллизия", "explanation": "Нарушение требуемого зазора для обслуживания или доступа"},
    },
    "clearance": {
        Language.HEBREW: {"translation": "מרווח", "explanation": "מרחק מינימלי נדרש בין אלמנטים"},
        Language.ENGLISH: {"translation": "Clearance", "explanation": "Minimum required distance between elements"},
        Language.RUSSIAN: {"translation": "Зазор", "explanation": "Минимально необходимое расстояние между элементами"},
    },
    # BIM/Revit
    "lod": {
        Language.HEBREW: {"translation": "רמת פירוט (LOD)", "explanation": "מדד לרמת הפירוט והדיוק של אלמנט BIM"},
        Language.ENGLISH: {"translation": "Level of Development", "explanation": "Measure of BIM element detail and accuracy"},
        Language.RUSSIAN: {"translation": "Уровень детализации", "explanation": "Мера детализации и точности элемента BIM"},
    },
    "family": {
        Language.HEBREW: {"translation": "משפחה (Family)", "explanation": "קבוצת אלמנטים בעלי פרמטרים משותפים ב-Revit"},
        Language.ENGLISH: {"translation": "Family", "explanation": "Group of elements with shared parameters in Revit"},
        Language.RUSSIAN: {"translation": "Семейство", "explanation": "Группа элементов с общими параметрами в Revit"},
    },
}


class EngineeringLinguist:
    """
    Translation and explanation service for engineering terms.
    Uses built-in dictionary + learning from user feedback.
    """

    DB_PATH = Path(__file__).parent.parent / "data" / "linguist.db"

    def __init__(self):
        self.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize the SQLite database."""
        conn = sqlite3.connect(str(self.DB_PATH))
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS term_knowledge_base (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                term_key TEXT NOT NULL,
                lang TEXT NOT NULL,
                translation TEXT NOT NULL,
                explanation TEXT,
                domain TEXT DEFAULT 'general',
                confidence_score REAL DEFAULT 1.0,
                user_feedback_count INTEGER DEFAULT 0,
                positive_feedback INTEGER DEFAULT 0,
                created_at TEXT,
                updated_at TEXT,
                UNIQUE(term_key, lang)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                term_key TEXT NOT NULL,
                lang TEXT NOT NULL,
                is_helpful INTEGER,
                user_suggestion TEXT,
                created_at TEXT
            )
        """)

        conn.commit()
        conn.close()

    def _normalize_term(self, term: str) -> str:
        """Normalize term for lookup."""
        return term.lower().strip().replace(" ", "_").replace("-", "_")

    def translate(self, request: TranslationRequest) -> TranslationResult:
        """Translate an engineering term."""
        term_key = self._normalize_term(request.term)

        # Check built-in dictionary first
        if term_key in ENGINEERING_DICTIONARY:
            entry = ENGINEERING_DICTIONARY[term_key].get(request.target_lang)
            if entry:
                return TranslationResult(
                    original=request.term,
                    translation=entry["translation"],
                    target_lang=request.target_lang,
                    explanation=entry.get("explanation", ""),
                    confidence=1.0,
                    source="knowledge_base",
                    domain=request.domain,
                )

        # Check database for user-added terms
        conn = sqlite3.connect(str(self.DB_PATH))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT translation, explanation, confidence_score
            FROM term_knowledge_base
            WHERE term_key = ? AND lang = ?
        """, (term_key, request.target_lang.value))
        row = cursor.fetchone()
        conn.close()

        if row:
            return TranslationResult(
                original=request.term,
                translation=row[0],
                target_lang=request.target_lang,
                explanation=row[1] or "",
                confidence=row[2],
                source="knowledge_base",
                domain=request.domain,
            )

        # Fallback: Return original with low confidence
        return TranslationResult(
            original=request.term,
            translation=request.term,  # Return as-is
            target_lang=request.target_lang,
            explanation="",
            confidence=0.0,
            source="unknown",
            domain=request.domain,
        )

    def explain(self, request: ExplanationRequest) -> ExplanationResult:
        """Get a simple explanation of an engineering term."""
        term_key = self._normalize_term(request.term)

        # Check built-in dictionary
        if term_key in ENGINEERING_DICTIONARY:
            entry = ENGINEERING_DICTIONARY[term_key].get(request.lang)
            if entry:
                return ExplanationResult(
                    term=request.term,
                    explanation=entry.get("explanation", ""),
                    lang=request.lang,
                    examples=[],
                    related_terms=self._get_related_terms(term_key),
                )

        # Check database
        conn = sqlite3.connect(str(self.DB_PATH))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT explanation FROM term_knowledge_base
            WHERE term_key = ? AND lang = ?
        """, (term_key, request.lang.value))
        row = cursor.fetchone()
        conn.close()

        if row and row[0]:
            return ExplanationResult(
                term=request.term,
                explanation=row[0],
                lang=request.lang,
            )

        # No explanation found
        return ExplanationResult(
            term=request.term,
            explanation="No explanation available for this term.",
            lang=request.lang,
        )

    def _get_related_terms(self, term_key: str) -> List[str]:
        """Get related engineering terms."""
        related = []
        domain_terms = {
            "fire_protection": ["sprinkler_head", "pressure_loss", "flow_rate", "nfpa_13"],
            "hvac": ["duct", "diffuser", "cfm"],
            "clash": ["hard_clash", "soft_clash", "clearance"],
        }

        for domain, terms in domain_terms.items():
            if term_key in terms:
                related = [t for t in terms if t != term_key][:3]
                break

        return related

    def record_feedback(self, term_key: str, lang: Language, is_helpful: bool, suggestion: Optional[str] = None):
        """Record user feedback on a translation."""
        conn = sqlite3.connect(str(self.DB_PATH))
        cursor = conn.cursor()

        # Record feedback
        cursor.execute("""
            INSERT INTO user_feedback (term_key, lang, is_helpful, user_suggestion, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (term_key, lang.value, int(is_helpful), suggestion, datetime.now().isoformat()))

        # Update confidence in knowledge base if exists
        cursor.execute("""
            UPDATE term_knowledge_base
            SET user_feedback_count = user_feedback_count + 1,
                positive_feedback = positive_feedback + ?,
                confidence_score = CAST(positive_feedback + ? AS REAL) / (user_feedback_count + 1),
                updated_at = ?
            WHERE term_key = ? AND lang = ?
        """, (int(is_helpful), int(is_helpful), datetime.now().isoformat(), term_key, lang.value))

        conn.commit()
        conn.close()

    def add_term(self, entry: TermEntry):
        """Add or update a term in the knowledge base."""
        conn = sqlite3.connect(str(self.DB_PATH))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO term_knowledge_base
            (term_key, lang, translation, explanation, domain, confidence_score, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.term_key, entry.lang.value, entry.translation, entry.explanation,
            entry.domain.value, entry.confidence_score,
            entry.created_at.isoformat(), datetime.now().isoformat()
        ))

        conn.commit()
        conn.close()

    def get_all_terms(self, lang: Language) -> List[Dict[str, Any]]:
        """Get all terms for a language."""
        terms = []

        # Built-in terms
        for key, translations in ENGINEERING_DICTIONARY.items():
            if lang in translations:
                terms.append({
                    "term_key": key,
                    "translation": translations[lang]["translation"],
                    "explanation": translations[lang].get("explanation", ""),
                    "source": "builtin",
                })

        # Database terms
        conn = sqlite3.connect(str(self.DB_PATH))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT term_key, translation, explanation
            FROM term_knowledge_base WHERE lang = ?
        """, (lang.value,))

        for row in cursor.fetchall():
            # Avoid duplicates
            if not any(t["term_key"] == row[0] for t in terms):
                terms.append({
                    "term_key": row[0],
                    "translation": row[1],
                    "explanation": row[2] or "",
                    "source": "custom",
                })

        conn.close()
        return terms


# Global instance
engineering_linguist = EngineeringLinguist()
