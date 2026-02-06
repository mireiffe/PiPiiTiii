<script lang="ts">
    import Modal from "$lib/components/ui/Modal.svelte";
    import type {
        ProjectKeyInfoData,
        KeyInfoSettings,
    } from "$lib/types/keyInfo";

    export let isOpen: boolean = false;
    export let keyInfoData: ProjectKeyInfoData;
    export let keyInfoSettings: KeyInfoSettings;

    import { createEventDispatcher } from "svelte";
    const dispatch = createEventDispatcher<{ close: void }>();

    // Log entry types
    type LogType = "instance_created" | "instance_updated" | "category_created";

    interface LogEntry {
        timestamp: string;
        type: LogType;
        label: string;
        detail: string;
    }

    const LOG_TYPE_META: Record<LogType, { label: string; color: string; bg: string }> = {
        instance_created: { label: "항목 추가", color: "text-green-700", bg: "bg-green-100" },
        instance_updated: { label: "항목 수정", color: "text-blue-700", bg: "bg-blue-100" },
        category_created: { label: "카테고리 생성", color: "text-purple-700", bg: "bg-purple-100" },
    };

    // Filter state
    let activeFilter: LogType | "all" = "all";

    // Helper: find category/item names
    function getCategoryName(categoryId: string): string {
        const cat = keyInfoSettings.categories.find((c) => c.id === categoryId);
        return cat?.name || categoryId;
    }

    function getItemTitle(categoryId: string, itemId: string): string {
        const cat = keyInfoSettings.categories.find((c) => c.id === categoryId);
        const item = cat?.items.find((i) => i.id === itemId);
        return item?.title || itemId;
    }

    // Extract log entries from existing data
    function extractLogs(): LogEntry[] {
        const entries: LogEntry[] = [];

        // 1. Category creation logs
        for (const category of keyInfoSettings.categories) {
            if (category.createdAt) {
                entries.push({
                    timestamp: category.createdAt,
                    type: "category_created",
                    label: category.name,
                    detail: `"${category.name}" 카테고리가 생성됨`,
                });
            }
        }

        // 2. Instance created/updated logs
        for (const instance of keyInfoData.instances) {
            const catName = getCategoryName(instance.categoryId);
            const itemTitle = getItemTitle(instance.categoryId, instance.itemId);

            if (instance.createdAt) {
                entries.push({
                    timestamp: instance.createdAt,
                    type: "instance_created",
                    label: `${catName} > ${itemTitle}`,
                    detail: `"${itemTitle}" 항목이 추가됨`,
                });
            }

            if (instance.updatedAt && instance.updatedAt !== instance.createdAt) {
                entries.push({
                    timestamp: instance.updatedAt,
                    type: "instance_updated",
                    label: `${catName} > ${itemTitle}`,
                    detail: `"${itemTitle}" 항목이 수정됨`,
                });
            }
        }

        // Sort descending (newest first)
        entries.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

        return entries;
    }

    // Format timestamp for display
    function formatTimestamp(iso: string): { date: string; time: string } {
        try {
            const d = new Date(iso);
            const date = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
            const time = `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
            return { date, time };
        } catch {
            return { date: iso, time: "" };
        }
    }

    // Group logs by date
    function groupByDate(logs: LogEntry[]): Map<string, LogEntry[]> {
        const groups = new Map<string, LogEntry[]>();
        for (const log of logs) {
            const { date } = formatTimestamp(log.timestamp);
            if (!groups.has(date)) groups.set(date, []);
            groups.get(date)!.push(log);
        }
        return groups;
    }

    // Reactive
    $: allLogs = extractLogs();
    $: filteredLogs = activeFilter === "all" ? allLogs : allLogs.filter((l) => l.type === activeFilter);
    $: groupedLogs = groupByDate(filteredLogs);

    // Filter button entries (precomputed for type safety)
    const LOG_TYPES: LogType[] = ["instance_created", "instance_updated", "category_created"];

    $: filterEntries = LOG_TYPES
        .map((type) => ({
            type,
            meta: LOG_TYPE_META[type],
            count: allLogs.filter((l) => l.type === type).length,
        }))
        .filter((e) => e.count > 0);

    function handleClose() {
        dispatch("close");
    }
</script>

<Modal {isOpen} title="활동 로그" size="lg" on:close={handleClose}>
    <!-- Filter buttons -->
    <div class="flex flex-wrap gap-1.5 mb-4 pb-3 border-b border-gray-100">
        <button
            class="px-2.5 py-1 text-xs rounded-full transition-colors
                   {activeFilter === 'all'
                ? 'bg-gray-800 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}"
            on:click={() => (activeFilter = "all")}
        >
            전체 <span class="ml-0.5 opacity-70">{allLogs.length}</span>
        </button>
        {#each filterEntries as entry (entry.type)}
            <button
                class="px-2.5 py-1 text-xs rounded-full transition-colors
                       {activeFilter === entry.type
                    ? `${entry.meta.bg} ${entry.meta.color} font-medium`
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}"
                on:click={() => (activeFilter = entry.type)}
            >
                {entry.meta.label} <span class="ml-0.5 opacity-70">{entry.count}</span>
            </button>
        {/each}
    </div>

    <!-- Log entries -->
    {#if filteredLogs.length === 0}
        <div class="text-center text-gray-400 py-12">
            <svg class="w-10 h-10 mx-auto mb-2 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p class="text-sm">기록된 활동이 없습니다.</p>
        </div>
    {:else}
        <div class="space-y-4 max-h-[60vh] overflow-y-auto">
            {#each [...groupedLogs] as [date, logs] (date)}
                <!-- Date header -->
                <div>
                    <div class="sticky top-0 bg-white/95 backdrop-blur-sm z-10 pb-1.5">
                        <span class="text-xs font-semibold text-gray-500">{date}</span>
                    </div>

                    <div class="space-y-1">
                        {#each logs as log (log.timestamp + log.type + log.label)}
                            {@const meta = LOG_TYPE_META[log.type]}
                            {@const { time } = formatTimestamp(log.timestamp)}
                            <div class="flex items-start gap-3 px-2 py-2 rounded-lg hover:bg-gray-50 transition-colors">
                                <!-- Time -->
                                <span class="text-xs text-gray-400 font-mono w-12 flex-shrink-0 pt-0.5">{time}</span>

                                <!-- Type badge -->
                                <span class="text-[10px] font-medium px-1.5 py-0.5 rounded flex-shrink-0 {meta.bg} {meta.color}">
                                    {meta.label}
                                </span>

                                <!-- Content -->
                                <div class="flex-1 min-w-0">
                                    <span class="text-xs text-gray-700">{log.detail}</span>
                                    <div class="text-[10px] text-gray-400 mt-0.5 truncate">{log.label}</div>
                                </div>
                            </div>
                        {/each}
                    </div>
                </div>
            {/each}
        </div>
    {/if}
</Modal>
