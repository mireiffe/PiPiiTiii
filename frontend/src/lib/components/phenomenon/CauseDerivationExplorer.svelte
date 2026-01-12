<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import { slide } from "svelte/transition";
    import type {
        PhenomenonData,
        CandidateCause,
        TodoItem,
        TodoType,
    } from "$lib/types/phenomenon";

    export let phenomenon: PhenomenonData;
    export let workflowActions: { id: string; name: string; params: any[] }[] = [];
    export let workflowConditions: { id: string; name: string; params: any[] }[] = [];

    // Manage local UI state
    let activeCauseId: string | null = null;
    let isAddingTodo = false;
    let newTodoText = "";
    let newTodoType: TodoType = "action";

    // Inline editing state
    let editingTodoId: string | null = null;
    let editingTodoText = "";

    // Drag-and-drop state for todo items
    let draggingTodoId: string | null = null;
    let dragOverTodoId: string | null = null;

    const dispatch = createEventDispatcher<{
        change: PhenomenonData;
    }>();

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
    }

    function cancelAddTodo() {
        isAddingTodo = false;
        newTodoText = "";
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

        cause.todoList = [...(cause.todoList || []), newTodo];
        phenomenon.candidateCauses = [...phenomenon.candidateCauses];
        dispatch("change", phenomenon);

        newTodoText = "";
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

    // ===== Predefined action/condition selection =====
    function selectPredefinedItem(item: { id: string; name: string }) {
        newTodoText = item.name;
    }

    // Reactive: get predefined items based on current todo type
    $: predefinedItems = newTodoType === "condition" ? workflowConditions : workflowActions;
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
                        <!-- svelte-ignore a11y-click-events-have-key-events -->
                        <!-- svelte-ignore a11y-no-static-element-interactions -->
                        <div
                            class="bg-white border rounded-lg shadow-sm transition-all duration-200
                                   {isActive
                                ? 'border-purple-500 ring-1 ring-purple-500 shadow-md transform scale-[1.01]'
                                : 'border-gray-200 hover:border-gray-300'}"
                        >
                            <!-- Cause Header Item -->
                            <div class="flex items-center p-2 gap-2">
                                <!-- Rank Badge -->
                                <div
                                    class="flex-shrink-0 w-6 h-6 rounded-full bg-gray-100 flex items-center justify-center text-xs font-bold text-gray-600 border border-gray-200"
                                >
                                    {index + 1}
                                </div>

                                <!-- Title -->
                                <div
                                    class="flex-1 min-w-0 text-sm cursor-pointer hover:text-purple-700 font-medium {isActive
                                        ? 'text-gray-900'
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
                                                            {/if}
                                                            {#if todo.type === "condition"}
                                                                <div
                                                                    class="mt-1 text-[10px] text-gray-400 flex items-center gap-1"
                                                                >
                                                                    <span
                                                                        >↳ True:
                                                                        다음
                                                                        단계</span
                                                                    >
                                                                    <span
                                                                        class="mx-1"
                                                                        >|</span
                                                                    >
                                                                    <span
                                                                        >False:
                                                                        🛑 중단
                                                                        및 다음
                                                                        후보로</span
                                                                    >
                                                                </div>
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

                                            <div class="text-[10px] text-gray-500 mb-1">
                                                {predefinedItems.length > 0 ? "또는 직접 입력:" : ""}
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
