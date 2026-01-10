// Workflow node type constants

export const NODE_TYPE_NAMES: Record<string, string> = {
    Phenomenon: "발생 현상",
    Selector: "원인 도출",
    Sequence: "원인 후보 분석",
    Condition: "분기",
    Action: "액션",
};

export const NODE_TYPE_COLORS: Record<
    string,
    { bg: string; border: string; text: string; darkBg: string; hex: string }
> = {
    Phenomenon: {
        bg: "bg-red-100",
        border: "border-red-400",
        text: "text-red-700",
        darkBg: "bg-red-500",
        hex: "#ef4444",
    },
    Selector: {
        bg: "bg-purple-100",
        border: "border-purple-400",
        text: "text-purple-700",
        darkBg: "bg-purple-500",
        hex: "#a855f7",
    },
    Sequence: {
        bg: "bg-blue-100",
        border: "border-blue-400",
        text: "text-blue-700",
        darkBg: "bg-blue-500",
        hex: "#3b82f6",
    },
    Condition: {
        bg: "bg-yellow-100",
        border: "border-yellow-400",
        text: "text-yellow-700",
        darkBg: "bg-yellow-500",
        hex: "#eab308",
    },
    Action: {
        bg: "bg-green-100",
        border: "border-green-400",
        text: "text-green-700",
        darkBg: "bg-green-500",
        hex: "#22c55e",
    },
};

// Node dimensions
export const NODE_WIDTH = 180;
export const NODE_HEIGHT = 80;
export const PHENOMENON_MIN_HEIGHT = 100;
export const PHENOMENON_MAX_HEIGHT = 300;

// Layout spacing
export const H_SPACING = 40;
export const V_SPACING = 80;

// History
export const MAX_HISTORY = 50;

// Node types that can have children
export const CONTAINER_NODE_TYPES = ["Phenomenon", "Selector", "Sequence"];

// Check if a node type can have children
export function canHaveChildren(nodeType: string): boolean {
    return CONTAINER_NODE_TYPES.includes(nodeType);
}
