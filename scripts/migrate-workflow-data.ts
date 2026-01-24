/**
 * Workflow Data Migration Script
 *
 * This script migrates legacy workflow data structures to the unified step system.
 * It converts:
 *   - workflowData.steps (legacy) → unifiedSteps (unified)
 *   - workflowData.coreStepInstances → merged into unifiedSteps
 *
 * Usage:
 *   cd frontend
 *   npx tsx ../scripts/migrate-workflow-data.ts
 *
 * Options:
 *   --dry-run    Preview changes without writing files
 *   --backup     Create backup files before migration (default: true)
 */

import * as fs from "fs";
import * as path from "path";

// Types matching the frontend workflow types
interface StepCapture {
    id: string;
    slideIndex: number;
    x: number;
    y: number;
    width: number;
    height: number;
    label?: string;
}

interface StepAttachment {
    id: string;
    type: "text" | "image";
    content?: string;
    imageId?: string;
    caption?: string;
    createdAt: string;
}

interface WorkflowStepInstance {
    id: string;
    stepId: string;
    captures: StepCapture[];
    attachments: StepAttachment[];
    order: number;
    createdAt: string;
}

interface CoreStepPresetValue {
    presetId: string;
    inputType: "capture" | "text" | "image_clipboard";
    captureValue?: StepCapture;
    textValue?: string;
    imageId?: string;
}

interface CoreStepInstance {
    id: string;
    coreStepId: string;
    presetValues: CoreStepPresetValue[];
    order: number;
    createdAt: string;
}

interface UnifiedStepItem {
    id: string;
    type: "core" | "regular";
    order: number;
    createdAt: string;
    // Core step specific
    coreStepId?: string;
    presetValues?: CoreStepPresetValue[];
    // Regular step specific
    stepId?: string;
    captures?: StepCapture[];
    attachments?: StepAttachment[];
}

interface SupportRelation {
    id: string;
    supporterStepId: string;
    targetStepId: string;
    phaseId: string;
    createdAt: string;
}

interface ProjectWorkflowData {
    steps: WorkflowStepInstance[];
    coreStepInstances?: CoreStepInstance[];
    unifiedSteps?: UnifiedStepItem[];
    supportRelations: SupportRelation[];
    keyStepLinks?: any[];
    isConfirmed?: boolean;
    confirmedAt?: string;
    createdAt: string;
    updatedAt: string;
}

interface ProjectData {
    workflows?: Record<string, ProjectWorkflowData>;
    [key: string]: any;
}

// Generate unique ID
function generateId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

// Migrate a single workflow's data to unified steps
function migrateWorkflowData(
    workflowData: ProjectWorkflowData
): ProjectWorkflowData {
    // If already has unifiedSteps, skip migration
    if (
        workflowData.unifiedSteps &&
        workflowData.unifiedSteps.length > 0
    ) {
        console.log("    Already has unifiedSteps, skipping...");
        return workflowData;
    }

    const unifiedSteps: UnifiedStepItem[] = [];
    let order = 0;

    // First, add core step instances (they should be first and last)
    const coreInstances = workflowData.coreStepInstances ?? [];
    const sortedCoreInstances = [...coreInstances].sort(
        (a, b) => a.order - b.order
    );

    // Add first core step (if exists)
    if (sortedCoreInstances.length > 0) {
        const firstCore = sortedCoreInstances[0];
        unifiedSteps.push({
            id: firstCore.id,
            type: "core",
            order: order++,
            createdAt: firstCore.createdAt,
            coreStepId: firstCore.coreStepId,
            presetValues: firstCore.presetValues,
        });
    }

    // Add regular steps in the middle
    const regularSteps = [...workflowData.steps].sort(
        (a, b) => a.order - b.order
    );
    for (const step of regularSteps) {
        unifiedSteps.push({
            id: step.id,
            type: "regular",
            order: order++,
            createdAt: step.createdAt,
            stepId: step.stepId,
            captures: step.captures,
            attachments: step.attachments,
        });
    }

    // Add remaining core steps (should be last one)
    for (let i = 1; i < sortedCoreInstances.length; i++) {
        const coreInstance = sortedCoreInstances[i];
        unifiedSteps.push({
            id: coreInstance.id,
            type: "core",
            order: order++,
            createdAt: coreInstance.createdAt,
            coreStepId: coreInstance.coreStepId,
            presetValues: coreInstance.presetValues,
        });
    }

    return {
        ...workflowData,
        unifiedSteps,
        // Keep legacy arrays for backward compatibility during transition
        steps: workflowData.steps,
        coreStepInstances: workflowData.coreStepInstances,
        updatedAt: new Date().toISOString(),
    };
}

