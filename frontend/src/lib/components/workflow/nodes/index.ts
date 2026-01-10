// Node components index
export { default as BaseNode } from "./BaseNode.svelte";
export { default as PhenomenonNode } from "./PhenomenonNode.svelte";
export { default as SelectorNode } from "./SelectorNode.svelte";
export { default as SequenceNode } from "./SequenceNode.svelte";
export { default as ConditionNode } from "./ConditionNode.svelte";
export { default as ActionNode } from "./ActionNode.svelte";

import PhenomenonNode from "./PhenomenonNode.svelte";
import SelectorNode from "./SelectorNode.svelte";
import SequenceNode from "./SequenceNode.svelte";
import ConditionNode from "./ConditionNode.svelte";
import ActionNode from "./ActionNode.svelte";

// Node types mapping for SvelteFlow
export const nodeTypes = {
    Phenomenon: PhenomenonNode,
    Selector: SelectorNode,
    Sequence: SequenceNode,
    Condition: ConditionNode,
    Action: ActionNode,
};
