<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import type { WorkflowStepColumn, WorkflowStepRow, WorkflowSteps } from "$lib/types/workflow";

    export let workflowSteps: WorkflowSteps = { columns: [], rows: [] };
    export let expandedRowId: string | null = null;

    let addingColumn = false;
    let newColumnName = "";

    const dispatch = createEventDispatcher<{
        update: { workflowSteps: WorkflowSteps };
        toggleRowExpand: { rowId: string };
    }>();

    function addColumn() {
        if (!newColumnName.trim()) {
            alert("컬럼 이름을 입력해주세요.");
            return;
        }
        const newId = `col_${Date.now()}`;
        workflowSteps.columns = [
            ...workflowSteps.columns,
            { id: newId, name: newColumnName.trim(), isDefault: false },
        ];
        newColumnName = "";
        addingColumn = false;
        dispatch("update", { workflowSteps });
    }

    function removeColumn(columnId: string) {
        const column = workflowSteps.columns.find(c => c.id === columnId);
        if (column?.isDefault) {
            alert("기본 컬럼은 삭제할 수 없습니다.");
            return;
        }
        if (confirm("이 컬럼을 삭제하시겠습니까? 모든 row에서 해당 컬럼의 값이 삭제됩니다.")) {
            workflowSteps.columns = workflowSteps.columns.filter(c => c.id !== columnId);
            workflowSteps.rows = workflowSteps.rows.map(row => {
                const newValues = { ...row.values };
                delete newValues[columnId];
                return { ...row, values: newValues };
            });
            dispatch("update", { workflowSteps });
        }
    }

    function addRow() {
        const newId = `row_${Date.now()}`;
        const newRow: WorkflowStepRow = { id: newId, values: {} };
        workflowSteps.columns.forEach(col => {
            newRow.values[col.id] = "";
        });
        workflowSteps.rows = [...workflowSteps.rows, newRow];
        dispatch("update", { workflowSteps });
        dispatch("toggleRowExpand", { rowId: newId });
    }

    function removeRow(rowId: string) {
        if (confirm("이 스텝을 삭제하시겠습니까?")) {
            workflowSteps.rows = workflowSteps.rows.filter(r => r.id !== rowId);
            dispatch("update", { workflowSteps });
        }
    }

    function moveRowUp(index: number) {
        if (index === 0) return;
        const temp = workflowSteps.rows[index - 1];
        workflowSteps.rows[index - 1] = workflowSteps.rows[index];
        workflowSteps.rows[index] = temp;
        workflowSteps.rows = [...workflowSteps.rows];
        dispatch("update", { workflowSteps });
    }

    function moveRowDown(index: number) {
        if (index === workflowSteps.rows.length - 1) return;
        const temp = workflowSteps.rows[index + 1];
        workflowSteps.rows[index + 1] = workflowSteps.rows[index];
        workflowSteps.rows[index] = temp;
        workflowSteps.rows = [...workflowSteps.rows];
        dispatch("update", { workflowSteps });
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

    function handleColumnNameChange(columnId: string, name: string) {
        const col = workflowSteps.columns.find(c => c.id === columnId);
        if (col) {
            col.name = name;
            workflowSteps.columns = [...workflowSteps.columns];
            dispatch("update", { workflowSteps });
        }
    }

    function handleRowValueChange(rowIndex: number, columnId: string, value: string) {
        workflowSteps.rows[rowIndex].values[columnId] = value;
        dispatch("update", { workflowSteps });
    }
</script>

<div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
    <div class="flex justify-between items-center mb-4">
        <div>
            <h2 class="text-xl font-bold text-gray-800">워크플로우 스텝</h2>
            <p class="text-sm text-gray-500 mt-1">
                워크플로우에서 사용할 스텝들을 정의합니다. 기본 컬럼은 삭제할 수 없습니다.
            </p>
        </div>
        <div class="flex gap-2">
            {#if addingColumn}
                <div class="flex items-center gap-2">
                    <input
                        type="text"
                        bind:value={newColumnName}
                        placeholder="컬럼 이름"
                        class="border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        on:keydown={(e) => e.key === 'Enter' && addColumn()}
                    />
                    <button
                        class="bg-blue-600 text-white px-3 py-1.5 rounded text-sm hover:bg-blue-700"
                        on:click={addColumn}
                    >
                        추가
                    </button>
                    <button
                        class="text-gray-500 px-2 py-1.5 text-sm hover:text-gray-700"
                        on:click={() => { addingColumn = false; newColumnName = ""; }}
                    >
                        취소
                    </button>
                </div>
            {:else}
                <button
                    class="bg-gray-100 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-200 transition text-sm font-medium"
                    on:click={() => addingColumn = true}
                >
                    + 컬럼 추가
                </button>
            {/if}
            <button
                class="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition text-sm font-medium"
                on:click={addRow}
            >
                + 스텝 추가
            </button>
        </div>
    </div>

    <!-- Column Headers -->
    <div class="mb-4 border border-gray-200 rounded-lg overflow-hidden">
        <div class="bg-gray-100 px-4 py-3">
            <div class="flex items-center gap-2 flex-wrap">
                <span class="text-sm font-medium text-gray-700 mr-2">컬럼:</span>
                {#each workflowSteps.columns as column (column.id)}
                    <div class="flex items-center gap-1 bg-white rounded px-2 py-1 border {column.isDefault ? 'border-blue-300' : 'border-gray-300'}">
                        <input
                            type="text"
                            value={column.name}
                            on:input={(e) => handleColumnNameChange(column.id, e.currentTarget.value)}
                            class="border-none bg-transparent text-sm focus:outline-none w-24"
                            title={column.isDefault ? "기본 컬럼 (삭제 불가)" : "커스텀 컬럼"}
                        />
                        {#if column.isDefault}
                            <span class="text-blue-500 text-xs" title="기본 컬럼">★</span>
                        {:else}
                            <button
                                class="text-red-400 hover:text-red-600 text-xs"
                                on:click={() => removeColumn(column.id)}
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

    <!-- Rows -->
    <div class="space-y-3">
        {#if workflowSteps.rows.length === 0}
            <div class="text-center text-gray-400 py-8 border border-dashed border-gray-300 rounded-lg">
                정의된 스텝이 없습니다. 스텝을 추가해주세요.
            </div>
        {:else}
            {#each workflowSteps.rows as row, index (row.id)}
                <div class="border border-gray-200 rounded-lg bg-gray-50 overflow-hidden">
                    <!-- Row Header -->
                    <div class="flex items-center gap-3 p-4">
                        <div class="flex flex-col gap-1">
                            <button
                                class="text-gray-500 hover:text-gray-700 disabled:opacity-30 text-xs"
                                on:click={() => moveRowUp(index)}
                                disabled={index === 0}
                                title="위로 이동"
                            >
                                ▲
                            </button>
                            <button
                                class="text-gray-500 hover:text-gray-700 disabled:opacity-30 text-xs"
                                on:click={() => moveRowDown(index)}
                                disabled={index === workflowSteps.rows.length - 1}
                                title="아래로 이동"
                            >
                                ▼
                            </button>
                        </div>

                        <div class="flex-1">
                            <span class="text-sm font-medium text-gray-800">
                                {getRowPreview(row)}
                            </span>
                            <span class="text-xs text-gray-400 ml-2">ID: {row.id}</span>
                        </div>

                        <button
                            class="text-gray-500 hover:text-blue-600 px-3 py-2 rounded transition text-sm"
                            on:click={() => dispatch("toggleRowExpand", { rowId: row.id })}
                            title="상세 편집"
                        >
                            {expandedRowId === row.id ? "▼ 접기" : "▶ 편집"}
                        </button>

                        <button
                            class="bg-red-500 text-white px-3 py-2 rounded hover:bg-red-600 transition text-sm font-medium"
                            on:click={() => removeRow(row.id)}
                        >
                            삭제
                        </button>
                    </div>

                    <!-- Expanded Row Section -->
                    {#if expandedRowId === row.id}
                        <div class="border-t border-gray-200 p-4 bg-white">
                            <div class="grid grid-cols-2 gap-4">
                                {#each workflowSteps.columns as column (column.id)}
                                    <div>
                                        <label class="block text-xs font-medium text-gray-600 mb-1">
                                            {column.name}
                                            {#if column.isDefault}
                                                <span class="text-blue-500">★</span>
                                            {/if}
                                        </label>
                                        <input
                                            type="text"
                                            value={row.values[column.id] || ""}
                                            on:input={(e) => handleRowValueChange(index, column.id, e.currentTarget.value)}
                                            class="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
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
</div>
