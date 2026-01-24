<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import type {
        WorkflowDefinition,
        WorkflowSteps,
        WorkflowStepColumn,
        WorkflowStepRow,
        PhaseType,
        CoreStepsSettings,
        CoreStepInputType,
    } from "$lib/types/workflow";
    import {
        DEFAULT_WORKFLOW_COLUMNS,
        createCoreStepDefinition,
        createCoreStepPreset,
        getInputTypeDisplayName,
    } from "$lib/types/workflow";

    export let workflows: WorkflowDefinition[] = [];
    export let phaseTypes: PhaseType[] = [];
    export let expandedWorkflowId: string | null = null;
    export let expandedRowId: string | null = null;

    let addingWorkflow = false;
    let newWorkflowName = "";
    let addingColumn: string | null = null; // workflow id that is adding column
    let newColumnName = "";

    // Drag and drop state
    let draggedWorkflowIndex: number | null = null;
    let dragOverWorkflowIndex: number | null = null;

    // Core Steps UI state
    let addingCoreStep: string | null = null; // workflow id that is adding core step
    let newCoreStepName = "";
    let expandedCoreStepId: string | null = null;
    let editingPresetStepId: string | null = null;
    let newPresetName = "";
    let newPresetTypes: CoreStepInputType[] = ["text"];
    const ALL_INPUT_TYPES: CoreStepInputType[] = [
        "capture",
        "text",
        "image_clipboard",
    ];

    const dispatch = createEventDispatcher<{
        update: {
            workflows: WorkflowDefinition[];
            phaseTypes: PhaseType[];
        };
        toggleWorkflowExpand: { workflowId: string };
        toggleRowExpand: { rowId: string };
    }>();

    function emitUpdate() {
        dispatch("update", { workflows, phaseTypes });
    }

    // Workflow Management
    function addWorkflow() {
        if (!newWorkflowName.trim()) {
            alert("워크플로우 이름을 입력해주세요.");
            return;
        }
        const newWorkflow: WorkflowDefinition = {
            id: `wf_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`,
            name: newWorkflowName.trim(),
            order: workflows.length,
            steps: { columns: [...DEFAULT_WORKFLOW_COLUMNS], rows: [] },
            createdAt: new Date().toISOString(),
        };
        workflows = [...workflows, newWorkflow];
        newWorkflowName = "";
        addingWorkflow = false;
        expandedWorkflowId = newWorkflow.id;
        emitUpdate();
    }

    function removeWorkflow(workflowId: string) {
        if (confirm("이 워크플로우를 삭제하시겠습니까?")) {
            workflows = workflows
                .filter((w) => w.id !== workflowId)
                .map((w, i) => ({ ...w, order: i }));
            if (expandedWorkflowId === workflowId) {
                expandedWorkflowId = null;
            }
            emitUpdate();
        }
    }

    function moveWorkflowUp(index: number) {
        if (index === 0) return;
        const temp = workflows[index - 1];
        workflows[index - 1] = workflows[index];
        workflows[index] = temp;
        workflows = workflows.map((w, i) => ({ ...w, order: i }));
        emitUpdate();
    }

    function moveWorkflowDown(index: number) {
        if (index === workflows.length - 1) return;
        const temp = workflows[index + 1];
        workflows[index + 1] = workflows[index];
        workflows[index] = temp;
        workflows = workflows.map((w, i) => ({ ...w, order: i }));
        emitUpdate();
    }

    // Drag and drop handlers for workflow reordering
    function handleDragStart(e: DragEvent, index: number) {
        draggedWorkflowIndex = index;
        if (e.dataTransfer) {
            e.dataTransfer.effectAllowed = "move";
            e.dataTransfer.setData("text/plain", index.toString());
        }
    }

    function handleDragOver(e: DragEvent, index: number) {
        e.preventDefault();
        if (e.dataTransfer) {
            e.dataTransfer.dropEffect = "move";
        }
        dragOverWorkflowIndex = index;
    }

    function handleDragLeave() {
        dragOverWorkflowIndex = null;
    }

    function handleDrop(e: DragEvent, targetIndex: number) {
        e.preventDefault();
        if (draggedWorkflowIndex === null || draggedWorkflowIndex === targetIndex) {
            draggedWorkflowIndex = null;
            dragOverWorkflowIndex = null;
            return;
        }

        const draggedWorkflow = workflows[draggedWorkflowIndex];
        const newWorkflows = [...workflows];
        newWorkflows.splice(draggedWorkflowIndex, 1);
        newWorkflows.splice(targetIndex, 0, draggedWorkflow);
        workflows = newWorkflows.map((w, i) => ({ ...w, order: i }));

        draggedWorkflowIndex = null;
        dragOverWorkflowIndex = null;
        emitUpdate();
    }

    function handleDragEnd() {
        draggedWorkflowIndex = null;
        dragOverWorkflowIndex = null;
    }

    function handleWorkflowNameChange(workflowId: string, name: string) {
        const workflow = workflows.find((w) => w.id === workflowId);
        if (workflow) {
            workflow.name = name;
            workflows = [...workflows];
            emitUpdate();
        }
    }

    // Column Management for workflow's own steps
    function addColumn(workflowId: string) {
        if (!newColumnName.trim()) {
            alert("컬럼 이름을 입력해주세요.");
            return;
        }
        const workflow = workflows.find((w) => w.id === workflowId);
        if (!workflow || !workflow.steps) return;

        const newId = `col_${Date.now()}`;
        workflow.steps.columns = [
            ...workflow.steps.columns,
            { id: newId, name: newColumnName.trim(), isDefault: false },
        ];
        workflows = [...workflows];
        newColumnName = "";
        addingColumn = null;
        emitUpdate();
    }

    function removeColumn(workflowId: string, columnId: string) {
        const workflow = workflows.find((w) => w.id === workflowId);
        if (!workflow || !workflow.steps) return;

        const column = workflow.steps.columns.find((c) => c.id === columnId);
        if (column?.isDefault) {
            alert("기본 컬럼은 삭제할 수 없습니다.");
            return;
        }
        if (
            confirm(
                "이 컬럼을 삭제하시겠습니까? 모든 row에서 해당 컬럼의 값이 삭제됩니다.",
            )
        ) {
            workflow.steps.columns = workflow.steps.columns.filter(
                (c) => c.id !== columnId,
            );
            workflow.steps.rows = workflow.steps.rows.map((row) => {
                const newValues = { ...row.values };
                delete newValues[columnId];
                return { ...row, values: newValues };
            });
            workflows = [...workflows];
            emitUpdate();
        }
    }

    function handleColumnNameChange(
        workflowId: string,
        columnId: string,
        name: string,
    ) {
        const workflow = workflows.find((w) => w.id === workflowId);
        if (!workflow || !workflow.steps) return;

        const col = workflow.steps.columns.find((c) => c.id === columnId);
        if (col) {
            col.name = name;
            workflows = [...workflows];
            emitUpdate();
        }
    }

    // Row Management for workflow's own steps
    function addRow(workflowId: string) {
        const workflow = workflows.find((w) => w.id === workflowId);
        if (!workflow || !workflow.steps) return;

        const newId = `row_${Date.now()}`;
        const newRow: WorkflowStepRow = { id: newId, values: {} };
        workflow.steps.columns.forEach((col) => {
            newRow.values[col.id] = "";
        });
        workflow.steps.rows = [...workflow.steps.rows, newRow];
        workflows = [...workflows];
        expandedRowId = newId;
        emitUpdate();
    }

    function removeRow(workflowId: string, rowId: string) {
        if (confirm("이 스텝을 삭제하시겠습니까?")) {
            const workflow = workflows.find((w) => w.id === workflowId);
            if (!workflow || !workflow.steps) return;

            workflow.steps.rows = workflow.steps.rows.filter(
                (r) => r.id !== rowId,
            );
            workflows = [...workflows];
            emitUpdate();
        }
    }

    function moveRowUp(workflowId: string, index: number) {
        const workflow = workflows.find((w) => w.id === workflowId);
        if (!workflow || !workflow.steps || index === 0) return;

        const temp = workflow.steps.rows[index - 1];
        workflow.steps.rows[index - 1] = workflow.steps.rows[index];
        workflow.steps.rows[index] = temp;
        workflow.steps.rows = [...workflow.steps.rows];
        workflows = [...workflows];
        emitUpdate();
    }

    function moveRowDown(workflowId: string, index: number) {
        const workflow = workflows.find((w) => w.id === workflowId);
        if (!workflow || !workflow.steps) return;
        if (index === workflow.steps.rows.length - 1) return;

        const temp = workflow.steps.rows[index + 1];
        workflow.steps.rows[index + 1] = workflow.steps.rows[index];
        workflow.steps.rows[index] = temp;
        workflow.steps.rows = [...workflow.steps.rows];
        workflows = [...workflows];
        emitUpdate();
    }

    function handleRowValueChange(
        workflowId: string,
        rowIndex: number,
        columnId: string,
        value: string,
    ) {
        const workflow = workflows.find((w) => w.id === workflowId);
        if (!workflow || !workflow.steps) return;

        workflow.steps.rows[rowIndex].values[columnId] = value;
        workflows = [...workflows];
        emitUpdate();
    }

    function getRowPreview(row: WorkflowStepRow): string {
        const stepCategory = row.values["step_category"];
        const purpose = row.values["purpose"];

        if (stepCategory && purpose) {
            return `[${stepCategory}] ${purpose}`;
        } else if (stepCategory) {
            return `[${stepCategory}]`;
        } else if (purpose) {
            return purpose;
        }
        return "(비어있음)";
    }

    // Core Steps Management
    function addCoreStep(workflowId: string) {
        if (!newCoreStepName.trim()) {
            alert("Core Step 이름을 입력해주세요.");
            return;
        }
        const workflow = workflows.find((w) => w.id === workflowId);
        if (!workflow) return;

        if (!workflow.coreSteps) {
            workflow.coreSteps = { definitions: [] };
        }

        const newDef = createCoreStepDefinition(newCoreStepName.trim());
        workflow.coreSteps.definitions = [
            ...workflow.coreSteps.definitions,
            newDef,
        ];
        workflows = [...workflows];
        newCoreStepName = "";
        addingCoreStep = null;
        expandedCoreStepId = newDef.id;
        emitUpdate();
    }

    function removeCoreStep(workflowId: string, stepId: string) {
        if (confirm("이 Core Step을 삭제하시겠습니까?")) {
            const workflow = workflows.find((w) => w.id === workflowId);
            if (!workflow || !workflow.coreSteps) return;

            workflow.coreSteps.definitions =
                workflow.coreSteps.definitions.filter((d) => d.id !== stepId);
            workflows = [...workflows];
            if (expandedCoreStepId === stepId) {
                expandedCoreStepId = null;
            }
            emitUpdate();
        }
    }

    function moveCoreStepUp(workflowId: string, index: number) {
        if (index === 0) return;
        const workflow = workflows.find((w) => w.id === workflowId);
        if (!workflow || !workflow.coreSteps) return;

        const temp = workflow.coreSteps.definitions[index - 1];
        workflow.coreSteps.definitions[index - 1] =
            workflow.coreSteps.definitions[index];
        workflow.coreSteps.definitions[index] = temp;
        workflow.coreSteps.definitions = [...workflow.coreSteps.definitions];
        workflows = [...workflows];
        emitUpdate();
    }

    function moveCoreStepDown(workflowId: string, index: number) {
        const workflow = workflows.find((w) => w.id === workflowId);
        if (!workflow || !workflow.coreSteps) return;
        if (index === workflow.coreSteps.definitions.length - 1) return;

        const temp = workflow.coreSteps.definitions[index + 1];
        workflow.coreSteps.definitions[index + 1] =
            workflow.coreSteps.definitions[index];
        workflow.coreSteps.definitions[index] = temp;
        workflow.coreSteps.definitions = [...workflow.coreSteps.definitions];
        workflows = [...workflows];
        emitUpdate();
    }

    function handleCoreStepNameChange(
        workflowId: string,
        stepId: string,
        name: string,
    ) {
        const workflow = workflows.find((w) => w.id === workflowId);
        if (!workflow || !workflow.coreSteps) return;

        const step = workflow.coreSteps.definitions.find(
            (d) => d.id === stepId,
        );
        if (step) {
            step.name = name;
            workflows = [...workflows];
            emitUpdate();
        }
    }

    function addPreset(workflowId: string, stepId: string) {
        if (!newPresetName.trim()) {
            alert("Preset 이름을 입력해주세요.");
            return;
        }
        if (newPresetTypes.length === 0) {
            alert("허용 형식을 최소 하나 선택해주세요.");
            return;
        }

        const workflow = workflows.find((w) => w.id === workflowId);
        if (!workflow || !workflow.coreSteps) return;

        const step = workflow.coreSteps.definitions.find(
            (d) => d.id === stepId,
        );
        if (step) {
            const order = step.presets.length;
            const newPreset = createCoreStepPreset(
                newPresetName.trim(),
                newPresetTypes,
                order,
            );
            step.presets = [...step.presets, newPreset];
            workflows = [...workflows];
            newPresetName = "";
            newPresetTypes = ["text"];
            editingPresetStepId = null;
            emitUpdate();
        }
    }

    function removePreset(
        workflowId: string,
        stepId: string,
        presetId: string,
    ) {
        if (confirm("이 Preset을 삭제하시겠습니까?")) {
            const workflow = workflows.find((w) => w.id === workflowId);
            if (!workflow || !workflow.coreSteps) return;

            const step = workflow.coreSteps.definitions.find(
                (d) => d.id === stepId,
            );
            if (step) {
                step.presets = step.presets.filter((p) => p.id !== presetId);
                step.presets = step.presets.map((p, i) => ({ ...p, order: i }));
                workflows = [...workflows];
                emitUpdate();
            }
        }
    }

    function movePresetUp(
        workflowId: string,
        stepId: string,
        presetIndex: number,
    ) {
        if (presetIndex === 0) return;
        const workflow = workflows.find((w) => w.id === workflowId);
        if (!workflow || !workflow.coreSteps) return;

        const step = workflow.coreSteps.definitions.find(
            (d) => d.id === stepId,
        );
        if (step) {
            const temp = step.presets[presetIndex - 1];
            step.presets[presetIndex - 1] = step.presets[presetIndex];
            step.presets[presetIndex] = temp;
            step.presets = step.presets.map((p, i) => ({ ...p, order: i }));
            workflows = [...workflows];
            emitUpdate();
        }
    }

    function movePresetDown(
        workflowId: string,
        stepId: string,
        presetIndex: number,
    ) {
        const workflow = workflows.find((w) => w.id === workflowId);
        if (!workflow || !workflow.coreSteps) return;

        const step = workflow.coreSteps.definitions.find(
            (d) => d.id === stepId,
        );
        if (step && presetIndex < step.presets.length - 1) {
            const temp = step.presets[presetIndex + 1];
            step.presets[presetIndex + 1] = step.presets[presetIndex];
            step.presets[presetIndex] = temp;
            step.presets = step.presets.map((p, i) => ({ ...p, order: i }));
            workflows = [...workflows];
            emitUpdate();
        }
    }

    function handlePresetNameChange(
        workflowId: string,
        stepId: string,
        presetId: string,
        name: string,
    ) {
        const workflow = workflows.find((w) => w.id === workflowId);
        if (!workflow || !workflow.coreSteps) return;

        const step = workflow.coreSteps.definitions.find(
            (d) => d.id === stepId,
        );
        if (step) {
            const preset = step.presets.find((p) => p.id === presetId);
            if (preset) {
                preset.name = name;
                workflows = [...workflows];
                emitUpdate();
            }
        }
    }

    function togglePresetType(
        workflowId: string,
        stepId: string,
        presetId: string,
        type: CoreStepInputType,
    ) {
        const workflow = workflows.find((w) => w.id === workflowId);
        if (!workflow || !workflow.coreSteps) return;

        const step = workflow.coreSteps.definitions.find(
            (d) => d.id === stepId,
        );
        if (step) {
            const preset = step.presets.find((p) => p.id === presetId);
            if (preset) {
                if (preset.allowedTypes.includes(type)) {
                    if (preset.allowedTypes.length > 1) {
                        preset.allowedTypes = preset.allowedTypes.filter(
                            (t) => t !== type,
                        );
                    }
                } else {
                    preset.allowedTypes = [...preset.allowedTypes, type];
                }
                workflows = [...workflows];
                emitUpdate();
            }
        }
    }

    function toggleNewPresetType(type: CoreStepInputType) {
        if (newPresetTypes.includes(type)) {
            if (newPresetTypes.length > 1) {
                newPresetTypes = newPresetTypes.filter((t) => t !== type);
            }
        } else {
            newPresetTypes = [...newPresetTypes, type];
        }
    }

    function toggleRequiresKeyStepLinking(workflowId: string, stepId: string) {
        const workflow = workflows.find((w) => w.id === workflowId);
        if (!workflow || !workflow.coreSteps) return;

        const step = workflow.coreSteps.definitions.find(
            (d) => d.id === stepId,
        );
        if (step) {
            step.requiresKeyStepLinking = !step.requiresKeyStepLinking;
            workflows = [...workflows];
            emitUpdate();
        }
    }
