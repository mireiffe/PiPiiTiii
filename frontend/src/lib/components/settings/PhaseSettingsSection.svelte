<script lang="ts">
    import { createEventDispatcher } from 'svelte';
    import type { PhaseType } from '$lib/types/workflow';
    import { createId } from '$lib/utils';
    import { reorder, removeById, updateById } from '$lib/utils';

    export let phases: PhaseType[] = [];

    let editingPhaseId: string | null = null;
    let editingName = '';
    let editingColor = '';
    let newPhaseName = '';
    let newPhaseColor = '#a855f7';
    let addingPhase = false;

    // Drag state
    let draggedIndex: number | null = null;
    let dropTargetIndex: number | null = null;

    const PRESET_COLORS = [
        '#a855f7', // Purple
        '#3b82f6', // Blue
        '#10b981', // Green
        '#f59e0b', // Amber
        '#ef4444', // Red
        '#6366f1', // Indigo
        '#ec4899', // Pink
        '#14b8a6', // Teal
    ];

    const dispatch = createEventDispatcher<{
        update: { phases: PhaseType[] };
    }>();

    function emitUpdate() {
        dispatch('update', { phases });
    }

    function addPhase() {
        if (!newPhaseName.trim()) {
            alert('위상 이름을 입력해주세요.');
            return;
        }
        const newPhase: PhaseType = {
            id: createId.phase(),
            name: newPhaseName.trim(),
            color: newPhaseColor,
            order: phases.length,
        };
        phases = [...phases, newPhase];
        newPhaseName = '';
        newPhaseColor = getNextColor();
        addingPhase = false;
        emitUpdate();
    }

    function getNextColor(): string {
        const usedColors = new Set(phases.map(p => p.color));
        return PRESET_COLORS.find(c => !usedColors.has(c)) || PRESET_COLORS[0];
    }

    function removePhase(phaseId: string) {
        if (confirm('이 위상을 삭제하시겠습니까?\n해당 위상을 사용 중인 지원 관계도 함께 삭제됩니다.')) {
            phases = removeById(phases, phaseId).map((p, i) => ({ ...p, order: i }));
            emitUpdate();
        }
    }

    function startEditing(phase: PhaseType) {
        editingPhaseId = phase.id;
        editingName = phase.name;
        editingColor = phase.color;
    }

    function saveEditing() {
        if (!editingName.trim()) {
            alert('이름을 입력해주세요.');
            return;
        }
        phases = updateById(phases, editingPhaseId!, p => ({
            ...p,
            name: editingName.trim(),
            color: editingColor,
        }));
        cancelEditing();
        emitUpdate();
    }

    function cancelEditing() {
        editingPhaseId = null;
        editingName = '';
        editingColor = '';
    }

    function handleKeydown(e: KeyboardEvent) {
        if (e.key === 'Enter') {
            saveEditing();
        } else if (e.key === 'Escape') {
            cancelEditing();
        }
    }

    // Drag and Drop handlers
    function handleDragStart(e: DragEvent, index: number) {
        draggedIndex = index;
        if (e.dataTransfer) {
            e.dataTransfer.effectAllowed = 'move';
        }
    }

    function handleDragOver(e: DragEvent, index: number) {
        e.preventDefault();
        if (draggedIndex === null || draggedIndex === index) return;
        dropTargetIndex = index;
    }

    function handleDragLeave() {
        dropTargetIndex = null;
    }

    function handleDrop(e: DragEvent, index: number) {
        e.preventDefault();
        if (draggedIndex === null || draggedIndex === index) {
            resetDragState();
            return;
        }

        phases = reorder(phases, draggedIndex, index).map((p, i) => ({ ...p, order: i }));
        emitUpdate();
        resetDragState();
    }

    function handleDragEnd() {
        resetDragState();
    }

    function resetDragState() {
        draggedIndex = null;
        dropTargetIndex = null;
    }
</script>

