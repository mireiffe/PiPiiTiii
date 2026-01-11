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

    // Manage local UI state
    let activeCauseId: string | null = null;
    let isAddingTodo = false;
    let newTodoText = "";
    let newTodoType: TodoType = "action";

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
                                            {#each cause.todoList as todo, tIndex}
                                                <div
                                                    class="relative pl-4 border-l-2 {todo.type ===
                                                    'condition'
                                                        ? 'border-orange-300'
                                                        : 'border-blue-300'} ml-1"
                                                >
                                                    <div
                                                        class="flex items-start justify-between group"
                                                    >
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
                                                            <div
                                                                class="text-gray-800 leading-snug"
                                                            >
                                                                {todo.text}
                                                            </div>
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
