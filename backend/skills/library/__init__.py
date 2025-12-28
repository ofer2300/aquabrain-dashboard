"""
AquaBrain Skills Library V8.0 - EMAIL COCKPIT Edition
=======================================================
Complete Autodesk ecosystem + Auto-Declaration + Virtual Engineer + Email Cockpit.

Categories:
- Revit: Full control via pyRevit Routes API
- AutoCAD: Headless processing via Core Console
- Navisworks: Clash detection API
- Declaration #501: Auto-sign engineer declarations in 18-35 seconds
- Virtual Engineer #601: 24/7 AI partner with full project memory
- Email Cockpit #701: All emails processed ONLY through AquaBrain
- Communication: WhatsApp, Email, Teams notifications
- Documents: PDF, DOCX processing
- Integration: Revit ↔ AutoCAD data exchange
"""

from .whatsapp_notify import WhatsAppNotifySkill
from .email_notify import EmailNotifySkill

# Revit Skills (pyRevit Routes API) - V4.0
from .revit_skills import (
    RoutesClient,
    get_routes_client,
    get_routes_endpoint,
    RevitScriptBuilder,
    MockRevitData,
    Skill_OpenProject,
    Skill_ExtractLOD500,
    Skill_HydraulicCalc,
    Skill_GenerateModel,
    Skill_AutoTag,
    Skill_ClashNavis,
    Skill_RevitExecute,
    call_revit_route,
    revit_execute
)

# Autodesk Full Domination - V5.0
from .autodesk_domination import (
    # Clients
    RevitRoutesClient,
    AutoCADCoreClient,

    # Script Templates
    RevitScripts,
    AutoCADScripts,

    # Revit Skills #201-#205
    Skill_OpenRevitProject,
    Skill_ExtractSemanticData,
    Skill_PushLOD500Model,
    Skill_ExportSheets,
    Skill_NavisworksClash,
    Skill_GetFireRating,
    Skill_AutoTagSprinklers,

    # AutoCAD Skills #301-#305
    Skill_OpenDWG,
    Skill_RunAutoLISP,
    Skill_ExportDWG,
    Skill_RevitToAutoCAD,
    Skill_GenerateTitleBlock,

    # Utilities
    autocad_core_execute
)

# SKILL #501 - Declaration Auto-Sign (V6.0 Platinum)
try:
    from .declaration_autosign import (
        Skill_DeclarationAutoSign,
        EngineerProfile,
        DeclarationData,
        TrafficLight,
        DeclarationEmailMonitor,
        DeclarationAnalyzer,
        DecisionEngine,
        PDFSigner as DeclarationPDFSigner,
        DeclarationEmailSender,
        SENIOR_ENGINEER_PROMPT
    )
except ImportError:
    pass

# SKILL #501 Alternative Implementation (Fire Edition)
try:
    from .skill_501_auto_sign import AutoSignDeclarationSkill, PDFSigner
except ImportError:
    pass

# SKILL #601 - Virtual Senior Engineer 24/7 (V7.0 Platinum)
try:
    from .virtual_senior_engineer import (
        Skill_VirtualSeniorEngineer,
        SeniorEngineerProfile,
        SecretsManager,
        ProjectMemory,
        MeetingPrepGenerator,
        CalendarIntegration,
        NotificationHub,
        ActionItemsTracker,
        EnhancedDeclarationHandler,
        MEETING_PREP_PROMPT
    )
except ImportError:
    pass

# SKILL #601 Alternative Implementation (Royal Edition)
try:
    from .skill_601_virtual_engineer import VirtualSeniorEngineerSkill
except ImportError:
    pass

# SKILL #701 - Email Cockpit (V8.0 Platinum)
try:
    from .email_cockpit import (
        Skill_EmailCockpit,
        EmailPoller,
        EmailAnalyzer,
        GoldenHoursDashboard,
        EmailResponder,
        InAppEmailHandler,
        EmailMessage,
        EmailAnalysis,
        EmailCard,
        RiskLevel,
        RequiredAction,
        SenderImportance,
        GOLDEN_HOURS,
        EMAIL_ANALYZER_PROMPT
    )
except ImportError:
    pass

# SKILL #801 - Sump Pit Optimizer (V9.0 Platinum)
try:
    from .skill_801_sump_pit import (
        SumpPitOptimizer,
        Skill_SumpPitOptimizer,
        calculate_pit_volume,
        validate_volume,
        ValidationStatus,
        VOLUME_REQUIREMENTS,
        SAFETY_FACTOR
    )
except ImportError:
    pass

