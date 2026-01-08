<script>
    import { slide } from "svelte/transition";
    import { marked } from "marked";
    import { createEventDispatcher } from "svelte";
    import WorkflowTree from "$lib/components/WorkflowTree.svelte";

    export let rightPaneFullscreen = false;
    export let rightPaneWidth = 300;
    export let expandedSection = null;
    export let workflowData;
    export let settings;
    export let allowEdit;
    export let savingWorkflow;
    export let summaryData;
    export let summaryDataLLM;
    export let savingSummary;
    export let generatingFieldIds;
    export let generatingAll;
    export let selectedSlideIndices = [];
    export let comparingFieldId = null;
    export let editingFieldId = null;
    export let allShapes = [];
    export let selectedShapeId = null;
    export let editingDescription = "";
    export let project;

    const dispatch = createEventDispatcher();

    let showSlideSelector = false;

    // Derived shapes
    $: imageShapes = allShapes.filter((s) => s.type_name === "Picture");
    $: textShapes = allShapes.filter(
        (s) => s.type_name === "TextBox" || s.type_name === "Title",
    );
    $: otherShapes = allShapes.filter(
        (s) =>
            s.type_name !== "Picture" &&
            s.type_name !== "TextBox" &&
            s.type_name !== "Title",
    );

    $: selectedShape = allShapes.find((s) => s.shape_index === selectedShapeId);
</script>

<div
    class="bg-white border-l border-gray-200 flex flex-col {rightPaneFullscreen
        ? 'flex-1'
        : 'shrink-0'}"
    style={rightPaneFullscreen ? "" : `width: ${rightPaneWidth}px;`}
