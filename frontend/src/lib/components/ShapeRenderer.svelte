<script>
    export let shape;
    // scale prop removed, we rely on CSS transform on parent
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
        // PPT font size is in points (pt). 1pt = 1.333px (96/72)
        const sizePt = style.font_size || 18;
        const sizePx = sizePt * (96 / 72);
        const bold = style.bold ? "bold" : "normal";
        const italic = style.italic ? "italic" : "normal";
        const underline = style.underline ? "underline" : "none";

        return `
      color: ${color};
      font-size: ${sizePx}px;
      font-weight: ${bold};
      font-style: ${italic};
      text-decoration: ${underline};
      font-family: ${style.font_name || "sans-serif"};
    `;
    }

    // Helper for fill
    function getFillStyle(fill, forceTransparent = false) {
        if (!fill || fill.visible === false) {
            // 테이블 셀 등에서 명시적으로 transparent 필요한 경우
            return forceTransparent ? "background-color: transparent;" : "";
        }
        const color = fill.fore_color_rgb || fill.back_color_rgb;
        if (!color)
            return forceTransparent ? "background-color: transparent;" : "";
        return `background-color: ${getCssColor(color)};`;
    }

    // Helper for border
    function getBorderStyle(line) {
        if (!line || line.visible === false) return "";
        // PPT weight is in points
        const widthPt = line.weight || 1;
        const widthPx = widthPt * (96 / 72);
        const color = getCssColor(line.color_rgb || [0, 0, 0]);
        // Dash style mapping could be added here
        return `border: ${widthPx}px solid ${color};`;
    }

    // Helper for cell individual borders
    function getCellBorderStyle(borders) {
        if (!borders) return "border: 1px solid #9ca3af;"; // Fallback to gray-400 if no border info

        let style = "";
        const sides = ["top", "bottom", "left", "right"];

        sides.forEach((side) => {
            const border = borders[side];
            if (border) {
                if (border.visible === false) {
                    style += `border-${side}: 0;`;
                } else {
                    const widthPt = border.weight || 1;
                    const widthPx = widthPt * (96 / 72);
                    const color = getCssColor(border.color_rgb || [0, 0, 0]);
                    // Default to solid for now, could map dash styles if needed
                    style += `border-${side}: ${widthPx}px solid ${color};`;
                }
            } else {
                // If specific side info is missing but borders object exists,
                // we might want a default or just no border.
                // Let's assume no border if not specified in the detailed object.
                style += `border-${side}: 0;`;
            }
        });

        return style;
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

    // 테이블 행/열 크기 계산 헬퍼 함수들 (비율 기반, scale 미적용)
    function getGridTemplateRows(table) {
        if (!table || !table.cells) return `repeat(${table.rows}, 1fr)`;
        const heights = [];
        for (let r = 0; r < table.rows; r++) {
            const cellIndex = r * table.cols;
            const cell = table.cells[cellIndex];
            // height 값을 fr 단위의 비율로 사용
            heights.push(cell?.height || 1);
        }
        return heights.map((h) => `${h}fr`).join(" ");
    }

    function getGridTemplateColumns(table) {
        if (!table || !table.cells) return `repeat(${table.cols}, 1fr)`;
        const widths = [];
        for (let c = 0; c < table.cols; c++) {
            const cell = table.cells[c];
            // width 값을 fr 단위의 비율로 사용
            widths.push(cell?.width || 1);
        }
        return widths.map((w) => `${w}fr`).join(" ");
    }

    // 셀 배경색 스타일
    function getCellFillStyle(cell) {
        // cell 자체가 visible=false면 투명 (셀 자체를 숨김)
        if (cell.visible === false) {
            return "background-color: transparent;";
        }

        // fill이 없으면 흰색 기본값
        if (!cell.fill) {
            return "background-color: white;";
        }

        // fill.visible 여부와 관계없이 색상 정보가 있으면 사용
        // (PPT에서 fill.visible=false는 "채우기 효과 없음"이지 투명이 아님)
        const color = cell.fill.fore_color_rgb || cell.fill.back_color_rgb;
        if (color) {
            return `background-color: ${getCssColor(color)};`;
        }

        // 색상 정보도 없으면 흰색 기본값
        return "background-color: white;";
    }

    $: style = `
    position: absolute;
    left: ${shape.left}px;
    top: ${shape.top}px;
    width: ${shape.width}px;
    height: ${shape.height}px;
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
        left: ${shape.left}px;
        top: ${shape.top}px;
        width: ${shape.width}px;
        height: ${shape.height}px;
        transform: rotate(${shape.rotation || 0}deg);
        z-index: ${shape.z_order_position || 1};
        overflow: visible;
        ${highlight ? "filter: drop-shadow(0 0 4px #ef4444);" : ""}
    `;

    $: fillColor = shape.fill?.fore_color_rgb ||
        shape.fill?.back_color_rgb || [255, 255, 255];
    $: lineColor = shape.line?.color_rgb || [0, 0, 0];
    $: lineWidth = (shape.line?.weight || 1) * (96 / 72);

    import { IMAGE_BASE_URL } from "$lib/api/client";
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
{:else if shape.is_connector}
    <!-- Connector Rendering -->
    <div
        {style}
        class="absolute select-none group pointer-events-none"
        data-shape-id={shape.shape_index}
    >
        <svg
            width="100%"
            height="100%"
            viewBox={`0 0 ${shape.width} ${shape.height}`}
            style="overflow: visible;"
        >
            {#if shape.auto_shape_type === -2 || shape.type_code === 3}
                <!-- Elbow Connector Logic -->
                {@const hFlip = shape.horizontal_flip}
                {@const vFlip = shape.vertical_flip}
                {@const w = shape.width}
                {@const h = shape.height}

                <!-- 
                        Determine Start (x1, y1) and End (x2, y2) based on flips.
                        Bounding box is (0,0) to (w,h).
                     -->
                {@const x1 = hFlip ? w : 0}
                {@const y1 = vFlip ? h : 0}
                {@const x2 = hFlip ? 0 : w}
                {@const y2 = vFlip ? 0 : h}

                <!-- 
                        Calculate Elbow Point.
                        Default L-shape: Move horizontally from Start to intersection, then vertically to End.
                        Or vertically first? 
                        PowerPoint elbow connectors usually try to exit the shape perpendicularly.
                        Without exact path, we can try a simple 50% split or just a direct L.
                        
                        Let's try a simple L-shape first: (x2, y1) corner.
                        Path: (x1, y1) -> (x2, y1) -> (x2, y2)
                        
                        Refinement with adjustments:
                        Adjustment[0] is often the position of the elbow relative to width/height.
                        If available, we can use it.
                     -->
                {@const adj =
                    shape.adjustments && shape.adjustments.length > 0
                        ? shape.adjustments[0]
                        : -1}

                <!-- 
                        If adj is present, it might define the split. 
                        Let's assume it's a ratio along the primary axis.
                     -->
                {@const elbowX =
                    adj !== -1
                        ? hFlip
                            ? w - w * Math.abs(adj)
                            : w * Math.abs(adj)
                        : x2}

                <!-- 
                        Construct Path Data.
                        Simple L for now: Start -> Corner -> End
                     -->
                <path
                    d={`M ${x1} ${y1} L ${x2} ${y1} L ${x2} ${y2}`}
                    fill="none"
                    stroke={getCssColor(lineColor)}
                    stroke-width={lineWidth}
                />
            {:else}
                <!-- Straight Line or other connector -->
                <line
                    x1={shape.horizontal_flip ? shape.width : 0}
                    y1={shape.vertical_flip ? shape.height : 0}
                    x2={shape.horizontal_flip ? 0 : shape.width}
                    y2={shape.vertical_flip ? 0 : shape.height}
                    stroke={getCssColor(lineColor)}
                    stroke-width={lineWidth}
                />
            {/if}
        </svg>
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
                src={`${IMAGE_BASE_URL}/results/${projectId}/${shape.image_file}`}
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
                        grid-template-columns: ${getGridTemplateColumns(shape.table)};
                        grid-template-rows: ${getGridTemplateRows(shape.table)};
                    `}
            >
                {#each shape.table.cells as cell}
                    <div
                        class="overflow-hidden"
                        style={`
                                ${getCellFillStyle(cell)}
                                ${getTextStyle(cell.text_style)}
                                ${getCellBorderStyle(cell.borders)}
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