</script>

<div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
    <div class="flex justify-between items-center mb-4">
        <div>
            <h2 class="text-xl font-bold text-gray-800">워크플로우 정의</h2>
            <p class="text-sm text-gray-500 mt-1">
                프로젝트에서 사용할 워크플로우를 정의합니다. 각 워크플로우는
                독립적인 스텝을 가질 수 있습니다.
            </p>
        </div>
        {#if addingWorkflow}
            <div class="flex items-center gap-2">
                <input
                    type="text"
                    bind:value={newWorkflowName}
                    placeholder="워크플로우 이름"
                    class="border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    on:keydown={(e) => e.key === "Enter" && addWorkflow()}
                />
                <button
                    class="bg-blue-600 text-white px-3 py-1.5 rounded text-sm hover:bg-blue-700"
                    on:click={addWorkflow}
                >
                    추가
                </button>
                <button
                    class="text-gray-500 px-2 py-1.5 text-sm hover:text-gray-700"
                    on:click={() => {
                        addingWorkflow = false;
                        newWorkflowName = "";
                    }}
                >
                    취소
                </button>
            </div>
        {:else}
            <button
                class="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition text-sm font-medium"
                on:click={() => (addingWorkflow = true)}
            >
                + 워크플로우 추가
            </button>
        {/if}
    </div>

    <!-- Workflows List -->
    <div class="space-y-4">
        {#if workflows.length === 0}
            <div
                class="text-center text-gray-400 py-8 border border-dashed border-gray-300 rounded-lg"
            >
                정의된 워크플로우가 없습니다. 워크플로우를 추가해주세요.
            </div>
        {:else}
            {#each workflows as workflow, index (workflow.id)}
                <div
                    class="border rounded-lg bg-gray-50 overflow-hidden transition-all duration-200
                        {draggedWorkflowIndex === index ? 'opacity-50 border-gray-400' : 'border-gray-200'}
                        {dragOverWorkflowIndex === index && draggedWorkflowIndex !== index ? 'border-blue-500 border-2 bg-blue-50/30' : ''}"
                    draggable="true"
                    on:dragstart={(e) => handleDragStart(e, index)}
                    on:dragover={(e) => handleDragOver(e, index)}
                    on:dragleave={handleDragLeave}
                    on:drop={(e) => handleDrop(e, index)}
                    on:dragend={handleDragEnd}
                >
                    <!-- Workflow Header -->
                    <div
                        class="flex items-center gap-3 p-4 bg-white border-b border-gray-100"
                    >
                        <!-- Drag Handle -->
                        <div
                            class="flex flex-col items-center justify-center w-6 h-8 cursor-grab active:cursor-grabbing text-gray-400 hover:text-gray-600 select-none"
                            title="드래그하여 순서 변경"
                        >
                            <span class="text-lg leading-none tracking-widest">⋮⋮</span>
                        </div>

                        <div class="flex-1 flex items-center gap-3">
                            {#if index === 0}
                                <span class="text-xs px-2 py-0.5 rounded bg-amber-100 text-amber-700 font-medium border border-amber-300">
                                    대표 워크플로우
                                </span>
                            {/if}
                            <input
                                type="text"
                                value={workflow.name}
                                on:input={(e) =>
                                    handleWorkflowNameChange(
                                        workflow.id,
                                        e.currentTarget.value,
                                    )}
                                class="border border-gray-300 rounded px-3 py-1.5 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-blue-500 w-48"
                            />
                            <span class="text-xs text-gray-400">
                                {workflow.steps?.rows?.length || 0} 스텝
                            </span>
                        </div>

                        <button
                            class="text-gray-500 hover:text-blue-600 px-3 py-2 rounded transition text-sm"
                            on:click={() =>
                                dispatch("toggleWorkflowExpand", {
                                    workflowId: workflow.id,
                                })}
                            title="상세 편집"
                        >
                            {expandedWorkflowId === workflow.id
                                ? "▼ 접기"
                                : "▶ 편집"}
                        </button>

                        <button
                            class="bg-red-500 text-white px-3 py-2 rounded hover:bg-red-600 transition text-sm font-medium"
                            on:click={() => removeWorkflow(workflow.id)}
                        >
                            삭제
                        </button>
                    </div>

                    <!-- Expanded Workflow Section -->
                    {#if expandedWorkflowId === workflow.id}
                        <div class="p-4 space-y-4">
                            <!-- Core Steps Section -->
                            <div
                                class="border border-purple-200 rounded-lg bg-purple-50/30 p-4"
                            >
                                <div
                                    class="flex justify-between items-center mb-3"
                                >
                                    <div>
                                        <h4
                                            class="text-sm font-semibold text-purple-800"
                                        >
                                            Core Step 정의
                                        </h4>
                                        <p
                                            class="text-xs text-purple-600 mt-0.5"
                                        >
                                            이 워크플로우에서 사용할 Core Step을
                                            정의합니다.
                                        </p>
                                    </div>
                                    {#if addingCoreStep === workflow.id}
                                        <div class="flex items-center gap-2">
                                            <input
                                                type="text"
                                                bind:value={newCoreStepName}
                                                placeholder="Core Step 이름"
                                                class="border border-gray-300 rounded px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-purple-500"
                                                on:keydown={(e) =>
                                                    e.key === "Enter" &&
                                                    addCoreStep(workflow.id)}
                                            />
                                            <button
                                                class="bg-purple-600 text-white px-2 py-1 rounded text-xs hover:bg-purple-700"
                                                on:click={() =>
                                                    addCoreStep(workflow.id)}
                                            >
                                                추가
                                            </button>
                                            <button
                                                class="text-gray-500 px-1 py-1 text-xs hover:text-gray-700"
                                                on:click={() => {
                                                    addingCoreStep = null;
                                                    newCoreStepName = "";
                                                }}
                                            >
                                                취소
                                            </button>
                                        </div>
                                    {:else}
                                        <button
                                            class="bg-purple-600 text-white px-3 py-1.5 rounded text-xs hover:bg-purple-700"
                                            on:click={() =>
                                                (addingCoreStep = workflow.id)}
                                        >
                                            + Core Step 추가
                                        </button>
                                    {/if}
                                </div>

                                <!-- Core Step List -->
                                <div class="space-y-2">
                                    {#if !workflow.coreSteps?.definitions?.length}
                                        <div
                                            class="text-center text-purple-400 py-4 border border-dashed border-purple-300 rounded-lg text-xs bg-white"
                                        >
                                            정의된 Core Step이 없습니다.
                                        </div>
                                    {:else}
                                        {#each workflow.coreSteps.definitions as coreStep, csIndex (coreStep.id)}
                                            <div
                                                class="border border-purple-200 rounded-lg bg-white overflow-hidden"
                                            >
                                                <!-- Core Step Header -->
                                                <div
                                                    class="flex items-center gap-2 p-3"
                                                >
                                                    <div
                                                        class="flex flex-col gap-0.5"
                                                    >
                                                        <button
                                                            class="text-gray-400 hover:text-gray-600 disabled:opacity-30 text-[10px]"
                                                            on:click={() =>
                                                                moveCoreStepUp(
                                                                    workflow.id,
                                                                    csIndex,
                                                                )}
                                                            disabled={csIndex ===
                                                                0}
                                                        >
                                                            ▲
                                                        </button>
                                                        <button
                                                            class="text-gray-400 hover:text-gray-600 disabled:opacity-30 text-[10px]"
                                                            on:click={() =>
                                                                moveCoreStepDown(
                                                                    workflow.id,
                                                                    csIndex,
                                                                )}
                                                            disabled={csIndex ===
                                                                workflow
                                                                    .coreSteps
                                                                    .definitions
                                                                    .length -
                                                                    1}
                                                        >
                                                            ▼
                                                        </button>
                                                    </div>

                                                    <div
                                                        class="w-6 h-6 rounded-full bg-purple-600 flex items-center justify-center text-white font-bold text-xs"
                                                    >
                                                        C
                                                    </div>

                                                    <div class="flex-1">
                                                        <div
                                                            class="flex items-center gap-2"
                                                        >
                                                            <input
                                                                type="text"
                                                                value={coreStep.name}
                                                                on:input={(e) =>
                                                                    handleCoreStepNameChange(
                                                                        workflow.id,
                                                                        coreStep.id,
                                                                        e
                                                                            .currentTarget
                                                                            .value,
                                                                    )}
                                                                class="bg-transparent border border-gray-200 rounded px-2 py-1 text-sm font-medium text-gray-800 focus:outline-none focus:ring-2 focus:ring-purple-500"
                                                            />
                                                            <span
                                                                class="text-xs text-gray-400"
                                                            >
                                                                Preset {coreStep
                                                                    .presets
                                                                    .length}개
                                                            </span>
                                                        </div>
                                                        <label
                                                            class="flex items-center gap-1 mt-1 cursor-pointer group"
                                                        >
                                                            <input
                                                                type="checkbox"
                                                                checked={coreStep.requiresKeyStepLinking ??
                                                                    false}
                                                                on:change={() =>
                                                                    toggleRequiresKeyStepLinking(
                                                                        workflow.id,
                                                                        coreStep.id,
                                                                    )}
                                                                class="w-3 h-3 text-purple-600 rounded border-gray-300 focus:ring-purple-500 cursor-pointer"
                                                            />
                                                            <span
                                                                class="text-[10px] text-gray-500 group-hover:text-gray-700"
                                                                >핵심 step 연결
                                                                필요</span
                                                            >
                                                            <span
                                                                class="text-[9px] text-gray-400 cursor-help"
                                                                title="이 옵션을 켜면 워크플로우 확정 시 이 Core Step에 대해 핵심적인 역할을 한 이전 스텝들을 연결해야 합니다."
                                                            >
                                                                (?)
                                                            </span>
                                                        </label>
                                                    </div>

                                                    <button
                                                        class="text-gray-400 hover:text-purple-600 px-2 py-1 text-xs"
                                                        on:click={() =>
                                                            (expandedCoreStepId =
                                                                expandedCoreStepId ===
                                                                coreStep.id
                                                                    ? null
                                                                    : coreStep.id)}
                                                    >
                                                        {expandedCoreStepId ===
                                                        coreStep.id
                                                            ? "▼ 접기"
                                                            : "▶ 편집"}
                                                    </button>

                                                    <button
                                                        class="text-red-400 hover:text-red-600 px-2 py-1 text-xs"
                                                        on:click={() =>
                                                            removeCoreStep(
                                                                workflow.id,
                                                                coreStep.id,
                                                            )}
                                                    >
                                                        삭제
                                                    </button>
                                                </div>

                                                <!-- Expanded Core Step Presets -->
                                                {#if expandedCoreStepId === coreStep.id}
                                                    <div
                                                        class="border-t border-purple-100 p-3 bg-purple-50/50"
                                                    >
                                                        <h5
                                                            class="text-xs font-semibold text-gray-700 mb-2"
                                                        >
                                                            Preset 필드 (필수
                                                            입력 항목)
                                                        </h5>

                                                        <!-- Preset List -->
                                                        <div
                                                            class="space-y-2 mb-3"
                                                        >
                                                            {#if coreStep.presets.length === 0}
                                                                <div
                                                                    class="text-xs text-gray-400 py-3 text-center border border-dashed border-gray-300 rounded bg-white"
                                                                >
                                                                    정의된
                                                                    Preset이
                                                                    없습니다.
                                                                </div>
                                                            {:else}
                                                                {#each coreStep.presets as preset, pIndex (preset.id)}
                                                                    <div
                                                                        class="flex items-center gap-2 p-2 bg-white rounded border border-gray-200"
                                                                    >
                                                                        <div
                                                                            class="flex flex-col gap-0.5"
                                                                        >
                                                                            <button
                                                                                class="text-gray-400 hover:text-gray-600 disabled:opacity-30 text-[10px]"
                                                                                on:click={() =>
                                                                                    movePresetUp(
                                                                                        workflow.id,
                                                                                        coreStep.id,
                                                                                        pIndex,
                                                                                    )}
                                                                                disabled={pIndex ===
                                                                                    0}
                                                                            >
                                                                                ▲
                                                                            </button>
                                                                            <button
                                                                                class="text-gray-400 hover:text-gray-600 disabled:opacity-30 text-[10px]"
                                                                                on:click={() =>
                                                                                    movePresetDown(
                                                                                        workflow.id,
                                                                                        coreStep.id,
                                                                                        pIndex,
                                                                                    )}
                                                                                disabled={pIndex ===
                                                                                    coreStep
                                                                                        .presets
                                                                                        .length -
                                                                                        1}
                                                                            >
                                                                                ▼
                                                                            </button>
                                                                        </div>

                                                                        <span
                                                                            class="text-xs text-gray-400 w-4"
                                                                            >{pIndex +
                                                                                1}.</span
                                                                        >

                                                                        <input
                                                                            type="text"
                                                                            value={preset.name}
                                                                            on:input={(
                                                                                e,
                                                                            ) =>
                                                                                handlePresetNameChange(
                                                                                    workflow.id,
                                                                                    coreStep.id,
                                                                                    preset.id,
                                                                                    e
                                                                                        .currentTarget
                                                                                        .value,
                                                                                )}
                                                                            class="flex-1 border border-gray-300 rounded px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-purple-500"
                                                                            placeholder="Preset 이름"
                                                                        />

                                                                        <div
                                                                            class="flex gap-1"
                                                                        >
                                                                            {#each ALL_INPUT_TYPES as type}
                                                                                <button
                                                                                    class="px-1.5 py-0.5 text-[10px] rounded border transition
                                                                                        {preset.allowedTypes.includes(
                                                                                        type,
                                                                                    )
                                                                                        ? 'bg-purple-100 border-purple-400 text-purple-700'
                                                                                        : 'bg-gray-100 border-gray-300 text-gray-500 hover:bg-gray-200'}"
                                                                                    on:click={() =>
                                                                                        togglePresetType(
                                                                                            workflow.id,
                                                                                            coreStep.id,
                                                                                            preset.id,
                                                                                            type,
                                                                                        )}
                                                                                    title="{getInputTypeDisplayName(
                                                                                        type,
                                                                                    )} {preset.allowedTypes.includes(
                                                                                        type,
                                                                                    )
                                                                                        ? '비활성화'
                                                                                        : '활성화'}"
                                                                                >
                                                                                    {getInputTypeDisplayName(
                                                                                        type,
                                                                                    )}
                                                                                </button>
                                                                            {/each}
                                                                        </div>

                                                                        <button
                                                                            class="text-red-400 hover:text-red-600 px-1 py-0.5"
                                                                            on:click={() =>
                                                                                removePreset(
                                                                                    workflow.id,
                                                                                    coreStep.id,
                                                                                    preset.id,
                                                                                )}
                                                                            title="Preset 삭제"
                                                                        >
                                                                            ✕
                                                                        </button>
                                                                    </div>
                                                                {/each}
                                                            {/if}
                                                        </div>

                                                        <!-- Add New Preset -->
                                                        {#if editingPresetStepId === coreStep.id}
                                                            <div
                                                                class="p-2 bg-purple-100/50 rounded border border-purple-200"
                                                            >
                                                                <div
                                                                    class="flex items-center gap-2"
                                                                >
                                                                    <input
                                                                        type="text"
                                                                        bind:value={
                                                                            newPresetName
                                                                        }
                                                                        placeholder="Preset 이름"
                                                                        class="flex-1 border border-gray-300 rounded px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-purple-500"
                                                                        on:keydown={(
                                                                            e,
                                                                        ) =>
                                                                            e.key ===
                                                                                "Enter" &&
                                                                            addPreset(
                                                                                workflow.id,
                                                                                coreStep.id,
                                                                            )}
                                                                    />
                                                                </div>
                                                                <div
                                                                    class="mt-2 flex items-center gap-2"
                                                                >
                                                                    <span
                                                                        class="text-[10px] text-gray-600"
                                                                        >허용
                                                                        형식:</span
                                                                    >
                                                                    {#each ALL_INPUT_TYPES as type}
                                                                        <button
                                                                            class="px-1.5 py-0.5 text-[10px] rounded border transition
                                                                                {newPresetTypes.includes(
                                                                                type,
                                                                            )
                                                                                ? 'bg-purple-100 border-purple-400 text-purple-700'
                                                                                : 'bg-gray-100 border-gray-300 text-gray-500 hover:bg-gray-200'}"
                                                                            on:click={() =>
                                                                                toggleNewPresetType(
                                                                                    type,
                                                                                )}
                                                                        >
                                                                            {getInputTypeDisplayName(
                                                                                type,
                                                                            )}
                                                                        </button>
                                                                    {/each}
                                                                    <div
                                                                        class="flex-1"
                                                                    ></div>
                                                                    <button
                                                                        class="bg-purple-600 text-white px-2 py-0.5 rounded text-[10px] hover:bg-purple-700"
                                                                        on:click={() =>
                                                                            addPreset(
                                                                                workflow.id,
                                                                                coreStep.id,
                                                                            )}
                                                                    >
                                                                        추가
                                                                    </button>
                                                                    <button
                                                                        class="text-gray-500 px-1 py-0.5 text-[10px] hover:text-gray-700"
                                                                        on:click={() => {
                                                                            editingPresetStepId =
                                                                                null;
                                                                            newPresetName =
                                                                                "";
                                                                            newPresetTypes =
                                                                                [
                                                                                    "text",
                                                                                ];
                                                                        }}
                                                                    >
                                                                        취소
                                                                    </button>
                                                                </div>
                                                            </div>
                                                        {:else}
                                                            <button
                                                                class="w-full py-1.5 border border-dashed border-purple-300 rounded text-purple-600 hover:bg-purple-50 transition text-xs"
                                                                on:click={() => {
                                                                    editingPresetStepId =
                                                                        coreStep.id;
                                                                    newPresetName =
                                                                        "";
                                                                    newPresetTypes =
                                                                        [
                                                                            "text",
                                                                        ];
                                                                }}
                                                            >
                                                                + Preset 추가
                                                            </button>
                                                        {/if}
                                                    </div>
                                                {/if}
                                            </div>
                                        {/each}
                                    {/if}
                                </div>
                            </div>

                            {#if workflow.steps}
                                <!-- Column Headers -->
                                <div
                                    class="border border-gray-200 rounded-lg overflow-hidden"
                                >
                                    <div class="bg-gray-100 px-4 py-3">
                                        <div
                                            class="flex items-center justify-between mb-2"
                                        >
                                            <span
                                                class="text-sm font-medium text-gray-700"
                                                >컬럼 정의:</span
                                            >
                                            {#if addingColumn === workflow.id}
                                                <div
                                                    class="flex items-center gap-2"
                                                >
                                                    <input
                                                        type="text"
                                                        bind:value={
                                                            newColumnName
                                                        }
                                                        placeholder="컬럼 이름"
                                                        class="border border-gray-300 rounded px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
                                                        on:keydown={(e) =>
                                                            e.key === "Enter" &&
                                                            addColumn(
                                                                workflow.id,
                                                            )}
                                                    />
                                                    <button
                                                        class="bg-blue-600 text-white px-2 py-1 rounded text-xs hover:bg-blue-700"
                                                        on:click={() =>
                                                            addColumn(
                                                                workflow.id,
                                                            )}
                                                    >
                                                        추가
                                                    </button>
                                                    <button
                                                        class="text-gray-500 px-1 py-1 text-xs hover:text-gray-700"
                                                        on:click={() => {
                                                            addingColumn = null;
                                                            newColumnName = "";
                                                        }}
                                                    >
                                                        취소
                                                    </button>
                                                </div>
                                            {:else}
                                                <button
                                                    class="text-xs text-blue-600 hover:text-blue-700"
                                                    on:click={() =>
                                                        (addingColumn =
                                                            workflow.id)}
                                                >
                                                    + 컬럼 추가
                                                </button>
                                            {/if}
                                        </div>
                                        <div
                                            class="flex items-center gap-2 flex-wrap"
                                        >
                                            {#each workflow.steps.columns as column (column.id)}
                                                <div
                                                    class="flex items-center gap-1 bg-white rounded px-2 py-1 border {column.isDefault
                                                        ? 'border-blue-300'
                                                        : 'border-gray-300'}"
                                                >
                                                    <input
                                                        type="text"
                                                        value={column.name}
                                                        on:input={(e) =>
                                                            handleColumnNameChange(
                                                                workflow.id,
                                                                column.id,
                                                                e.currentTarget
                                                                    .value,
                                                            )}
                                                        class="border-none bg-transparent text-xs focus:outline-none w-20"
                                                        title={column.isDefault
                                                            ? "기본 컬럼 (삭제 불가)"
                                                            : "커스텀 컬럼"}
                                                    />
                                                    {#if column.isDefault}
                                                        <span
                                                            class="text-blue-500 text-xs"
                                                            title="기본 컬럼"
                                                            >★</span
                                                        >
                                                    {:else}
                                                        <button
                                                            class="text-red-400 hover:text-red-600 text-xs"
                                                            on:click={() =>
                                                                removeColumn(
                                                                    workflow.id,
                                                                    column.id,
                                                                )}
                                                            title="컬럼 삭제"
                                                        >
                                                            ✕
                                                        </button>
                                                    {/if}
                                                </div>
                                            {/each}
                                        </div>
                                    </div>
                                </div>

                                <!-- Steps (Rows) -->
                                <div class="space-y-2">
                                    <div
                                        class="flex justify-between items-center"
                                    >
                                        <span
                                            class="text-sm font-medium text-gray-700"
                                            >스텝 정의:</span
                                        >
                                        <button
                                            class="bg-green-600 text-white px-3 py-1.5 rounded text-xs hover:bg-green-700"
                                            on:click={() => addRow(workflow.id)}
                                        >
                                            + 스텝 추가
                                        </button>
                                    </div>

                                    {#if workflow.steps.rows.length === 0}
                                        <div
                                            class="text-center text-gray-400 py-6 border border-dashed border-gray-300 rounded-lg text-sm"
                                        >
                                            정의된 스텝이 없습니다. 스텝을
                                            추가해주세요.
                                        </div>
                                    {:else}
                                        {#each workflow.steps.rows as row, rowIndex (row.id)}
                                            <div
                                                class="border border-gray-200 rounded-lg bg-white overflow-hidden"
                                            >
                                                <!-- Row Header -->
                                                <div
                                                    class="flex items-center gap-2 p-3"
                                                >
                                                    <div
                                                        class="flex flex-col gap-0.5"
                                                    >
                                                        <button
                                                            class="text-gray-400 hover:text-gray-600 disabled:opacity-30 text-[10px]"
                                                            on:click={() =>
                                                                moveRowUp(
                                                                    workflow.id,
                                                                    rowIndex,
                                                                )}
                                                            disabled={rowIndex ===
                                                                0}
                                                        >
                                                            ▲
                                                        </button>
                                                        <button
                                                            class="text-gray-400 hover:text-gray-600 disabled:opacity-30 text-[10px]"
                                                            on:click={() =>
                                                                moveRowDown(
                                                                    workflow.id,
                                                                    rowIndex,
                                                                )}
                                                            disabled={rowIndex ===
                                                                workflow.steps
                                                                    .rows
                                                                    .length -
                                                                    1}
                                                        >
                                                            ▼
                                                        </button>
                                                    </div>

                                                    <div class="flex-1">
                                                        <span
                                                            class="text-sm text-gray-700"
                                                        >
                                                            {getRowPreview(row)}
                                                        </span>
                                                    </div>

                                                    <button
                                                        class="text-gray-400 hover:text-blue-600 px-2 py-1 text-xs"
                                                        on:click={() =>
                                                            dispatch(
                                                                "toggleRowExpand",
                                                                {
                                                                    rowId: row.id,
                                                                },
                                                            )}
                                                    >
                                                        {expandedRowId ===
                                                        row.id
                                                            ? "▼ 접기"
                                                            : "▶ 편집"}
                                                    </button>

                                                    <button
                                                        class="text-red-400 hover:text-red-600 px-2 py-1 text-xs"
                                                        on:click={() =>
                                                            removeRow(
                                                                workflow.id,
                                                                row.id,
                                                            )}
                                                    >
                                                        삭제
                                                    </button>
                                                </div>

                                                <!-- Expanded Row Section -->
                                                {#if expandedRowId === row.id}
                                                    <div
                                                        class="border-t border-gray-100 p-3 bg-gray-50"
                                                    >
                                                        <div
                                                            class="grid grid-cols-2 gap-3"
                                                        >
                                                            {#each workflow.steps.columns as column (column.id)}
                                                                <div>
                                                                    <label
                                                                        class="block text-xs font-medium text-gray-500 mb-1"
                                                                    >
                                                                        {column.name}
                                                                        {#if column.isDefault}
                                                                            <span
                                                                                class="text-blue-500"
                                                                                >★</span
                                                                            >
                                                                        {/if}
                                                                    </label>
                                                                    <input
                                                                        type="text"
                                                                        value={row
                                                                            .values[
                                                                            column
                                                                                .id
                                                                        ] || ""}
                                                                        on:input={(
                                                                            e,
                                                                        ) =>
                                                                            handleRowValueChange(
                                                                                workflow.id,
                                                                                rowIndex,
                                                                                column.id,
                                                                                e
                                                                                    .currentTarget
                                                                                    .value,
                                                                            )}
                                                                        class="w-full border border-gray-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                                                                        placeholder="{column.name} 입력"
                                                                    />
                                                                </div>
                                                            {/each}
                                                        </div>
                                                    </div>
                                                {/if}
                                            </div>
                                        {/each}
                                    {/if}
                                </div>
                            {/if}
                        </div>
                    {/if}
                </div>
            {/each}
        {/if}
    </div>
</div>
