import { ref } from "vue";

// Clicks on these keep doing what they do instead of opening the card.
const INTERACTIVE =
  "a, button, input, select, textarea, summary, label, [role=button], .dropdown-menu";

/**
 * A result card in Explore opens its details on a click anywhere but its
 * links and controls (or a text selection), as the Indicators index opens a
 * row.
 */
export function useCardExpand() {
  const expanded = ref(false);

  function onCardClick(event) {
    if (event.target.closest(INTERACTIVE)) return;
    if (window.getSelection()?.toString()) return;
    expanded.value = !expanded.value;
  }

  return { expanded, onCardClick };
}
