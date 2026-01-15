<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import { slide } from "svelte/transition";
    import type {
        PhenomenonData,
        CandidateCause,
        TodoItem,
        TodoType,
        ConditionStatus,
    } from "$lib/types/phenomenon";
    import { createActionCapture } from "$lib/types/phenomenon";
    import CauseDerivationTodoItem from "./CauseDerivationTodoItem.svelte";
    import CauseDerivationAddForm from "./CauseDerivationAddForm.svelte";

    export let phenomenon: PhenomenonData;
    export let workflowActions: { id: string; name: string; params: any[] }[] = [];
    export let workflowConditions: { id: string; name: string; params: any[] }[] = [];
    export let actionCaptureMode = false;
    export let actionCaptureTodoId: string | null = null;

    let activeCauseId: string | null = null;
    let isAddingTodo = false;
    let newTodoText = "";
    let newTodoType: TodoType = "action";
    let selectedPredefinedItem: { id: string; name: string; params: any[] } | null = null;
    let paramValues: Record<string, string> = {};
    let editingTodoId: string | null = null;
    let editingTodoText = "";
    let draggingTodoId: string | null = null;
    let dragOverTodoId: string | null = null;
    let draggingCauseId: string | null = null;
    let dragOverCauseId: string | null = null;
    let expandedCapturesTodoId: string | null = null;

    const dispatch = createEventDispatcher<{
        change: PhenomenonData;
        workflowComplete: { finalCauseId: string };
        toggleActionCaptureMode: { todoId: string | null; causeId: string | null };
    }>();

    $: if (phenomenon.candidateCauses) {
        let changed = false;
        phenomenon.candidateCauses.forEach((cause) => {
            if (!cause.todoList) { cause.todoList = []; changed = true; }
        });
        if (changed) phenomenon.candidateCauses = [...phenomenon.candidateCauses];
    }

    $: predefinedItems = newTodoType === "condition" ? workflowConditions : workflowActions;

    // Status helpers
    function getCauseStatus(cause: CandidateCause): 'active' | 'inactive' | 'pending' {
        if (!cause.todoList) return 'pending';
        const conditions = cause.todoList.filter(t => t.type === 'condition');
        if (conditions.length === 0) return 'pending';
        if (conditions.some(c => c.conditionStatus === 'false')) return 'inactive';
        if (conditions.every(c => c.conditionStatus === 'true')) return 'active';
        return 'pending';
    }

    function getEffectiveCauseStatus(cause: CandidateCause, index: number): 'active' | 'inactive' | 'pending' {
        const baseStatus = getCauseStatus(cause);
        if (baseStatus === 'inactive') return 'inactive';
        const allPreviousInactive = phenomenon.candidateCauses.slice(0, index).every(c => getCauseStatus(c) === 'inactive');
        if (allPreviousInactive && baseStatus === 'pending') return 'active';
        return baseStatus;
    }

    // Cause operations
    function moveCause(index: number, direction: "up" | "down") {
        const newIndex = direction === "up" ? index - 1 : index + 1;
        if (newIndex < 0 || newIndex >= phenomenon.candidateCauses.length) return;
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

    function finalizeCause(causeId: string) {
        phenomenon.finalCauseId = causeId;
        phenomenon.workflowCompleted = true;
        phenomenon.candidateCauses = [...phenomenon.candidateCauses];
        dispatch("change", phenomenon);
        dispatch("workflowComplete", { finalCauseId: causeId });
    }

    function revokeFinalCause() {
        phenomenon.finalCauseId = null;
        phenomenon.workflowCompleted = false;
        phenomenon.candidateCauses = [...phenomenon.candidateCauses];
        dispatch("change", phenomenon);
    }

    // Todo operations
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
        const cause = phenomenon.candidateCauses.find(c => c.id === activeCauseId);
        if (!cause) return;
        const newTodo: TodoItem = { id: `todo_${Date.now()}`, type: newTodoType, text: newTodoText.trim(), isCompleted: false };
        if (Object.keys(paramValues).length > 0) newTodo.paramValues = { ...paramValues };
        cause.todoList = [...(cause.todoList || []), newTodo];
        phenomenon.candidateCauses = [...phenomenon.candidateCauses];
        dispatch("change", phenomenon);
        cancelAddTodo();
    }

    function removeTodo(todoId: string) {
        if (!activeCauseId) return;
        const cause = phenomenon.candidateCauses.find(c => c.id === activeCauseId);
        if (!cause?.todoList) return;
        cause.todoList = cause.todoList.filter(t => t.id !== todoId);
        phenomenon.candidateCauses = [...phenomenon.candidateCauses];
        dispatch("change", phenomenon);
    }

    function selectPredefinedItem(item: { id: string; name: string; params: any[] }) {
        selectedPredefinedItem = item;
        newTodoText = item.name;
        paramValues = {};
        item.params?.forEach(param => (paramValues[param.id] = ""));
    }

    // Inline editing
    function startEditTodo(todo: TodoItem) { editingTodoId = todo.id; editingTodoText = todo.text; }
    function cancelEditTodo() { editingTodoId = null; editingTodoText = ""; }
    function saveEditTodo() {
        if (!editingTodoId || !editingTodoText.trim() || !activeCauseId) { cancelEditTodo(); return; }
        const cause = phenomenon.candidateCauses.find(c => c.id === activeCauseId);
        if (!cause?.todoList) { cancelEditTodo(); return; }
        const todo = cause.todoList.find(t => t.id === editingTodoId);
        if (todo) { todo.text = editingTodoText.trim(); phenomenon.candidateCauses = [...phenomenon.candidateCauses]; dispatch("change", phenomenon); }
        cancelEditTodo();
    }
    function handleEditKeyDown(e: KeyboardEvent) { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); saveEditTodo(); } else if (e.key === "Escape") cancelEditTodo(); }

    // Todo drag & drop
    function handleTodoDragStart(e: DragEvent, todoId: string) { draggingTodoId = todoId; if (e.dataTransfer) { e.dataTransfer.effectAllowed = "move"; e.dataTransfer.setData("text/plain", todoId); } }
    function handleTodoDragOver(e: DragEvent, todoId: string) { e.preventDefault(); if (e.dataTransfer) e.dataTransfer.dropEffect = "move"; dragOverTodoId = todoId; }
    function handleTodoDragLeave() { dragOverTodoId = null; }
    function handleTodoDrop(e: DragEvent, targetTodoId: string) {
        e.preventDefault(); dragOverTodoId = null;
        if (!draggingTodoId || draggingTodoId === targetTodoId || !activeCauseId) return;
        const cause = phenomenon.candidateCauses.find(c => c.id === activeCauseId);
        if (!cause?.todoList) return;
        const todoList = [...cause.todoList];
        const dragIndex = todoList.findIndex(t => t.id === draggingTodoId);
        const targetIndex = todoList.findIndex(t => t.id === targetTodoId);
        if (dragIndex === -1 || targetIndex === -1) return;
        const [draggedItem] = todoList.splice(dragIndex, 1);
        todoList.splice(targetIndex, 0, draggedItem);
        cause.todoList = todoList;
        phenomenon.candidateCauses = [...phenomenon.candidateCauses];
        dispatch("change", phenomenon);
        draggingTodoId = null;
    }
    function handleTodoDragEnd() { draggingTodoId = null; dragOverTodoId = null; }

    // Cause drag & drop
    function handleCauseDragStart(e: DragEvent, causeId: string) { draggingCauseId = causeId; if (e.dataTransfer) { e.dataTransfer.effectAllowed = "move"; e.dataTransfer.setData("text/plain", causeId); } }
    function handleCauseDragOver(e: DragEvent, causeId: string) { e.preventDefault(); if (e.dataTransfer) e.dataTransfer.dropEffect = "move"; dragOverCauseId = causeId; }
    function handleCauseDragLeave() { dragOverCauseId = null; }
    function handleCauseDrop(e: DragEvent, targetCauseId: string) {
        e.preventDefault(); dragOverCauseId = null;
        if (!draggingCauseId || draggingCauseId === targetCauseId) return;
        const causes = [...phenomenon.candidateCauses];
        const dragIndex = causes.findIndex(c => c.id === draggingCauseId);
        const targetIndex = causes.findIndex(c => c.id === targetCauseId);
        if (dragIndex === -1 || targetIndex === -1) return;
        const [draggedCause] = causes.splice(dragIndex, 1);
        causes.splice(targetIndex, 0, draggedCause);
        phenomenon.candidateCauses = causes;
        dispatch("change", phenomenon);
        draggingCauseId = null;
    }
    function handleCauseDragEnd() { draggingCauseId = null; dragOverCauseId = null; }

    // Condition status
    function toggleConditionStatus(todoId: string, newStatus: ConditionStatus) {
        if (!activeCauseId) return;
        const cause = phenomenon.candidateCauses.find(c => c.id === activeCauseId);
        if (!cause?.todoList) return;
        const todo = cause.todoList.find(t => t.id === todoId);
        if (todo && todo.type === 'condition') {
            todo.conditionStatus = todo.conditionStatus === newStatus ? null : newStatus;
            phenomenon.candidateCauses = [...phenomenon.candidateCauses];
            dispatch("change", phenomenon);
        }
    }

    // Action capture
    function toggleActionCapture(todoId: string) {
        if (actionCaptureMode && actionCaptureTodoId === todoId) dispatch("toggleActionCaptureMode", { todoId: null, causeId: null });
        else dispatch("toggleActionCaptureMode", { todoId, causeId: activeCauseId });
    }

    function toggleCapturesExpand(todoId: string) { expandedCapturesTodoId = expandedCapturesTodoId === todoId ? null : todoId; }

    function removeCapture(todoId: string, captureId: string) {
        if (!activeCauseId) return;
        const cause = phenomenon.candidateCauses.find(c => c.id === activeCauseId);
        if (!cause?.todoList) return;
        const todo = cause.todoList.find(t => t.id === todoId);
        if (!todo?.captures) return;
        todo.captures = todo.captures.filter(c => c.id !== captureId);
        phenomenon.candidateCauses = [...phenomenon.candidateCauses];
        dispatch("change", phenomenon);
    }

    export function addCaptureToAction(todoId: string, causeId: string, capture: { slideIndex: number; x: number; y: number; width: number; height: number; }) {
        const cause = phenomenon.candidateCauses.find(c => c.id === causeId);
        if (!cause?.todoList) return;
        const todo = cause.todoList.find(t => t.id === todoId);
        if (!todo) return;
        if (!todo.captures) todo.captures = [];
        todo.captures = [...todo.captures, createActionCapture(capture.slideIndex, capture.x, capture.y, capture.width, capture.height)];
        phenomenon.candidateCauses = [...phenomenon.candidateCauses];
        dispatch("change", phenomenon);
        expandedCapturesTodoId = todoId;
    }
