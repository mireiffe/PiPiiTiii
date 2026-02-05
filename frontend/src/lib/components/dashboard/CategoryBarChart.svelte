<script lang="ts">
    import { onMount } from 'svelte';
    import { browser } from '$app/environment';

    export let data: { name: string; count: number; color?: string }[] = [];
    export let height: number = 200;

    let container: HTMLDivElement;
    let width = 400;

    const defaultColors = [
        '#3B82F6', // blue
        '#10B981', // green
        '#F59E0B', // amber
        '#EF4444', // red
        '#8B5CF6', // purple
        '#EC4899', // pink
        '#06B6D4', // cyan
        '#84CC16', // lime
    ];

    function getColor(index: number, customColor?: string): string {
        if (customColor) return customColor;
        return defaultColors[index % defaultColors.length];
    }

    $: maxCount = Math.max(...data.map(d => d.count), 1);

    onMount(() => {
        if (!browser || !container) return;
        const resizeObserver = new ResizeObserver(entries => {
            for (const entry of entries) {
                width = entry.contentRect.width;
            }
        });
        resizeObserver.observe(container);
        return () => resizeObserver.disconnect();
    });
</script>

<div bind:this={container} class="w-full" style="height: {height}px;">
    {#if data.length === 0}
        <div class="h-full flex items-center justify-center text-gray-400 text-sm">
            데이터가 없습니다
        </div>
    {:else}
        <div class="h-full flex flex-col gap-2 py-2">
            {#each data as item, i}
                {@const barWidth = (item.count / maxCount) * 100}
                <div class="flex items-center gap-3 group">
                    <div class="w-20 text-right text-xs font-medium text-gray-600 truncate" title={item.name}>
                        {item.name}
                    </div>
                    <div class="flex-1 h-6 bg-gray-100 rounded overflow-hidden relative">
                        <div
                            class="h-full rounded transition-all duration-300 ease-out group-hover:brightness-110"
                            style="width: {barWidth}%; background-color: {getColor(i, item.color)};"
                        ></div>
                        <span
                            class="absolute right-2 top-1/2 -translate-y-1/2 text-xs font-semibold"
                            style="color: {barWidth > 80 ? 'white' : '#374151'};"
                        >
                            {item.count}
                        </span>
                    </div>
                </div>
            {/each}
        </div>
    {/if}
</div>
