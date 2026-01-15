<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import type { StepContainer } from "$lib/types/workflow";
    import { generateContainerId } from "$lib/types/workflow";

    export let containers: StepContainer[] = [];

    let editingContainerId: string | null = null;
    let editingName = "";
    let newContainerName = "";
    let addingContainer = false;

    // Drag state
    let draggedIndex: number | null = null;
    let dropTargetIndex: number | null = null;

    const dispatch = createEventDispatcher<{
        update: { containers: StepContainer[] };
    }>();

    function addContainer() {
        if (!newContainerName.trim()) {
            alert("Container 이름을 입력해주세요.");
            return;
        }
        const newContainer: StepContainer = {
            id: generateContainerId(),
            name: newContainerName.trim(),
            order: containers.length,
        };
        containers = [...containers, newContainer];
        newContainerName = "";
        addingContainer = false;
        dispatch("update", { containers });
    }

    function removeContainer(containerId: string) {
        if (confirm("이 Container를 삭제하시겠습니까?\n해당 Container에 속한 스텝들은 '미분류'로 이동됩니다.")) {
            containers = containers
                .filter((c) => c.id !== containerId)
                .map((c, i) => ({ ...c, order: i }));
            dispatch("update", { containers });
        }
    }

    function startEditing(container: StepContainer) {
        editingContainerId = container.id;
        editingName = container.name;
    }

    function saveEditing() {
        if (!editingName.trim()) {
            alert("이름을 입력해주세요.");
            return;
        }
        containers = containers.map((c) =>
            c.id === editingContainerId ? { ...c, name: editingName.trim() } : c
        );
        editingContainerId = null;
        editingName = "";
        dispatch("update", { containers });
    }

    function cancelEditing() {
        editingContainerId = null;
        editingName = "";
    }

    function handleKeydown(e: KeyboardEvent) {
        if (e.key === "Enter") {
            saveEditing();
        } else if (e.key === "Escape") {
            cancelEditing();
        }
    }

    // Drag and Drop handlers
    function handleDragStart(e: DragEvent, index: number) {
        draggedIndex = index;
        if (e.dataTransfer) {
            e.dataTransfer.effectAllowed = "move";
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

        const newContainers = [...containers];
        const [removed] = newContainers.splice(draggedIndex, 1);
        newContainers.splice(index, 0, removed);

        // Update order
        containers = newContainers.map((c, i) => ({ ...c, order: i }));
        dispatch("update", { containers });
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
            <h2 class="text-xl font-bold text-gray-800">Step Containers</h2>
            <p class="text-sm text-gray-500 mt-1">
                Workflow Step들을 그룹화할 Container를 정의합니다. 드래그로 순서를 변경할 수 있습니다.
            </p>
        </div>
        <div class="flex gap-2">
            {#if addingContainer}
                <div class="flex items-center gap-2">
                    <input
                        type="text"
                        bind:value={newContainerName}
                        placeholder="Container 이름"
                        class="border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        on:keypress={(e) => e.key === "Enter" && addContainer()}
                    />
                    <button
                        class="bg-blue-600 text-white px-3 py-1.5 rounded text-sm hover:bg-blue-700"
                        on:click={addContainer}
                    >
                        추가
                    </button>
                    <button
                        class="text-gray-500 px-2 py-1.5 text-sm hover:text-gray-700"
                        on:click={() => {
                            addingContainer = false;
                            newContainerName = "";
                        }}
                    >
                        취소
                    </button>
                </div>
            {:else}
                <button
                    class="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition text-sm font-medium"
                    on:click={() => (addingContainer = true)}
                >
                    + Container 추가
                </button>
            {/if}
        </div>
    </div>

    <div class="space-y-2">
        {#if containers.length === 0}
            <div
                class="text-center text-gray-400 py-8 border border-dashed border-gray-300 rounded-lg"
            >
                정의된 Container가 없습니다. Container를 추가해주세요.
            </div>
        {:else}
            {#each containers as container, index (container.id)}
                <div
                    class="border rounded-lg bg-gray-50 overflow-hidden transition-all
                        {draggedIndex === index ? 'opacity-50' : ''}
                        {dropTargetIndex === index ? 'border-blue-500 border-2' : 'border-gray-200'}"
                    draggable="true"
                    on:dragstart={(e) => handleDragStart(e, index)}
                    on:dragover={(e) => handleDragOver(e, index)}
                    on:dragleave={handleDragLeave}
                    on:drop={(e) => handleDrop(e, index)}
                    on:dragend={handleDragEnd}
                >
                    <div class="flex items-center gap-3 p-4">
                        <!-- Drag Handle -->
                        <div class="cursor-grab text-gray-400 hover:text-gray-600">
                            <svg
                                class="w-5 h-5"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                            >
                                <path
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    stroke-width="2"
                                    d="M4 8h16M4 16h16"
                                />
                            </svg>
                        </div>

                        <!-- Order Number -->
                        <span
                            class="text-xs font-medium text-gray-400 bg-gray-200 rounded-full w-6 h-6 flex items-center justify-center"
                        >
                            {index + 1}
                        </span>

                        <!-- Name (Editable) -->
                        <div class="flex-1">
                            {#if editingContainerId === container.id}
                                <input
                                    type="text"
                                    bind:value={editingName}
                                    on:keydown={handleKeydown}
                                    on:blur={saveEditing}
                                    class="border border-blue-400 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-full max-w-xs"
                                    autofocus
                                />
                            {:else}
                                <button
                                    class="text-sm font-medium text-gray-800 hover:text-blue-600 cursor-pointer text-left"
                                    on:click={() => startEditing(container)}
                                    title="클릭하여 이름 편집"
                                >
                                    {container.name}
                                </button>
                            {/if}
                        </div>

                        <!-- Edit Button -->
                        {#if editingContainerId !== container.id}
                            <button
                                class="text-gray-500 hover:text-blue-600 px-2 py-1 rounded transition text-sm"
                                on:click={() => startEditing(container)}
                                title="이름 편집"
                            >
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
                                        d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                                    />
                                </svg>
                            </button>
                        {/if}

                        <!-- Delete Button -->
                        <button
                            class="bg-red-500 text-white px-3 py-1.5 rounded hover:bg-red-600 transition text-sm font-medium"
                            on:click={() => removeContainer(container.id)}
                        >
                            삭제
                        </button>
                    </div>
                </div>
            {/each}
        {/if}
    </div>
</div>