</script>

<div class="flex flex-col h-full bg-gray-50/50">
    <div class="px-4 py-3 border-b border-gray-200 bg-white">
        <div class="flex items-center gap-2">
            <div class="w-2 h-2 rounded-full bg-purple-500"></div>
            <h2 class="text-sm font-semibold text-gray-800">원인 도출 및 검증</h2>
        </div>
        <p class="text-xs text-gray-500 mt-1">원인 후보의 우선순위를 정하고, 검증을 위한 행동(Todo)을 계획하세요.</p>
    </div>

    <div class="flex-1 flex flex-col min-h-0 overflow-y-auto p-4 space-y-4">
        <div class="space-y-2">
            <h3 class="text-xs font-bold text-gray-500 uppercase">우선순위 설정 (위에서부터 분석)</h3>

            {#if !phenomenon.candidateCauses?.length}
                <div class="text-center py-4 text-gray-400 text-xs border-2 border-dashed border-gray-200 rounded-lg">
                    등록된 원인 후보가 없습니다.<br />원인후보 탭에서 후보를 먼저 추가하세요.
                </div>
            {:else}
                <div class="space-y-2">
                    {#each phenomenon.candidateCauses as cause, index (cause.id)}
                        {@const isActive = activeCauseId === cause.id}
                        {@const causeStatus = getEffectiveCauseStatus(cause, index)}
                        <!-- svelte-ignore a11y-no-static-element-interactions -->
                        <div
                            class="bg-white border rounded-lg shadow-sm transition-all duration-200
                                   {isActive ? 'border-purple-500 ring-1 ring-purple-500 shadow-md' : causeStatus === 'inactive' ? 'border-gray-300 bg-gray-50 opacity-60' : causeStatus === 'active' ? 'border-green-300 bg-green-50/30' : 'border-gray-200 hover:border-gray-300'}
                                   {dragOverCauseId === cause.id ? 'border-blue-400 border-2 ring-2 ring-blue-200' : ''}"
                            draggable="true"
                            on:dragstart={(e) => handleCauseDragStart(e, cause.id)}
                            on:dragover={(e) => handleCauseDragOver(e, cause.id)}
                            on:dragleave={handleCauseDragLeave}
                            on:drop={(e) => handleCauseDrop(e, cause.id)}
                            on:dragend={handleCauseDragEnd}
                        >
                            <div class="flex items-center p-2 gap-2">
                                <div class="flex-shrink-0 cursor-move opacity-40 hover:opacity-100">
                                    <svg class="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8h16M4 16h16"/></svg>
                                </div>
                                <div class="flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold border {causeStatus === 'inactive' ? 'bg-gray-200 text-gray-500' : causeStatus === 'active' ? 'bg-green-100 text-green-700 border-green-300' : 'bg-gray-100 text-gray-600'}">
                                    {index + 1}
                                </div>
                                {#if causeStatus === 'active'}
                                    <span class="flex-shrink-0 px-1.5 py-0.5 text-[10px] font-bold rounded bg-green-100 text-green-700 border border-green-300">탐색중</span>
                                {:else if causeStatus === 'inactive'}
                                    <span class="flex-shrink-0 px-1.5 py-0.5 text-[10px] font-bold rounded bg-gray-200 text-gray-500 line-through">제외됨</span>
                                {/if}
                                <!-- svelte-ignore a11y-click-events-have-key-events -->
                                <div class="flex-1 min-w-0 text-sm cursor-pointer hover:text-purple-700 font-medium {causeStatus === 'inactive' ? 'text-gray-400 line-through' : ''}" on:click={() => toggleActiveCause(cause.id)}>
                                    {cause.text}
                                </div>
                                <div class="flex flex-col gap-0.5">
                                    <button class="p-0.5 hover:bg-gray-100 rounded text-gray-500 disabled:opacity-30" disabled={index === 0} on:click|stopPropagation={() => moveCause(index, "up")}><svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7"/></svg></button>
                                    <button class="p-0.5 hover:bg-gray-100 rounded text-gray-500 disabled:opacity-30" disabled={index === phenomenon.candidateCauses.length - 1} on:click|stopPropagation={() => moveCause(index, "down")}><svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg></button>
                                </div>
                            </div>

                            {#if isActive}
                                <div class="border-t border-gray-100 bg-gray-50/50 p-3" transition:slide>
                                    <div class="mb-2 text-xs font-bold text-gray-500 uppercase">검증 계획 (Todo List)</div>
                                    <div class="space-y-2 mb-3">
                                        {#if !cause.todoList?.length}
                                            <div class="text-xs text-gray-400 italic text-center py-2">등록된 행동이나 조건이 없습니다.</div>
                                        {:else}
                                            {#each cause.todoList as todo, tIndex (todo.id)}
                                                <CauseDerivationTodoItem
                                                    {todo}
                                                    todoIndex={tIndex}
                                                    isDragging={draggingTodoId === todo.id}
                                                    isDragOver={dragOverTodoId === todo.id}
                                                    isEditing={editingTodoId === todo.id}
                                                    editingText={editingTodoText}
                                                    {actionCaptureMode}
                                                    {actionCaptureTodoId}
                                                    {expandedCapturesTodoId}
                                                    on:dragstart={(e) => handleTodoDragStart(e.detail.event, e.detail.todoId)}
                                                    on:dragover={(e) => handleTodoDragOver(e.detail.event, e.detail.todoId)}
                                                    on:dragleave={handleTodoDragLeave}
                                                    on:drop={(e) => handleTodoDrop(e.detail.event, e.detail.todoId)}
                                                    on:dragend={handleTodoDragEnd}
                                                    on:startEdit={(e) => startEditTodo(e.detail)}
                                                    on:saveEdit={saveEditTodo}
                                                    on:cancelEdit={cancelEditTodo}
                                                    on:editKeydown={(e) => handleEditKeyDown(e.detail)}
                                                    on:editTextChange={(e) => (editingTodoText = e.detail)}
                                                    on:remove={(e) => removeTodo(e.detail)}
                                                    on:toggleConditionStatus={(e) => toggleConditionStatus(e.detail.todoId, e.detail.status)}
                                                    on:toggleActionCapture={(e) => toggleActionCapture(e.detail)}
                                                    on:toggleCapturesExpand={(e) => toggleCapturesExpand(e.detail)}
                                                    on:removeCapture={(e) => removeCapture(e.detail.todoId, e.detail.captureId)}
                                                />
                                            {/each}
                                        {/if}
                                    </div>

                                    <CauseDerivationAddForm
                                        {isAddingTodo}
                                        {newTodoType}
                                        {newTodoText}
                                        {predefinedItems}
                                        {selectedPredefinedItem}
                                        {paramValues}
                                        on:startAdd={(e) => startAddTodo(e.detail)}
                                        on:cancel={cancelAddTodo}
                                        on:save={saveNewTodo}
                                        on:selectItem={(e) => selectPredefinedItem(e.detail)}
                                        on:textChange={(e) => (newTodoText = e.detail)}
                                        on:paramChange={(e) => (paramValues[e.detail.paramId] = e.detail.value)}
                                    />

                                    <div class="mt-4 pt-3 border-t border-gray-200 flex items-center justify-end">
                                        {#if phenomenon.workflowCompleted && phenomenon.finalCauseId === cause.id}
                                            <div class="w-full flex items-center justify-between bg-green-50 border border-green-200 rounded px-3 py-2">
                                                <div class="flex items-center gap-2">
                                                    <div class="w-5 h-5 rounded-full bg-green-500 text-white flex items-center justify-center"><svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"/></svg></div>
                                                    <div class="text-xs font-bold text-green-800">최종 원인 확정됨</div>
                                                </div>
                                                <button class="text-[10px] text-gray-500 hover:text-red-600 underline" on:click={revokeFinalCause}>선택 철회</button>
                                            </div>
                                        {:else if causeStatus === 'active' && !phenomenon.workflowCompleted}
                                            <div class="flex items-center gap-2">
                                                <span class="text-[10px] text-gray-400">모든 검증이 완료되었다면:</span>
                                                <button class="flex items-center gap-1.5 px-3 py-1.5 bg-white border border-gray-300 hover:border-green-500 hover:text-green-700 hover:bg-green-50 text-gray-600 text-xs font-medium rounded shadow-sm" on:click={() => finalizeCause(cause.id)}>
                                                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
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
    div::-webkit-scrollbar { width: 4px; }
    div::-webkit-scrollbar-track { background: transparent; }
    div::-webkit-scrollbar-thumb { background-color: #cbd5e1; border-radius: 4px; }
</style>
