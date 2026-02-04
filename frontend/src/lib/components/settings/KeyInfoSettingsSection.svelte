<script lang="ts">
    import { createEventDispatcher, onMount } from 'svelte';
    import type { KeyInfoCategoryDefinition, KeyInfoItemDefinition, KeyInfoSettings } from '$lib/types/keyInfo';
    import {
        generateKeyInfoCategoryId,
        generateKeyInfoItemId,
        createKeyInfoCategory,
        createKeyInfoItem
    } from '$lib/types/keyInfo';
    import { fetchKeyinfoUsageCounts } from '$lib/api/project';

    export let keyInfoSettings: KeyInfoSettings = { categories: [] };
    export let expandedCategoryId: string | null = null;

    let editingCategoryId: string | null = null;
    let editingCategoryName = '';
    let editingItemId: string | null = null;
    let editingItemTitle = '';
    let editingItemDescription = '';
    let newCategoryName = '';
    let addingCategory = false;
    let addingItemToCategoryId: string | null = null;
    let newItemTitle = '';
    let newItemDescription = '';

    // Usage counts: how many projects use each keyinfo item
    let usageCounts: Record<string, number> = {};

    async function loadUsageCounts() {
        try {
            const res = await fetchKeyinfoUsageCounts();
            if (res.ok) {
                const data = await res.json();
                usageCounts = data.counts || {};
            }
        } catch (e) {
            console.error("Failed to load keyinfo usage counts", e);
        }
    }

    onMount(() => {
        loadUsageCounts();
    });

    function getItemUsageCount(categoryId: string, itemId: string): number {
        return usageCounts[`${categoryId}_${itemId}`] || 0;
    }

    function getCategoryUsageCount(category: KeyInfoCategoryDefinition): number {
        let total = 0;
        for (const item of category.items) {
            total += getItemUsageCount(category.id, item.id);
        }
        return total;
    }

    // Drag state for categories
    let draggedCategoryIndex: number | null = null;
    let dropTargetCategoryIndex: number | null = null;

    // Drag state for items within a category
    let draggedItemIndex: number | null = null;
    let dropTargetItemIndex: number | null = null;
    let dragItemCategoryId: string | null = null;

    const dispatch = createEventDispatcher<{
        update: { keyInfoSettings: KeyInfoSettings };
        toggleCategoryExpand: { categoryId: string };
    }>();

    function emitUpdate() {
        dispatch('update', { keyInfoSettings });
    }

    // ========== Category Operations ==========

    function addCategory() {
        if (!newCategoryName.trim()) {
            alert('카테고리 이름을 입력해주세요.');
            return;
        }
        const newCategory = createKeyInfoCategory(newCategoryName.trim(), keyInfoSettings.categories.length);
        keyInfoSettings.categories = [...keyInfoSettings.categories, newCategory];
        newCategoryName = '';
        addingCategory = false;
        expandedCategoryId = newCategory.id;
        dispatch('toggleCategoryExpand', { categoryId: newCategory.id });
        emitUpdate();
    }

    function removeCategory(categoryId: string) {
        const category = keyInfoSettings.categories.find(c => c.id === categoryId);
        if (!category) return;

        const itemCount = category.items.length;
        const message = itemCount > 0
            ? `이 카테고리와 포함된 ${itemCount}개의 핵심정보 항목을 삭제하시겠습니까?`
            : '이 카테고리를 삭제하시겠습니까?';

        if (confirm(message)) {
            keyInfoSettings.categories = keyInfoSettings.categories
                .filter(c => c.id !== categoryId)
                .map((c, i) => ({ ...c, order: i }));
            emitUpdate();
        }
    }

    function startEditingCategory(category: KeyInfoCategoryDefinition) {
        editingCategoryId = category.id;
        editingCategoryName = category.name;
    }

    function saveEditingCategory() {
        if (!editingCategoryName.trim()) {
            alert('이름을 입력해주세요.');
            return;
        }
        keyInfoSettings.categories = keyInfoSettings.categories.map(c =>
            c.id === editingCategoryId
                ? { ...c, name: editingCategoryName.trim() }
                : c
        );
        cancelEditingCategory();
        emitUpdate();
    }

    function cancelEditingCategory() {
        editingCategoryId = null;
        editingCategoryName = '';
    }

    function toggleCategoryExpand(categoryId: string) {
        dispatch('toggleCategoryExpand', { categoryId });
    }

    // Category Drag and Drop
    function handleCategoryDragStart(e: DragEvent, index: number) {
        draggedCategoryIndex = index;
        if (e.dataTransfer) {
            e.dataTransfer.effectAllowed = 'move';
        }
    }

    function handleCategoryDragOver(e: DragEvent, index: number) {
        e.preventDefault();
        if (draggedCategoryIndex === null || draggedCategoryIndex === index) return;
        dropTargetCategoryIndex = index;
    }

    function handleCategoryDragLeave() {
        dropTargetCategoryIndex = null;
    }

    function handleCategoryDrop(e: DragEvent, index: number) {
        e.preventDefault();
        if (draggedCategoryIndex === null || draggedCategoryIndex === index) {
            resetCategoryDragState();
            return;
        }

        const newCategories = [...keyInfoSettings.categories];
        const [moved] = newCategories.splice(draggedCategoryIndex, 1);
        newCategories.splice(index, 0, moved);
        keyInfoSettings.categories = newCategories.map((c, i) => ({ ...c, order: i }));
        emitUpdate();
        resetCategoryDragState();
    }

    function handleCategoryDragEnd() {
        resetCategoryDragState();
    }

    function resetCategoryDragState() {
        draggedCategoryIndex = null;
        dropTargetCategoryIndex = null;
    }

    // ========== Item Operations ==========

    function startAddingItem(categoryId: string) {
        addingItemToCategoryId = categoryId;
        newItemTitle = '';
        newItemDescription = '';
    }

    function addItem(categoryId: string) {
        if (!newItemTitle.trim()) {
            alert('핵심정보 제목을 입력해주세요.');
            return;
        }

        keyInfoSettings.categories = keyInfoSettings.categories.map(c => {
            if (c.id !== categoryId) return c;
            const newItem = createKeyInfoItem(
                newItemTitle.trim(),
                newItemDescription.trim(),
                c.items.length
            );
            return { ...c, items: [...c.items, newItem] };
        });

        addingItemToCategoryId = null;
        newItemTitle = '';
        newItemDescription = '';
        emitUpdate();
    }

    function removeItem(categoryId: string, itemId: string) {
        if (confirm('이 핵심정보 항목을 삭제하시겠습니까?')) {
            keyInfoSettings.categories = keyInfoSettings.categories.map(c => {
                if (c.id !== categoryId) return c;
                return {
                    ...c,
                    items: c.items
                        .filter(item => item.id !== itemId)
                        .map((item, i) => ({ ...item, order: i }))
                };
            });
            emitUpdate();
        }
    }

    function startEditingItem(item: KeyInfoItemDefinition) {
        editingItemId = item.id;
        editingItemTitle = item.title;
        editingItemDescription = item.description;
    }

    function saveEditingItem(categoryId: string) {
        if (!editingItemTitle.trim()) {
            alert('제목을 입력해주세요.');
            return;
        }
        keyInfoSettings.categories = keyInfoSettings.categories.map(c => {
            if (c.id !== categoryId) return c;
            return {
                ...c,
                items: c.items.map(item =>
                    item.id === editingItemId
                        ? { ...item, title: editingItemTitle.trim(), description: editingItemDescription.trim() }
                        : item
                )
            };
        });
        cancelEditingItem();
        emitUpdate();
    }

    function cancelEditingItem() {
        editingItemId = null;
        editingItemTitle = '';
        editingItemDescription = '';
    }

    // Item Drag and Drop
    function handleItemDragStart(e: DragEvent, categoryId: string, index: number) {
        draggedItemIndex = index;
        dragItemCategoryId = categoryId;
        if (e.dataTransfer) {
            e.dataTransfer.effectAllowed = 'move';
        }
    }

    function handleItemDragOver(e: DragEvent, categoryId: string, index: number) {
        e.preventDefault();
        if (dragItemCategoryId !== categoryId) return; // Only allow drag within same category
        if (draggedItemIndex === null || draggedItemIndex === index) return;
        dropTargetItemIndex = index;
    }

    function handleItemDragLeave() {
        dropTargetItemIndex = null;
    }

    function handleItemDrop(e: DragEvent, categoryId: string, index: number) {
        e.preventDefault();
        if (dragItemCategoryId !== categoryId || draggedItemIndex === null || draggedItemIndex === index) {
            resetItemDragState();
            return;
        }

        keyInfoSettings.categories = keyInfoSettings.categories.map(c => {
            if (c.id !== categoryId) return c;
            const newItems = [...c.items];
            const [moved] = newItems.splice(draggedItemIndex!, 1);
            newItems.splice(index, 0, moved);
            return { ...c, items: newItems.map((item, i) => ({ ...item, order: i })) };
        });
        emitUpdate();
        resetItemDragState();
    }

    function handleItemDragEnd() {
        resetItemDragState();
    }

    function resetItemDragState() {
        draggedItemIndex = null;
        dropTargetItemIndex = null;
        dragItemCategoryId = null;
    }

    function updateCategoryPrompt(categoryId: string, field: 'systemPrompt' | 'userPrompt', value: string) {
        keyInfoSettings.categories = keyInfoSettings.categories.map(c =>
            c.id === categoryId ? { ...c, [field]: value } : c
        );
        emitUpdate();
    }

    function handleCategoryKeydown(e: KeyboardEvent) {
        if (e.key === 'Enter') {
            saveEditingCategory();
        } else if (e.key === 'Escape') {
            cancelEditingCategory();
        }
    }
