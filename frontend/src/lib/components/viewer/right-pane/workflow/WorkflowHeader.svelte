<script lang="ts">
    import { createEventDispatcher } from "svelte";
    import type { PhaseType } from "$lib/types/workflow";

    export let isWorkflowConfirmed: boolean = false;
    export let canConfirmWorkflow: boolean = false;
    export let viewMode: "list" | "graph" = "list";
    export let globalPhases: PhaseType[] = [];
    export let showPhaseListPopup: boolean = false;

    let phaseListPopupRef: HTMLDivElement | null = null;

    const dispatch = createEventDispatcher<{
        confirm: void;
        unconfirm: void;
        delete: void;
        viewModeChange: "list" | "graph";
        phasePopupToggle: boolean;
    }>();

    function handleViewModeChange(mode: "list" | "graph") {
        dispatch("viewModeChange", mode);
    }

    function handlePhasePopupToggle() {
        dispatch("phasePopupToggle", !showPhaseListPopup);
    }

    export function getPhaseListPopupRef(): HTMLDivElement | null {
        return phaseListPopupRef;
    }
</script>

<div class="flex items-center gap-1 mr-2">
    <!-- Workflow Confirmation Status / Button -->
    {#if isWorkflowConfirmed}
        <div class="flex items-center gap-1">
            <span
                class="px-2 py-0.5 bg-green-100 text-green-700 text-[10px] font-medium rounded-full flex items-center gap-1"
            >
                <svg
                    class="w-3 h-3"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                >
                    <path
                        fill-rule="evenodd"
                        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                        clip-rule="evenodd"
                    />
                </svg>
                확정됨
            </span>
            <button
                class="px-1.5 py-0.5 text-[10px] text-gray-400 hover:text-gray-600 hover:underline transition-colors"
                on:click|stopPropagation={() => dispatch("unconfirm")}
                title="확정 취소 - 수정 모드로 전환"
            >
                취소
            </button>
        </div>
    {:else if canConfirmWorkflow}
        <button
            class="px-2 py-1 bg-green-600 text-white text-[10px] font-medium rounded-md
                   hover:bg-green-700 transition-colors flex items-center gap-1"
            on:click|stopPropagation={() => dispatch("confirm")}
            title="워크플로우 확정"
        >
            <svg
                class="w-3 h-3"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
            >
                <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M5 13l4 4L19 7"
                />
            </svg>
            확정
        </button>
    {/if}

    <div class="w-px h-4 bg-gray-200 mx-1"></div>

    <!-- View Mode Toggle -->
    <div
        class="flex bg-gray-100 p-0.5 rounded-md border border-gray-200"
    >
        <button
            class="px-1.5 py-0.5 rounded text-[10px] font-medium transition-all {viewMode ===
            'list'
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-400 hover:text-gray-700'}"
            on:click|stopPropagation={() => handleViewModeChange("list")}
        >
            List
        </button>
        <button
            class="px-1.5 py-0.5 rounded text-[10px] font-medium transition-all {viewMode ===
            'graph'
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-400 hover:text-gray-700'}"
            on:click|stopPropagation={() => handleViewModeChange("graph")}
        >
            Graph
        </button>
    </div>

    <!-- Phase Button / Popup -->
    {#if globalPhases.length > 0}
        <div class="relative">
            <button
                class="px-1.5 py-0.5 rounded text-[10px] font-medium bg-purple-100 text-purple-600 border border-purple-200 flex items-center gap-1 hover:bg-purple-200 transition-colors cursor-pointer"
                title="클릭하여 위상 목록 보기"
                on:click|stopPropagation={handlePhasePopupToggle}
            >
                <svg
                    class="w-3 h-3"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"
                    />
                </svg>
                위상 {globalPhases.length}개
                <svg
                    class="w-2.5 h-2.5 ml-0.5 transition-transform {showPhaseListPopup
                        ? 'rotate-180'
                        : ''}"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M19 9l-7 7-7-7"
                    />
                </svg>
            </button>

            <!-- Phase List Popup -->
            {#if showPhaseListPopup}
                <div
                    bind:this={phaseListPopupRef}
                    class="absolute top-full right-0 mt-1 bg-white rounded-lg shadow-lg border border-gray-200 py-2 min-w-[160px] z-50"
                    on:click|stopPropagation
                >
                    <div
                        class="px-3 py-1.5 text-[10px] font-semibold text-gray-400 uppercase tracking-wider border-b border-gray-100 mb-1"
                    >
                        정의된 위상
                    </div>
                    {#each globalPhases as phase (phase.id)}
                        <div
                            class="px-3 py-1.5 flex items-center gap-2 text-xs text-gray-700 hover:bg-gray-50"
                        >
                            <span
                                class="w-3 h-3 rounded-full shrink-0"
                                style="background-color: {phase.color}"
                            ></span>
                            <span class="truncate">{phase.name}</span>
                        </div>
                    {/each}
                    <div class="border-t border-gray-100 mt-1 pt-1">
                        <a
                            href="/settings#section-phases"
                            class="px-3 py-1.5 flex items-center gap-1.5 text-xs text-purple-600 hover:bg-purple-50"
                            on:click={() => dispatch("phasePopupToggle", false)}
                        >
                            <svg
                                class="w-3 h-3"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                            >
                                <path
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    stroke-width="2"
                                    d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                                />
                                <path
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    stroke-width="2"
                                    d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                                />
                            </svg>
                            설정에서 관리
                        </a>
                    </div>
                </div>
            {/if}
        </div>
    {:else}
        <a
            href="/settings#section-phases"
            class="px-1.5 py-0.5 rounded text-[10px] font-medium bg-gray-100 text-gray-400 hover:text-purple-600 hover:bg-purple-50 border border-gray-200 flex items-center gap-1"
            title="설정에서 위상 추가"
        >
            <svg
                class="w-3 h-3"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
            >
                <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M12 6v6m0 0v6m0-6h6m-6 0H6"
                />
            </svg>
            위상 추가
        </a>
    {/if}

    <!-- Delete Workflow Button -->
    <button
        class="p-1 text-gray-300 hover:text-red-500 hover:bg-red-50 rounded transition-colors"
        on:click|stopPropagation={() => dispatch("delete")}
        title="현재 워크플로우 데이터 삭제"
    >
        <svg
            class="w-3.5 h-3.5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
        >
            <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
            />
        </svg>
    </button>
</div>
