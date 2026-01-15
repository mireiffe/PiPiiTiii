<script lang="ts">
    import { createEventDispatcher } from "svelte";

    interface SummaryField {
        id: string;
        name: string;
        order: number;
        system_prompt: string;
        user_prompt: string;
    }

    export let fields: SummaryField[] = [];
    export let expandedFieldId: string | null = null;

    const dispatch = createEventDispatcher<{
        add: void;
        remove: { index: number };
        moveUp: { index: number };
        moveDown: { index: number };
        toggleExpand: { fieldId: string };
        update: { fields: SummaryField[] };
    }>();

    function handleFieldNameChange(index: number, name: string) {
        fields[index].name = name;
        dispatch("update", { fields });
    }

    function handleSystemPromptChange(index: number, value: string) {
        fields[index].system_prompt = value;
        dispatch("update", { fields });
    }

    function handleUserPromptChange(index: number, value: string) {
        fields[index].user_prompt = value;
        dispatch("update", { fields });
    }
</script>

<div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
    <div class="flex justify-between items-center mb-4">
        <div>
            <h2 class="text-xl font-bold text-gray-800">PPT 요약 필드</h2>
            <p class="text-sm text-gray-500 mt-1">
                각 필드별로 LLM에 전달할 프롬프트를 설정합니다.
            </p>
        </div>
        <button
            class="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition text-sm font-medium"
            on:click={() => dispatch("add")}
        >
            + 필드 추가
        </button>
    </div>

    <div class="space-y-3">
        {#if fields.length === 0}
            <div class="text-center text-gray-400 py-8">
                필드가 없습니다. 필드를 추가해주세요.
            </div>
        {:else}
            {#each fields as field, index (field.id)}
                <div class="border border-gray-200 rounded-lg bg-gray-50 overflow-hidden">
                    <!-- Field Header -->
                    <div class="flex items-center gap-3 p-4">
                        <div class="flex flex-col gap-1">
                            <button
                                class="text-gray-500 hover:text-gray-700 disabled:opacity-30"
                                on:click={() => dispatch("moveUp", { index })}
                                disabled={index === 0}
                                title="위로 이동"
                            >
                                ▲
                            </button>
                            <button
                                class="text-gray-500 hover:text-gray-700 disabled:opacity-30"
                                on:click={() => dispatch("moveDown", { index })}
                                disabled={index === fields.length - 1}
                                title="아래로 이동"
                            >
                                ▼
                            </button>
                        </div>

                        <div class="flex-1 flex items-center gap-3">
                            <div class="flex-1">
                                <label class="block text-xs text-gray-500 mb-1">필드명</label>
                                <input
                                    type="text"
                                    value={field.name}
                                    on:input={(e) => handleFieldNameChange(index, e.currentTarget.value)}
                                    class="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    placeholder="필드 이름"
                                />
                            </div>
                            <div class="w-48">
                                <label class="block text-xs text-gray-500 mb-1">ID (읽기전용)</label>
                                <input
                                    type="text"
                                    value={field.id}
                                    readonly
                                    class="w-full border border-gray-200 rounded px-3 py-2 bg-gray-100 text-gray-500 text-sm"
                                />
                            </div>
                        </div>

                        <button
                            class="text-gray-500 hover:text-blue-600 px-3 py-2 rounded transition text-sm"
                            on:click={() => dispatch("toggleExpand", { fieldId: field.id })}
                            title="프롬프트 설정"
                        >
                            {expandedFieldId === field.id ? "▼ 접기" : "▶ 프롬프트"}
                        </button>

                        <button
                            class="bg-red-500 text-white px-3 py-2 rounded hover:bg-red-600 transition text-sm font-medium"
                            on:click={() => dispatch("remove", { index })}
                        >
                            삭제
                        </button>
                    </div>

                    <!-- Expanded Prompt Section -->
                    {#if expandedFieldId === field.id}
                        <div class="border-t border-gray-200 p-4 bg-white space-y-4">
                            <div>
                                <label class="block text-sm font-medium text-gray-700 mb-2">
                                    System Prompt
                                </label>
                                <textarea
                                    value={field.system_prompt}
                                    on:input={(e) => handleSystemPromptChange(index, e.currentTarget.value)}
                                    class="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                                    rows="3"
                                    placeholder="LLM의 역할과 행동 지침을 정의합니다. 예: 당신은 PPT 문서를 분석하는 전문가입니다."
                                ></textarea>
                            </div>

                            <div>
                                <label class="block text-sm font-medium text-gray-700 mb-2">
                                    User Query Prompt
                                </label>
                                <textarea
                                    value={field.user_prompt}
                                    on:input={(e) => handleUserPromptChange(index, e.currentTarget.value)}
                                    class="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                                    rows="3"
                                    placeholder="실제 요청 내용입니다. 예: 이 슬라이드들의 핵심 내용을 3줄로 요약해주세요."
                                ></textarea>
                            </div>
                        </div>
                    {/if}
                </div>
            {/each}
        {/if}
    </div>
</div>