<div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
    <div class="flex justify-between items-center mb-4">
        <div>
            <h2 class="text-xl font-bold text-gray-800">위상 (Phase) 설정</h2>
            <p class="text-sm text-gray-500 mt-1">
                Workflow에서 Step간 지원 관계를 분류할 위상을 정의합니다. 드래그로 순서를 변경할 수 있습니다.
            </p>
        </div>
        <div class="flex gap-2">
            {#if addingPhase}
                <div class="flex items-center gap-2">
                    <input
                        type="color"
                        bind:value={newPhaseColor}
                        class="w-8 h-8 rounded cursor-pointer border border-gray-300"
                    />
                    <input
                        type="text"
                        bind:value={newPhaseName}
                        placeholder="위상 이름"
                        class="border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                        on:keypress={(e) => e.key === 'Enter' && addPhase()}
                    />
                    <button
                        class="bg-purple-600 text-white px-3 py-1.5 rounded text-sm hover:bg-purple-700"
                        on:click={addPhase}
                    >
                        추가
                    </button>
                    <button
                        class="text-gray-500 px-2 py-1.5 text-sm hover:text-gray-700"
                        on:click={() => {
                            addingPhase = false;
                            newPhaseName = '';
                        }}
                    >
                        취소
                    </button>
                </div>
            {:else}
                <button
                    class="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 transition text-sm font-medium"
                    on:click={() => {
                        addingPhase = true;
                        newPhaseColor = getNextColor();
                    }}
                >
                    + 위상 추가
                </button>
            {/if}
        </div>
    </div>

    <div class="space-y-2">
        {#if phases.length === 0}
            <div class="text-center text-gray-400 py-8 border border-dashed border-gray-300 rounded-lg">
                <div class="text-purple-400 mb-2">
                    <svg class="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
                    </svg>
                </div>
                정의된 위상이 없습니다. 위상을 추가하면 Workflow에서 Step간 지원 관계를 만들 수 있습니다.
            </div>
        {:else}
            {#each phases as phase, index (phase.id)}
                <div
                    class="border rounded-lg bg-gray-50 overflow-hidden transition-all
                        {draggedIndex === index ? 'opacity-50' : ''}
                        {dropTargetIndex === index ? 'border-purple-500 border-2' : 'border-gray-200'}"
                    draggable="true"
                    on:dragstart={(e) => handleDragStart(e, index)}
                    on:dragover={(e) => handleDragOver(e, index)}
                    on:dragleave={handleDragLeave}
                    on:drop={(e) => handleDrop(e, index)}
                    on:dragend={handleDragEnd}
                    role="listitem"
                >
                    <div class="flex items-center gap-3 p-4">
                        <!-- Drag Handle -->
                        <div class="cursor-grab text-gray-400 hover:text-gray-600">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8h16M4 16h16" />
                            </svg>
                        </div>

                        <!-- Color Indicator -->
                        {#if editingPhaseId === phase.id}
                            <input
                                type="color"
                                bind:value={editingColor}
                                class="w-8 h-8 rounded cursor-pointer border border-gray-300"
                            />
                        {:else}
                            <div
                                class="w-8 h-8 rounded-full shadow-sm"
                                style="background-color: {phase.color}"
                            ></div>
                        {/if}

                        <!-- Name (Editable) -->
                        <div class="flex-1">
                            {#if editingPhaseId === phase.id}
                                <input
                                    type="text"
                                    bind:value={editingName}
                                    on:keydown={handleKeydown}
                                    class="border border-purple-400 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 w-full max-w-xs"
                                    autofocus
                                />
                            {:else}
                                <button
                                    class="text-sm font-medium text-gray-800 hover:text-purple-600 cursor-pointer text-left"
                                    on:click={() => startEditing(phase)}
                                    title="클릭하여 편집"
                                >
                                    {phase.name}
                                </button>
                            {/if}
                        </div>

                        <!-- Action Buttons -->
                        {#if editingPhaseId === phase.id}
                            <button
                                class="bg-purple-600 text-white px-3 py-1.5 rounded text-sm hover:bg-purple-700"
                                on:click={saveEditing}
                            >
                                저장
                            </button>
                            <button
                                class="text-gray-500 px-2 py-1.5 text-sm hover:text-gray-700"
                                on:click={cancelEditing}
                            >
                                취소
                            </button>
                        {:else}
                            <button
                                class="text-gray-500 hover:text-purple-600 px-2 py-1 rounded transition text-sm"
                                on:click={() => startEditing(phase)}
                                title="편집"
                            >
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                </svg>
                            </button>
                            <button
                                class="bg-red-500 text-white px-3 py-1.5 rounded hover:bg-red-600 transition text-sm font-medium"
                                on:click={() => removePhase(phase.id)}
                            >
                                삭제
                            </button>
                        {/if}
                    </div>
                </div>
            {/each}
        {/if}
    </div>
</div>
