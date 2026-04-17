## SVG Vector Creation Workshop
Generate and iterate SVG graphics through dialogue — logos, icons, illustrations, infographics.

Why can't this be accomplished by a simple function (skill)? A skill only allows a model to generate SVG code, and you must then copy-paste this code into a browser to view the result. In contrast, a vertical Agent provides:

- A real-time SVG rendering panel on the left, where each code modification is immediately visible
- The "shape_library" tool — a preconfigured library of over 200 basic shapes and patterns that the model can combine rather than drawing from scratch
- The layer manager ("layer_manager") — layer management enabling individual layer modification via dialogue
- The "export_variants" tool — simultaneous export in multiple formats and sizes (favicon, app icon, social media profile image)
- Persistent design version history — ability to revert to any previous iteration

Added value: Independent developers or social media content creators often need simple vector graphics without wanting to open Figma or Illustrator. A simple instruction such as "Create me a minimalist coffee cup icon with a 2px stroke width and warm tones" is sufficient to obtain the image and perform iterations.

## Web Novel/World-Building Workshop
Maintain a complete world-building database for novels/stories to ensure consistency during writing.

Why isn't this something a skill can do?

Persistent world-building database: character profiles, locations, event timelines, faction relationships, setting rules
character_graph — visual character relationship graph (rendered with Streamlit)
timeline_view — story timeline visualization, annotating which characters are involved in each event
consistency_check — automatically check for contradictions with existing settings after writing a chapter
write_chapter — generate chapter drafts constrained by the existing world-building
what_if — "What happens to the subsequent plot if character A dies in Chapter 3?"
Value: The core pain point for long-form creators is "setting collapse." Forgetting a detail from Chapter 3 when writing Chapter 50. This is not something a skill can solve — it requires a true database to maintain world state.

## Algorithm Visualization Lab
// Can also consider physics and mathematics visualization teaching materials preparation
Describe algorithms through dialogue; the Agent generates code and renders real-time animations of algorithm execution.

Why isn't this something a skill can do?

visualize_sort / visualize_tree / visualize_graph — pre-configured visualizers for classic data structures
Step-by-step execution mode — pause, step forward, step backward, and view state changes at each step
Side-by-side code and visualization — showing which line is currently executing and what the data structure looks like at that moment
compare_algorithms — run two algorithms side-by-side on the same dataset to compare performance
Automatically generate complexity analysis reports
Value: The best way to learn algorithms is to "see them in motion." This direction has tremendous value for CS students.

## SVG Vector Creation Workshop
Generate and iterate SVG graphics through dialogue — logos, icons, illustrations, infographics.

Why isn't this something a skill can do? A skill only allows a model to generate SVG code, and you must then copy-paste this code into a browser to view the result. In contrast, a vertical Agent provides:

- A real-time SVG rendering panel on the left, where each code modification is immediately visible
- The "shape_library" tool — a preconfigured library of over 200 basic shapes and patterns that the model can combine rather than drawing from scratch
- The layer manager ("layer_manager") — layer management enabling individual layer modification via dialogue
- The "export_variants" tool — simultaneous export in multiple formats and sizes (favicon, app icon, social media profile image)
- Persistent design version history — ability to revert to any previous iteration

Value: Independent developers or social media content creators often need simple vector graphics without wanting to open Figma or Illustrator. A simple instruction such as "Create me a minimalist coffee cup icon with a 2px stroke width and warm tones" is sufficient to obtain the image and perform iterations.

## Playwright Web Automation Console
Use an Agent to drive a real browser for web automation, testing, and data collection.

After Agent wrapping:

"Take screenshots of these three competitors' pricing pages every morning at 9 AM"
"Log into this admin panel and export last month's sales report"
"Test how this webpage displays at different screen resolutions"
Domain-specific tools:

open_page — open a URL and return a screenshot
interact — click/input/scroll operations
screenshot — full-page or element-specific screenshots
extract_data — extract page data into structured format
record_workflow — record operation sequences for replay
Python library: playwright (Microsoft's offering, more modern than Selenium)

Streamlit preview: Real-time browser screenshot display + operation playback