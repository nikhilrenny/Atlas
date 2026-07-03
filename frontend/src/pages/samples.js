import SearchResultsSample from "./SearchResultsSample";
import FontPreview from "./FontPreview";

// Registry of hardcoded dev/demo pages, reachable from the real command bar
// via the £ prefix (e.g. "£kaizen"). Add new sample pages here as they're built.
export const SAMPLE_PAGES = {
  kaizen: SearchResultsSample,
  fonts: FontPreview, // kept as a souvenir of the wordmark font pick (Cinzel won)
};
