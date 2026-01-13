<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import { slide } from "svelte/transition";
    import type {
        PhenomenonData,
        CandidateCause,
        TodoItem,
        TodoType,
        ConditionStatus,
        ActionCapture,
        CaptureEvidence,
    } from "$lib/types/phenomenon";
    import { createActionCapture, EVIDENCE_COLORS } from "$lib/types/phenomenon";

    export let phenomenon: PhenomenonData;
    export let workflowActions: { id: string; name: string; params: any[] }[] = [];
    export let workflowConditions: { id: string; name: string; params: any[] }[] = [];

    // Capture mode props - passed from parent for action captures
    export let captureMode = false;
    export let captureModeActionId: string | null = null;

    // Manage local UI state
    let activeCauseId: string | null = null;
    let isAddingTodo = false;
    let newTodoText = "";
    let newTodoType: TodoType = "action";
    let selectedPredefinedItem: { id: string; name: string; params: any[] } | null = null;
    let paramValues: Record<string, string> = {};

    // Inline editing state
    let editingTodoId: string | null = null;
    let editingTodoText = "";

    // Drag-and-drop state for todo items
    let draggingTodoId: string | null = null;
    let dragOverTodoId: string | null = null;

    // Drag-and-drop state for cause candidates
    let draggingCauseId: string | null = null;
    let dragOverCauseId: string | null = null;

    const dispatch = createEventDispatcher<{
        change: PhenomenonData;
        workflowComplete: { finalCauseId: string };
        toggleActionCaptureMode: { todoId: string | null };
    }>();

    // Action capture state
    let expandedCapturesTodoId: string | null = null;

    // Ensure todoList exists for all causes
    $: {
        if (phenomenon.candidateCauses) {
            let changed = false;
            phenomenon.candidateCauses.forEach((cause) => {
                if (!cause.todoList) {
                    cause.todoList = [];
                    changed = true;
                }
            });
            if (changed) {
                // We don't dispatch here to avoid loops, just local mutation is fine if references are kept,
                // but strictly we should probably update properly.
                // However, since we modify the object in place, Svelte might not react unless we reassign.
                phenomenon.candidateCauses = [...phenomenon.candidateCauses];
            }
        }
    }

    function moveCause(index: number, direction: "up" | "down") {
        if (!phenomenon.candidateCauses) return;
        const newIndex = direction === "up" ? index - 1 : index + 1;
        if (newIndex < 0 || newIndex >= phenomenon.candidateCauses.length)
            return;

        const causes = [...phenomenon.candidateCauses];
        const [moved] = causes.splice(index, 1);
        causes.splice(newIndex, 0, moved);

        phenomenon.candidateCauses = causes;
        dispatch("change", phenomenon);
    }

    function toggleActiveCause(id: string) {
        activeCauseId = activeCauseId === id ? null : id;
        isAddingTodo = false;
        newTodoText = "";
    }

    function startAddTodo(type: TodoType) {
        newTodoType = type;
        isAddingTodo = true;
        newTodoText = "";
        selectedPredefinedItem = null;
        paramValues = {};
    }

    function cancelAddTodo() {
        isAddingTodo = false;
        newTodoText = "";
        selectedPredefinedItem = null;
        paramValues = {};
    }

    function saveNewTodo() {
        if (!newTodoText.trim() || !activeCauseId) return;

        const cause = phenomenon.candidateCauses.find(
            (c) => c.id === activeCauseId,
        );
        if (!cause) return;

        const newTodo: TodoItem = {
            id: `todo_${Date.now()}`,
            type: newTodoType,
            text: newTodoText.trim(),
            isCompleted: false,
        };

        // Add parameter values if any were collected
        if (Object.keys(paramValues).length > 0) {
            newTodo.paramValues = { ...paramValues };
        }

        cause.todoList = [...(cause.todoList || []), newTodo];
        phenomenon.candidateCauses = [...phenomenon.candidateCauses];
        dispatch("change", phenomenon);

        newTodoText = "";
        selectedPredefinedItem = null;
        paramValues = {};
        isAddingTodo = false;
    }

    function removeTodo(todoId: string) {
        if (!activeCauseId) return;
        const cause = phenomenon.candidateCauses.find(
            (c) => c.id === activeCauseId,
        );
        if (!cause || !cause.todoList) return;

        cause.todoList = cause.todoList.filter((t) => t.id !== todoId);
        phenomenon.candidateCauses = [...phenomenon.candidateCauses];
        dispatch("change", phenomenon);
    }

    function handleKeyDown(e: KeyboardEvent) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            saveNewTodo();
        } else if (e.key === "Escape") {
            cancelAddTodo();
        }
    }

    // ===== Inline editing functions =====
    function startEditTodo(todo: TodoItem) {
        editingTodoId = todo.id;
        editingTodoText = todo.text;
    }

    function cancelEditTodo() {
        editingTodoId = null;
        editingTodoText = "";
    }

    function saveEditTodo() {
        if (!editingTodoId || !editingTodoText.trim() || !activeCauseId) {
            cancelEditTodo();
            return;
        }

        const cause = phenomenon.candidateCauses.find(
            (c) => c.id === activeCauseId,
        );
        if (!cause || !cause.todoList) {
            cancelEditTodo();
            return;
        }

        const todo = cause.todoList.find((t) => t.id === editingTodoId);
        if (todo) {
            todo.text = editingTodoText.trim();
            phenomenon.candidateCauses = [...phenomenon.candidateCauses];
            dispatch("change", phenomenon);
        }

        cancelEditTodo();
    }

    function handleEditKeyDown(e: KeyboardEvent) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            saveEditTodo();
        } else if (e.key === "Escape") {
            cancelEditTodo();
        }
    }

    // ===== Drag-and-drop functions for todo items =====
    function handleTodoDragStart(e: DragEvent, todoId: string) {
        draggingTodoId = todoId;
        if (e.dataTransfer) {
            e.dataTransfer.effectAllowed = "move";
            e.dataTransfer.setData("text/plain", todoId);
        }
    }

    function handleTodoDragOver(e: DragEvent, todoId: string) {
        e.preventDefault();
        if (e.dataTransfer) {
            e.dataTransfer.dropEffect = "move";
        }
        dragOverTodoId = todoId;
    }

    function handleTodoDragLeave(e: DragEvent) {
        dragOverTodoId = null;
    }

    function handleTodoDrop(e: DragEvent, targetTodoId: string) {
        e.preventDefault();
        dragOverTodoId = null;

        if (!draggingTodoId || draggingTodoId === targetTodoId || !activeCauseId)
            return;

        const cause = phenomenon.candidateCauses.find(
            (c) => c.id === activeCauseId,
        );
        if (!cause || !cause.todoList) return;

        const todoList = [...cause.todoList];
        const dragIndex = todoList.findIndex((t) => t.id === draggingTodoId);
        const targetIndex = todoList.findIndex((t) => t.id === targetTodoId);

        if (dragIndex === -1 || targetIndex === -1) return;

        const [draggedItem] = todoList.splice(dragIndex, 1);
        todoList.splice(targetIndex, 0, draggedItem);

        cause.todoList = todoList;
        phenomenon.candidateCauses = [...phenomenon.candidateCauses];
        dispatch("change", phenomenon);

        draggingTodoId = null;
    }

    function handleTodoDragEnd() {
        draggingTodoId = null;
        dragOverTodoId = null;
    }

    // ===== Drag-and-drop functions for cause candidates =====
    function handleCauseDragStart(e: DragEvent, causeId: string) {
        draggingCauseId = causeId;
        if (e.dataTransfer) {
            e.dataTransfer.effectAllowed = "move";
            e.dataTransfer.setData("text/plain", causeId);
        }
    }

    function handleCauseDragOver(e: DragEvent, causeId: string) {
        e.preventDefault();
        if (e.dataTransfer) {
            e.dataTransfer.dropEffect = "move";
        }
        dragOverCauseId = causeId;
    }

    function handleCauseDragLeave(e: DragEvent) {
        dragOverCauseId = null;
    }

    function handleCauseDrop(e: DragEvent, targetCauseId: string) {
        e.preventDefault();
        dragOverCauseId = null;

        if (!draggingCauseId || draggingCauseId === targetCauseId) return;

        const causes = [...phenomenon.candidateCauses];
        const dragIndex = causes.findIndex((c) => c.id === draggingCauseId);
        const targetIndex = causes.findIndex((c) => c.id === targetCauseId);

        if (dragIndex === -1 || targetIndex === -1) return;

        const [draggedCause] = causes.splice(dragIndex, 1);
        causes.splice(targetIndex, 0, draggedCause);

        phenomenon.candidateCauses = causes;
        dispatch("change", phenomenon);

        draggingCauseId = null;
    }

    function handleCauseDragEnd() {
        draggingCauseId = null;
        dragOverCauseId = null;
    }

    // ===== Predefined action/condition selection =====
    function selectPredefinedItem(item: { id: string; name: string; params: any[] }) {
        selectedPredefinedItem = item;
        newTodoText = item.name;

        // Initialize param values with empty strings
        paramValues = {};
        if (item.params) {
            item.params.forEach(param => {
                paramValues[param.id] = "";
            });
        }
    }

    // ===== Condition status toggle =====
    function toggleConditionStatus(todoId: string, newStatus: ConditionStatus) {
        if (!activeCauseId) return;
        const cause = phenomenon.candidateCauses.find(
            (c) => c.id === activeCauseId,
        );
        if (!cause || !cause.todoList) return;

        const todo = cause.todoList.find((t) => t.id === todoId);
        if (todo && todo.type === 'condition') {
            // Toggle: if already same status, set to null (미설정)
            todo.conditionStatus = todo.conditionStatus === newStatus ? null : newStatus;
            phenomenon.candidateCauses = [...phenomenon.candidateCauses];
            dispatch("change", phenomenon);
        }
    }

    // 원인후보의 전체 상태를 계산 (모든 condition이 설정되었는지, active인지)
    function getCauseStatus(cause: CandidateCause): 'active' | 'inactive' | 'pending' {
        if (!cause.todoList) return 'pending';

        const conditions = cause.todoList.filter(t => t.type === 'condition');
        if (conditions.length === 0) return 'pending';

        // 하나라도 false(inactive)가 있으면 전체가 inactive
        const hasInactive = conditions.some(c => c.conditionStatus === 'false');
        if (hasInactive) return 'inactive';

        // 모든 condition이 true면 active
        const allActive = conditions.every(c => c.conditionStatus === 'true');
        if (allActive) return 'active';

        return 'pending';
    }

    // 우선순위를 고려한 효과적인 상태 계산
    // 상위 원인후보가 제외되면 자동으로 다음 후보가 active로 표시됨
    function getEffectiveCauseStatus(cause: CandidateCause, index: number): 'active' | 'inactive' | 'pending' {
        const baseStatus = getCauseStatus(cause);

        // 이미 inactive면 그대로 유지
        if (baseStatus === 'inactive') return 'inactive';

        // 상위 모든 원인후보가 inactive인지 확인
        const allPreviousInactive = phenomenon.candidateCauses
            .slice(0, index)
            .every(c => getCauseStatus(c) === 'inactive');

        // 상위가 모두 inactive이고, 현재 cause가 첫 번째 non-inactive면 active로 표시
        if (allPreviousInactive && baseStatus === 'pending') {
            return 'active';
        }

        return baseStatus;
    }

    // ===== Workflow finalization =====
    function finalizeCause(causeId: string) {
        phenomenon.finalCauseId = causeId;
        phenomenon.workflowCompleted = true;
        phenomenon.candidateCauses = [...phenomenon.candidateCauses];
        dispatch("change", phenomenon);
        dispatch("workflowComplete", { finalCauseId: causeId });
    }

    // [추가됨] 원인 지목 철회 함수
    function revokeFinalCause() {
        phenomenon.finalCauseId = null;
        phenomenon.workflowCompleted = false;
        phenomenon.candidateCauses = [...phenomenon.candidateCauses];
        dispatch("change", phenomenon);
    }

    // Reactive: get predefined items based on current todo type
    $: predefinedItems = newTodoType === "condition" ? workflowConditions : workflowActions;

    // ===== Action Capture Functions =====

    // Get phenomenon captures for linking
    $: phenomenonCaptures = (phenomenon.evidences || []).filter(
        (e): e is CaptureEvidence => e.type === 'capture'
    );

    function toggleCapturesExpand(todoId: string) {
        expandedCapturesTodoId = expandedCapturesTodoId === todoId ? null : todoId;
    }

    function toggleCaptureLink(todoId: string, captureId: string) {
        if (!activeCauseId) return;
        const cause = phenomenon.candidateCauses.find(c => c.id === activeCauseId);
        if (!cause || !cause.todoList) return;

        const todo = cause.todoList.find(t => t.id === todoId);
        if (!todo) return;

        if (!todo.captures) {
            todo.captures = [];
        }

        const existingIdx = todo.captures.findIndex(c => c.id === captureId);
        if (existingIdx >= 0) {
            // Remove
            todo.captures.splice(existingIdx, 1);
        } else {
            // Add - copy capture data from phenomenon
            const phenomenonCapture = phenomenonCaptures.find(c => c.id === captureId);
            if (phenomenonCapture) {
                const actionCapture: ActionCapture = {
                    id: captureId, // Use same ID to link
                    slideIndex: phenomenonCapture.slideIndex,
                    x: phenomenonCapture.x,
                    y: phenomenonCapture.y,
                    width: phenomenonCapture.width,
                    height: phenomenonCapture.height,
                    label: phenomenonCapture.label,
                };
                todo.captures.push(actionCapture);
            }
        }

        phenomenon.candidateCauses = [...phenomenon.candidateCauses];
        dispatch("change", phenomenon);
    }

    function isCaptureLinked(todo: TodoItem, captureId: string): boolean {
        return todo.captures?.some(c => c.id === captureId) || false;
    }

    function getCaptureCount(todo: TodoItem): number {
        return todo.captures?.length || 0;
    }

    function removeCapture(todoId: string, captureId: string) {
        if (!activeCauseId) return;
        const cause = phenomenon.candidateCauses.find(c => c.id === activeCauseId);
        if (!cause || !cause.todoList) return;

        const todo = cause.todoList.find(t => t.id === todoId);
        if (!todo || !todo.captures) return;

        todo.captures = todo.captures.filter(c => c.id !== captureId);
        phenomenon.candidateCauses = [...phenomenon.candidateCauses];
        dispatch("change", phenomenon);
    }

    function getCaptureColor(captureId: string) {
        const idx = phenomenonCaptures.findIndex(c => c.id === captureId);
        if (idx !== -1) return EVIDENCE_COLORS[idx % EVIDENCE_COLORS.length];
        return { bg: 'rgba(156, 163, 175, 0.2)', border: '#9ca3af', name: '회색' }; // Gray for action captures
    }
