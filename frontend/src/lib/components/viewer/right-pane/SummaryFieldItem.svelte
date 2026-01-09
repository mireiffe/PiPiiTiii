<script>
    import { marked } from "marked";
    import { createEventDispatcher } from "svelte";

    export let field;
    export let summaryData;
    export let summaryDataLLM;
    export let generatingFieldIds;
    export let generatingAll = false;
    export let comparingFieldId = null;
    export let editingFieldId = null;

    const dispatch = createEventDispatcher();

    $: isGenerating = generatingFieldIds.has(field.id);
    $: isComparing = comparingFieldId === field.id;
    $: isEditing = editingFieldId === field.id;
    $: hasLLMVersion = summaryDataLLM[field.id] && summaryDataLLM[field.id] !== summaryData[field.id];
</script>

<div class="group">
    <div class="flex items-center justify-between mb-2">
        <div class="flex items-center gap-2">
            <div
                class="h-4 w-1 bg-gradient-to-b from-indigo-500 to-purple-500 rounded-full"
            ></div>
            <label class="text-sm font-bold text-gray-700 tracking-tight">
                {field.name}
            </label>

            <!-- Compare button -->
            {#if hasLLMVersion}
                <button
                    class="text-[9px] px-2 py-0.5 rounded-full transition-all flex items-center gap-1 ml-1 {isComparing
                        ? 'bg-amber-100 text-amber-700 border border-amber-200 shadow-sm'
                        : 'bg-gray-100 text-gray-500 hover:bg-amber-50 hover:text-amber-600 border border-transparent hover:border-amber-200'}"
                    on:click={() => dispatch("toggleCompare", { fieldId: field.id })}
                    title={isComparing ? "비교 닫기" : "LLM 버전과 비교"}
                >
                    <svg class="w-2.5 h-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                        />
                    </svg>
                    <span>{isComparing ? "닫기" : "비교"}</span>
                </button>
            {/if}
        </div>

        <button
            class="flex items-center gap-1.5 px-2.5 py-1.5 text-[10px] font-bold rounded-lg
            bg-white border border-indigo-100 text-indigo-600 hover:bg-indigo-50 hover:border-indigo-200
            shadow-sm hover:shadow transition-all duration-200
            disabled:opacity-50 disabled:cursor-not-allowed group-hover:opacity-100 opacity-0 transition-opacity"
            class:opacity-100={isGenerating}
            on:click={() => dispatch("generateSummaryForField", { fieldId: field.id })}
            disabled={isGenerating || generatingAll}
            title="이 항목을 LLM으로 자동 생성"
        >
            {#if isGenerating}
                <svg class="animate-spin w-3 h-3" viewBox="0 0 24 24">
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
                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
    {#if isComparing && summaryDataLLM[field.id]}
        <div class="mb-3 p-3 bg-amber-50/80 border border-amber-200 rounded-xl">
            <div class="flex items-center justify-between mb-2">
                <span
                    class="text-[10px] font-bold text-amber-700 uppercase tracking-wide flex items-center gap-1.5"
                >
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M19.428 15.428a2 2 0 00-1.022-.547l-2.384-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"
                        />
                    </svg>
                    LLM 생성 버전
                </span>
                <button
                    class="text-[9px] px-2 py-1 bg-white hover:bg-amber-50 text-amber-600 border border-amber-200 rounded-lg transition-all flex items-center gap-1.5 shadow-sm"
                    on:click={() => dispatch("restoreLLMVersion", { fieldId: field.id })}
                    title="LLM 버전으로 되돌리기"
                >
                    <svg class="w-2.5 h-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
                {@html marked(summaryDataLLM[field.id] || "")}
            </div>
        </div>
    {/if}

    <div class="relative group/edit">
        <!-- Edit/Preview Toggle -->
        <div
            class="flex justify-end mb-0 absolute right-2 top-2 z-10 opacity-0 group-hover/edit:opacity-100 transition-opacity"
        >
            <div class="inline-flex rounded-lg border border-gray-200 p-0.5 bg-white shadow-sm">
                <button
                    class="px-2.5 py-1 text-[10px] font-medium rounded-md transition-all {isEditing
                        ? 'bg-gray-100 text-gray-900'
                        : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'}"
                    on:click={() => dispatch("setEditing", { fieldId: field.id })}
                >
                    편집
                </button>
                <button
                    class="px-2.5 py-1 text-[10px] font-medium rounded-md transition-all {!isEditing
                        ? 'bg-gray-100 text-gray-900'
                        : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'}"
                    on:click={() => {
                        dispatch("clearEditing");
                        dispatch("saveSummary");
                    }}
                >
                    미리보기
                </button>
            </div>
        </div>

        {#if isEditing}
            <!-- Edit Mode -->
            <textarea
                class="w-full text-base leading-relaxed p-4 border border-gray-200 rounded-xl shadow-sm focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all placeholder-gray-300 resize-y min-h-[320px] hover:border-gray-300 {isGenerating
                    ? 'bg-indigo-50/30'
                    : 'bg-white'}"
                style="font-size: 15px;"
                rows="12"
                placeholder="{field.name}에 대한 내용을 입력하세요... (자동 저장됨)"
                bind:value={summaryData[field.id]}
                on:blur={() => dispatch("saveSummary")}
                on:keydown={(e) => {
                    if ((e.ctrlKey || e.metaKey) && e.key === "s") {
                        e.preventDefault();
                        dispatch("saveSummary");
                        dispatch("clearEditing");
                        e.target.blur();
                    }
                }}
                disabled={isGenerating}
            ></textarea>
        {:else}
            <!-- Preview Mode (Markdown Rendered) -->
            <!-- svelte-ignore a11y-click-events-have-key-events -->
            <!-- svelte-ignore a11y-no-static-element-interactions -->
            <div
                class="w-full min-h-[120px] p-4 border border-gray-200 rounded-xl shadow-sm bg-white cursor-pointer hover:border-indigo-300 hover:shadow-md transition-all overflow-hidden relative group-hover/edit:border-gray-300"
                on:click={() => dispatch("setEditing", { fieldId: field.id })}
                title="클릭하여 편집"
            >
                {#if summaryData[field.id]}
                    <div
                        class="prose prose-sm max-w-none prose-headings:text-gray-800 prose-p:text-gray-600 prose-strong:text-gray-700 prose-ul:text-gray-600 prose-ol:text-gray-600"
                    >
                        {@html marked(summaryData[field.id] || "")}
                    </div>
                {:else}
                    <p
                        class="text-gray-300 italic text-sm flex items-center justify-center py-8"
                    >
                        {field.name} 내용을 입력하려면 클릭하세요...
                    </p>
                {/if}
            </div>
        {/if}

        {#if isGenerating}
            <div
                class="absolute inset-0 flex items-center justify-center bg-white/60 backdrop-blur-[2px] rounded-xl z-20"
            >
                <div class="flex flex-col items-center gap-3 text-indigo-600">
                    <div class="relative">
                        <div
                            class="absolute inset-0 bg-indigo-200 rounded-full animate-ping opacity-75"
                        ></div>
                        <div class="relative bg-white p-2 rounded-full shadow-sm">
                            <svg class="animate-spin h-6 w-6" viewBox="0 0 24 24">
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
                    <span class="text-xs font-bold tracking-wide animate-pulse">
                        AI 작성 중...
                    </span>
                </div>
            </div>
        {/if}
    </div>
</div>
