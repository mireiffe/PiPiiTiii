<script>
    import { slide } from "svelte/transition";
    import { createEventDispatcher } from "svelte";
    import AccordionHeader from "./AccordionHeader.svelte";
    import ShapeList from "./ShapeList.svelte";
    import DescriptionEditor from "./DescriptionEditor.svelte";

    export let isExpanded = false;
    export let allShapes = [];
    export let selectedShapeId = null;
    export let editingDescription = "";

    const dispatch = createEventDispatcher();

    // Derived shapes
    $: imageShapes = allShapes.filter((s) => s.type_name === "Picture");
    $: textShapes = allShapes.filter(
        (s) => s.type_name === "TextBox" || s.type_name === "Title",
    );
    $: otherShapes = allShapes.filter(
        (s) =>
            s.type_name !== "Picture" &&
            s.type_name !== "TextBox" &&
            s.type_name !== "Title",
    );

    $: selectedShape = allShapes.find((s) => s.shape_index === selectedShapeId);
</script>

<div
    class="border-b border-gray-200 {isExpanded
        ? 'flex-1 flex flex-col min-h-0'
        : ''}"
>
    <AccordionHeader
        icon="📦"
        title="객체 목록"
        {isExpanded}
        badge={allShapes.length}
        on:click={() => dispatch("toggleExpand")}
    />

    {#if isExpanded}
        <div
            transition:slide={{ duration: 200, axis: "y" }}
            class="overflow-y-auto flex-1 p-0 min-h-0 bg-gray-50/50 border-t border-gray-100"
        >
            {#if allShapes.length === 0}
                <div
                    class="p-8 text-gray-400 text-sm text-center flex flex-col items-center gap-2"
                >
                    <span class="text-2xl">📭</span>
                    <span>발견된 객체가 없습니다</span>
                </div>
            {:else}
                <div class="p-2 space-y-4">
                    <!-- Image Shapes -->
                    <ShapeList
                        shapes={imageShapes}
                        {selectedShapeId}
                        title="이미지 assets"
                        icon="status"
                        colorScheme="orange"
                        borderColor="orange-200"
                        on:select={(e) =>
                            dispatch("selectShape", { shapeIndex: e.detail.shapeIndex })}
                    />

                    <!-- Text Shapes -->
                    <ShapeList
                        shapes={textShapes}
                        {selectedShapeId}
                        title="텍스트 객체"
                        icon="T"
                        colorScheme="indigo"
                        borderColor="indigo-200"
                        on:select={(e) =>
                            dispatch("selectShape", { shapeIndex: e.detail.shapeIndex })}
                    />

                    <!-- Other Shapes -->
                    <ShapeList
                        shapes={otherShapes}
                        {selectedShapeId}
                        title="기타 객체"
                        icon="🔹"
                        colorScheme="blue"
                        borderColor="gray-200"
                        on:select={(e) =>
                            dispatch("selectShape", { shapeIndex: e.detail.shapeIndex })}
                    />
                </div>
            {/if}
        </div>

        <!-- Description Editor -->
        <DescriptionEditor
            {selectedShape}
            {editingDescription}
            on:save={() => dispatch("handleSaveDescription")}
        />
    {/if}
</div>
