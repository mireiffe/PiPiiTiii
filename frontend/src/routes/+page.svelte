<script>
  import { onMount } from "svelte";
  import ShapeRenderer from "$lib/components/ShapeRenderer.svelte";
  import MultiSelectFilter from "$lib/components/filters/MultiSelectFilter.svelte";
  import RangeFilter from "$lib/components/filters/RangeFilter.svelte";
  import ToggleFilter from "$lib/components/filters/ToggleFilter.svelte";
  import SortToggleFilter from "$lib/components/filters/SortToggleFilter.svelte";
  import {
    fetchProjects,
    fetchProject,
    fetchFilters,
    downloadProject,
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
      left: [{ key: "slide_count", suffix: " slides" }, { key: "author", prefix: "by " }],
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

  $: displayNameMap = {
    ...BUILT_IN_DISPLAY_NAMES,
    ...filters.reduce(
      (acc, filter) => {
        acc[filter.key] = filter.display_name;
        return acc;
      },
      {}
    ),
  };

  $: attributeKeys = filters.map((f) => f.key);

  // Primary vs Secondary Filters 구분
  $: primaryFilters = filters.filter(f => PRIMARY_FILTER_KEYS.includes(f.key));
  $: secondaryFilters = filters.filter(f => !PRIMARY_FILTER_KEYS.includes(f.key));
  // 화면에 표시할 최종 필터 목록
  $: visibleFilters = showDetailedFilters ? [...primaryFilters, ...secondaryFilters] : primaryFilters;

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
        if (!isNaN(Number(valA)) && !isNaN(Number(valB)) && valA !== "" && valB !== "") {
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
    try {
      const [projectsRes, filtersRes] = await Promise.all([
        fetchProjects(),
        fetchFilters(),
      ]);

      if (projectsRes.ok) {
        projects = await projectsRes.json();
      }
      if (filtersRes.ok) {
        const fetchedFilters = await filtersRes.json();
        filters = fetchedFilters;
        selectedFilters = fetchedFilters.reduce(
          (acc, f) => {
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
          },
          {},
        );
      }
    } catch (e) {
      console.error(e);
    } finally {
      loading = false;
    }
  });

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

  const getPrimaryBadges = (project) => getBadges(project, CARD_CONFIG.footer.primary);
  const getSecondaryBadges = (project) => getBadges(project, CARD_CONFIG.footer.secondary);

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
  <div class="bg-white border-b border-gray-200 px-8 py-4 flex justify-between items-center shrink-0 z-10 shadow-sm">
    <h1 class="text-2xl font-bold text-gray-800">PiPiiTiii</h1>
    <a
      href="/upload"
      class="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition shadow-sm text-sm font-medium"
    >
      Upload New PPT
    </a>
  </div>

  <div class="flex-1 flex overflow-hidden">
    <div class="w-2/3 min-w-[60vh] max-w-[120vh] flex flex-col border-r border-gray-200 bg-white">
      <div class="p-5 border-b border-gray-100 bg-white z-10 shadow-[0_4px_6px_-1px_rgba(0,0,0,0.02)]">
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
             <SortToggleFilter
               title="Date"
               active={sortBy === "date"}
               direction={sortBy === "date" ? sortDirection : "desc"}
               onToggle={() => handleSortChange("date")}
             />
             <SortToggleFilter
               title="Name"
               active={sortBy === "name"}
               direction={sortBy === "name" ? sortDirection : "asc"}
               onToggle={() => handleSortChange("name")}
             />

             {#each visibleFilters as filter (filter.key)}
                {#if getVariant(filter) === "multi_select"}
                  <MultiSelectFilter
                    title={filter.display_name}
                    options={filter.options || []}
                    selected={selectedFilters[filter.key] || []}
                    onChange={(newSelected) => (selectedFilters[filter.key] = newSelected)}
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
                on:click={() => showDetailedFilters = !showDetailedFilters}
              >
                <span>{showDetailedFilters ? 'Show Less Filters' : 'Detailed Filtering'}</span>
                <svg class="w-3 h-3 transform transition-transform {showDetailedFilters ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                </svg>
              </button>
            </div>
          {/if}
        </div>
      </div>

      <div class="flex-1 overflow-y-auto bg-gray-50/50">
        {#if loading}
          <div class="p-8 text-center text-gray-500 text-sm">Loading projects...</div>
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
              
              <button
                class="w-full text-left p-4 rounded-xl transition-all duration-200 border bg-white flex flex-col gap-2 group
                  {isSelected 
                    ? 'border-blue-500 ring-1 ring-blue-500 shadow-md z-10' 
                    : 'border-gray-200 shadow-sm hover:shadow-md hover:border-blue-300'}"
                on:click={() => selectProject(project)}
              >
                <div class="flex justify-between items-start w-full">
                  <h3 class="font-bold text-gray-800 text-lg truncate pr-2 group-hover:text-blue-700 transition-colors">
                    {getFieldValue(project, CARD_CONFIG.header.title) || "Untitled"}
                  </h3>
                  {#if CARD_CONFIG.header.date && project[CARD_CONFIG.header.date]}
                    <span class="text-xs font-medium text-gray-400 whitespace-nowrap bg-gray-50 px-2 py-1 rounded">
                      {new Date(project[CARD_CONFIG.header.date]).toLocaleDateString()}
                    </span>
                  {/if}
                </div>

                {#if CARD_CONFIG.subtitle}
                  {@const subtitleValue = getFieldValue(project, CARD_CONFIG.subtitle)}
                  {#if subtitleValue}
                    <p class="text-sm text-gray-600 truncate">{subtitleValue}</p>
                  {/if}
                {/if}

                <div class="h-px bg-gray-100 w-full my-1"></div>

                <div class="flex items-end justify-between gap-3">
                  <div class="flex items-center gap-3 text-xs text-gray-500 shrink-0">
                    {#each CARD_CONFIG.footer.left as field}
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
            {/each}
          </div>
        {/if}
      </div>
    </div>

    <div class="flex-1 bg-gray-50 flex flex-col overflow-hidden relative">
      {#if !selectedProjectId}
        <div class="flex-1 flex flex-col items-center justify-center text-gray-400">
          <svg class="w-20 h-20 mb-4 opacity-10" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clip-rule="evenodd" />
          </svg>
          <p class="text-lg font-medium text-gray-500">Select a project to preview</p>
        </div>
      {:else if loadingDetails}
        <div class="flex-1 flex items-center justify-center text-gray-500">
          <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 mb-2"></div>
        </div>
      {:else if selectedProjectDetails}
        <div class="bg-white border-b border-gray-200 px-6 py-4 flex justify-between items-center shadow-sm z-10">
          <div>
            <h2 class="text-xl font-bold text-gray-800">{selectedProjectDetails.name}</h2>
            <div class="flex items-center gap-2 mt-1">
                 <span class="text-sm text-gray-500">
                   {selectedProjectDetails.slide_count} slides
                 </span>
                 <span class="text-gray-300">•</span>
                 <span class="text-sm text-gray-500">
                   Modified {new Date(selectedProjectDetails.created_at).toLocaleDateString()}
                 </span>
            </div>
          </div>
          <div class="flex gap-2">
            <a
              href={`/viewer/${selectedProjectId}`}
              class="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition shadow-sm text-sm font-medium flex items-center gap-2"
            >
              <span>Open Viewer</span>
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                 <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"/>
              </svg>
            </a>
            <button
              class="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition shadow-sm text-sm font-medium flex items-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed"
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
              disabled={downloading}
            >
              {#if downloading}
                <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span>Generating...</span>
              {:else}
                <span>Download</span>
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
                </svg>
              {/if}
            </button>
          </div>
        </div>

        <div class="flex-1 overflow-y-auto p-8 bg-gray-50">
          <div class="grid grid-cols-1 gap-8 max-w-4xl mx-auto">
            {#each selectedProjectDetails.slides as slide}
              <div class="group flex flex-col items-center">
                <div class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden group-hover:shadow-lg transition-shadow duration-300 relative">
                  <div
                    class="relative"
                    bind:clientWidth={thumbnailWidth}
                    style={`height: ${thumbnailHeight}px;`}
                  >
                    <div
                      class="absolute top-0 left-0 origin-top-left pointer-events-none"
                      style={`width: ${baseSlideWidth}px; height: ${baseSlideHeight}px; transform: scale(${thumbnailScale});`}
                    >
                      {#each slide.shapes.sort((a, b) => (a.z_order_position || 0) - (b.z_order_position || 0)) as shape}
                        <div class="absolute top-0 left-0">
                          <ShapeRenderer {shape} projectId={selectedProjectId} />
                        </div>
                      {/each}
                    </div>
                    <a
                      href={`/viewer/${selectedProjectId}?slide=${slide.slide_index}`}
                      class="absolute inset-0 bg-blue-900 bg-opacity-0 group-hover:bg-opacity-5 transition-all flex items-center justify-center"
                    >
                      <span class="opacity-0 group-hover:opacity-100 bg-white text-blue-600 px-4 py-2 rounded-full font-semibold shadow-lg transform translate-y-2 group-hover:translate-y-0 transition-all">
                        View Slide
                      </span>
                    </a>
                  </div>
                </div>
                <p class="text-center text-sm text-gray-500 mt-3 font-medium bg-white px-3 py-1 rounded-full border border-gray-100 shadow-sm">
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
