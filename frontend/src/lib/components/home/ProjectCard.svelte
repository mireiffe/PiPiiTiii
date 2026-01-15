<script>
    import { createEventDispatcher } from "svelte";

    /** @type {any} */
    export let project;
    /** @type {boolean} */
    export let isSelected = false;
    /** @type {boolean} */
    export let isChecked = false;
    /** @type {boolean} */
    export let selectionMode = false;
    /** @type {{has_summary: boolean, is_outdated: boolean} | undefined} */
    export let summaryStatus = undefined;
    /** @type {boolean} */
    export let hasWorkflowWarning = false;
    /** @type {boolean} */
    export let isBatchProcessing = false;
    /** @type {any} */
    export let cardConfig;
    /** @type {Record<string, string>} */
    export let displayNameMap = {};

    const dispatch = createEventDispatcher();

    const formatValue = (value) => {
        if (value === undefined || value === null) return "";
        if (Array.isArray(value)) return value.join(", ");
        if (typeof value === "boolean") return value ? "Yes" : "No";
        return value === "" ? "" : String(value);
    };

    const getFieldValue = (project, field) => {
        if (!project) return "";
        const key = typeof field === "string" ? field : field.key;
        const prefix = typeof field === "object" ? field.prefix || "" : "";
        const suffix = typeof field === "object" ? field.suffix || "" : "";
        const value = formatValue(project[key]);
        return value ? `${prefix}${value}${suffix}` : "";
    };

    const getBadges = (project, keys) => {
        if (!project || !keys) return [];
        return keys.map((key) => {
            const value = formatValue(project[key]);
            if (!value) return null;
            return { key, label: displayNameMap[key] || key, value };
        }).filter(Boolean);
    };

    $: primaryBadges = getBadges(project, cardConfig?.footer?.primary || []);
    $: secondaryBadges = getBadges(project, cardConfig?.footer?.secondary || []);
</script>

<button
    class="w-full text-left p-4 rounded-xl transition-all duration-200 border bg-white flex flex-col gap-2 group relative
        {selectionMode && isChecked ? 'border-purple-400 ring-1 ring-purple-300 bg-purple-50/50' : isSelected ? 'border-blue-500 ring-1 ring-blue-500 shadow-md z-10' : 'border-gray-200 shadow-sm hover:shadow-md hover:border-blue-300'}
        {isBatchProcessing ? 'animate-pulse' : ''}"
    on:click={() => dispatch("click", { project })}
>
    {#if selectionMode}
        <div class="absolute -left-1 -top-1 z-10">
            <div class="w-6 h-6 rounded-full flex items-center justify-center transition-all {isChecked ? 'bg-purple-500' : 'bg-white border-2 border-gray-300'}">
                {#if isChecked}
                    <svg class="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
                    </svg>
                {/if}
            </div>
        </div>
    {/if}

    <div class="flex justify-between items-start w-full">
        <div class="flex items-center gap-2 min-w-0 flex-1">
            <h3 class="font-bold text-gray-800 text-lg truncate pr-2 group-hover:text-blue-700 transition-colors">
                {getFieldValue(project, cardConfig?.header?.title) || "Untitled"}
            </h3>
            {#if summaryStatus?.has_summary}
                {#if summaryStatus.is_outdated}
                    <div class="flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-50 border border-amber-200" title="프롬프트가 변경되어 재생성이 필요합니다">
                        <svg class="w-3 h-3 text-amber-500" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                        </svg>
                        <span class="text-[10px] font-medium text-amber-600">업데이트 필요</span>
                    </div>
                {:else}
                    <div class="flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-50 border border-emerald-200" title="요약이 최신 상태입니다">
                        <svg class="w-3 h-3 text-emerald-500" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                        </svg>
                        <span class="text-[10px] font-medium text-emerald-600">요약 완료</span>
                    </div>
                {/if}
            {/if}
            {#if hasWorkflowWarning}
                <div class="flex items-center gap-1 px-2 py-0.5 rounded-full bg-red-50 border border-red-200" title="워크플로우에 삭제된 액션 또는 파라미터가 사용되고 있습니다">
                    <svg class="w-3 h-3 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                    </svg>
                    <span class="text-[10px] font-medium text-red-600">워크플로우 오류</span>
                </div>
            {/if}
        </div>
        {#if cardConfig?.header?.date && project[cardConfig.header.date]}
            <span class="text-xs font-medium text-gray-400 whitespace-nowrap bg-gray-50 px-2 py-1 rounded shrink-0">
                {new Date(project[cardConfig.header.date]).toLocaleDateString()}
            </span>
        {/if}
    </div>

    {#if cardConfig?.subtitle}
        {@const subtitleValue = getFieldValue(project, cardConfig.subtitle)}
        {#if subtitleValue}
            <p class="text-sm text-gray-600 truncate">{subtitleValue}</p>
        {/if}
    {/if}

    <div class="h-px bg-gray-100 w-full my-1"></div>

    <div class="flex items-end justify-between gap-3">
        <div class="flex items-center gap-3 text-xs text-gray-500 shrink-0">
            {#each cardConfig?.footer?.left || [] as field}
                {@const fieldValue = getFieldValue(project, field)}
                {#if fieldValue}
                    <span class="flex items-center gap-1">
                        <span class="w-1.5 h-1.5 rounded-full bg-gray-300"></span>
                        {fieldValue}
                    </span>
                {/if}
            {/each}
        </div>

        {#if primaryBadges.length || secondaryBadges.length}
            <div class="flex flex-col items-end gap-1.5 min-w-0">
                {#if primaryBadges.length}
                    <div class="flex flex-wrap gap-1.5 justify-end">
                        {#each primaryBadges as badge}
                            <span class="text-xs leading-none px-2 py-1 rounded-md bg-blue-50 text-blue-700 border border-blue-100 font-semibold truncate max-w-[150px]" title={`${badge.label}: ${badge.value}`}>
                                {badge.value}
                            </span>
                        {/each}
                    </div>
                {/if}
                {#if secondaryBadges.length}
                    <div class="flex flex-wrap gap-1.5 justify-end">
                        {#each secondaryBadges as badge}
                            <span class="text-[11px] leading-none px-1.5 py-0.5 rounded-md bg-gray-100 text-gray-600 border border-gray-200 truncate max-w-[120px]" title={`${badge.label}: ${badge.value}`}>
                                {badge.value}
                            </span>
                        {/each}
                    </div>
                {/if}
            </div>
        {/if}
    </div>
</button>