// Find all project JSON files in results directory
function findProjectFiles(resultsDir: string): string[] {
    const files: string[] = [];

    if (!fs.existsSync(resultsDir)) {
        console.log(`Results directory not found: ${resultsDir}`);
        return files;
    }

    const entries = fs.readdirSync(resultsDir, { withFileTypes: true });

    for (const entry of entries) {
        if (entry.isDirectory()) {
            const projectJsonPath = path.join(
                resultsDir,
                entry.name,
                `${entry.name}.json`
            );
            if (fs.existsSync(projectJsonPath)) {
                files.push(projectJsonPath);
            }
        }
    }

    return files;
}

// Main migration function
async function main() {
    const args = process.argv.slice(2);
    const dryRun = args.includes("--dry-run");
    const noBackup = args.includes("--no-backup");

    console.log("=".repeat(60));
    console.log("Workflow Data Migration Script");
    console.log("=".repeat(60));
    console.log(`Mode: ${dryRun ? "DRY RUN (no changes)" : "LIVE"}`);
    console.log(`Backup: ${noBackup ? "DISABLED" : "ENABLED"}`);
    console.log("");

    // Find results directory (relative to script location)
    const scriptDir = __dirname;
    const projectRoot = path.dirname(scriptDir);
    const resultsDir = path.join(projectRoot, "results");

    console.log(`Looking for projects in: ${resultsDir}`);
    console.log("");

    const projectFiles = findProjectFiles(resultsDir);

    if (projectFiles.length === 0) {
        console.log("No project files found to migrate.");
        return;
    }

    console.log(`Found ${projectFiles.length} project(s) to check.`);
    console.log("");

    let migratedCount = 0;
    let skippedCount = 0;
    let errorCount = 0;

    for (const filePath of projectFiles) {
        const projectId = path.basename(path.dirname(filePath));
        console.log(`Processing: ${projectId}`);

        try {
            const content = fs.readFileSync(filePath, "utf-8");
            const projectData: ProjectData = JSON.parse(content);

            if (!projectData.workflows) {
                console.log("  No workflows found, skipping...");
                skippedCount++;
                continue;
            }

            let hasChanges = false;

            for (const [workflowId, workflowData] of Object.entries(
                projectData.workflows
            )) {
                console.log(`  Workflow: ${workflowId}`);

                // Check if migration is needed
                const hasLegacySteps = workflowData.steps?.length > 0;
                const hasCoreInstances =
                    workflowData.coreStepInstances?.length > 0;
                const hasUnifiedSteps =
                    workflowData.unifiedSteps?.length > 0;

                if (!hasLegacySteps && !hasCoreInstances) {
                    console.log("    No data to migrate, skipping...");
                    continue;
                }

                if (hasUnifiedSteps) {
                    console.log("    Already migrated, skipping...");
                    continue;
                }

                console.log(
                    `    Legacy steps: ${workflowData.steps?.length ?? 0}`
                );
                console.log(
                    `    Core instances: ${
                        workflowData.coreStepInstances?.length ?? 0
                    }`
                );

                const migratedData = migrateWorkflowData(workflowData);
                console.log(
                    `    Unified steps created: ${
                        migratedData.unifiedSteps?.length ?? 0
                    }`
                );

                projectData.workflows[workflowId] = migratedData;
                hasChanges = true;
            }

            if (hasChanges) {
                if (!dryRun) {
                    // Create backup
                    if (!noBackup) {
                        const backupPath = filePath.replace(
                            ".json",
                            `.backup-${Date.now()}.json`
                        );
                        fs.copyFileSync(filePath, backupPath);
                        console.log(`  Backup created: ${path.basename(backupPath)}`);
                    }

                    // Write migrated data
                    fs.writeFileSync(
                        filePath,
                        JSON.stringify(projectData, null, 2)
                    );
                    console.log("  Migration complete!");
                } else {
                    console.log("  Would migrate (dry run)");
                }
                migratedCount++;
            } else {
                skippedCount++;
            }
        } catch (error) {
            console.error(`  Error: ${error}`);
            errorCount++;
        }

        console.log("");
    }

    console.log("=".repeat(60));
    console.log("Migration Summary");
    console.log("=".repeat(60));
    console.log(`Total projects: ${projectFiles.length}`);
    console.log(`Migrated: ${migratedCount}`);
    console.log(`Skipped: ${skippedCount}`);
    console.log(`Errors: ${errorCount}`);

    if (dryRun) {
        console.log("");
        console.log(
            "This was a dry run. Run without --dry-run to apply changes."
        );
    }
}

main().catch(console.error);
