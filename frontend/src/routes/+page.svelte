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

  /** @type {any[]} */
  let projects = [];
  let loading = true;
  let searchTerm = "";

  // Sorting state
  let sortBy = "date"; // 'date' | 'name' | 'author' | 'title' | attribute_key
  let sortDirection = "desc"; // 'asc' | 'desc'

  // Dynamic filters
  /** @type {any[]} */
  let filters = [];
  /** @type {Record<string, any>} */
  let selectedFilters = {};
  let showAttributeFilters = false;

  // Attribute display mapping
  $: attributeDisplayMap = filters.reduce(
    (/** @type {Record<string, any>} */ acc, /** @type {any} */ filter) => {
      acc[filter.key] = filter.display_name;
      return acc;
    },
    {},
  );

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

  // 선택된 프로젝트의 기본 슬라이드 크기
  $: baseSlideWidth = selectedProjectDetails?.slide_width || 960;
  $: baseSlideHeight = selectedProjectDetails?.slide_height || 540;

  // 썸네일 스케일
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
        // Attribute sort
        valA = a[sortBy];
        valB = b[sortBy];

        // Try to parse as number if possible for correct sorting
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
      if (valA === undefined || valA === null) return 1; // push nulls to end
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
          (/** @type {Record<string, any>} */ acc, /** @type {any} */ f) => {
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

  /** @param {any} project */
  async function selectProject(project) {
    selectedProjectId = project.id;
    selectedProjectDetails = null; // Reset while loading
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

  $: console.log("selectedProjectDetails", selectedProjectDetails);

  /** @param {any} value */
  const formatAttributeValue = (value) => {
    if (value === undefined || value === null) return "";
    if (Array.isArray(value)) return value.join(", ");
    if (typeof value === "boolean") return value ? "Yes" : "No";
    return value === "" ? "" : String(value);
  };

  /** @param {any} project */
  const projectAttributes = (project) => {
    if (!project || filters.length === 0) return [];

    return filters
      .map((filter) => {
        const value = project[filter.key];
        const formatted = formatAttributeValue(value);

        if (!formatted) return null;

        return {
          key: filter.key,
          label: attributeDisplayMap[filter.key] || filter.key,
          value: formatted,
        };
      })
      .filter(Boolean);
  };

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
  <!-- Header -->
  <div
    class="bg-white border-b border-gray-200 px-8 py-4 flex justify-between items-center shrink-0"
  >
    <h1 class="text-2xl font-bold text-gray-800">PiPiiTiii</h1>
    <a
      href="/upload"
      class="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition shadow-sm text-sm font-medium"
    >
      Upload New PPT
    </a>
  </div>

  <div class="flex-1 flex overflow-hidden">
    <!-- Left Panel: Project List -->
    <div
      class="w-2/3 min-w-[60vh] max-w-[120vh] flex flex-col border-r border-gray-200 bg-white"
    >
      <!-- Search & Sort -->
      <div class="p-4 border-b border-gray-100 space-y-3">
        <input
          type="text"
          placeholder="Search projects..."
          bind:value={searchTerm}
          class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <div class="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          <!-- Default Sort Filters -->
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
          <SortToggleFilter
            title="Author"
            active={sortBy === "author"}
            direction={sortBy === "author" ? sortDirection : "asc"}
            onToggle={() => handleSortChange("author")}
          />
        </div>

        {#if filters.length > 0}
          <div class="grid gap-3 md:grid-cols-2 lg:grid-cols-3 pt-2">
            {#each filters as filter (filter.key)}
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
              {:else if getVariant(filter) === "sort_only"}
                <SortToggleFilter
                  title={filter.display_name}
                  active={sortBy === filter.key}
                  direction={sortBy === filter.key ? sortDirection : "asc"}
                  onToggle={() => handleSortChange(filter.key)}
                />
              {:else}
                <!-- Fallback for other types -->
                <div class="flex flex-col gap-1">
                  <span class="font-semibold text-gray-600 text-xs"
                    >{filter.display_name}</span
                  >
                  <input
                    type="text"
                    bind:value={selectedFilters[filter.key]}
                    placeholder={`Filter...`}
                    class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              {/if}
            {/each}
          </div>
        {/if}
      </div>

      <!-- List -->
      <div class="flex-1 overflow-y-auto">
        {#if loading}
          <div class="p-8 text-center text-gray-500 text-sm">Loading...</div>
        {:else if filteredProjects.length === 0}
          <div class="p-8 text-center text-gray-500 text-sm">
            No projects found.
          </div>
        {:else}
          <div class="divide-y divide-gray-100">
            {#each filteredProjects as project}
              {@const projectAttrs = projectAttributes(project)}
              <button
                class="w-full text-left p-4 hover:bg-gray-50 transition flex flex-col gap-1 {selectedProjectId ===
                project.id
                  ? 'bg-blue-50 border-l-4 border-blue-500'
                  : 'border-l-4 border-transparent'}"
                on:click={() => selectProject(project)}
              >
                <div class="flex justify-between items-start w-full">
                  <h3 class="font-semibold text-gray-800 truncate pr-2">
                    {project.name}
                  </h3>
                  <span class="text-xs text-gray-400 whitespace-nowrap">
                    {new Date(project.created_at).toLocaleDateString()}
                  </span>
                </div>
                {#if project.title}
                  <p class="text-sm text-gray-600 truncate">{project.title}</p>
                {/if}
                <div class="flex items-end justify-between mt-2 gap-2">
                  <div
                    class="flex items-center gap-2 text-xs text-gray-400 mb-0.5"
                  >
                    <span
                      class="bg-gray-100 px-1.5 py-0.5 rounded text-gray-600"
                    >
                      {project.slide_count} slides
                    </span>
                    {#if project.author}
                      <span class="truncate">by {project.author}</span>
                    {/if}
                  </div>

                  {#if projectAttrs.length}
                    <div class="flex flex-wrap gap-1.5 justify-end">
                      {#each projectAttrs as attr}
                        <div
                          class="inline-flex items-center text-[11px] leading-3 border border-blue-200 rounded overflow-hidden"
                        >
                          <span
                            class="bg-blue-50 px-2 py-1 text-blue-600 font-medium border-r border-blue-200"
                          >
                            {attr.label}
                          </span>
                          <span
                            class="bg-white px-2 py-1 text-blue-900 font-medium"
                          >
                            {attr.value}
                          </span>
                        </div>
                      {/each}
                    </div>
                  {/if}
                </div>
              </button>
            {/each}
          </div>
        {/if}
      </div>
    </div>

    <!-- Right Panel: Preview -->
    <div class="flex-1 bg-gray-50 flex flex-col overflow-hidden relative">
      {#if !selectedProjectId}
        <div
          class="flex-1 flex flex-col items-center justify-center text-gray-400"
        >
          <svg
            class="w-16 h-16 mb-4 opacity-20"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fill-rule="evenodd"
              d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z"
              clip-rule="evenodd"
            />
          </svg>
          <p class="text-lg font-medium">Select a project to preview</p>
        </div>
      {:else if loadingDetails}
        <div class="flex-1 flex items-center justify-center text-gray-500">
          <div
            class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mb-2"
          ></div>
        </div>
      {:else if selectedProjectDetails}
        <!-- Preview Header -->
        <div
          class="bg-white border-b border-gray-200 px-6 py-4 flex justify-between items-center shadow-sm z-10"
        >
          <div>
            <h2 class="text-xl font-bold text-gray-800">
              {selectedProjectDetails.name}
            </h2>
            <p class="text-sm text-gray-500">
              {selectedProjectDetails.slide_count} slides • Last modified {new Date(
                selectedProjectDetails.created_at,
              ).toLocaleDateString()}
            </p>

            {#if projectAttributes(selectedProjectDetails).length}
              <div class="flex flex-wrap gap-1.5 mt-2">
                {#each projectAttributes(selectedProjectDetails) as attr}
                  <div
                    class="inline-flex items-center text-[11px] leading-3 border border-blue-200 rounded overflow-hidden"
                  >
                    <span
                      class="bg-blue-50 px-2 py-1 text-blue-600 font-medium border-r border-blue-200"
                    >
                      {attr.label}
                    </span>
                    <span class="bg-white px-2 py-1 text-blue-900 font-medium">
                      {attr.value}
                    </span>
                  </div>
                {/each}
              </div>
            {/if}
          </div>
          <a
            href={`/viewer/${selectedProjectId}`}
            class="bg-blue-600 text-white px-3 py-1.5 rounded-md hover:bg-blue-700 transition shadow-sm text-sm font-medium flex items-center gap-2"
          >
            <span>Open Viewer</span>
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
                d="M14 5l7 7m0 0l-7 7m7-7H3"
              />
            </svg>
          </a>
          <button
            class="bg-green-600 text-white px-3 py-1.5 rounded-md hover:bg-green-700 transition shadow-sm text-sm font-medium flex items-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed"
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
              <svg
                class="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  class="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  stroke-width="4"
                ></circle>
                <path
                  class="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                ></path>
              </svg>
              <span>Generating...</span>
            {:else}
              <span>Download PPT</span>
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
                  d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                />
              </svg>
            {/if}
          </button>
        </div>

        <!-- Slides Grid -->
        <div class="flex-1 overflow-y-auto p-8">
          <div class="grid grid-cols-1 md:grid-cols-1 xl:grid-cols-1 gap-6">
            {#each selectedProjectDetails.slides as slide}
              <div class="group">
                <div
                  class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden group-hover:shadow-md"
                >
                  <div
                    class="relative"
                    bind:clientWidth={thumbnailWidth}
                    style={`height: ${thumbnailHeight}px;`}
                  >
                    <!-- Thumbnail Renderer -->
                    <div
                      class="absolute top-0 left-0 origin-top-left pointer-events-none"
                      style={`width: ${baseSlideWidth}px;
                    height: ${baseSlideHeight}px;
                    transform: scale(${thumbnailScale});`}
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

                    <!-- Overlay -->
                    <a
                      href={`/viewer/${selectedProjectId}?slide=${slide.slide_index}`}
                      class="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-5 transition flex items-center justify-center"
                    >
                    </a>
                  </div>
                </div>

                <p class="text-center text-sm text-gray-500 mt-2 font-medium">
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
