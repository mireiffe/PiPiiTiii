<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import type {
        WorkflowDefinition,
        WorkflowSteps,
        WorkflowStepColumn,
        WorkflowStepRow,
        PhaseType
    } from "$lib/types/workflow";
    import { DEFAULT_WORKFLOW_COLUMNS } from "$lib/types/workflow";

    export let workflows: WorkflowDefinition[] = [];
    export let phaseTypes: PhaseType[] = [];
    export let globalStepsLabel: string = "발생현상";
    export let expandedWorkflowId: string | null = null;
    export let expandedRowId: string | null = null;

    let addingWorkflow = false;
    let newWorkflowName = "";
    let addingColumn: string | null = null;  // workflow id that is adding column
    let newColumnName = "";

    const dispatch = createEventDispatcher<{
        update: { workflows: WorkflowDefinition[]; phaseTypes: PhaseType[]; globalStepsLabel: string };
        toggleWorkflowExpand: { workflowId: string };
        toggleRowExpand: { rowId: string };
    }>();

    function emitUpdate() {
        dispatch("update", { workflows, phaseTypes, globalStepsLabel });
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
            useGlobalSteps: false,
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
                .filter(w => w.id !== workflowId)
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

    function handleWorkflowNameChange(workflowId: string, name: string) {
        const workflow = workflows.find(w => w.id === workflowId);
        if (workflow) {
            workflow.name = name;
            workflows = [...workflows];
            emitUpdate();
        }
    }

    function toggleUseGlobalSteps(workflowId: string) {
        const workflow = workflows.find(w => w.id === workflowId);
        if (workflow) {
            workflow.useGlobalSteps = !workflow.useGlobalSteps;
            if (!workflow.useGlobalSteps && !workflow.steps) {
                workflow.steps = { columns: [...DEFAULT_WORKFLOW_COLUMNS], rows: [] };
            }
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
        const workflow = workflows.find(w => w.id === workflowId);
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
        const workflow = workflows.find(w => w.id === workflowId);
        if (!workflow || !workflow.steps) return;

        const column = workflow.steps.columns.find(c => c.id === columnId);
        if (column?.isDefault) {
            alert("기본 컬럼은 삭제할 수 없습니다.");
            return;
        }
        if (confirm("이 컬럼을 삭제하시겠습니까? 모든 row에서 해당 컬럼의 값이 삭제됩니다.")) {
            workflow.steps.columns = workflow.steps.columns.filter(c => c.id !== columnId);
            workflow.steps.rows = workflow.steps.rows.map(row => {
                const newValues = { ...row.values };
                delete newValues[columnId];
                return { ...row, values: newValues };
            });
            workflows = [...workflows];
            emitUpdate();
        }
    }

    function handleColumnNameChange(workflowId: string, columnId: string, name: string) {
        const workflow = workflows.find(w => w.id === workflowId);
        if (!workflow || !workflow.steps) return;

        const col = workflow.steps.columns.find(c => c.id === columnId);
        if (col) {
            col.name = name;
            workflows = [...workflows];
            emitUpdate();
        }
    }

    // Row Management for workflow's own steps
    function addRow(workflowId: string) {
        const workflow = workflows.find(w => w.id === workflowId);
        if (!workflow || !workflow.steps) return;

        const newId = `row_${Date.now()}`;
        const newRow: WorkflowStepRow = { id: newId, values: {} };
        workflow.steps.columns.forEach(col => {
            newRow.values[col.id] = "";
        });
        workflow.steps.rows = [...workflow.steps.rows, newRow];
        workflows = [...workflows];
        expandedRowId = newId;
        emitUpdate();
    }

    function removeRow(workflowId: string, rowId: string) {
        if (confirm("이 스텝을 삭제하시겠습니까?")) {
            const workflow = workflows.find(w => w.id === workflowId);
            if (!workflow || !workflow.steps) return;

            workflow.steps.rows = workflow.steps.rows.filter(r => r.id !== rowId);
            workflows = [...workflows];
            emitUpdate();
        }
    }

    function moveRowUp(workflowId: string, index: number) {
        const workflow = workflows.find(w => w.id === workflowId);
        if (!workflow || !workflow.steps || index === 0) return;

        const temp = workflow.steps.rows[index - 1];
        workflow.steps.rows[index - 1] = workflow.steps.rows[index];
        workflow.steps.rows[index] = temp;
        workflow.steps.rows = [...workflow.steps.rows];
        workflows = [...workflows];
        emitUpdate();
    }

    function moveRowDown(workflowId: string, index: number) {
        const workflow = workflows.find(w => w.id === workflowId);
        if (!workflow || !workflow.steps) return;
        if (index === workflow.steps.rows.length - 1) return;

        const temp = workflow.steps.rows[index + 1];
        workflow.steps.rows[index + 1] = workflow.steps.rows[index];
        workflow.steps.rows[index] = temp;
        workflow.steps.rows = [...workflow.steps.rows];
        workflows = [...workflows];
        emitUpdate();
    }

    function handleRowValueChange(workflowId: string, rowIndex: number, columnId: string, value: string) {
        const workflow = workflows.find(w => w.id === workflowId);
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
</script>

<div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
    <div class="flex justify-between items-center mb-4">
        <div>
            <h2 class="text-xl font-bold text-gray-800">워크플로우 정의</h2>
            <p class="text-sm text-gray-500 mt-1">
                프로젝트에서 사용할 워크플로우를 정의합니다. 각 워크플로우는 독립적인 스텝을 가질 수 있습니다.
            </p>
        </div>
        {#if addingWorkflow}
            <div class="flex items-center gap-2">
                <input
                    type="text"
                    bind:value={newWorkflowName}
                    placeholder="워크플로우 이름"
                    class="border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    on:keydown={(e) => e.key === 'Enter' && addWorkflow()}
                />
                <button
                    class="bg-blue-600 text-white px-3 py-1.5 rounded text-sm hover:bg-blue-700"
                    on:click={addWorkflow}
                >
                    추가
                </button>
                <button
                    class="text-gray-500 px-2 py-1.5 text-sm hover:text-gray-700"
                    on:click={() => { addingWorkflow = false; newWorkflowName = ""; }}
                >
                    취소
                </button>
            </div>
        {:else}
            <button
                class="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition text-sm font-medium"
                on:click={() => addingWorkflow = true}
            >
                + 워크플로우 추가
            </button>
        {/if}
    </div>

    <!-- Workflows List -->
    <div class="space-y-4">
        {#if workflows.length === 0}
            <div class="text-center text-gray-400 py-8 border border-dashed border-gray-300 rounded-lg">
                정의된 워크플로우가 없습니다. 워크플로우를 추가해주세요.
            </div>
        {:else}
            {#each workflows as workflow, index (workflow.id)}
                <div class="border border-gray-200 rounded-lg bg-gray-50 overflow-hidden">
                    <!-- Workflow Header -->
                    <div class="flex items-center gap-3 p-4 bg-white border-b border-gray-100">
                        <div class="flex flex-col gap-1">
                            <button
                                class="text-gray-500 hover:text-gray-700 disabled:opacity-30 text-xs"
                                on:click={() => moveWorkflowUp(index)}
                                disabled={index === 0}
                                title="위로 이동"
                            >
                                ▲
                            </button>
                            <button
                                class="text-gray-500 hover:text-gray-700 disabled:opacity-30 text-xs"
                                on:click={() => moveWorkflowDown(index)}
                                disabled={index === workflows.length - 1}
                                title="아래로 이동"
                            >
                                ▼
                            </button>
                        </div>

                        <div class="flex-1 flex items-center gap-3">
                            <input
                                type="text"
                                value={workflow.name}
                                on:input={(e) => handleWorkflowNameChange(workflow.id, e.currentTarget.value)}
                                class="border border-gray-300 rounded px-3 py-1.5 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-blue-500 w-48"
                            />
                            <span class="text-xs text-gray-400">
                                {workflow.steps?.rows?.length || 0} 스텝
                            </span>
                            <span class="text-xs px-2 py-0.5 rounded {workflow.useGlobalSteps ? 'bg-blue-100 text-blue-600' : 'bg-purple-100 text-purple-600'}">
                                {workflow.useGlobalSteps ? '글로벌 스텝 사용' : '독립 스텝'}
                            </span>
                        </div>

                        <button
                            class="text-gray-500 hover:text-blue-600 px-3 py-2 rounded transition text-sm"
                            on:click={() => dispatch("toggleWorkflowExpand", { workflowId: workflow.id })}
                            title="상세 편집"
                        >
                            {expandedWorkflowId === workflow.id ? "▼ 접기" : "▶ 편집"}
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
                            <!-- Use Global Steps Toggle -->
                            <div class="flex items-center gap-3 p-3 bg-blue-50 rounded-lg border border-blue-200">
                                <label class="flex items-center gap-2 cursor-pointer">
                                    <input
                                        type="checkbox"
                                        checked={workflow.useGlobalSteps}
                                        on:change={() => toggleUseGlobalSteps(workflow.id)}
                                        class="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                                    />
                                    <span class="text-sm text-gray-700">글로벌 스텝 사용 (발생현상과 동일한 스텝 정의 사용)</span>
                                </label>
                            </div>

                            {#if !workflow.useGlobalSteps && workflow.steps}
                                <!-- Column Headers -->
                                <div class="border border-gray-200 rounded-lg overflow-hidden">
                                    <div class="bg-gray-100 px-4 py-3">
                                        <div class="flex items-center justify-between mb-2">
                                            <span class="text-sm font-medium text-gray-700">컬럼 정의:</span>
                                            {#if addingColumn === workflow.id}
                                                <div class="flex items-center gap-2">
                                                    <input
                                                        type="text"
                                                        bind:value={newColumnName}
                                                        placeholder="컬럼 이름"
                                                        class="border border-gray-300 rounded px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
                                                        on:keydown={(e) => e.key === 'Enter' && addColumn(workflow.id)}
                                                    />
                                                    <button
                                                        class="bg-blue-600 text-white px-2 py-1 rounded text-xs hover:bg-blue-700"
                                                        on:click={() => addColumn(workflow.id)}
                                                    >
                                                        추가
                                                    </button>
                                                    <button
                                                        class="text-gray-500 px-1 py-1 text-xs hover:text-gray-700"
                                                        on:click={() => { addingColumn = null; newColumnName = ""; }}
                                                    >
                                                        취소
                                                    </button>
                                                </div>
                                            {:else}
                                                <button
                                                    class="text-xs text-blue-600 hover:text-blue-700"
                                                    on:click={() => addingColumn = workflow.id}
                                                >
                                                    + 컬럼 추가
                                                </button>
                                            {/if}
                                        </div>
                                        <div class="flex items-center gap-2 flex-wrap">
                                            {#each workflow.steps.columns as column (column.id)}
                                                <div class="flex items-center gap-1 bg-white rounded px-2 py-1 border {column.isDefault ? 'border-blue-300' : 'border-gray-300'}">
                                                    <input
                                                        type="text"
                                                        value={column.name}
                                                        on:input={(e) => handleColumnNameChange(workflow.id, column.id, e.currentTarget.value)}
                                                        class="border-none bg-transparent text-xs focus:outline-none w-20"
                                                        title={column.isDefault ? "기본 컬럼 (삭제 불가)" : "커스텀 컬럼"}
                                                    />
                                                    {#if column.isDefault}
                                                        <span class="text-blue-500 text-xs" title="기본 컬럼">★</span>
                                                    {:else}
                                                        <button
                                                            class="text-red-400 hover:text-red-600 text-xs"
                                                            on:click={() => removeColumn(workflow.id, column.id)}
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
                                    <div class="flex justify-between items-center">
                                        <span class="text-sm font-medium text-gray-700">스텝 정의:</span>
                                        <button
                                            class="bg-green-600 text-white px-3 py-1.5 rounded text-xs hover:bg-green-700"
                                            on:click={() => addRow(workflow.id)}
                                        >
                                            + 스텝 추가
                                        </button>
                                    </div>

                                    {#if workflow.steps.rows.length === 0}
                                        <div class="text-center text-gray-400 py-6 border border-dashed border-gray-300 rounded-lg text-sm">
                                            정의된 스텝이 없습니다. 스텝을 추가해주세요.
                                        </div>
                                    {:else}
                                        {#each workflow.steps.rows as row, rowIndex (row.id)}
                                            <div class="border border-gray-200 rounded-lg bg-white overflow-hidden">
                                                <!-- Row Header -->
                                                <div class="flex items-center gap-2 p-3">
                                                    <div class="flex flex-col gap-0.5">
                                                        <button
                                                            class="text-gray-400 hover:text-gray-600 disabled:opacity-30 text-[10px]"
                                                            on:click={() => moveRowUp(workflow.id, rowIndex)}
                                                            disabled={rowIndex === 0}
                                                        >
                                                            ▲
                                                        </button>
                                                        <button
                                                            class="text-gray-400 hover:text-gray-600 disabled:opacity-30 text-[10px]"
                                                            on:click={() => moveRowDown(workflow.id, rowIndex)}
                                                            disabled={rowIndex === workflow.steps.rows.length - 1}
                                                        >
                                                            ▼
                                                        </button>
                                                    </div>

                                                    <div class="flex-1">
                                                        <span class="text-sm text-gray-700">
                                                            {getRowPreview(row)}
                                                        </span>
                                                    </div>

                                                    <button
                                                        class="text-gray-400 hover:text-blue-600 px-2 py-1 text-xs"
                                                        on:click={() => dispatch("toggleRowExpand", { rowId: row.id })}
                                                    >
                                                        {expandedRowId === row.id ? "▼ 접기" : "▶ 편집"}
                                                    </button>

                                                    <button
                                                        class="text-red-400 hover:text-red-600 px-2 py-1 text-xs"
                                                        on:click={() => removeRow(workflow.id, row.id)}
                                                    >
                                                        삭제
                                                    </button>
                                                </div>

                                                <!-- Expanded Row Section -->
                                                {#if expandedRowId === row.id}
                                                    <div class="border-t border-gray-100 p-3 bg-gray-50">
                                                        <div class="grid grid-cols-2 gap-3">
                                                            {#each workflow.steps.columns as column (column.id)}
                                                                <div>
                                                                    <label class="block text-xs font-medium text-gray-500 mb-1">
                                                                        {column.name}
                                                                        {#if column.isDefault}
                                                                            <span class="text-blue-500">★</span>
                                                                        {/if}
                                                                    </label>
                                                                    <input
                                                                        type="text"
                                                                        value={row.values[column.id] || ""}
                                                                        on:input={(e) => handleRowValueChange(workflow.id, rowIndex, column.id, e.currentTarget.value)}
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