</script>

<div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
    <div class="flex justify-between items-center mb-4">
        <div>
            <h2 class="text-xl font-bold text-gray-800">핵심정보 설정</h2>
            <p class="text-sm text-gray-500 mt-1">
                Viewer에서 사용할 핵심정보 카테고리와 항목을 정의합니다.
            </p>
        </div>
        <div class="flex gap-2">
            {#if addingCategory}
                <div class="flex items-center gap-2">
                    <input
                        type="text"
                        bind:value={newCategoryName}
                        placeholder="카테고리 이름"
                        class="border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        on:keypress={(e) => e.key === 'Enter' && addCategory()}
                    />
                    <button
                        class="bg-blue-600 text-white px-3 py-1.5 rounded text-sm hover:bg-blue-700"
                        on:click={addCategory}
                    >
                        추가
                    </button>
                    <button
                        class="text-gray-500 px-2 py-1.5 text-sm hover:text-gray-700"
                        on:click={() => {
                            addingCategory = false;
                            newCategoryName = '';
                        }}
                    >
                        취소
                    </button>
                </div>
            {:else}
                <button
                    class="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition text-sm font-medium"
                    on:click={() => addingCategory = true}
                >
                    + 카테고리 추가
                </button>
            {/if}
        </div>
    </div>

    <div class="space-y-3">
        {#if keyInfoSettings.categories.length === 0}
            <div class="text-center text-gray-400 py-8 border border-dashed border-gray-300 rounded-lg">
                <div class="text-blue-400 mb-2">
                    <svg class="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                    </svg>
                </div>
                정의된 카테고리가 없습니다. 카테고리를 추가하여 핵심정보를 구성하세요.
            </div>
        {:else}
            {#each keyInfoSettings.categories as category, catIndex (category.id)}
                <div
                    class="border rounded-lg bg-gray-50 overflow-hidden transition-all
                        {draggedCategoryIndex === catIndex ? 'opacity-50' : ''}
                        {dropTargetCategoryIndex === catIndex ? 'border-blue-500 border-2' : 'border-gray-200'}"
                    draggable="true"
                    on:dragstart={(e) => handleCategoryDragStart(e, catIndex)}
                    on:dragover={(e) => handleCategoryDragOver(e, catIndex)}
                    on:dragleave={handleCategoryDragLeave}
                    on:drop={(e) => handleCategoryDrop(e, catIndex)}
                    on:dragend={handleCategoryDragEnd}
                    role="listitem"
                >
                    <!-- Category Header -->
                    <div class="flex items-center gap-3 p-4 bg-white border-b border-gray-100">
                        <!-- Drag Handle -->
                        <div class="cursor-grab text-gray-400 hover:text-gray-600">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8h16M4 16h16" />
                            </svg>
                        </div>

                        <!-- Expand/Collapse Button -->
                        <button
                            class="text-gray-500 hover:text-gray-700 p-1"
                            on:click={() => toggleCategoryExpand(category.id)}
                        >
                            <svg
                                class="w-4 h-4 transition-transform {expandedCategoryId === category.id ? 'rotate-90' : ''}"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                            >
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                            </svg>
                        </button>

                        <!-- Category Name -->
                        <div class="flex-1">
                            {#if editingCategoryId === category.id}
                                <input
                                    type="text"
                                    bind:value={editingCategoryName}
                                    on:keydown={handleCategoryKeydown}
                                    class="border border-blue-400 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-full max-w-xs"
                                    autofocus
                                />
                            {:else}
                                <button
                                    class="text-sm font-medium text-gray-800 hover:text-blue-600 cursor-pointer text-left"
                                    on:click={() => startEditingCategory(category)}
                                    title="클릭하여 편집"
                                >
                                    {category.name}
                                </button>
                            {/if}
                        </div>

                        <!-- Item Count Badge -->
                        <span class="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                            {category.items.length}개 항목
                        </span>
                        {#if getCategoryUsageCount(category) > 0}
                            <span class="text-xs text-blue-500 bg-blue-50 px-2 py-1 rounded" title="이 카테고리의 항목들이 총 {getCategoryUsageCount(category)}개 프로젝트에서 사용 중">
                                {getCategoryUsageCount(category)}번 사용됨
                            </span>
                        {/if}

                        <!-- Action Buttons -->
                        {#if editingCategoryId === category.id}
                            <button
                                class="bg-blue-600 text-white px-3 py-1.5 rounded text-sm hover:bg-blue-700"
                                on:click={saveEditingCategory}
                            >
                                저장
                            </button>
                            <button
                                class="text-gray-500 px-2 py-1.5 text-sm hover:text-gray-700"
                                on:click={cancelEditingCategory}
                            >
                                취소
                            </button>
                        {:else}
                            <button
                                class="text-gray-500 hover:text-blue-600 px-2 py-1 rounded transition text-sm"
                                on:click={() => startEditingCategory(category)}
                                title="편집"
                            >
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                </svg>
                            </button>
                            <button
                                class="bg-red-500 text-white px-3 py-1.5 rounded hover:bg-red-600 transition text-sm font-medium"
                                on:click={() => removeCategory(category.id)}
                            >
                                삭제
                            </button>
                        {/if}
                    </div>

                    <!-- Category Content (Items) -->
                    {#if expandedCategoryId === category.id}
                        <div class="p-4 bg-gray-50">
                            <div class="space-y-2">
                                {#if category.items.length === 0}
                                    <div class="text-center text-gray-400 py-4 border border-dashed border-gray-300 rounded-lg bg-white">
                                        핵심정보 항목이 없습니다.
                                    </div>
                                {:else}
                                    {#each category.items as item, itemIndex (item.id)}
                                        <div
                                            class="border rounded-lg bg-white p-3 transition-all
                                                {dragItemCategoryId === category.id && draggedItemIndex === itemIndex ? 'opacity-50' : ''}
                                                {dragItemCategoryId === category.id && dropTargetItemIndex === itemIndex ? 'border-blue-500 border-2' : 'border-gray-200'}"
                                            draggable="true"
                                            on:dragstart={(e) => handleItemDragStart(e, category.id, itemIndex)}
                                            on:dragover={(e) => handleItemDragOver(e, category.id, itemIndex)}
                                            on:dragleave={handleItemDragLeave}
                                            on:drop={(e) => handleItemDrop(e, category.id, itemIndex)}
                                            on:dragend={handleItemDragEnd}
                                            role="listitem"
                                        >
                                            {#if editingItemId === item.id}
                                                <!-- Editing Mode -->
                                                <div class="space-y-2">
                                                    <input
                                                        type="text"
                                                        bind:value={editingItemTitle}
                                                        placeholder="제목"
                                                        class="border border-blue-400 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-full"
                                                        autofocus
                                                    />
                                                    <textarea
                                                        bind:value={editingItemDescription}
                                                        placeholder="설명 (선택사항)"
                                                        class="border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-full resize-none"
                                                        rows="2"
                                                    ></textarea>
                                                    <div class="flex gap-2 justify-end">
                                                        <button
                                                            class="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700"
                                                            on:click={() => saveEditingItem(category.id)}
                                                        >
                                                            저장
                                                        </button>
                                                        <button
                                                            class="text-gray-500 px-2 py-1 text-sm hover:text-gray-700"
                                                            on:click={cancelEditingItem}
                                                        >
                                                            취소
                                                        </button>
                                                    </div>
                                                </div>
                                            {:else}
                                                <!-- Display Mode -->
                                                <div class="flex items-start gap-3">
                                                    <!-- Drag Handle -->
                                                    <div class="cursor-grab text-gray-400 hover:text-gray-600 mt-1">
                                                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8h16M4 16h16" />
                                                        </svg>
                                                    </div>

                                                    <!-- Item Content -->
                                                    <div class="flex-1 min-w-0">
                                                        <div class="flex items-center gap-1.5">
                                                            <span class="text-sm font-medium text-gray-800">{item.title}</span>
                                                            {#if getItemUsageCount(category.id, item.id) > 0}
                                                                <span class="text-[10px] text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded" title="{getItemUsageCount(category.id, item.id)}개 프로젝트에서 사용 중">{getItemUsageCount(category.id, item.id)}번 사용됨</span>
                                                            {/if}
                                                        </div>
                                                        {#if item.description}
                                                            <div class="text-xs text-gray-500 mt-1">{item.description}</div>
                                                        {/if}
                                                    </div>

                                                    <!-- Action Buttons -->
                                                    <div class="flex gap-1 shrink-0">
                                                        <button
                                                            class="text-gray-500 hover:text-blue-600 p-1 rounded transition"
                                                            on:click={() => startEditingItem(item)}
                                                            title="편집"
                                                        >
                                                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                                            </svg>
                                                        </button>
                                                        <button
                                                            class="text-gray-500 hover:text-red-600 p-1 rounded transition"
                                                            on:click={() => removeItem(category.id, item.id)}
                                                            title="삭제"
                                                        >
                                                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                                            </svg>
                                                        </button>
                                                    </div>
                                                </div>
                                            {/if}
                                        </div>
                                    {/each}
                                {/if}

                                <!-- LLM 프롬프트 설정 -->
                                <div class="mt-4 pt-4 border-t border-gray-200">
                                    <div class="flex items-center gap-2 mb-3">
                                        <svg class="w-4 h-4 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                                        </svg>
                                        <span class="text-sm font-medium text-gray-700">LLM 자동 생성 프롬프트</span>
                                    </div>
                                    <div class="space-y-3">
                                        <div>
                                            <label class="block text-xs font-medium text-gray-600 mb-1">System Prompt</label>
                                            <textarea
                                                value={category.systemPrompt || ''}
                                                on:input={(e) => updateCategoryPrompt(category.id, 'systemPrompt', e.currentTarget.value)}
                                                placeholder="예: 당신은 PPT 프레젠테이션을 분석하는 전문가입니다."
                                                class="w-full border border-gray-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 resize-none bg-white"
                                                rows="2"
                                            ></textarea>
                                        </div>
                                        <div>
                                            <label class="block text-xs font-medium text-gray-600 mb-1">User Prompt</label>
                                            <textarea
                                                value={category.userPrompt || ''}
                                                on:input={(e) => updateCategoryPrompt(category.id, 'userPrompt', e.currentTarget.value)}
                                                placeholder={'예: 슬라이드에서 {{key_info_title}}에 해당하는 내용을 찾아 설명해주세요.'}
                                                class="w-full border border-gray-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 resize-none bg-white"
                                                rows="3"
                                            ></textarea>
                                            <p class="text-[10px] text-gray-400 mt-1">
                                                사용 가능한 변수: <code class="bg-gray-100 px-1 rounded">{'{{key_info_title}}'}</code> (항목 제목), <code class="bg-gray-100 px-1 rounded">{'{{key_info_description}}'}</code> (항목 설명)
                                            </p>
                                        </div>
                                    </div>
                                </div>

                                <!-- Add Item Button -->
                                {#if addingItemToCategoryId === category.id}
                                    <div class="border rounded-lg bg-white p-3 border-blue-200">
                                        <div class="space-y-2">
                                            <input
                                                type="text"
                                                bind:value={newItemTitle}
                                                placeholder="제목"
                                                class="border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-full"
                                                autofocus
                                            />
                                            <textarea
                                                bind:value={newItemDescription}
                                                placeholder="설명 (선택사항)"
                                                class="border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-full resize-none"
                                                rows="2"
                                            ></textarea>
                                            <div class="flex gap-2 justify-end">
                                                <button
                                                    class="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700"
                                                    on:click={() => addItem(category.id)}
                                                >
                                                    추가
                                                </button>
                                                <button
                                                    class="text-gray-500 px-2 py-1 text-sm hover:text-gray-700"
                                                    on:click={() => {
                                                        addingItemToCategoryId = null;
                                                        newItemTitle = '';
                                                        newItemDescription = '';
                                                    }}
                                                >
                                                    취소
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                {:else}
                                    <button
                                        class="w-full border border-dashed border-gray-300 rounded-lg py-2 text-sm text-gray-500 hover:text-blue-600 hover:border-blue-300 transition"
                                        on:click={() => startAddingItem(category.id)}
                                    >
                                        + 핵심정보 항목 추가
                                    </button>
                                {/if}
                            </div>
                        </div>
                    {/if}
                </div>
            {/each}
        {/if}
    </div>
</div>