</script>

<div class="flex flex-col h-full bg-gray-50/50">
    <!-- Header -->
    <div class="px-4 py-3 border-b border-gray-200 bg-white">
        <div class="flex items-center gap-2">
            <div class="w-2 h-2 rounded-full bg-purple-500"></div>
            <h2 class="text-sm font-semibold text-gray-800">
                원인 도출 및 검증
            </h2>
        </div>
        <p class="text-xs text-gray-500 mt-1">
            원인 후보의 우선순위를 정하고, 검증을 위한 행동(Todo)을 계획하세요.
        </p>
    </div>

    <div class="flex-1 flex flex-col min-h-0 overflow-y-auto p-4 space-y-4">
        <!-- Priority List Section -->
        <div class="space-y-2">
            <div class="flex items-center justify-between">
                <h3 class="text-xs font-bold text-gray-500 uppercase">
                    우선순위 설정 (위에서부터 분석)
                </h3>
            </div>

            {#if !phenomenon.candidateCauses || phenomenon.candidateCauses.length === 0}
                <div
                    class="text-center py-4 text-gray-400 text-xs border-2 border-dashed border-gray-200 rounded-lg"
                >
                    등록된 원인 후보가 없습니다.<br />
                    '원인후보' 탭에서 후보를 먼저 추가하세요.
                </div>
            {:else}
                <div class="space-y-2">
                    {#each phenomenon.candidateCauses as cause, index (cause.id)}
                        {@const isActive = activeCauseId === cause.id}
                        {@const causeStatus = getEffectiveCauseStatus(cause, index)}
                        {@const isDragOver = dragOverCauseId === cause.id}
                        <!-- svelte-ignore a11y-click-events-have-key-events -->
                        <!-- svelte-ignore a11y-no-static-element-interactions -->
                        <div
                            class="bg-white border rounded-lg shadow-sm transition-all duration-200
                                   {isActive
                                ? 'border-purple-500 ring-1 ring-purple-500 shadow-md transform scale-[1.01]'
                                : causeStatus === 'inactive'
                                    ? 'border-gray-300 bg-gray-50 opacity-60'
                                    : causeStatus === 'active'
                                        ? 'border-green-300 bg-green-50/30'
                                        : 'border-gray-200 hover:border-gray-300'}
                                   {isDragOver ? 'border-blue-400 border-2 ring-2 ring-blue-200' : ''}"
                            draggable="true"
                            on:dragstart={(e) => handleCauseDragStart(e, cause.id)}
                            on:dragover={(e) => handleCauseDragOver(e, cause.id)}
                            on:dragleave={handleCauseDragLeave}
                            on:drop={(e) => handleCauseDrop(e, cause.id)}
                            on:dragend={handleCauseDragEnd}
                        >
                            <!-- Cause Header Item -->
                            <div class="flex items-center p-2 gap-2">
                                <!-- Drag Handle -->
                                <div class="flex-shrink-0 cursor-move opacity-40 hover:opacity-100 transition-opacity">
                                    <svg class="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8h16M4 16h16"/>
                                    </svg>
                                </div>
                                <!-- Rank Badge -->
                                <div
                                    class="flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold border
                                           {causeStatus === 'inactive'
                                        ? 'bg-gray-200 text-gray-500 border-gray-300'
                                        : causeStatus === 'active'
                                            ? 'bg-green-100 text-green-700 border-green-300'
                                            : 'bg-gray-100 text-gray-600 border-gray-200'}"
                                >
                                    {index + 1}
                                </div>

                                <!-- Status Badge -->
                                {#if causeStatus === 'active'}
                                    <span class="flex-shrink-0 px-1.5 py-0.5 text-[10px] font-bold rounded bg-green-100 text-green-700 border border-green-300">
                                        탐색중
                                    </span>
                                {:else if causeStatus === 'inactive'}
                                    <span class="flex-shrink-0 px-1.5 py-0.5 text-[10px] font-bold rounded bg-gray-200 text-gray-500 border border-gray-300 line-through">
                                        제외됨
                                    </span>
                                {/if}

                                <!-- Title -->
                                <div
                                    class="flex-1 min-w-0 text-sm cursor-pointer hover:text-purple-700 font-medium
                                           {isActive
                                        ? 'text-gray-900'
                                        : causeStatus === 'inactive'
                                            ? 'text-gray-400 line-through'
                                            : 'text-gray-700'}"
                                    on:click={() => toggleActiveCause(cause.id)}
                                >
                                    {cause.text}
                                </div>

                                <!-- Reorder Buttons -->
                                <div
                                    class="flex flex-col gap-0.5 opacity-50 hover:opacity-100"
                                >
                                    <button
                                        class="p-0.5 hover:bg-gray-100 rounded text-gray-500 disabled:opacity-30"
                                        disabled={index === 0}
                                        on:click|stopPropagation={() =>
                                            moveCause(index, "up")}
                                        aria-label="Move cause up"
                                    >
                                        <svg
                                            class="w-3 h-3"
                                            fill="none"
                                            stroke="currentColor"
                                            viewBox="0 0 24 24"
                                            ><path
                                                stroke-linecap="round"
                                                stroke-linejoin="round"
                                                stroke-width="2"
                                                d="M5 15l7-7 7 7"
                                            /></svg
                                        >
                                    </button>
                                    <button
                                        class="p-0.5 hover:bg-gray-100 rounded text-gray-500 disabled:opacity-30"
                                        disabled={index ===
                                            phenomenon.candidateCauses.length -
                                                1}
                                        on:click|stopPropagation={() =>
                                            moveCause(index, "down")}
                                        aria-label="Move cause down"
                                    >
                                        <svg
                                            class="w-3 h-3"
                                            fill="none"
                                            stroke="currentColor"
                                            viewBox="0 0 24 24"
                                            ><path
                                                stroke-linecap="round"
                                                stroke-linejoin="round"
                                                stroke-width="2"
                                                d="M19 9l-7 7-7-7"
                                            /></svg
                                        >
                                    </button>
                                </div>
                            </div>

                            <!-- Expanded Action Plan -->
                            {#if isActive}
                                <div
                                    class="border-t border-gray-100 bg-gray-50/50 p-3"
                                    transition:slide
                                >
                                    <div
                                        class="mb-2 text-xs font-bold text-gray-500 uppercase flex justify-between items-center"
                                    >
                                        <span>검증 계획 (Todo List)</span>
                                    </div>

                                    <!-- Todo List -->
                                    <div class="space-y-2 mb-3">
                                        {#if !cause.todoList || cause.todoList.length === 0}
                                            <div
                                                class="text-xs text-gray-400 italic text-center py-2"
                                            >
                                                등록된 행동이나 조건이 없습니다.
                                            </div>
                                        {:else}
                                            {#each cause.todoList as todo, tIndex (todo.id)}
                                                <!-- svelte-ignore a11y-no-static-element-interactions -->
                                                <div
                                                    class="relative pl-4 border-l-2 {todo.type ===
                                                    'condition'
                                                        ? 'border-orange-300'
                                                        : 'border-blue-300'} ml-1 transition-all duration-150
                                                        {draggingTodoId === todo.id ? 'opacity-50' : ''}
                                                        {dragOverTodoId === todo.id ? 'border-l-4 bg-blue-50' : ''}"
                                                    draggable="true"
                                                    on:dragstart={(e) => handleTodoDragStart(e, todo.id)}
                                                    on:dragover={(e) => handleTodoDragOver(e, todo.id)}
                                                    on:dragleave={handleTodoDragLeave}
                                                    on:drop={(e) => handleTodoDrop(e, todo.id)}
                                                    on:dragend={handleTodoDragEnd}
                                                >
                                                    <div
                                                        class="flex items-start justify-between group"
                                                    >
                                                        <!-- Drag handle -->
                                                        <div class="flex-shrink-0 cursor-grab active:cursor-grabbing text-gray-300 hover:text-gray-500 mr-1 mt-0.5">
                                                            <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 24 24">
                                                                <circle cx="9" cy="5" r="1.5" />
                                                                <circle cx="15" cy="5" r="1.5" />
                                                                <circle cx="9" cy="12" r="1.5" />
                                                                <circle cx="15" cy="12" r="1.5" />
                                                                <circle cx="9" cy="19" r="1.5" />
                                                                <circle cx="15" cy="19" r="1.5" />
                                                            </svg>
                                                        </div>
                                                        <div
                                                            class="text-xs flex-1"
                                                        >
                                                            <div
                                                                class="flex items-center gap-1.5 mb-0.5"
                                                            >
                                                                <span
                                                                    class="px-1.5 py-0.5 rounded text-[10px] font-bold uppercase
                                                                    {todo.type ===
                                                                    'condition'
                                                                        ? 'bg-orange-100 text-orange-700'
                                                                        : 'bg-blue-100 text-blue-700'}"
                                                                >
                                                                    {todo.type ===
                                                                    "condition"
                                                                        ? "Condition"
                                                                        : "Action"}
                                                                </span>
                                                            </div>
                                                            {#if editingTodoId === todo.id}
                                                                <!-- Inline edit mode -->
                                                                <input
                                                                    type="text"
                                                                    bind:value={editingTodoText}
                                                                    class="w-full text-xs border border-gray-300 rounded px-1 py-0.5 focus:border-purple-500 focus:outline-none"
                                                                    on:keydown={handleEditKeyDown}
                                                                    on:blur={saveEditTodo}
                                                                />
                                                            {:else}
                                                                <!-- svelte-ignore a11y-click-events-have-key-events -->
                                                                <!-- svelte-ignore a11y-no-static-element-interactions -->
                                                                <div
                                                                    class="text-gray-800 leading-snug cursor-pointer hover:bg-gray-100 rounded px-1 -mx-1"
                                                                    on:click={() => startEditTodo(todo)}
                                                                    title="클릭하여 수정"
                                                                >
                                                                    {todo.text}
                                                                </div>
                                                                <!-- Display parameter values if they exist -->
                                                                {#if todo.paramValues && Object.keys(todo.paramValues).length > 0}
                                                                    <div class="mt-1 space-y-0.5 pl-1 border-l-2 border-gray-200">
                                                                        {#each Object.entries(todo.paramValues) as [paramId, paramValue]}
                                                                            {#if paramValue}
                                                                                <div class="text-[10px] text-gray-600">
                                                                                    <span class="font-medium">{paramId}:</span>
                                                                                    <span class="text-gray-800">{paramValue}</span>
                                                                                </div>
                                                                            {/if}
                                                                        {/each}
                                                                    </div>
                                                                {/if}
                                                            {/if}
                                                            {#if todo.type === "condition"}
                                                                <div class="mt-1.5 flex items-center gap-2">
                                                                    <!-- True/False Toggle Buttons -->
                                                                    <div class="flex items-center gap-1 bg-gray-100 rounded-full p-0.5">
                                                                        <button
                                                                            type="button"
                                                                            class="px-2 py-0.5 text-[10px] font-bold rounded-full transition-all
                                                                                   {todo.conditionStatus === 'true'
                                                                                ? 'bg-green-500 text-white shadow-sm'
                                                                                : 'text-gray-500 hover:text-green-600 hover:bg-green-50'}"
                                                                            on:click|stopPropagation={() => toggleConditionStatus(todo.id, 'true')}
                                                                            title="True: 탐색 계속 (Active)"
                                                                        >
                                                                            True
                                                                        </button>
                                                                        <button
                                                                            type="button"
                                                                            class="px-2 py-0.5 text-[10px] font-bold rounded-full transition-all
                                                                                   {todo.conditionStatus === 'false'
                                                                                ? 'bg-red-500 text-white shadow-sm'
                                                                                : 'text-gray-500 hover:text-red-600 hover:bg-red-50'}"
                                                                            on:click|stopPropagation={() => toggleConditionStatus(todo.id, 'false')}
                                                                            title="False: 탐색 종료 (Inactive)"
                                                                        >
                                                                            False
                                                                        </button>
                                                                    </div>
                                                                    <!-- Status indicator -->
                                                                    {#if todo.conditionStatus === 'true'}
                                                                        <span class="text-[10px] text-green-600 font-medium">탐색중</span>
                                                                    {:else if todo.conditionStatus === 'false'}
                                                                        <span class="text-[10px] text-red-500 font-medium">탐색종료</span>
                                                                    {:else}
                                                                        <span class="text-[10px] text-gray-400">미설정</span>
                                                                    {/if}
                                                                </div>
                                                            {/if}

                                                            <!-- Action Captures (only for action type) -->
                                                            {#if todo.type === "action"}
                                                                <div class="mt-1.5 flex items-center gap-2 flex-wrap">
                                                                    <!-- Capture count badge - clickable to expand -->
                                                                    <button
                                                                        type="button"
                                                                        class="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] rounded transition-colors
                                                                               {getCaptureCount(todo) > 0
                                                                            ? 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                                                                            : 'bg-gray-50 text-gray-400 hover:bg-gray-100'}"
                                                                        on:click|stopPropagation={() => toggleCapturesExpand(todo.id)}
                                                                        title="연관 캡처 관리"
                                                                    >
                                                                        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                                                        </svg>
                                                                        캡처 {getCaptureCount(todo)}개
                                                                        <svg class="w-2.5 h-2.5 transition-transform {expandedCapturesTodoId === todo.id ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                                                                        </svg>
                                                                    </button>

                                                                    <!-- Linked captures inline preview (gray color) -->
                                                                    {#if todo.captures && todo.captures.length > 0 && expandedCapturesTodoId !== todo.id}
                                                                        {#each todo.captures.slice(0, 3) as capture (capture.id)}
                                                                            <span
                                                                                class="inline-flex items-center gap-0.5 px-1 py-0.5 text-[9px] rounded bg-gray-200 text-gray-600 border border-gray-300"
                                                                                title={capture.label || `슬라이드 ${capture.slideIndex + 1}`}
                                                                            >
                                                                                <span class="w-1.5 h-1.5 rounded-full bg-gray-500"></span>
                                                                                {capture.label || `S${capture.slideIndex + 1}`}
                                                                            </span>
                                                                        {/each}
                                                                        {#if todo.captures.length > 3}
                                                                            <span class="text-[9px] text-gray-400">+{todo.captures.length - 3}</span>
                                                                        {/if}
                                                                    {/if}
                                                                </div>

                                                                <!-- Expanded capture selection -->
                                                                {#if expandedCapturesTodoId === todo.id}
                                                                    <div class="mt-2 p-2 bg-gray-50 rounded border border-gray-200" transition:slide>
                                                                        <div class="text-[9px] font-bold text-gray-500 uppercase mb-1.5">발생현상 캡처에서 선택</div>
                                                                        {#if phenomenonCaptures.length === 0}
                                                                            <div class="text-[10px] text-gray-400 italic">
                                                                                발생현상 탭에서 캡처를 먼저 추가하세요.
                                                                            </div>
                                                                        {:else}
                                                                            <div class="flex flex-wrap gap-1">
                                                                                {#each phenomenonCaptures as pCapture, idx (pCapture.id)}
                                                                                    {@const isLinked = isCaptureLinked(todo, pCapture.id)}
                                                                                    {@const color = getCaptureColor(pCapture.id)}
                                                                                    <button
                                                                                        type="button"
                                                                                        class="inline-flex items-center gap-1 px-1.5 py-1 text-[10px] rounded border transition-all
                                                                                               {isLinked
                                                                                            ? 'bg-gray-200 border-gray-400 text-gray-700 ring-1 ring-gray-400'
                                                                                            : 'bg-white border-gray-200 text-gray-500 hover:bg-gray-50'}"
                                                                                        on:click|stopPropagation={() => toggleCaptureLink(todo.id, pCapture.id)}
                                                                                        title={isLinked ? '클릭하여 연결 해제' : '클릭하여 연결'}
                                                                                    >
                                                                                        <span
                                                                                            class="w-2 h-2 rounded-full shrink-0"
                                                                                            style="background-color: {color.border}"
                                                                                        ></span>
                                                                                        <span class="truncate max-w-[60px]">
                                                                                            {pCapture.label || `캡처 ${idx + 1}`}
                                                                                        </span>
                                                                                        {#if isLinked}
                                                                                            <svg class="w-2.5 h-2.5 text-gray-600" fill="currentColor" viewBox="0 0 20 20">
                                                                                                <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
                                                                                            </svg>
                                                                                        {/if}
                                                                                    </button>
                                                                                {/each}
                                                                            </div>
                                                                        {/if}
                                                                    </div>
                                                                {/if}
                                                            {/if}
                                                        </div>
                                                        <button
                                                            class="text-gray-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
                                                            on:click={() =>
                                                                removeTodo(
                                                                    todo.id,
                                                                )}
                                                            aria-label="Remove todo item"
                                                        >
                                                            <svg
                                                                class="w-3.5 h-3.5"
                                                                fill="none"
                                                                stroke="currentColor"
                                                                viewBox="0 0 24 24"
                                                                ><path
                                                                    stroke-linecap="round"
                                                                    stroke-linejoin="round"
                                                                    stroke-width="2"
                                                                    d="M6 18L18 6M6 6l12 12"
                                                                /></svg
                                                            >
                                                        </button>
                                                    </div>
                                                </div>
                                            {/each}
                                        {/if}
                                    </div>

                                    <!-- Add New Todo Input -->
                                    {#if isAddingTodo}
                                        <div
                                            class="bg-white border border-gray-300 rounded p-2 shadow-sm animate-fadeIn"
                                        >
                                            <div
                                                class="text-[10px] font-bold mb-1
                                                {newTodoType === 'condition'
                                                    ? 'text-orange-600'
                                                    : 'text-blue-600'}"
                                            >
                                                {newTodoType === "condition"
                                                    ? "새 조건 (Condition) 추가"
                                                    : "새 행동 (Action) 추가"}
                                            </div>

                                            <!-- Predefined options from settings -->
                                            {#if predefinedItems.length > 0}
                                                <div class="mb-2">
                                                    <div class="text-[10px] text-gray-500 mb-1">미리 정의된 항목:</div>
                                                    <div class="flex flex-wrap gap-1">
                                                        {#each predefinedItems as item}
                                                            <button
                                                                type="button"
                                                                class="px-2 py-0.5 text-[10px] rounded border transition-colors
                                                                    {newTodoText === item.name
                                                                        ? (newTodoType === 'condition'
                                                                            ? 'bg-orange-100 border-orange-400 text-orange-700'
                                                                            : 'bg-blue-100 border-blue-400 text-blue-700')
                                                                        : 'bg-gray-50 border-gray-200 text-gray-600 hover:bg-gray-100'}"
                                                                on:click={() => selectPredefinedItem(item)}
                                                            >
                                                                {item.name}
                                                            </button>
                                                        {/each}
                                                    </div>
                                                </div>
                                            {/if}

                                            <!-- Parameter inputs for selected predefined item -->
                                            {#if selectedPredefinedItem && selectedPredefinedItem.params && selectedPredefinedItem.params.length > 0}
                                                <div class="mb-2 space-y-2 border-t border-gray-200 pt-2">
                                                    <div class="text-[10px] text-gray-500 font-medium">파라미터:</div>
                                                    {#each selectedPredefinedItem.params as param}
                                                        <div class="space-y-1">
                                                            <label class="text-[10px] text-gray-600 flex items-center gap-1">
                                                                {param.name}
                                                                {#if param.required}
                                                                    <span class="text-red-500">*</span>
                                                                {/if}
                                                            </label>
                                                            {#if param.param_type === 'selection' && param.selection_values && param.selection_values.length > 0}
                                                                <select
                                                                    bind:value={paramValues[param.id]}
                                                                    class="w-full text-xs border border-gray-200 rounded px-2 py-1 focus:border-purple-500 focus:outline-none"
                                                                >
                                                                    <option value="">선택하세요...</option>
                                                                    {#each param.selection_values as value}
                                                                        <option value={value}>{value}</option>
                                                                    {/each}
                                                                </select>
                                                            {:else}
                                                                <input
                                                                    type="text"
                                                                    bind:value={paramValues[param.id]}
                                                                    class="w-full text-xs border border-gray-200 rounded px-2 py-1 focus:border-purple-500 focus:outline-none"
                                                                    placeholder="값을 입력하세요..."
                                                                />
                                                            {/if}
                                                        </div>
                                                    {/each}
                                                </div>
                                            {/if}

                                            <div class="text-[10px] text-gray-500 mb-1">
                                                {predefinedItems.length > 0 && !selectedPredefinedItem ? "또는 직접 입력:" : selectedPredefinedItem ? "이름 (수정 가능):" : ""}
                                            </div>
                                            <input
                                                type="text"
                                                bind:value={newTodoText}
                                                class="w-full text-xs border-b border-gray-200 focus:border-purple-500 focus:outline-none py-1 mb-2"
                                                placeholder={newTodoType ===
                                                "condition"
                                                    ? "예: 전압이 5V 이상인가?"
                                                    : "예: 보드를 재부팅한다."}
                                                on:keydown={handleKeyDown}
                                            />
                                            <div
                                                class="flex justify-end gap-2 text-[10px]"
                                            >
                                                <button
                                                    class="px-2 py-1 text-gray-500 hover:text-gray-700"
                                                    on:click={cancelAddTodo}
                                                    >취소</button
                                                >
                                                <button
                                                    class="px-2 py-1 bg-purple-500 text-white rounded hover:bg-purple-600"
                                                    on:click={saveNewTodo}
                                                    >추가</button
                                                >
                                            </div>
                                        </div>
                                    {:else}
                                        <div class="flex gap-2 mt-2">
                                            <button
                                                class="flex-1 py-1.5 border border-dashed border-blue-300 text-blue-600 hover:bg-blue-50 rounded text-xs gap-1 flex items-center justify-center transition-colors"
                                                on:click={() =>
                                                    startAddTodo("action")}
                                            >
                                                <span class="font-bold">+</span>
                                                Action
                                            </button>
                                            <button
                                                class="flex-1 py-1.5 border border-dashed border-orange-300 text-orange-600 hover:bg-orange-50 rounded text-xs gap-1 flex items-center justify-center transition-colors"
                                                on:click={() =>
                                                    startAddTodo("condition")}
                                            >
                                                <span class="font-bold">+</span>
                                                Condition
                                            </button>
                                        </div>
                                    {/if}

                                    <div class="mt-4 pt-3 border-t border-gray-200 flex items-center justify-end">
                                        {#if phenomenon.workflowCompleted && phenomenon.finalCauseId === cause.id}
                                            <div class="w-full flex items-center justify-between bg-green-50 border border-green-200 rounded px-3 py-2">
                                                <div class="flex items-center gap-2">
                                                    <div class="flex items-center justify-center w-5 h-5 rounded-full bg-green-500 text-white shadow-sm">
                                                        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7" />
                                                        </svg>
                                                    </div>
                                                    <div>
                                                        <div class="text-xs font-bold text-green-800">최종 원인 확정됨</div>
                                                    </div>
                                                </div>
                                                <button
                                                    class="text-[10px] text-gray-500 hover:text-red-600 underline decoration-gray-300 hover:decoration-red-400 transition-colors"
                                                    on:click={revokeFinalCause}
                                                >
                                                    선택 철회
                                                </button>
                                            </div>
                                        {:else if causeStatus === 'active' && !phenomenon.workflowCompleted}
                                            <div class="flex items-center gap-2">
                                                <span class="text-[10px] text-gray-400">모든 검증이 완료되었다면:</span>
                                                <button
                                                    class="flex items-center gap-1.5 px-3 py-1.5 bg-white border border-gray-300 hover:border-green-500 hover:text-green-700 hover:bg-green-50 text-gray-600 text-xs font-medium rounded transition-all shadow-sm"
                                                    on:click={() => finalizeCause(cause.id)}
                                                >
                                                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                                    </svg>
                                                    최종 원인으로 지목
                                                </button>
                                            </div>
                                        {/if}
                                    </div>
                                </div>
                            {/if}
                        </div>
                    {/each}
                </div>
            {/if}
        </div>
    </div>
</div>

<style>
    /* smooth scrollbar if needed */
    div::-webkit-scrollbar {
        width: 4px;
    }
    div::-webkit-scrollbar-track {
        background: transparent;
    }
    div::-webkit-scrollbar-thumb {
        background-color: #cbd5e1;
        border-radius: 4px;
    }
    @keyframes fadeIn {
        from {
            opacity: 0;
            transform: translateY(-5px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    .animate-fadeIn {
        animation: fadeIn 0.15s ease-out forwards;
    }
</style>
