/**
 * AquaBrain Software Controller
 * ==============================
 * Manages Autodesk software (Revit, AutoCAD) lifecycle
 *
 * Supported Software:
 * - Revit 2024, 2025, 2026
 * - AutoCAD 2026
 */

const { spawn, execSync, exec } = require('child_process');
const path = require('path');

// Software definitions
const SOFTWARE_CATALOG = {
    'revit2024': {
        name: 'Revit 2024',
        script: 'revit2024.ps1',
        icon: '🏗️',
        category: 'BIM'
    },
    'revit2025': {
        name: 'Revit 2025',
        script: 'revit2025.ps1',
        icon: '🏗️',
        category: 'BIM'
    },
    'revit2026': {
        name: 'Revit 2026',
        script: 'revit2026.ps1',
        icon: '🏗️',
        category: 'BIM'
    },
    'autocad2026': {
        name: 'AutoCAD 2026',
        script: 'autocad2026.ps1',
        icon: '📐',
        category: 'CAD'
    }
};

// Scripts are in C:\AquaBrain\Scripts\software on Windows
const SCRIPTS_DIR = process.platform === 'linux'
  ? 'C:\\AquaBrain\\Scripts\\software'  // WSL uses Windows path
  : __dirname;

/**
 * Execute PowerShell script for software control
 */
function executePowerShell(scriptName, action, filePath = '') {
    return new Promise((resolve, reject) => {
        // Build Windows path for the script
        const scriptPath = `${SCRIPTS_DIR}\\${scriptName}`;

        // Build PowerShell command
        let psCommand = `powershell.exe -ExecutionPolicy Bypass -File "${scriptPath}" -Action ${action}`;
        if (filePath) {
            psCommand += ` -FilePath "${filePath}"`;
        }

        exec(psCommand, { encoding: 'utf8' }, (error, stdout, stderr) => {
            // Clean the output (remove PowerShell profile messages)
            let cleanOutput = stdout;
            if (stdout.includes('{')) {
                // Find JSON in output
                const jsonStart = stdout.indexOf('{');
                const jsonEnd = stdout.lastIndexOf('}') + 1;
                if (jsonStart !== -1 && jsonEnd > jsonStart) {
                    cleanOutput = stdout.substring(jsonStart, jsonEnd);
                }
            }

            try {
                const result = JSON.parse(cleanOutput.trim());
                resolve(result);
            } catch (e) {
                if (!error) {
                    resolve({ success: true, output: stdout });
                } else {
                    reject(new Error(stderr || stdout || error.message));
                }
            }
        });
    });
}

/**
 * Software Controller Class
 */
class SoftwareController {
    constructor() {
        this.catalog = SOFTWARE_CATALOG;
    }

    /**
     * Get list of available software
     */
    getAvailableSoftware() {
        return Object.entries(this.catalog).map(([id, info]) => ({
            id,
            ...info
        }));
    }

    /**
     * Get status of a specific software
     */
    async getStatus(softwareId) {
        const software = this.catalog[softwareId];
        if (!software) {
            throw new Error(`Unknown software: ${softwareId}`);
        }

        return await executePowerShell(software.script, 'status');
    }

    /**
     * Get status of all software
     */
    async getAllStatus() {
        const results = {};
        for (const [id, software] of Object.entries(this.catalog)) {
            try {
                results[id] = await executePowerShell(software.script, 'status');
            } catch (e) {
                results[id] = { running: false, error: e.message };
            }
        }
        return results;
    }

    /**
     * Open software
     */
    async open(softwareId, filePath = '') {
        const software = this.catalog[softwareId];
        if (!software) {
            throw new Error(`Unknown software: ${softwareId}`);
        }

        return await executePowerShell(software.script, 'open', filePath);
    }

    /**
     * Close software
     */
    async close(softwareId) {
        const software = this.catalog[softwareId];
        if (!software) {
            throw new Error(`Unknown software: ${softwareId}`);
        }

        return await executePowerShell(software.script, 'close');
    }

    /**
     * Restart software
     */
    async restart(softwareId, filePath = '') {
        await this.close(softwareId);
        // Wait a bit for process to fully terminate
        await new Promise(resolve => setTimeout(resolve, 3000));
        return await this.open(softwareId, filePath);
    }
}

module.exports = {
    SoftwareController,
    SOFTWARE_CATALOG
};
