<script lang="ts">
    import { slide, fly } from "svelte/transition";
    import { createEventDispatcher } from "svelte";
    import type { WorkflowSteps, WorkflowStepRow, WorkflowStepColumn } from "$lib/types/workflow";

    export let workflowSteps: WorkflowSteps;
    export let getStepUsageCount: (stepId: string) => number;

    const dispatch = createEventDispatcher<{
        addStep: WorkflowStepRow;
        deleteStepDefinition: { stepId: string };
        createStepDefinition: { values: Record<string, string> };
        updateStepDefinition: { stepId: string; values: Record<string, string> };
        close: void;
    }>();

    let searchQuery = "";
    let selectedCategoryTab = "all";
    let showNewStepForm = false;
    let newStepValues: Record<string, string> = {};
    let editingStepDefId: string | null = null;
    let editStepValues: Record<string, string> = {};

    $: categories = [
        ...new Set(
            workflowSteps.rows
                .map((r) => r.values["step_category"])
                .filter(Boolean)
        ),
    ];

    $: filteredSteps = workflowSteps.rows.filter((row) => {
        if (selectedCategoryTab !== "all") {
            if (row.values["step_category"] !== selectedCategoryTab) return false;
        }
        if (searchQuery.trim()) {
            const query = searchQuery.toLowerCase();
            return Object.values(row.values).some((v) =>
                v?.toLowerCase().includes(query)
            );
        }
        return true;
    });

    function initNewStepForm() {
        newStepValues = {};
        workflowSteps.columns.forEach((col) => {
            newStepValues[col.id] = "";
        });
        showNewStepForm = true;
        editingStepDefId = null;
    }

    function handleAddNewStep() {
        if (!newStepValues["purpose"]?.trim()) {
            alert("목적을 입력해주세요.");
            return;
        }

        const trimmedValues: Record<string, string> = {};
        Object.keys(newStepValues).forEach((key) => {
            trimmedValues[key] = newStepValues[key]?.trim() || "";
        });

        dispatch("createStepDefinition", { values: trimmedValues });
        newStepValues = {};
        showNewStepForm = false;
    }

    function cancelNewStepForm() {
        newStepValues = {};
        showNewStepForm = false;
    }

    function initEditStepForm(stepRow: WorkflowStepRow, event: MouseEvent) {
        event.stopPropagation();
        editStepValues = { ...stepRow.values };
        editingStepDefId = stepRow.id;
        showNewStepForm = false;
    }

    function handleUpdateStepDef() {
        if (!editingStepDefId) return;

        if (!editStepValues["purpose"]?.trim()) {
            alert("목적을 입력해주세요.");
            return;
        }

        const trimmedValues: Record<string, string> = {};
        Object.keys(editStepValues).forEach((key) => {
            trimmedValues[key] = editStepValues[key]?.trim() || "";
        });

        dispatch("updateStepDefinition", {
            stepId: editingStepDefId,
            values: trimmedValues,
        });

        editStepValues = {};
        editingStepDefId = null;
    }

    function cancelEditStepForm() {
        editStepValues = {};
        editingStepDefId = null;
    }

    function handleDeleteStepFromPopup(event: MouseEvent, stepRow: WorkflowStepRow) {
        event.stopPropagation();
        const usageCount = getStepUsageCount(stepRow.id);

        if (usageCount > 0) {
            alert(
                `이 스텝은 워크플로우에서 ${usageCount}번 사용 중입니다.\n설정 페이지에서 직접 삭제해주세요.`
            );
            return;
        }

        if (
            confirm(
                "이 스텝 정의를 설정에서 삭제하시겠습니까?\n(모든 프로젝트에서 이 스텝을 사용할 수 없게 됩니다)"
            )
        ) {
            dispatch("deleteStepDefinition", { stepId: stepRow.id });
            dispatch("close");
        }
    }

    function handleSelectStep(step: WorkflowStepRow) {
        dispatch("addStep", step);
        dispatch("close");
    }
</script>

<div
    class="absolute top-full left-3 right-3 mt-1 bg-white rounded-lg shadow-xl border border-gray-200 z-50 flex flex-col max-h-[600px] overflow-hidden"
    transition:fly={{ y: -10, duration: 150 }}
    on:click|stopPropagation
