<script>
    export let shape;
    export let scale = 1;
    export let projectId = "";
    export let highlight = false;

    // Helper to convert PPT color to CSS
    function getCssColor(rgb) {
        if (!rgb) return "transparent";
        return `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`;
    }

    // Helper to get font style
    function getTextStyle(style) {
        if (!style) return "";
        const color = getCssColor(style.color_rgb || [0, 0, 0]);
        const size = (style.font_size || 18) * scale;
        const bold = style.bold ? "bold" : "normal";
        const italic = style.italic ? "italic" : "normal";
        const underline = style.underline ? "underline" : "none";

        return `
      color: ${color};
      font-size: ${size}px;
      font-weight: ${bold};
      font-style: ${italic};
      text-decoration: ${underline};
      font-family: ${style.font_name || "sans-serif"};
    `;
    }

    // Helper for fill
    function getFillStyle(fill) {
        if (!fill || fill.visible === false) return "";
        const color = fill.fore_color_rgb || fill.back_color_rgb;
        if (!color) return "";
        return `background-color: ${getCssColor(color)};`;
    }

    // Helper for border
    function getBorderStyle(line) {
        if (!line || line.visible === false) return "";
        const width = (line.weight || 1) * scale;
        const color = getCssColor(line.color_rgb || [0, 0, 0]);
        // Dash style mapping could be added here
        return `border: ${width}px solid ${color};`;
    }

    // Helper for clip-path based on shape type
    function isCloud(shape) {
        if (shape.auto_shape_type === 203) return true;
        const name = (shape.name || "").toLowerCase();
        return name.includes("cloud") || name.includes("구름");
    }

    // getClipPath에서 cloud 부분 제거 (SVG로 대체)
    function getClipPath(shape) {
        if (!shape) return "";

        // Use auto_shape_type if available, otherwise fallback to name heuristic or type_code
        let type = shape.auto_shape_type;
        if (!type) {
            // Simple name heuristic for frontend display if auto_shape_type is missing
            const name = (shape.name || "").toLowerCase();
            if (name.includes("trapezoid") || name.includes("사다리꼴"))
                type = 3;
            else if (name.includes("arrow") || name.includes("화살표")) {
                if (name.includes("right") || name.includes("오른쪽"))
                    type = 33;
                else if (name.includes("left") || name.includes("왼쪽"))
                    type = 34;
                else if (name.includes("up") || name.includes("위쪽"))
                    type = 35;
                else if (name.includes("down") || name.includes("아래쪽"))
                    type = 36;
                else type = 33;
            }
        }

        // MSO Shape Types
        // Trapezoid = 3
        if (type === 3) {
            return "clip-path: polygon(20% 0%, 80% 0%, 100% 100%, 0% 100%);";
        }
        // Right Arrow = 33
        if (type === 33) {
            return "clip-path: polygon(0% 20%, 60% 20%, 60% 0%, 100% 50%, 60% 100%, 60% 80%, 0% 80%);";
        }
        // Left Arrow = 34
        if (type === 34) {
            return "clip-path: polygon(40% 0%, 40% 20%, 100% 20%, 100% 80%, 40% 80%, 40% 100%, 0% 50%);";
        }
        // Up Arrow = 35
        if (type === 35) {
            return "clip-path: polygon(50% 0%, 0% 40%, 20% 40%, 20% 100%, 80% 100%, 80% 40%, 100% 40%);";
        }
        // Down Arrow = 36
        if (type === 36) {
            return "clip-path: polygon(20% 0%, 80% 0%, 80% 60%, 100% 60%, 50% 100%, 0% 60%, 20% 60%);";
        }
        // Cloud는 여기서 처리 안 함 (SVG로 대체)
        return "";
    }

    $: style = `
    position: absolute;
    left: ${shape.left * scale}px;
    top: ${shape.top * scale}px;
    width: ${shape.width * scale}px;
    height: ${shape.height * scale}px;
    transform: rotate(${shape.rotation || 0}deg);
    ${getFillStyle(shape.fill)}
    ${getBorderStyle(shape.line)}
    ${getClipPath(shape)}
    z-index: ${shape.z_order_position || 1};
    overflow: hidden;
    ${highlight ? "box-shadow: 0 0 0 4px #ef4444; z-index: 9999;" : ""} 
  `;

    // Cloud용 style (clip-path 제외)
    $: cloudStyle = `
        position: absolute;
        left: ${shape.left * scale}px;
        top: ${shape.top * scale}px;
        width: ${shape.width * scale}px;
        height: ${shape.height * scale}px;
        transform: rotate(${shape.rotation || 0}deg);
        z-index: ${shape.z_order_position || 1};
        overflow: visible;
        ${highlight ? "filter: drop-shadow(0 0 4px #ef4444);" : ""}
    `;

    $: fillColor = shape.fill?.fore_color_rgb ||
        shape.fill?.back_color_rgb || [255, 255, 255];
    $: lineColor = shape.line?.color_rgb || [0, 0, 0];
    $: lineWidth = (shape.line?.weight || 1) * scale;

    const IMAGE_BASE = "http://localhost:8000";
