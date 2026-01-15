<script>
  import { onMount } from "svelte";
  import ShapeRenderer from "$lib/components/ShapeRenderer.svelte";
  import Button from "$lib/components/ui/Button.svelte";
  import MultiSelectFilter from "$lib/components/filters/MultiSelectFilter.svelte";
  import RangeFilter from "$lib/components/filters/RangeFilter.svelte";
  import ToggleFilter from "$lib/components/filters/ToggleFilter.svelte";
  import SortToggleFilter from "$lib/components/filters/SortToggleFilter.svelte";
  import {
    fetchProjects,
    fetchProject,
    fetchFilters,
    downloadProject,
    fetchSettings,
    updateSettings,
    fetchProjectsSummaryStatus,
    batchGenerateSummary,
    validateWorkflows,
  } from "$lib/api/project";

  // ============================================
  // CONFIGURATION
  // ============================================

  // 우선적으로 노출할 필터들의 key 목록 (여기에 없는 필터는 'Detailed Filtering'을 켜야 보임)
  const PRIMARY_FILTER_KEYS = ["year", "semester", "subject", "grade"];

  const CARD_CONFIG = {
    header: {
      title: "name",
      date: "created_at",
    },
    subtitle: "title",
    footer: {
      left: [
        { key: "db_no", prefix: "DB No. " },
        { key: "slide_count", suffix: " slides" },
        { key: "author", prefix: "by " },
      ],
      primary: [], // top row badges
      secondary: [], // bottom row badges
    },
  };

  const BUILT_IN_DISPLAY_NAMES = {
    name: "Name",
    title: "Title",
    author: "Author",
    subject: "Subject",
    created_at: "Date",
    slide_count: "Slides",
  };

  /** @type {any[]} */
  let projects = [];
  let loading = true;
  let searchTerm = "";

  // Sorting state
  let sortBy = "date";
  let sortDirection = "desc";

  // Dynamic filters
  /** @type {any[]} */
  let filters = [];
  /** @type {Record<string, any>} */
  let selectedFilters = {};

  // UI State: 상세 필터 보기 여부
  let showDetailedFilters = false;

  // Feature toggles
  let enableUpload = false;
  let enableDownload = true;
  let allowEdit = true;

  // Thumbnail toggle
  let useThumbnails = false;
  let loadingSettings = false;

  // Batch summary generation mode
  let selectionMode = false;
  /** @type {Set<string>} */
  let selectedProjectIds = new Set();
  let batchGenerating = false;
  let batchProgress = { current: 0, total: 0, currentProjectId: "" };

  // Summary status tracking
  /** @type {Record<string, { has_summary: boolean, is_outdated: boolean }>} */
  let summaryStatusMap = {};
  let currentPromptVersion = "";

  // Workflow validation status (projects with invalid actions/params)
  /** @type {Set<string>} */
  let workflowWarningProjects = new Set();

  // Pinned projects (stored in localStorage)
  const PINNED_STORAGE_KEY = "pipiiitiii_pinned_projects";
  /** @type {Set<string>} */
  let pinnedProjectIds = new Set();

  function loadPinnedProjects() {
    try {
      const stored = localStorage.getItem(PINNED_STORAGE_KEY);
      if (stored) {
        pinnedProjectIds = new Set(JSON.parse(stored));
      }
    } catch (e) {
      console.error("Failed to load pinned projects", e);
    }
  }

  function savePinnedProjects() {
    try {
      localStorage.setItem(PINNED_STORAGE_KEY, JSON.stringify([...pinnedProjectIds]));
    } catch (e) {
      console.error("Failed to save pinned projects", e);
    }
  }

  function togglePinProject(projectId, event) {
    event.stopPropagation();
    if (pinnedProjectIds.has(projectId)) {
      pinnedProjectIds.delete(projectId);
    } else {
      pinnedProjectIds.add(projectId);
    }
    pinnedProjectIds = pinnedProjectIds; // Trigger reactivity
    savePinnedProjects();
  }

  $: displayNameMap = {
    ...BUILT_IN_DISPLAY_NAMES,
    ...filters.reduce((acc, filter) => {
      acc[filter.key] = filter.display_name;
      return acc;
    }, {}),
  };

  $: attributeKeys = filters.map((f) => f.key);

  // Primary vs Secondary Filters 구분
  $: primaryFilters = filters.filter((f) =>
    PRIMARY_FILTER_KEYS.includes(f.key),
  );
  $: secondaryFilters = filters.filter(
    (f) => !PRIMARY_FILTER_KEYS.includes(f.key),
  );
  // 화면에 표시할 최종 필터 목록
  $: visibleFilters = showDetailedFilters
    ? [...primaryFilters, ...secondaryFilters]
    : primaryFilters;

  /** @param {any} filter */
  const getVariant = (filter) => filter?.attr_type?.variant || "multi_select";

  /** @param {any} value */
  const normalizeBool = (value) =>
    value === true || value === "true" || value === 1 || value === "1";

  // Selection state
  let selectedProjectId = null;
  /** @type {any} */
  let selectedProjectDetails = null;
  let loadingDetails = false;
  let downloading = false;
  let thumbnailWidth = 0;

  $: baseSlideWidth = selectedProjectDetails?.slide_width || 960;
  $: baseSlideHeight = selectedProjectDetails?.slide_height || 540;
  $: thumbnailScale = thumbnailWidth ? thumbnailWidth / baseSlideWidth : 0;
  $: thumbnailHeight = baseSlideHeight * thumbnailScale;

  $: filteredProjects = projects
    .filter((p) => {
      const term = searchTerm.toLowerCase();
      const matchesSearch =
        p.name.toLowerCase().includes(term) ||
        (p.author && p.author.toLowerCase().includes(term)) ||
        (p.title && p.title.toLowerCase().includes(term)) ||
        (p.subject && p.subject.toLowerCase().includes(term));

      if (!matchesSearch) return false;

      // Check dynamic filters
      for (const filter of filters) {
        const variant = getVariant(filter);
        const selectedValue = selectedFilters[filter.key];
        const projectValue = p[filter.key];

        if (variant === "multi_select") {
          if (Array.isArray(selectedValue) && selectedValue.length > 0) {
            if (!selectedValue.includes(projectValue)) {
              return false;
            }
          }
        } else if (variant === "range") {
          const min = selectedValue?.min;
          const max = selectedValue?.max;
          const numericValue = Number(projectValue);
          if (min !== "" && min !== undefined && min !== null) {
            if (Number.isNaN(numericValue) || numericValue < Number(min)) {
              return false;
            }
          }
          if (max !== "" && max !== undefined && max !== null) {
            if (Number.isNaN(numericValue) || numericValue > Number(max)) {
              return false;
            }
          }
        } else if (variant === "toggle") {
          if (selectedValue === "on" && !normalizeBool(projectValue)) {
            return false;
          }
          if (selectedValue === "off" && normalizeBool(projectValue)) {
            return false;
          }
        } else if (selectedValue && selectedValue !== "") {
          if (projectValue != selectedValue) {
            return false;
          }
        }
      }
      return true;
    })
    .sort((a, b) => {
      // Pinned projects always come first
      const aPinned = pinnedProjectIds.has(a.id);
      const bPinned = pinnedProjectIds.has(b.id);
      if (aPinned && !bPinned) return -1;
      if (!aPinned && bPinned) return 1;

      let valA, valB;

      if (sortBy === "date") {
        valA = new Date(a.created_at);
        valB = new Date(b.created_at);
      } else if (sortBy === "name") {
        valA = a.name;
        valB = b.name;
      } else if (sortBy === "author") {
        valA = a.author || "";
        valB = b.author || "";
      } else if (sortBy === "title") {
        valA = a.title || "";
        valB = b.title || "";
      } else {
        valA = a[sortBy];
        valB = b[sortBy];
        if (
          !isNaN(Number(valA)) &&
          !isNaN(Number(valB)) &&
          valA !== "" &&
          valB !== ""
        ) {
          valA = Number(valA);
          valB = Number(valB);
        }
      }

      if (valA === valB) return 0;
      if (valA === undefined || valA === null) return 1;
      if (valB === undefined || valB === null) return -1;

      let comparison = 0;
      if (typeof valA === "string" && typeof valB === "string") {
        comparison = valA.localeCompare(valB);
      } else {
        comparison = valA > valB ? 1 : -1;
      }

      return sortDirection === "asc" ? comparison : -comparison;
    });

  onMount(async () => {
    // Load pinned projects from localStorage first
    loadPinnedProjects();

    try {
      const [projectsRes, filtersRes, settingsRes] = await Promise.all([
        fetchProjects(),
        fetchFilters(),
        fetchSettings(),
      ]);

      if (projectsRes.ok) {
        projects = await projectsRes.json();
      }
      if (filtersRes.ok) {
        const fetchedFilters = await filtersRes.json();
        filters = fetchedFilters;
        selectedFilters = fetchedFilters.reduce((acc, f) => {
          const variant = getVariant(f);
          if (variant === "multi_select") {
            acc[f.key] = [];
          } else if (variant === "range") {
            acc[f.key] = {
              min: f.range?.min ?? "",
              max: f.range?.max ?? "",
            };
          } else if (variant === "toggle") {
            acc[f.key] = "";
          } else {
            acc[f.key] = "";
          }
          return acc;
        }, {});
      }
      if (settingsRes.ok) {
        const settings = await settingsRes.json();
        useThumbnails = settings.use_thumbnails || false;
      }

      // Load summary status
      await loadSummaryStatus();
      // Load workflow validation status
      await loadWorkflowValidation();
    } catch (e) {
      console.error(e);
    } finally {
      loading = false;
    }
  });

  async function loadSummaryStatus() {
    try {
      const res = await fetchProjectsSummaryStatus();
      if (res.ok) {
        const data = await res.json();
        currentPromptVersion = data.current_version;
        summaryStatusMap = {};
        for (const project of data.projects) {
          summaryStatusMap[project.id] = {
            has_summary: project.has_summary,
            is_outdated: project.is_outdated,
          };
        }
      }
    } catch (e) {
      console.error("Failed to load summary status", e);
    }
  }

  async function loadWorkflowValidation() {
    try {
      const res = await validateWorkflows();
      if (res.ok) {
        const data = await res.json();
        workflowWarningProjects = new Set(
          data.invalid_projects.map(p => p.project_id)
        );
      }
    } catch (e) {
      console.error("Failed to load workflow validation", e);
    }
  }

  function toggleSelectionMode() {
    selectionMode = !selectionMode;
    if (!selectionMode) {
      selectedProjectIds = new Set();
    }
  }

  function toggleProjectSelection(projectId) {
    if (selectedProjectIds.has(projectId)) {
      selectedProjectIds.delete(projectId);
    } else {
      selectedProjectIds.add(projectId);
    }
    selectedProjectIds = selectedProjectIds; // Trigger reactivity
  }

  function selectAll() {
    selectedProjectIds = new Set(filteredProjects.map(p => p.id));
  }

  function deselectAll() {
    selectedProjectIds = new Set();
  }

  function selectOutdatedOnly() {
    selectedProjectIds = new Set(
      filteredProjects
        .filter(p => {
          const status = summaryStatusMap[p.id];
          return !status?.has_summary || status?.is_outdated;
        })
        .map(p => p.id)
    );
  }

  async function startBatchGeneration() {
    if (selectedProjectIds.size === 0) return;

    // Save selected IDs before clearing
    const projectIdsToGenerate = Array.from(selectedProjectIds);

    batchGenerating = true;
    batchProgress = { current: 0, total: projectIdsToGenerate.length, currentProjectId: "" };

    // Exit selection mode immediately - let it run in background
    selectionMode = false;
    selectedProjectIds = new Set();

    try {
      const stream = await batchGenerateSummary(projectIdsToGenerate);
      if (!stream) {
        throw new Error("No stream returned");
      }

      const reader = stream.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const text = decoder.decode(value, { stream: true });
        const lines = text.split("\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));

              if (data.type === "progress") {
                batchProgress = {
                  current: data.current,
                  total: data.total,
                  currentProjectId: data.project_id,
                };
              } else if (data.type === "complete") {
                // Update local status
                summaryStatusMap[data.project_id] = {
                  has_summary: true,
                  is_outdated: false,
                };
                summaryStatusMap = summaryStatusMap;
              } else if (data.type === "error") {
                console.error(`Error for ${data.project_id}: ${data.message}`);
              } else if (data.type === "done") {
                // All done
              }
            } catch (e) {
              // Ignore parse errors for incomplete JSON
            }
          }
        }
      }

      // Reload summary status after completion
      await loadSummaryStatus();
    } catch (e) {
      console.error("Batch generation failed", e);
      alert("일괄 생성 중 오류가 발생했습니다.");
    } finally {
      batchGenerating = false;
    }
  }

  async function selectProject(project) {
    selectedProjectId = project.id;
    selectedProjectDetails = null;
    loadingDetails = true;
    try {
      const res = await fetchProject(project.id);
      if (res.ok) {
        selectedProjectDetails = await res.json();
      }
    } catch (e) {
      console.error("Failed to load project details", e);
    } finally {
      loadingDetails = false;
    }
  }

  async function toggleThumbnailView() {
    loadingSettings = true;
    try {
      // Get current settings first
      const settingsRes = await fetchSettings();
      if (settingsRes.ok) {
        const settings = await settingsRes.json();
        // Toggle the value
        settings.use_thumbnails = !useThumbnails;
        // Save updated settings
        const updateRes = await updateSettings(settings);
        if (updateRes.ok) {
          useThumbnails = settings.use_thumbnails;
        } else {
          console.error("Failed to update settings");
        }
      }
    } catch (e) {
      console.error("Failed to toggle thumbnail view", e);
    } finally {
      loadingSettings = false;
    }
  }

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
    return keys
      .map((key) => {
        const value = formatValue(project[key]);
        if (!value) return null;
        return {
          key,
          label: displayNameMap[key] || key,
          value,
        };
      })
      .filter(Boolean);
  };

  const getPrimaryBadges = (project) =>
    getBadges(project, CARD_CONFIG.footer.primary);
  const getSecondaryBadges = (project) =>
    getBadges(project, CARD_CONFIG.footer.secondary);

  function handleSortChange(key) {
    if (sortBy === key) {
      sortDirection = sortDirection === "asc" ? "desc" : "asc";
    } else {
      sortBy = key;
      sortDirection = "asc";
    }
  }