>
    <!-- Search & Category Tabs -->
    <div class="p-2 border-b border-gray-100 bg-gray-50/80 backdrop-blur sticky top-0">
        <div class="relative mb-1.5">
            <svg
                class="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
            >
                <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
            </svg>
            <input
                type="text"
                bind:value={searchQuery}
                placeholder="작업 검색..."
                class="w-full pl-8 pr-2 py-1.5 text-xs bg-white border border-gray-200 rounded focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all"
                autofocus
            />
        </div>
        <div class="flex gap-1 overflow-x-auto no-scrollbar pb-0.5">
            <button
                class="px-2 py-0.5 text-[10px] font-medium rounded-full whitespace-nowrap transition-colors {selectedCategoryTab === 'all'
                    ? 'bg-gray-700 text-white'
                    : 'bg-white border border-gray-200 text-gray-500 hover:bg-gray-50'}"
                on:click={() => (selectedCategoryTab = "all")}
            >
                All
            </button>
            {#each categories as category}
                <button
                    class="px-2 py-0.5 text-[10px] font-medium rounded-full whitespace-nowrap transition-colors {selectedCategoryTab === category
                        ? 'bg-blue-600 text-white'
                        : 'bg-white border border-gray-200 text-gray-500 hover:bg-gray-50'}"
                    on:click={() => (selectedCategoryTab = category)}
                >
                    {category}
                </button>
            {/each}
        </div>
    </div>

    <!-- Step List -->
    <div class="flex-1 overflow-y-auto p-2 bg-gray-50/50 space-y-1.5">
        <!-- New Step Form -->
        {#if showNewStepForm}
            <div
                class="p-3 bg-blue-50 border border-blue-200 rounded-lg space-y-2.5"
                transition:slide={{ duration: 150 }}
            >
                <div class="text-xs font-medium text-blue-700">새 스텝 추가</div>
                <div class="space-y-2">
                    {#each workflowSteps.columns as column (column.id)}
                        <div class="flex items-center gap-2">
                            <label class="text-[10px] text-gray-500 w-16 shrink-0 text-right">
                                {column.name}
                                {#if column.id === "purpose"}
                                    <span class="text-red-500">*</span>
                                {/if}
                            </label>
                            <input
                                type="text"
                                bind:value={newStepValues[column.id]}
                                placeholder={column.name}
                                class="flex-1 px-2 py-1 text-xs border border-blue-200 rounded focus:outline-none focus:ring-1 focus:ring-blue-400 bg-white"
                                on:keydown={(e) => e.key === "Enter" && handleAddNewStep()}
                            />
                        </div>
                    {/each}
                </div>
                <div class="flex justify-end gap-2 pt-1">
                    <button
                        class="px-2.5 py-1 text-[10px] text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded transition-colors"
                        on:click={cancelNewStepForm}
                    >
                        취소
                    </button>
                    <button
                        class="px-2.5 py-1 text-[10px] bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors font-medium"
                        on:click={handleAddNewStep}
                    >
                        추가
                    </button>
                </div>
            </div>
        {:else}
            <button
                class="w-full p-2 border border-dashed border-blue-300 rounded-lg text-blue-500 hover:bg-blue-50 hover:border-blue-400 transition-all flex items-center justify-center gap-1 text-xs"
                on:click={initNewStepForm}
            >
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                </svg>
                새 스텝 정의 추가
            </button>
        {/if}

        {#if filteredSteps.length === 0 && !showNewStepForm}
            <div class="py-6 text-center text-gray-400">
                <p class="text-[10px]">일치하는 스텝이 없습니다</p>
            </div>
        {:else}
            {#each filteredSteps as step, idx (step.id)}
                {@const usageCount = getStepUsageCount(step.id)}
                {@const isEditing = editingStepDefId === step.id}

                {#if isEditing}
                    <!-- Edit Step Form -->
                    <div
                        class="p-3 bg-amber-50 border border-amber-200 rounded-lg space-y-2.5"
                        transition:slide={{ duration: 150 }}
                        on:click|stopPropagation
                    >
                        <div class="text-xs font-medium text-amber-700 flex items-center gap-1.5">
                            <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" />
                                <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" />
                            </svg>
                            스텝 정의 편집
                        </div>
                        <div class="space-y-2">
                            {#each workflowSteps.columns as column (column.id)}
                                <div class="flex items-center gap-2">
                                    <label class="text-[10px] text-gray-500 w-16 shrink-0 text-right">
                                        {column.name}
                                        {#if column.id === "purpose"}
                                            <span class="text-red-500">*</span>
                                        {/if}
                                    </label>
                                    <input
                                        type="text"
                                        bind:value={editStepValues[column.id]}
                                        placeholder={column.name}
                                        class="flex-1 px-2 py-1 text-xs border border-amber-200 rounded focus:outline-none focus:ring-1 focus:ring-amber-400 bg-white"
                                        on:keydown={(e) => e.key === "Enter" && handleUpdateStepDef()}
                                    />
                                </div>
                            {/each}
                        </div>
                        <div class="flex justify-end gap-2 pt-1">
                            <button
                                class="px-2.5 py-1 text-[10px] text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded transition-colors"
                                on:click={cancelEditStepForm}
                            >
                                취소
                            </button>
                            <button
                                class="px-2.5 py-1 text-[10px] bg-amber-600 text-white rounded hover:bg-amber-700 transition-colors font-medium"
                                on:click={handleUpdateStepDef}
                            >
                                저장
                            </button>
                        </div>
                    </div>
                {:else}
                    <!-- Step Row -->
                    <div
                        class="w-full text-left p-2.5 bg-white hover:bg-blue-50/80 rounded-lg group transition-all flex items-start gap-2.5 cursor-pointer border border-gray-100 hover:border-blue-200 hover:shadow-sm"
                        on:click={() => handleSelectStep(step)}
                    >
                        <div class="flex-1 min-w-0">
                            <div class="flex items-start gap-1.5 mb-1">
                                <span
                                    class="inline-flex items-center justify-center px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 font-bold tracking-tight shrink-0 text-[9px] whitespace-nowrap"
                                >
                                    {step.values["step_category"] || "ETC"}
                                </span>
                                <span class="text-xs font-medium text-gray-800 group-hover:text-blue-700 break-words leading-snug flex-1">
                                    {workflowSteps.columns
                                    .filter(col => col.id !== "step_category" && col.id !== "purpose")
                                    .map(col => step.values[col.id])
                                    .filter(Boolean)
                                    .join(" / ") || "-"}
                                </span>
                            </div>
                            <div class="text-[10px] text-gray-400 pl-0.5 break-words leading-snug line-clamp-2">
                                {step.values["purpose"] || "목적 없음"}                              
                            </div>
                        </div>

                        <div class="flex items-center gap-1.5 shrink-0 self-center">
                            {#if usageCount > 0}
                                <span class="text-[9px] px-1.5 py-0.5 rounded-full bg-green-100 text-green-700 font-medium whitespace-nowrap">
                                    {usageCount}회 사용
                                </span>
                            {/if}
                            <!-- Edit button -->
                            <button
                                class="p-1 hover:bg-blue-100 rounded text-gray-300 hover:text-blue-500 transition-colors"
                                on:click={(e) => initEditStepForm(step, e)}
                                title="스텝 정의 편집"
                            >
                                <svg class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" />
                                    <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" />
                                </svg>
                            </button>
                            <!-- Delete button -->
                            {#if usageCount > 0}
                                <span class="p-1 text-gray-200 cursor-not-allowed" title="사용 중인 스텝은 설정에서 삭제해주세요" on:click|stopPropagation>
                                    <svg class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <path d="M12 15v2m0 0v2m0-2h2m-2 0H10m9.364-9.364l-2.829 2.829m0 0L14.5 12.5m2.036-2.035a3 3 0 10-4.07 4.07m4.07-4.07l-4.07 4.07M5.636 5.636l2.829 2.829m0 0l2.035 2.035m-2.035-2.035a3 3 0 104.07 4.07" />
                                    </svg>
                                </span>
                            {:else}
                                <button
                                    class="p-1 hover:bg-red-100 rounded text-gray-300 hover:text-red-500 transition-colors"
                                    on:click={(e) => handleDeleteStepFromPopup(e, step)}
                                    title="스텝 정의 삭제"
                                >
                                    <svg class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <path d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                    </svg>
                                </button>
                            {/if}
                        </div>
                    </div>
                {/if}
            {/each}
        {/if}
    </div>
</div>

<style>
    .no-scrollbar::-webkit-scrollbar {
        display: none;
    }
    .no-scrollbar {
        -ms-overflow-style: none;
        scrollbar-width: none;
    }
</style>
