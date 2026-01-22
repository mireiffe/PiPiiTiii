<script lang="ts">
    import { createEventDispatcher, onMount } from "svelte";
    import { fetchProjects } from "$lib/api/project";
    import { goto } from "$app/navigation";

    export let tutorialProjectId: string | undefined = undefined;

    const dispatch = createEventDispatcher();

    interface ProjectItem {
        id: string;
        name: string;
        title?: string;
    }

    let projects: ProjectItem[] = [];
    let loading = true;

    onMount(async () => {
        try {
            const res = await fetchProjects();
            if (res.ok) {
                const data = await res.json();
                projects = data.map((p: any) => ({
                    id: p.id,
                    name: p.name || p.id,
                    title: p.title,
                }));
            }
        } catch (e) {
            console.error("Failed to load projects", e);
        } finally {
            loading = false;
        }
    });

    function handleSelectChange(e: Event) {
        const target = e.target as HTMLSelectElement;
        const value = target.value || undefined;
        dispatch("update", { tutorialProjectId: value });
    }

    function startTutorial() {
        if (tutorialProjectId) {
            goto(`/tutorial/${tutorialProjectId}`);
        }
    }

    $: selectedProject = projects.find(p => p.id === tutorialProjectId);
</script>

<div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
    <h2 class="text-xl font-bold text-gray-800 mb-4">Tutorial 설정</h2>
    <p class="text-sm text-gray-500 mb-4">
        Tutorial 모드에서 사용할 PPT를 지정합니다. Tutorial 모드에서는 모든 작업이 임시로만 저장되며, 페이지를 벗어나면 변경사항이 초기화됩니다.
    </p>

    <div class="space-y-4">
        <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">Tutorial PPT 선택</label>
            {#if loading}
                <div class="text-gray-500 text-sm">프로젝트 목록 로딩 중...</div>
            {:else if projects.length === 0}
                <div class="text-gray-500 text-sm">등록된 PPT가 없습니다. 먼저 PPT를 업로드해주세요.</div>
            {:else}
                <select
                    value={tutorialProjectId || ""}
                    on:change={handleSelectChange}
                    class="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                >
                    <option value="">선택 안함</option>
                    {#each projects as project}
                        <option value={project.id}>
                            {project.title || project.name}
                        </option>
                    {/each}
                </select>
            {/if}
        </div>

        {#if tutorialProjectId && selectedProject}
            <div class="pt-4 border-t border-gray-200">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-sm text-gray-600">
                            선택된 PPT: <span class="font-medium text-gray-900">{selectedProject.title || selectedProject.name}</span>
                        </p>
                        <p class="text-xs text-gray-400 mt-1">
                            Tutorial 모드에서 모든 작업은 실제로 저장되지 않습니다.
                        </p>
                    </div>
                    <button
                        on:click={startTutorial}
                        class="bg-emerald-600 text-white px-6 py-2.5 rounded-lg hover:bg-emerald-700 transition shadow-sm font-medium flex items-center gap-2"
                    >
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        Tutorial 진행
                    </button>
                </div>
            </div>
        {/if}
    </div>
</div>
