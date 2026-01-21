<script>
    import { createEventDispatcher } from "svelte";
    import WorkflowSection from "./right-pane/WorkflowSection.svelte";
    import SummarySection from "./right-pane/SummarySection.svelte";
    import ObjectsSection from "./right-pane/ObjectsSection.svelte";

    export let rightPaneFullscreen = false;
    export let rightPaneWidth = 300;
    export let expandedSection = null;
    export let settings;
    export let allowEdit;
    export let savingWorkflow;
    export let captureMode = false;
    export let workflowSectionRef = null;
    export let summaryData;
    export let summaryDataLLM;
    export let savingSummary;
    export let generatingFieldIds;
    export let generatingAll;
    export let selectedSlideIndices = [];
    export let comparingFieldId = null;
    export let editingFieldId = null;
    export let allShapes = [];
    export let selectedShapeId = null;
    export let editingDescription = "";
    export let project;
    export let projectId = "";

    // Workflow step-based data - now supports multiple workflows
    export let workflowData = { steps: [] };
    export let allWorkflowsData = {};  // { workflowId: ProjectWorkflowData }
    export let captureTargetStepId = null;

    // Currently selected workflow tab
    export let activeWorkflowId = null;

    const dispatch = createEventDispatcher();

    // Get workflows from settings
    $: workflows = settings?.workflow_settings?.workflows || [];

    // Auto-select first workflow if none selected
    $: if (workflows.length > 0 && !activeWorkflowId) {
        activeWorkflowId = workflows[0].id;
    }

    // Get current workflow definition
    $: currentWorkflow = workflows.find(w => w.id === activeWorkflowId);

    // Get workflow steps for current workflow (either its own or global)
    $: currentWorkflowSteps = (() => {
        let result;
        if (currentWorkflow?.useGlobalSteps) {
            result = settings?.workflow_steps || { columns: [], rows: [] };
        } else {
            result = currentWorkflow?.steps || { columns: [], rows: [] };
        }
        console.log('[ViewerRightPane] currentWorkflowSteps:', {
            activeWorkflowId,
            useGlobalSteps: currentWorkflow?.useGlobalSteps,
            includeGlobalSteps: currentWorkflow?.includeGlobalSteps,
            resultRows: result.rows?.map(r => ({ id: r.id, values: r.values })),
            globalStepsRows: settings?.workflow_steps?.rows?.map(r => ({ id: r.id, values: r.values })),
            workflowOwnSteps: currentWorkflow?.steps?.rows?.map(r => ({ id: r.id, values: r.values })),
            additionalSteps: currentWorkflow?.additionalSteps?.rows?.map(r => ({ id: r.id, values: r.values }))
        });
        return result;
    })();

    // Get current workflow data
    $: currentWorkflowData = allWorkflowsData[activeWorkflowId] || workflowData;

    // Get core steps for current workflow
    $: currentCoreStepsSettings = currentWorkflow?.coreSteps || { definitions: [] };

    function toggleSection(section) {
        expandedSection = expandedSection === section ? null : section;
    }

    function selectWorkflowTab(workflowId) {
        activeWorkflowId = workflowId;
        dispatch("workflowTabChange", { workflowId });
    }

    function handleWorkflowChange(event) {
        // Include the workflow ID in the event
        dispatch("workflowChange", {
            ...event.detail,
            workflowId: activeWorkflowId,
        });
    }
</script>

<div
    class="bg-white border-l border-gray-200 flex flex-col {rightPaneFullscreen
        ? 'flex-1'
        : 'shrink-0'}"
    style={rightPaneFullscreen ? "" : `width: ${rightPaneWidth}px;`}
>
    <!-- Header -->
    <div class="p-4 border-b border-gray-200 flex items-center justify-between">
        <h2 class="font-bold text-gray-800">프로젝트 정보</h2>
        <button
            class="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-lg transition-all
                   {rightPaneFullscreen
                ? 'bg-blue-100 text-blue-700 hover:bg-blue-200'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}"
            on:click={() => (rightPaneFullscreen = !rightPaneFullscreen)}
            title={rightPaneFullscreen ? "일반 보기" : "전체 보기"}
        >
            {#if rightPaneFullscreen}
                <svg
                    class="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M9 9V4.5M9 9H4.5M9 9L3.5 3.5M9 15v4.5M9 15H4.5M9 15l-5.5 5.5M15 9h4.5M15 9V4.5M15 9l5.5-5.5M15 15h4.5M15 15v4.5m0-4.5l5.5 5.5"
                    />
                </svg>
                <span>일반</span>
            {:else}
                <svg
                    class="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"
                    />
                </svg>
                <span>전체</span>
            {/if}
        </button>
    </div>

    <div class="flex-1 overflow-y-auto min-h-0 flex flex-col">
        <!-- Workflow Section -->
        <WorkflowSection
            isExpanded={expandedSection === "workflow"}
            {projectId}
            workflowData={currentWorkflowData}
            workflowSteps={currentWorkflowSteps}
            globalPhases={settings?.phase_types || []}
            coreStepsSettings={currentCoreStepsSettings}
            workflowName={currentWorkflow?.name || "Workflow"}
            {savingWorkflow}
            {captureMode}
            {captureTargetStepId}
            {workflows}
            {activeWorkflowId}
            bind:this={workflowSectionRef}
            on:toggleExpand={() => toggleSection("workflow")}
            on:workflowChange={handleWorkflowChange}
            on:toggleCaptureMode
            on:deleteWorkflow
            on:deleteStepDefinition
            on:createStepDefinition
            on:updateStepDefinition
            on:selectWorkflowTab={(e) => selectWorkflowTab(e.detail.workflowId)}
        />

        <!-- Summary Section -->
        <SummarySection
            isExpanded={expandedSection === "summary"}
            {settings}
            {summaryData}
            {summaryDataLLM}
            {savingSummary}
            {generatingFieldIds}
            {generatingAll}
            {selectedSlideIndices}
            {comparingFieldId}
            {editingFieldId}
            {project}
            on:toggleExpand={() => toggleSection("summary")}
            on:generateAllSummaries
            on:toggleSlideSelection
            on:toggleCompare
            on:restoreLLMVersion
            on:generateSummaryForField
            on:saveSummary
        />

        <!-- Objects Section -->
        <ObjectsSection
            isExpanded={expandedSection === "objects"}
            {allShapes}
            {selectedShapeId}
            {editingDescription}
            on:toggleExpand={() => toggleSection("objects")}
            on:selectShape
            on:handleSaveDescription
        />
    </div>
</div>