# SKILL #802 - DWG Updater & Delivery (V9.0 Platinum)
try:
    from .skill_802_dwg_updater import (
        DWGUpdaterSkill,
        Skill_DWGUpdater,
        open_dwg_file,
        find_and_replace_text,
        save_dwg_as,
        export_pdf,
        send_update_email
    )
except ImportError:
    pass

# SKILL #901 - AquaSkill Core v2.0 (V10.0 Platinum)
try:
    from .skill_901_aquaskill_core import (
        AquaSkillCore,
        Skill_AquaSkillCore,
        AquaPlanner,
        AquaVerifier,
        PlanStep,
        ExecutionPlan,
        VerificationResult,
        RiskProfile,
        TrafficLight as CoreTrafficLight,
        StepTool,
        NFPA_HAZARD_CLASSES
    )
except ImportError:
    pass

__all__ = [
    # Communication
    'WhatsAppNotifySkill',
    'EmailNotifySkill',

    # Revit Routes API (V4.0)
    'RoutesClient',
    'get_routes_client',
    'get_routes_endpoint',
    'RevitScriptBuilder',
    'MockRevitData',
    'Skill_OpenProject',
    'Skill_ExtractLOD500',
    'Skill_HydraulicCalc',
    'Skill_GenerateModel',
    'Skill_AutoTag',
    'Skill_ClashNavis',
    'Skill_RevitExecute',
    'call_revit_route',
    'revit_execute',

    # Autodesk Full Domination (V5.0)
    'RevitRoutesClient',
    'AutoCADCoreClient',
    'RevitScripts',
    'AutoCADScripts',

    # Revit Skills #201-#205, #105-#106
    'Skill_OpenRevitProject',
    'Skill_ExtractSemanticData',
    'Skill_PushLOD500Model',
    'Skill_ExportSheets',
    'Skill_NavisworksClash',
    'Skill_GetFireRating',
    'Skill_AutoTagSprinklers',

    # AutoCAD Skills #301-#305
    'Skill_OpenDWG',
    'Skill_RunAutoLISP',
    'Skill_ExportDWG',
    'Skill_RevitToAutoCAD',
    'Skill_GenerateTitleBlock',

    # Utilities
    'autocad_core_execute',

    # SKILL #501 - Declaration Auto-Sign (V6.0 Platinum)
    'Skill_DeclarationAutoSign',
    'EngineerProfile',
    'DeclarationData',
    'TrafficLight',
    'DeclarationEmailMonitor',
    'DeclarationAnalyzer',
    'DecisionEngine',
    'PDFSigner',
    'DeclarationEmailSender',
    'SENIOR_ENGINEER_PROMPT',

    # SKILL #601 - Virtual Senior Engineer 24/7 (V7.0 Platinum)
    'Skill_VirtualSeniorEngineer',
    'SeniorEngineerProfile',
    'SecretsManager',
    'ProjectMemory',
    'MeetingPrepGenerator',
    'CalendarIntegration',
    'NotificationHub',
    'ActionItemsTracker',
    'EnhancedDeclarationHandler',
    'MEETING_PREP_PROMPT',

    # SKILL #701 - Email Cockpit (V8.0 Platinum)
    'Skill_EmailCockpit',
    'EmailPoller',
    'EmailAnalyzer',
    'GoldenHoursDashboard',
    'EmailResponder',
    'InAppEmailHandler',
    'EmailMessage',
    'EmailAnalysis',
    'EmailCard',
    'RiskLevel',
    'RequiredAction',
    'SenderImportance',
    'GOLDEN_HOURS',
    'EMAIL_ANALYZER_PROMPT',

    # SKILL #801 - Sump Pit Optimizer (V9.0 Platinum)
    'SumpPitOptimizer',
    'Skill_SumpPitOptimizer',
    'calculate_pit_volume',
    'validate_volume',
    'ValidationStatus',
    'VOLUME_REQUIREMENTS',
    'SAFETY_FACTOR',

    # SKILL #802 - DWG Updater & Delivery (V9.0 Platinum)
    'DWGUpdaterSkill',
    'Skill_DWGUpdater',
    'open_dwg_file',
    'find_and_replace_text',
    'save_dwg_as',
    'export_pdf',
    'send_update_email',

    # SKILL #901 - AquaSkill Core v2.0 (V10.0 Platinum)
    'AquaSkillCore',
    'Skill_AquaSkillCore',
    'AquaPlanner',
    'AquaVerifier',
    'PlanStep',
    'ExecutionPlan',
    'VerificationResult',
    'RiskProfile',
    'CoreTrafficLight',
    'StepTool',
    'NFPA_HAZARD_CLASSES'
]