</script>

{#if isCloud(shape)}
    <!-- Cloud Shape - SVG 렌더링 -->
    <div
        style={cloudStyle}
        class="absolute select-none group"
        data-shape-id={shape.shape_index}
    >
        <svg
            viewBox="0 0 100 60"
            width="100%"
            height="100%"
            preserveAspectRatio="none"
        >
            <path
                d="M25,50 
                   a15,15 0 0,1 0,-25 
                   a18,18 0 0,1 30,-10 
                   a15,15 0 0,1 25,5 
                   a12,12 0 0,1 0,20 
                   a10,10 0 0,1 -10,10 
                   z"
                fill={getCssColor(fillColor)}
                stroke={shape.line?.visible !== false
                    ? getCssColor(lineColor)
                    : "none"}
                stroke-width={lineWidth}
            />
        </svg>

        <!-- Text overlay for cloud -->
        {#if shape.text && !shape.table}
            <div
                class="absolute inset-0 flex items-center justify-center p-2 whitespace-pre-wrap break-words pointer-events-none text-center"
                style={getTextStyle(shape.text_style)}
            >
                {shape.text}
            </div>
        {/if}

        <div
            class="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"
            style="filter: drop-shadow(0 0 2px #3b82f6);"
        ></div>
    </div>
{:else}
    <!-- 기존 Shape 렌더링 -->
    <div
        {style}
        class="absolute select-none group"
        data-shape-id={shape.shape_index}
    >
        <!-- Image -->
        {#if shape.image_file}
            <img
                src={`${IMAGE_BASE}/results/${projectId}/${shape.image_file}`}
                alt={shape.name}
                class="w-full h-full object-contain pointer-events-none"
            />
        {/if}

        {#if shape.text && !shape.table}
            <div
                class="w-full h-full p-1 whitespace-pre-wrap break-words pointer-events-none"
                style={getTextStyle(shape.text_style)}
            >
                {shape.text}
            </div>
        {/if}

        <!-- Table -->
        {#if shape.table}
            <div
                class="w-full h-full grid pointer-events-none"
                style={`
      grid-template-columns: repeat(${shape.table.cols}, 1fr);
      grid-template-rows: repeat(${shape.table.rows}, 1fr);
    `}
            >
                {#each shape.table.cells as cell}
                    <div
                        class="border border-gray-400 p-1 overflow-hidden"
                        style={`
          ${getFillStyle(cell.fill)}
          ${getTextStyle(cell.text_style)}
        `}
                    >
                        {cell.text}
                    </div>
                {/each}
            </div>
        {/if}

        <!-- Recursive Children (Groups) -->
        {#if shape.children && shape.children.length > 0}
            {#each shape.children as child}
                <!-- 
                    IMPORTANT: Children in JSON have absolute coordinates (slide-relative).
                    But here they are rendered inside the parent div, which is already positioned.
                    So we must adjust their coordinates to be relative to the parent.
                -->
                <svelte:self
                    shape={{
                        ...child,
                        left: child.left - shape.left,
                        top: child.top - shape.top,
                    }}
                    {scale}
                    {projectId}
                    {highlight}
                />
            {/each}
        {/if}

        <div
            class="absolute inset-0 border-2 border-blue-500 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"
        ></div>
    </div>
{/if}