</script>

<div class="h-screen flex flex-col bg-gray-100 overflow-hidden">
  <div
    class="bg-white border-b border-gray-200 px-8 py-4 flex justify-between items-center shrink-0 z-10 shadow-sm"
  >
    <h1 class="text-2xl font-bold text-gray-800">PiPiiTiii</h1>
    <div class="flex gap-2 items-center">
      <button
        class="flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-lg transition-all duration-200
               {selectionMode
                   ? 'bg-purple-100 text-purple-700 hover:bg-purple-200 ring-1 ring-purple-300'
                   : 'bg-gradient-to-r from-purple-500 to-indigo-600 hover:from-purple-600 hover:to-indigo-700 text-white shadow-sm hover:shadow-md'}"
        on:click={toggleSelectionMode}
        disabled={batchGenerating}
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
        {selectionMode ? '선택 모드 해제' : '선택 PPT 요약 자동생성'}
      </button>
      <div class="w-px h-6 bg-gray-300"></div>
      <Button
        variant="secondary"
        on:click={toggleThumbnailView}
        disabled={loadingSettings}
        title={useThumbnails ? "렌더링 보기로 전환" : "썸네일 보기로 전환"}
      >
        {#if useThumbnails}
          <svg
            class="w-4 h-4 mr-2"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M4 5a1 1 0 011-1h4a1 1 0 011 1v7a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM14 5a1 1 0 011-1h4a1 1 0 011 1v7a1 1 0 01-1 1h-4a1 1 0 01-1-1V5zM4 16a1 1 0 011-1h4a1 1 0 011 1v3a1 1 0 01-1 1H5a1 1 0 01-1-1v-3zM14 16a1 1 0 011-1h4a1 1 0 011 1v3a1 1 0 01-1 1h-4a1 1 0 01-1-1v-3z"
            />
          </svg>
          썸네일 보기
        {:else}
          <svg
            class="w-4 h-4 mr-2"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
            />
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
            />
          </svg>
          렌더링 보기
        {/if}
      </Button>
      <Button
        href="/settings"
        variant="secondary"
        class="flex items-center gap-2"
      >
        <svg
          class="w-4 h-4 mr-1"
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
        설정
      </Button>
      {#if enableUpload}
        <Button href="/upload" variant="primary">Upload New PPT</Button>
      {/if}
    </div>
  </div>

  <div class="flex-1 flex overflow-hidden">
    <div
      class="w-2/3 min-w-[60vh] max-w-[120vh] flex flex-col border-r border-gray-200 bg-white"
    >
      <div
        class="p-5 border-b border-gray-100 bg-white z-10 shadow-[0_4px_6px_-1px_rgba(0,0,0,0.02)]"
      >
        <div class="mb-4">
          <input
            type="text"
            placeholder="Search projects by name, author, or subject..."
            bind:value={searchTerm}
            class="w-full border border-gray-200 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent shadow-sm transition-all"
          />
        </div>

        <div class="space-y-4">
          <div class="grid gap-3 grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {#each visibleFilters as filter (filter.key)}
              {#if getVariant(filter) === "multi_select"}
                <MultiSelectFilter
                  title={filter.display_name}
                  options={filter.options || []}
                  selected={selectedFilters[filter.key] || []}
                  onChange={(newSelected) =>
                    (selectedFilters[filter.key] = newSelected)}
                />
              {:else if getVariant(filter) === "range"}
                <RangeFilter
                  title={filter.display_name}
                  min={filter.range?.min ?? 0}
                  max={filter.range?.max ?? 100}
                  selectedMin={selectedFilters[filter.key]?.min}
                  selectedMax={selectedFilters[filter.key]?.max}
                  onChange={(range) => (selectedFilters[filter.key] = range)}
                  isSorted={sortBy === filter.key}
                  {sortDirection}
                  onSortChange={() => handleSortChange(filter.key)}
                />
              {:else if getVariant(filter) === "toggle"}
                <ToggleFilter
                  title={filter.display_name}
                  value={selectedFilters[filter.key] || ""}
                  onChange={(val) => (selectedFilters[filter.key] = val)}
                />
              {:else}
                <SortToggleFilter
                  title={filter.display_name}
                  active={sortBy === filter.key}
                  direction={sortBy === filter.key ? sortDirection : "asc"}
                  onToggle={() => handleSortChange(filter.key)}
                />
              {/if}
            {/each}
          </div>

          {#if secondaryFilters.length > 0}
            <div class="flex justify-center pt-2">
              <button
                class="flex items-center gap-2 text-xs font-medium text-gray-500 hover:text-blue-600 transition-colors"
                on:click={() => (showDetailedFilters = !showDetailedFilters)}
              >
                <span
                  >{showDetailedFilters
                    ? "Show Less Filters"
                    : "Detailed Filtering"}</span
                >
                <svg
                  class="w-3 h-3 transform transition-transform {showDetailedFilters
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
            </div>
          {/if}
        </div>
      </div>

      <div class="flex-1 overflow-y-auto bg-gray-50/50">
        <!-- Selection Mode Toolbar -->
        {#if selectionMode}
          <div class="sticky top-0 z-20 bg-purple-50 border-b border-purple-200 px-4 py-3 flex items-center justify-between shadow-sm">
            <div class="flex items-center gap-3">
              <span class="text-sm font-medium text-purple-700">
                {selectedProjectIds.size}개 선택됨
              </span>
              <div class="flex items-center gap-1">
                <button
                  class="px-3 py-1.5 text-xs font-medium rounded-md bg-white text-gray-700 border border-gray-300 hover:bg-gray-50 transition-colors"
                  on:click={selectAll}
                >
                  전체 선택
                </button>
                <button
                  class="px-3 py-1.5 text-xs font-medium rounded-md bg-white text-gray-700 border border-gray-300 hover:bg-gray-50 transition-colors"
                  on:click={deselectAll}
                >
                  전체 해제
                </button>
                <button
                  class="px-3 py-1.5 text-xs font-medium rounded-md bg-amber-100 text-amber-700 border border-amber-300 hover:bg-amber-200 transition-colors"
                  on:click={selectOutdatedOnly}
                  title="요약이 없거나 이전 버전인 프로젝트만 선택"
                >
                  업데이트 필요만 선택
                </button>
              </div>
            </div>
            <button
              class="flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-lg
                     bg-gradient-to-r from-purple-500 to-indigo-600 hover:from-purple-600 hover:to-indigo-700
                     text-white shadow-sm hover:shadow-md transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              on:click={startBatchGeneration}
              disabled={selectedProjectIds.size === 0 || batchGenerating}
            >
              {#if batchGenerating}
                <svg class="animate-spin w-4 h-4" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span>생성 중... ({batchProgress.current}/{batchProgress.total})</span>
              {:else}
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                <span>선택 항목 요약 생성</span>
              {/if}
            </button>
          </div>
        {/if}

        {#if loading}
          <div class="p-8 text-center text-gray-500 text-sm">
            Loading projects...
          </div>
        {:else if filteredProjects.length === 0}
          <div class="p-8 text-center text-gray-500 text-sm">
            No projects found matching your criteria.
          </div>
        {:else}
          <div class="p-4 space-y-3">
            {#each filteredProjects as project (project.id)}
              {@const primaryBadges = getPrimaryBadges(project)}
              {@const secondaryBadges = getSecondaryBadges(project)}
              {@const isSelected = selectedProjectId === project.id}
              {@const isChecked = selectedProjectIds.has(project.id)}
              {@const summaryStatus = summaryStatusMap[project.id]}
              {@const hasWorkflowWarning = workflowWarningProjects.has(project.id)}
              {@const isPinned = pinnedProjectIds.has(project.id)}

              <div class="relative group">
                <!-- Pin Button (outside the card button to avoid nesting) -->
                <button
                  class="absolute -right-1 -top-1 z-20 w-7 h-7 rounded-full flex items-center justify-center transition-all
                         {isPinned
                         ? 'bg-amber-500 text-white shadow-md hover:bg-amber-600'
                         : 'bg-white border-2 border-gray-200 text-gray-400 opacity-0 group-hover:opacity-100 hover:border-amber-400 hover:text-amber-500'}"
                  on:click={(e) => togglePinProject(project.id, e)}
                  title={isPinned ? '고정 해제' : '상단에 고정'}
                >
                  <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 2C8.69 2 6 4.69 6 8c0 2.36 1.37 4.41 3.36 5.42L8 18h3v4l1 1 1-1v-4h3l-1.36-4.58C16.63 12.41 18 10.36 18 8c0-3.31-2.69-6-6-6zm0 11c-1.66 0-3-1.34-3-3s1.34-3 3-3 3 1.34 3 3-1.34 3-3 3z"/>
                  </svg>
                </button>

                <button
                  class="w-full text-left p-4 rounded-xl transition-all duration-200 border bg-white flex flex-col gap-2 relative
                    {selectionMode && isChecked
                    ? 'border-purple-400 ring-1 ring-purple-300 bg-purple-50/50'
                    : isPinned
                    ? 'border-amber-400 ring-1 ring-amber-300 bg-amber-50/30 shadow-md'
                    : isSelected
                    ? 'border-blue-500 ring-1 ring-blue-500 shadow-md z-10'
                    : 'border-gray-200 shadow-sm hover:shadow-md hover:border-blue-300'}
                    {batchGenerating && batchProgress.currentProjectId === project.id ? 'animate-pulse' : ''}"
                  on:click={() => selectionMode ? toggleProjectSelection(project.id) : selectProject(project)}
                >
                  <!-- Selection Checkbox (shown in selection mode) -->
                  {#if selectionMode}
                    <div class="absolute -left-1 -top-1 z-10">
                      <div class="w-6 h-6 rounded-full flex items-center justify-center transition-all
                                  {isChecked ? 'bg-purple-500' : 'bg-white border-2 border-gray-300'}">
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
                      <!-- Pinned Badge -->
                      {#if isPinned}
                        <div class="flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-100 border border-amber-300" title="고정된 프로젝트">
                          <svg class="w-3 h-3 text-amber-600" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M12 2C8.69 2 6 4.69 6 8c0 2.36 1.37 4.41 3.36 5.42L8 18h3v4l1 1 1-1v-4h3l-1.36-4.58C16.63 12.41 18 10.36 18 8c0-3.31-2.69-6-6-6zm0 11c-1.66 0-3-1.34-3-3s1.34-3 3-3 3 1.34 3 3-1.34 3-3 3z"/>
                          </svg>
                          <span class="text-[10px] font-medium text-amber-700">고정됨</span>
                        </div>
                      {/if}
                      <h3
                        class="font-bold text-gray-800 text-lg truncate pr-2 group-hover:text-blue-700 transition-colors"
                      >
                        {getFieldValue(project, CARD_CONFIG.header.title) ||
                          "Untitled"}
                      </h3>
                      <!-- Summary Status Indicator -->
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
                    <!-- Workflow Warning -->
                    {#if hasWorkflowWarning}
                      <div class="flex items-center gap-1 px-2 py-0.5 rounded-full bg-red-50 border border-red-200" title="워크플로우에 삭제된 액션 또는 파라미터가 사용되고 있습니다">
                        <svg class="w-3 h-3 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                          <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                        </svg>
                        <span class="text-[10px] font-medium text-red-600">워크플로우 오류</span>
                      </div>
                    {/if}
                  </div>
                  {#if CARD_CONFIG.header.date && project[CARD_CONFIG.header.date]}
                    <span
                      class="text-xs font-medium text-gray-400 whitespace-nowrap bg-gray-50 px-2 py-1 rounded shrink-0"
                    >
                      {new Date(
                        project[CARD_CONFIG.header.date],
                      ).toLocaleDateString()}
                    </span>
                  {/if}
                </div>

                {#if CARD_CONFIG.subtitle}
                  {@const subtitleValue = getFieldValue(
                    project,
                    CARD_CONFIG.subtitle,
                  )}
                  {#if subtitleValue}
                    <p class="text-sm text-gray-600 truncate">
                      {subtitleValue}
                    </p>
                  {/if}
                {/if}

                <div class="h-px bg-gray-100 w-full my-1"></div>

                <div class="flex items-end justify-between gap-3">
                  <div
                    class="flex items-center gap-3 text-xs text-gray-500 shrink-0"
                  >
                    {#each CARD_CONFIG.footer.left as field}
                      {@const fieldValue = getFieldValue(project, field)}
                      {#if fieldValue}
                        <span class="flex items-center gap-1">
                          <span class="w-1.5 h-1.5 rounded-full bg-gray-300"
                          ></span>
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
                            <span
                              class="text-xs leading-none px-2 py-1 rounded-md bg-blue-50 text-blue-700 border border-blue-100 font-semibold truncate max-w-[150px]"
                              title={`${badge.label}: ${badge.value}`}
                            >
                              {badge.value}
                            </span>
                          {/each}
                        </div>
                      {/if}
                      {#if secondaryBadges.length}
                        <div class="flex flex-wrap gap-1.5 justify-end">
                          {#each secondaryBadges as badge}
                            <span
                              class="text-[11px] leading-none px-1.5 py-0.5 rounded-md bg-gray-100 text-gray-600 border border-gray-200 truncate max-w-[120px]"
                              title={`${badge.label}: ${badge.value}`}
                            >
                              {badge.value}
                            </span>
                          {/each}
                        </div>
                      {/if}
                    </div>
                  {/if}
                </div>
                </button>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    </div>

    <div class="flex-1 bg-gray-50 flex flex-col overflow-hidden relative">
      {#if !selectedProjectId}
        <div
          class="flex-1 flex flex-col items-center justify-center text-gray-400"
        >
          <svg
            class="w-20 h-20 mb-4 opacity-10"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fill-rule="evenodd"
              d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z"
              clip-rule="evenodd"
            />
          </svg>
          <p class="text-lg font-medium text-gray-500">
            Select a project to preview
          </p>
        </div>
      {:else if loadingDetails}
        <div class="flex-1 flex items-center justify-center text-gray-500">
          <div
            class="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 mb-2"
          ></div>
        </div>
      {:else if selectedProjectDetails}
        <div
          class="bg-white border-b border-gray-200 px-6 py-4 flex justify-between items-center shadow-sm z-10"
        >
          <div>
            <h2 class="text-xl font-bold text-gray-800">
              {selectedProjectDetails.name}
            </h2>
            <div class="flex items-center gap-2 mt-1">
              <span class="text-sm text-gray-500">
                {selectedProjectDetails.slide_count} slides
              </span>
              <span class="text-gray-300">•</span>
              <span class="text-sm text-gray-500">
                Modified {new Date(
                  selectedProjectDetails.created_at,
                ).toLocaleDateString()}
              </span>
            </div>
          </div>
          <div class="flex gap-2">
            <Button
              href={`/viewer/${selectedProjectId}?allowEdit=${allowEdit}`}
              variant="primary"
            >
              <span>Open Viewer</span>
              <svg
                class="w-4 h-4 ml-2"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M14 5l7 7m0 0l-7 7m7-7H3"
                />
              </svg>
            </Button>
            {#if enableDownload}
              <Button
                variant="success"
                loading={downloading}
                disabled={downloading}
                on:click={async () => {
                  if (downloading) return;
                  downloading = true;
                  try {
                    await downloadProject(selectedProjectId);
                  } catch (e) {
                    console.error(e);
                    alert("Failed to download PPT");
                  } finally {
                    downloading = false;
                  }
                }}
              >
                Download
              </Button>
            {/if}
          </div>
        </div>

        <div class="flex-1 overflow-y-auto p-8 bg-gray-50">
          <div class="grid grid-cols-1 gap-8 max-w-4xl mx-auto">
            {#each selectedProjectDetails.slides as slide}
              <div class="group flex flex-col items-center w-full">
                <div
                  class="w-full bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden group-hover:shadow-lg transition-shadow duration-300 relative"
                >
                  <div
                    class="relative w-full"
                    bind:clientWidth={thumbnailWidth}
                    style={`height: ${thumbnailHeight}px;`}
                  >
                    {#if useThumbnails}
                      <img
                        src={`/api/results/${selectedProjectId}/thumbnails/slide_${slide.slide_index.toString().padStart(3, "0")}_thumb.png`}
                        alt={`Slide ${slide.slide_index} thumbnail`}
                        class="w-full h-full object-contain"
                        on:error={(e) => {
                          console.warn(
                            `Thumbnail not found for slide ${slide.slide_index}, falling back to rendering`,
                          );
                          e.target.style.display = "none";
                        }}
                      />
                    {:else}
                      <div
                        class="absolute top-0 left-0 origin-top-left pointer-events-none"
                        style={`width: ${baseSlideWidth}px; height: ${baseSlideHeight}px; transform: scale(${thumbnailScale});`}
                      >
                        {#each slide.shapes.sort((a, b) => (a.z_order_position || 0) - (b.z_order_position || 0)) as shape}
                          <div class="absolute top-0 left-0">
                            <ShapeRenderer
                              {shape}
                              projectId={selectedProjectId}
                            />
                          </div>
                        {/each}
                      </div>
                    {/if}
                    <a
                      href={`/viewer/${selectedProjectId}?slide=${slide.slide_index}`}
                      class="absolute inset-0 bg-blue-900 bg-opacity-0 group-hover:bg-opacity-5 transition-all flex items-center justify-center"
                    >
                      <span
                        class="opacity-0 group-hover:opacity-100 bg-white text-blue-600 px-4 py-2 rounded-full font-semibold shadow-lg transform translate-y-2 group-hover:translate-y-0 transition-all"
                      >
                        View Slide
                      </span>
                    </a>
                  </div>
                </div>
                <p
                  class="text-center text-sm text-gray-500 mt-3 font-medium bg-white px-3 py-1 rounded-full border border-gray-100 shadow-sm"
                >
                  Slide {slide.slide_index}
                </p>
              </div>
            {/each}
          </div>
        </div>
      {/if}
    </div>
  </div>
</div>