>
    <!-- Header -->
    <div class="p-4 border-b border-gray-200 flex items-center justify-between">
        <h2 class="font-bold text-gray-800">프로젝트 정보</h2>
        <button
            class="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-lg transition-all
                   {rightPaneFullscreen
                ? 'bg-blue-100 text-blue-700 hover:bg-blue-200'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}"
            on:click={() => (rightPaneFullscreen = !rightPaneFullscreen)}
            title={rightPaneFullscreen ? "일반 보기" : "전체 보기"}
        >
            {#if rightPaneFullscreen}
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
                        d="M9 9V4.5M9 9H4.5M9 9L3.5 3.5M9 15v4.5M9 15H4.5M9 15l-5.5 5.5M15 9h4.5M15 9V4.5M15 9l5.5-5.5M15 15h4.5M15 15v4.5m0-4.5l5.5 5.5"
                    />
                </svg>
                <span>일반</span>
            {:else}
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
                        d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"
                    />
                </svg>
                <span>전체</span>
            {/if}
        </button>
    </div>

    <div class="flex-1 overflow-y-auto min-h-0 flex flex-col">
        <!-- ====== ACCORDION SECTION 1: Workflow ====== -->
        <div
            class="border-b border-gray-200 {expandedSection === 'workflow'
                ? 'flex-1 flex flex-col min-h-0'
                : ''}"
        >
            <button
                class="w-full flex items-center justify-between px-4 py-2 cursor-pointer hover:bg-gray-50 transition-all font-medium text-gray-700 hover:text-blue-600 focus:outline-none"
                on:click={() =>
                    (expandedSection =
                        expandedSection === "workflow" ? null : "workflow")}
            >
                <div class="flex items-center gap-2.5">
                    <span class="text-lg">🔄</span>
                    <span class="font-bold text-sm tracking-wide"
                        >워크플로우</span
                    >
                    {#if savingWorkflow}
                        <span
                            class="text-xs font-normal text-blue-500 animate-pulse bg-blue-50 px-2 py-0.5 rounded-full"
                            >저장 중...</span
                        >
                    {/if}
                </div>
                <svg
                    class="w-4 h-4 text-gray-400 transition-transform duration-300 ease-in-out {expandedSection ===
                    'workflow'
                        ? 'rotate-180 text-blue-500'
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
            {#if expandedSection === "workflow"}
                <div
                    transition:slide={{ duration: 200, axis: "y" }}
                    class="border-t border-gray-100 bg-gray-50/30 flex-1 flex flex-col min-h-0"
                >
                    <div class="px-4 py-3 bg-white border-b border-gray-100">
                        <label
                            class="block text-xs font-semibold text-gray-500 mb-1.5 flex items-center justify-between"
                        >
                            <span>✨ AI 워크플로우 수정</span>
                            {#if !workflowData}
                                <span class="text-[10px] text-red-400"
                                    >워크플로우가 없습니다</span
                                >
                            {/if}
                        </label>
                        <div class="relative">
                            <textarea
                                class="w-full text-xs p-2.5 pr-10 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none bg-gray-50 focus:bg-white transition-colors"
                                rows="2"
                                placeholder="예: 검사 노드 추가해줘, 분석 파라미터를 필수로 변경해줘..."
                                on:keydown={(e) => {
                                    if (e.key === "Enter" && !e.shiftKey) {
                                        e.preventDefault();
                                        dispatch(
                                            "generateWorkflow",
                                            e.currentTarget.value,
                                        );
                                        e.currentTarget.value = "";
                                    }
                                }}
                            ></textarea>
                            <button
                                class="absolute right-2 bottom-2 text-blue-500 hover:text-blue-600 disabled:opacity-50"
                                title="전송"
                                on:click={(e) => {
                                    const textarea =
                                        e.currentTarget.previousElementSibling;
                                    if (textarea.value.trim()) {
                                        dispatch(
                                            "generateWorkflow",
                                            textarea.value,
                                        );
                                        textarea.value = "";
                                    }
                                }}
                            >
                                <svg
                                    class="w-4 h-4"
                                    fill="none"
                                    stroke="currentColor"
                                    viewBox="0 0 24 24"
                                    ><path
                                        stroke-linecap="round"
                                        stroke-linejoin="round"
                                        stroke-width="2"
                                        d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                                    ></path></svg
                                >
                            </button>
                        </div>
                    </div>
                    <div class="flex-1 h-full overflow-auto custom-scrollbar">
                        <WorkflowTree
                            workflow={workflowData}
                            workflowActions={settings.workflow_actions || []}
                            readonly={false}
                            on:change={(e) =>
                                dispatch("workflowChange", e.detail)}
                        />
                    </div>
                </div>
            {/if}
        </div>

        <!-- ====== ACCORDION SECTION 2: Summary ====== -->
        <div
            class="border-b border-gray-200 {expandedSection === 'summary'
                ? 'flex-1 flex flex-col min-h-0'
                : ''}"
        >
            <button
                class="w-full flex items-center justify-between px-4 py-2 cursor-pointer hover:bg-gray-50 transition-all font-medium text-gray-700 hover:text-blue-600 focus:outline-none"
                on:click={() =>
                    (expandedSection =
                        expandedSection === "summary" ? null : "summary")}
            >
                <div class="flex items-center gap-2.5">
                    <span class="text-lg">📄</span>
                    <span class="font-bold text-sm tracking-wide"
                        >요약 정보</span
                    >
                    {#if savingSummary}
                        <span
                            class="text-xs font-normal text-blue-500 animate-pulse bg-blue-50 px-2 py-0.5 rounded-full"
                            >저장 중...</span
                        >
                    {/if}
                </div>
                <svg
                    class="w-4 h-4 text-gray-400 transition-transform duration-300 ease-in-out {expandedSection ===
                    'summary'
                        ? 'rotate-180 text-blue-500'
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
            {#if expandedSection === "summary"}
                <div
                    transition:slide={{ duration: 200, axis: "y" }}
                    class="border-t border-gray-100 bg-gray-50/30 flex-1 flex flex-col min-h-0"
                >
                    <div
                        class="p-5 space-y-5 flex-1 h-full overflow-y-auto custom-scrollbar"
                    >
                        <div class="flex items-center justify-end">
                            {#if settings.summary_fields && settings.summary_fields.length > 0}
                                <button
                                    on:click={() =>
                                        dispatch("generateAllSummaries")}
                                    disabled={generatingFieldIds.size > 0 ||
                                        generatingAll}
                                    title="모든 요약 필드를 LLM으로 자동 생성"
                                    class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg
                                        bg-gradient-to-r from-purple-500 to-indigo-600 hover:from-purple-600 hover:to-indigo-700
                                        text-white shadow-sm hover:shadow-md transition-all duration-200
                                        disabled:opacity-50 disabled:cursor-not-allowed active:scale-95"
                                >
                                    {#if generatingAll}
                                        <svg
                                            class="animate-spin h-3.5 w-3.5"
                                            viewBox="0 0 24 24"
                                        >
                                            <circle
                                                class="opacity-25"
                                                cx="12"
                                                cy="12"
                                                r="10"
                                                stroke="currentColor"
                                                stroke-width="4"
                                                fill="none"
                                            ></circle>
                                            <path
                                                class="opacity-75"
                                                fill="currentColor"
                                                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                                            ></path>
                                        </svg>
                                    {:else}
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
                                                d="M13 10V3L4 14h7v7l9-11h-7z"
                                            />
                                        </svg>
                                    {/if}
                                    <span>전체 자동 생성</span>
                                </button>
                            {/if}
                        </div>

                        <!-- Slide Selection for Summary -->
                        {#if settings.summary_fields && settings.summary_fields.length > 0}
                            <div
                                class="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm"
                            >
                                <button
                                    class="w-full flex items-center justify-between p-3.5 text-left hover:bg-gray-50 transition-colors"
                                    on:click={() =>
                                        (showSlideSelector =
                                            !showSlideSelector)}
                                >
                                    <div
                                        class="flex items-center gap-2 overflow-hidden"
                                    >
                                        <span
                                            class="text-xs font-semibold text-gray-500 whitespace-nowrap uppercase tracking-wider"
                                            >참조 슬라이드</span
                                        >
                                        <div class="flex gap-1 overflow-hidden">
                                            {#if selectedSlideIndices.length === 0}
                                                <span
                                                    class="text-xs text-gray-400 italic"
                                                    >선택 없음</span
                                                >
                                            {:else}
                                                {#each selectedSlideIndices.sort((a, b) => a - b) as idx}
                                                    <span
                                                        class="bg-blue-50 border border-blue-100 text-blue-600 text-[10px] font-medium px-2 py-0.5 rounded-full"
                                                    >
                                                        #{idx}
                                                    </span>
                                                {/each}
                                            {/if}
                                        </div>
                                    </div>
                                    <svg
                                        class="w-4 h-4 text-gray-400 transform transition-transform {showSlideSelector
                                            ? 'rotate-180'
                                            : ''}"
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

                                {#if showSlideSelector}
                                    <div
                                        class="p-4 bg-gray-50/50 border-t border-gray-100 animate-in fade-in slide-in-from-top-1 duration-200"
                                    >
                                        <div
                                            class="flex items-center justify-between mb-3"
                                        >
                                            <p
                                                class="text-[11px] text-gray-400 flex items-center gap-1"
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
                                                        d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                                                    /></svg
                                                >
                                                최대 3개 선택 가능
                                            </p>
                                        </div>
                                        <div
                                            class="grid grid-cols-5 gap-1.5 max-h-32 overflow-y-auto p-1"
                                        >
                                            {#if project}
                                                {#each project.slides as slide}
                                                    <button
                                                        class="text-xs p-2 rounded-lg border transition-all flex flex-col items-center justify-center gap-1 {selectedSlideIndices.includes(
                                                            slide.slide_index,
                                                        )
                                                            ? 'bg-blue-50 text-blue-600 border-blue-200 ring-2 ring-blue-100 font-bold'
                                                            : 'bg-white text-gray-500 border-gray-200 hover:border-blue-200 hover:text-blue-500 shadow-sm'}
                                                            {selectedSlideIndices.length >=
                                                            3 &&
                                                        !selectedSlideIndices.includes(
                                                            slide.slide_index,
                                                        )
                                                            ? 'opacity-40 cursor-not-allowed grayscale'
                                                            : ''}"
                                                        on:click={() =>
                                                            dispatch(
                                                                "toggleSlideSelection",
                                                                {
                                                                    slideIndex:
                                                                        slide.slide_index,
                                                                },
                                                            )}
                                                        disabled={selectedSlideIndices.length >=
                                                            3 &&
                                                            !selectedSlideIndices.includes(
                                                                slide.slide_index,
                                                            )}
                                                    >
                                                        <span class=""
                                                            >{slide.slide_index}</span
                                                        >
                                                    </button>
                                                {/each}
                                            {/if}
                                        </div>
                                    </div>
                                {/if}
                            </div>
                        {/if}

                        <!-- Summary Fields -->
                        {#if settings.summary_fields && settings.summary_fields.length > 0}
                            <div class="space-y-6">
                                {#each settings.summary_fields.sort((a, b) => a.order - b.order) as field}
                                    <div class="group">
                                        <div
                                            class="flex items-center justify-between mb-2"
                                        >
                                            <div
                                                class="flex items-center gap-2"
                                            >
                                                <div
                                                    class="h-4 w-1 bg-gradient-to-b from-indigo-500 to-purple-500 rounded-full"
                                                ></div>
                                                <label
                                                    class="text-sm font-bold text-gray-700 tracking-tight"
                                                >
                                                    {field.name}
                                                </label>
                                                <!-- Compare button -->
                                                {#if summaryDataLLM[field.id] && summaryDataLLM[field.id] !== summaryData[field.id]}
                                                    <button
                                                        class="text-[9px] px-2 py-0.5 rounded-full transition-all flex items-center gap-1 ml-1 {comparingFieldId ===
                                                        field.id
                                                            ? 'bg-amber-100 text-amber-700 border border-amber-200 shadow-sm'
                                                            : 'bg-gray-100 text-gray-500 hover:bg-amber-50 hover:text-amber-600 border border-transparent hover:border-amber-200'}"
                                                        on:click={() =>
                                                            dispatch(
                                                                "toggleCompare",
                                                                {
                                                                    fieldId:
                                                                        field.id,
                                                                },
                                                            )}
                                                        title={comparingFieldId ===
                                                        field.id
                                                            ? "비교 닫기"
                                                            : "LLM 버전과 비교"}
                                                    >
                                                        <svg
                                                            class="w-2.5 h-2.5"
                                                            fill="none"
                                                            stroke="currentColor"
                                                            viewBox="0 0 24 24"
                                                        >
                                                            <path
                                                                stroke-linecap="round"
                                                                stroke-linejoin="round"
                                                                stroke-width="2"
                                                                d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                                                            />
                                                        </svg>
                                                        <span
                                                            >{comparingFieldId ===
                                                            field.id
                                                                ? "닫기"
                                                                : "비교"}</span
                                                        >
                                                    </button>
                                                {/if}
                                            </div>
                                            <button
                                                class="flex items-center gap-1.5 px-2.5 py-1.5 text-[10px] font-bold rounded-lg
                                                bg-white border border-indigo-100 text-indigo-600 hover:bg-indigo-50 hover:border-indigo-200
                                                shadow-sm hover:shadow transition-all duration-200
                                                disabled:opacity-50 disabled:cursor-not-allowed group-hover:opacity-100 opacity-0 transition-opacity"
                                                class:opacity-100={generatingFieldIds.has(
                                                    field.id,
                                                )}
                                                on:click={() =>
                                                    dispatch(
                                                        "generateSummaryForField",
                                                        { fieldId: field.id },
                                                    )}
                                                disabled={generatingFieldIds.has(
                                                    field.id,
                                                ) || generatingAll}
                                                title="이 항목을 LLM으로 자동 생성"
                                            >
                                                {#if generatingFieldIds.has(field.id)}
                                                    <svg
                                                        class="animate-spin w-3 h-3"
                                                        viewBox="0 0 24 24"
                                                    >
                                                        <circle
                                                            class="opacity-25"
                                                            cx="12"
                                                            cy="12"
                                                            r="10"
                                                            stroke="currentColor"
                                                            stroke-width="4"
                                                            fill="none"
                                                        ></circle>
                                                        <path
                                                            class="opacity-75"
                                                            fill="currentColor"
                                                            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                                                        ></path>
                                                    </svg>
                                                {:else}
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
                                                            d="M13 10V3L4 14h7v7l9-11h-7z"
                                                        />
                                                    </svg>
                                                {/if}
                                                <span>자동 생성</span>
                                            </button>
                                        </div>

                                        <!-- Comparison View -->
                                        {#if comparingFieldId === field.id && summaryDataLLM[field.id]}
                                            <div
                                                class="mb-3 p-3 bg-amber-50/80 border border-amber-200 rounded-xl"
                                            >
                                                <div
                                                    class="flex items-center justify-between mb-2"
                                                >
                                                    <span
                                                        class="text-[10px] font-bold text-amber-700 uppercase tracking-wide flex items-center gap-1.5"
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
                                                                d="M19.428 15.428a2 2 0 00-1.022-.547l-2.384-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"
                                                            /></svg
                                                        >
                                                        LLM 생성 버전
                                                    </span>
                                                    <button
                                                        class="text-[9px] px-2 py-1 bg-white hover:bg-amber-50 text-amber-600 border border-amber-200 rounded-lg transition-all flex items-center gap-1.5 shadow-sm"
                                                        on:click={() =>
                                                            dispatch(
                                                                "restoreLLMVersion",
                                                                {
                                                                    fieldId:
                                                                        field.id,
                                                                },
                                                            )}
                                                        title="LLM 버전으로 되돌리기"
                                                    >
                                                        <svg
                                                            class="w-2.5 h-2.5"
                                                            fill="none"
                                                            stroke="currentColor"
                                                            viewBox="0 0 24 24"
                                                        >
                                                            <path
                                                                stroke-linecap="round"
                                                                stroke-linejoin="round"
                                                                stroke-width="2"
                                                                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                                                            />
                                                        </svg>
                                                        <span>복원하기</span>
                                                    </button>
                                                </div>
                                                <div
                                                    class="text-xs text-amber-900/80 leading-relaxed max-h-48 overflow-y-auto prose prose-sm prose-amber bg-white/50 p-2 rounded-lg border border-amber-100"
                                                >
                                                    {@html marked(
                                                        summaryDataLLM[
                                                            field.id
                                                        ] || "",
                                                    )}
                                                </div>
                                            </div>
                                        {/if}

                                        <div class="relative group/edit">
                                            <!-- Edit/Preview Toggle -->
                                            <div
                                                class="flex justify-end mb-0 absolute right-2 top-2 z-10 opacity-0 group-hover/edit:opacity-100 transition-opacity"
                                            >
                                                <div
                                                    class="inline-flex rounded-lg border border-gray-200 p-0.5 bg-white shadow-sm"
                                                >
                                                    <button
                                                        class="px-2.5 py-1 text-[10px] font-medium rounded-md transition-all {editingFieldId ===
                                                        field.id
                                                            ? 'bg-gray-100 text-gray-900'
                                                            : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'}"
                                                        on:click={() =>
                                                            (editingFieldId =
                                                                field.id)}
                                                    >
                                                        편집
                                                    </button>
                                                    <button
                                                        class="px-2.5 py-1 text-[10px] font-medium rounded-md transition-all {editingFieldId !==
                                                        field.id
                                                            ? 'bg-gray-100 text-gray-900'
                                                            : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'}"
                                                        on:click={() => {
                                                            editingFieldId =
                                                                null;
                                                            dispatch(
                                                                "saveSummary",
                                                            );
                                                        }}
                                                    >
                                                        미리보기
                                                    </button>
                                                </div>
                                            </div>

                                            {#if editingFieldId === field.id}
                                                <!-- Edit Mode -->
                                                <textarea
                                                    class="w-full text-base leading-relaxed p-4 border border-gray-200 rounded-xl shadow-sm focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all placeholder-gray-300 resize-y min-h-[320px] hover:border-gray-300 {generatingFieldIds.has(
                                                        field.id,
                                                    )
                                                        ? 'bg-indigo-50/30'
                                                        : 'bg-white'}"
                                                    style="font-size: 15px;"
                                                    rows="12"
                                                    placeholder="{field.name}에 대한 내용을 입력하세요... (자동 저장됨)"
                                                    bind:value={
                                                        summaryData[field.id]
                                                    }
                                                    on:blur={() =>
                                                        dispatch("saveSummary")}
                                                    on:keydown={(e) => {
                                                        if (
                                                            (e.ctrlKey ||
                                                                e.metaKey) &&
                                                            e.key === "s"
                                                        ) {
                                                            e.preventDefault();
                                                            dispatch(
                                                                "saveSummary",
                                                            );
                                                            editingFieldId =
                                                                null;
                                                            e.target.blur();
                                                        }
                                                    }}
                                                    disabled={generatingFieldIds.has(
                                                        field.id,
                                                    )}
                                                ></textarea>
                                            {:else}
                                                <!-- Preview Mode (Markdown Rendered) -->
                                                <!-- svelte-ignore a11y-click-events-have-key-events -->
                                                <!-- svelte-ignore a11y-no-static-element-interactions -->
                                                <div
                                                    class="w-full min-h-[120px] p-4 border border-gray-200 rounded-xl shadow-sm bg-white cursor-pointer hover:border-indigo-300 hover:shadow-md transition-all overflow-hidden relative group-hover/edit:border-gray-300"
                                                    on:click={() =>
                                                        (editingFieldId =
                                                            field.id)}
                                                    title="클릭하여 편집"
                                                >
                                                    {#if summaryData[field.id]}
                                                        <div
                                                            class="prose prose-sm max-w-none prose-headings:text-gray-800 prose-p:text-gray-600 prose-strong:text-gray-700 prose-ul:text-gray-600 prose-ol:text-gray-600"
                                                        >
                                                            {@html marked(
                                                                summaryData[
                                                                    field.id
                                                                ] || "",
                                                            )}
                                                        </div>
                                                    {:else}
                                                        <p
                                                            class="text-gray-300 italic text-sm flex items-center justify-center py-8"
                                                        >
                                                            {field.name} 내용을 입력하려면
                                                            클릭하세요...
                                                        </p>
                                                    {/if}
                                                </div>
                                            {/if}

                                            {#if generatingFieldIds.has(field.id)}
                                                <div
                                                    class="absolute inset-0 flex items-center justify-center bg-white/60 backdrop-blur-[2px] rounded-xl z-20"
                                                >
                                                    <div
                                                        class="flex flex-col items-center gap-3 text-indigo-600"
                                                    >
                                                        <div class="relative">
                                                            <div
                                                                class="absolute inset-0 bg-indigo-200 rounded-full animate-ping opacity-75"
                                                            ></div>
                                                            <div
                                                                class="relative bg-white p-2 rounded-full shadow-sm"
                                                            >
                                                                <svg
                                                                    class="animate-spin h-6 w-6"
                                                                    viewBox="0 0 24 24"
                                                                >
                                                                    <circle
                                                                        class="opacity-25"
                                                                        cx="12"
                                                                        cy="12"
                                                                        r="10"
                                                                        stroke="currentColor"
                                                                        stroke-width="4"
                                                                        fill="none"
                                                                    ></circle>
                                                                    <path
                                                                        class="opacity-75"
                                                                        fill="currentColor"
                                                                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                                                                    ></path>
                                                                </svg>
                                                            </div>
                                                        </div>
                                                        <span
                                                            class="text-xs font-bold tracking-wide animate-pulse"
                                                            >AI 작성 중...</span
                                                        >
                                                    </div>
                                                </div>
                                            {/if}
                                        </div>
                                    </div>
                                {/each}
                            </div>
                        {:else}
                            <div
                                class="text-center py-12 bg-gray-50 rounded-xl border border-dashed border-gray-200 flex flex-col items-center gap-3"
                            >
                                <div class="bg-gray-100 p-3 rounded-full">
                                    <svg
                                        class="w-6 h-6 text-gray-400"
                                        fill="none"
                                        stroke="currentColor"
                                        viewBox="0 0 24 24"
                                        ><path
                                            stroke-linecap="round"
                                            stroke-linejoin="round"
                                            stroke-width="2"
                                            d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
                                        /></svg
                                    >
                                </div>
                                <div>
                                    <p
                                        class="text-sm font-medium text-gray-600 mb-1"
                                    >
                                        요약 필드가 없습니다
                                    </p>
                                    <p class="text-xs text-gray-400">
                                        설정에서 요약 필드를 추가해주세요.
                                    </p>
                                </div>
                            </div>
                        {/if}
                    </div>
                </div>
            {/if}
        </div>

        <!-- ====== ACCORDION SECTION 3: Object List ====== -->
        <div
            class="border-b border-gray-200 {expandedSection === 'objects'
                ? 'flex-1 flex flex-col min-h-0'
                : ''}"
        >
            <button
                class="w-full flex items-center justify-between px-4 py-2 cursor-pointer hover:bg-gray-50 transition-all font-medium text-gray-700 hover:text-blue-600 focus:outline-none"
                on:click={() =>
                    (expandedSection =
                        expandedSection === "objects" ? null : "objects")}
            >
                <div class="flex items-center gap-2.5">
                    <span class="text-lg">📦</span>
                    <span class="font-bold text-sm tracking-wide"
                        >객체 목록</span
                    >
                    <span
                        class="bg-blue-50 text-blue-600 border border-blue-100 text-xs px-2 py-0.5 rounded-full font-mono"
                        >{allShapes.length}</span
                    >
                </div>
                <svg
                    class="w-4 h-4 text-gray-400 transition-transform duration-300 ease-in-out {expandedSection ===
                    'objects'
                        ? 'rotate-180 text-blue-500'
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

            {#if expandedSection === "objects"}
                <div
                    transition:slide={{ duration: 200, axis: "y" }}
                    class="overflow-y-auto flex-1 p-0 min-h-0 bg-gray-50/50 border-t border-gray-100"
                >
                    {#if allShapes.length === 0}
                        <div
                            class="p-8 text-gray-400 text-sm text-center flex flex-col items-center gap-2"
                        >
                            <span class="text-2xl">📭</span>
                            <span>발견된 객체가 없습니다</span>
                        </div>
                    {:else}
                        <div class="p-2 space-y-4">
                            <!-- Image Shapes -->
                            {#if imageShapes.length > 0}
                                <div>
                                    <div
                                        class="flex items-center gap-2 px-2 py-1 mb-1"
                                    >
                                        <span
                                            class="text-xs font-bold text-orange-600 uppercase tracking-wide"
                                            >이미지 assets</span
                                        >
                                        <span class="h-px flex-1 bg-orange-200"
                                        ></span>
                                    </div>
                                    <ul class="space-y-1">
                                        {#each imageShapes as shape}
                                            <li>
                                                <button
                                                    class="w-full text-left p-2 rounded-lg text-sm flex items-start gap-3 transition-all border {selectedShapeId ===
                                                    shape.shape_index
                                                        ? 'bg-orange-50 border-orange-200 shadow-sm ring-1 ring-orange-200'
                                                        : 'bg-white border-transparent hover:border-orange-200 hover:shadow-sm'}"
                                                    on:click={() =>
                                                        dispatch(
                                                            "selectShape",
                                                            {
                                                                shapeIndex:
                                                                    shape.shape_index,
                                                            },
                                                        )}
                                                >
                                                    {#if shape.description}
                                                        <div
                                                            class="mt-0.5 text-green-500"
                                                            title="설명 완료"
                                                        >
                                                            ✅
                                                        </div>
                                                    {:else}
                                                        <div
                                                            class="mt-0.5 text-orange-400 animate-pulse"
                                                            title="설명 필요"
                                                        >
                                                            ⚠️
                                                        </div>
                                                    {/if}
                                                    <div class="flex-1 min-w-0">
                                                        <div
                                                            class="font-medium text-gray-700 truncate"
                                                            title={shape.name}
                                                        >
                                                            {shape.name}
                                                        </div>
                                                        {#if shape.description}
                                                            <div
                                                                class="text-xs text-gray-400 truncate mt-0.5"
                                                            >
                                                                {shape.description}
                                                            </div>
                                                        {:else}
                                                            <div
                                                                class="text-xs text-orange-400 mt-0.5"
                                                            >
                                                                설명을
                                                                입력해주세요
                                                            </div>
                                                        {/if}
                                                    </div>
                                                </button>
                                            </li>
                                        {/each}
                                    </ul>
                                </div>
                            {/if}

                            <!-- Text Shapes -->
                            {#if textShapes.length > 0}
                                <div>
                                    <div
                                        class="flex items-center gap-2 px-2 py-1 mb-1"
                                    >
                                        <span
                                            class="text-xs font-bold text-indigo-600 uppercase tracking-wide"
                                            >텍스트 객체</span
                                        >
                                        <span class="h-px flex-1 bg-indigo-200"
                                        ></span>
                                    </div>
                                    <ul class="space-y-1">
                                        {#each textShapes as shape}
                                            <li>
                                                <button
                                                    class="w-full text-left p-2 rounded-lg text-sm flex items-start gap-3 transition-all border {selectedShapeId ===
                                                    shape.shape_index
                                                        ? 'bg-indigo-50 border-indigo-200 shadow-sm ring-1 ring-indigo-200'
                                                        : 'bg-white border-transparent hover:border-indigo-200 hover:shadow-sm'}"
                                                    on:click={() =>
                                                        dispatch(
                                                            "selectShape",
                                                            {
                                                                shapeIndex:
                                                                    shape.shape_index,
                                                            },
                                                        )}
                                                >
                                                    <div
                                                        class="mt-0.5 text-indigo-400"
                                                    >
                                                        T
                                                    </div>
                                                    <div class="flex-1 min-w-0">
                                                        <div
                                                            class="font-medium text-gray-700 truncate"
                                                            title={shape.name}
                                                        >
                                                            {shape.name}
                                                        </div>
                                                        {#if shape.description}
                                                            <div
                                                                class="text-xs text-gray-400 truncate mt-0.5"
                                                            >
                                                                {shape.description}
                                                            </div>
                                                        {:else}
                                                            <div
                                                                class="text-xs text-orange-400 mt-0.5"
                                                            >
                                                                설명을
                                                                입력해주세요
                                                            </div>
                                                        {/if}
                                                    </div>
                                                </button>
                                            </li>
                                        {/each}
                                    </ul>
                                </div>
                            {/if}

                            <!-- Other Shapes -->
                            {#if otherShapes.length > 0}
                                <div>
                                    <div
                                        class="flex items-center gap-2 px-2 py-1 mb-1"
                                    >
                                        <span
                                            class="text-xs font-bold text-gray-500 uppercase tracking-wide"
                                            >기타 객체</span
                                        >
                                        <span class="h-px flex-1 bg-gray-200"
                                        ></span>
                                    </div>
                                    <ul class="space-y-1">
                                        {#each otherShapes as shape}
                                            <li>
                                                <button
                                                    class="w-full text-left p-2 rounded-lg text-sm flex items-start gap-3 transition-all border {selectedShapeId ===
                                                    shape.shape_index
                                                        ? 'bg-blue-50 border-blue-200 shadow-sm ring-1 ring-blue-200'
                                                        : 'bg-white border-transparent hover:border-gray-200 hover:shadow-sm'}"
                                                    on:click={() =>
                                                        dispatch(
                                                            "selectShape",
                                                            {
                                                                shapeIndex:
                                                                    shape.shape_index,
                                                            },
                                                        )}
                                                >
                                                    <div
                                                        class="mt-0.5 text-gray-400"
                                                    >
                                                        🔹
                                                    </div>
                                                    <div class="flex-1 min-w-0">
                                                        <div
                                                            class="font-medium text-gray-700 truncate"
                                                            title={shape.name}
                                                        >
                                                            {shape.name}
                                                        </div>
                                                        {#if shape.description}
                                                            <div
                                                                class="text-xs text-gray-400 truncate mt-0.5"
                                                            >
                                                                {shape.description}
                                                            </div>
                                                        {/if}
                                                    </div>
                                                    {#if shape.description}
                                                        <div
                                                            class="mt-0.5 text-gray-300"
                                                            title="설명 있음"
                                                        >
                                                            📝
                                                        </div>
                                                    {/if}
                                                </button>
                                            </li>
                                        {/each}
                                    </ul>
                                </div>
                            {/if}
                        </div>
                    {/if}
                </div>

                <!-- Description Editor -->
                {#if selectedShape}
                    <div
                        class="p-3 bg-white border-t border-gray-200 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.05)] z-10"
                    >
                        <div class="flex items-center justify-between mb-2">
                            <span
                                class="text-xs font-bold text-gray-500 uppercase"
                                >Description</span
                            >
                            <span
                                class="text-xs text-gray-400 max-w-[150px] truncate"
                                >{selectedShape.name}</span
                            >
                        </div>
                        <div class="relative">
                            <textarea
                                class="w-full text-sm p-2 pr-10 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none resize-none transition-shadow"
                                rows="2"
                                placeholder="객체에 대한 설명을 입력하세요..."
                                bind:value={editingDescription}
                                on:keydown={(e) => {
                                    if (e.key === "Enter" && !e.shiftKey) {
                                        e.preventDefault();
                                        dispatch("handleSaveDescription");
                                    }
                                }}
                            ></textarea>
                            <button
                                class="absolute right-2 bottom-2 p-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-md shadow-sm transition-transform active:scale-95"
                                on:click={() =>
                                    dispatch("handleSaveDescription")}
                                title="저장 (Enter)"
                            >
                                <svg
                                    class="w-4 h-4"
                                    fill="none"
                                    stroke="currentColor"
                                    viewBox="0 0 24 24"
                                    ><path
                                        stroke-linecap="round"
                                        stroke-linejoin="round"
                                        stroke-width="2"
                                        d="M5 13l4 4L19 7"
                                    /></svg
                                >
                            </button>
                        </div>
                    </div>
                {/if}
            {/if}
        </div>
    </div>
</div>
