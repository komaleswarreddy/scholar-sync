

\#\#\# \*\*File 5: \`5\_Design\_Specifications.md\` (Expanded)\*\*

\`\`\`markdown  
\# Design Specifications & Design Tokens  
\*\*Theme:\*\* "Notebook Dark" (High Contrast, Focus-Driven)

\#\# 1\. Design Tokens (Tailwind Config)

\#\#\# 1.1. Colors (Dark Mode Palette)  
These specific hex codes replicate the NotebookLM aesthetic.

\* \*\*Backgrounds\*\*  
    \* \`bg-background\`: \`\#1E1E1E\` (Main Canvas)  
    \* \`bg-surface\`: \`\#2D2D2D\` (Cards, Sidebars, Inputs)  
    \* \`bg-surface-hover\`: \`\#383838\` (Interactive Elements)  
    \* \`bg-modal\`: \`\#252525\` (Dialogs/Popovers)

\* \*\*Borders\*\*  
    \* \`border-default\`: \`\#444444\` (Subtle separation)  
    \* \`border-active\`: \`\#666666\` (Focus states)

\* \*\*Typography\*\*  
    \* \`text-primary\`: \`\#FFFFFF\` (100% Opacity)  
    \* \`text-secondary\`: \`\#A1A1A1\` (63% Opacity \- timestamps, citations)  
    \* \`text-tertiary\`: \`\#757575\` (Placeholders)

\* \*\*Accents (Functional)\*\*  
    \* \`accent-blue\`: \`\#A8C7FA\` (Links, Primary Actions)  
    \* \`accent-green\`: \`\#C4EED0\` (Success, source added)  
    \* \`citation-badge\`: \`\#444746\` (Background for \[1\])

\#\#\# 1.2. Typography (Inter / Sans)  
\* \*\*Scale:\*\*  
    \* \`text-xs\`: 12px (Line height 16px) \- \*Metadata, Citations\*  
    \* \`text-sm\`: 14px (Line height 20px) \- \*Sidebar items, Input text\*  
    \* \`text-base\`: 16px (Line height 24px) \- \*Chat body, General reading\*  
    \* \`text-lg\`: 18px (Line height 28px) \- \*Card Titles\*  
    \* \`text-xl\`: 20px (Line height 28px) \- \*Section Headers\*  
    \* \`text-2xl\`: 24px (Line height 32px) \- \*Welcome Message\*

\#\#\# 1.3. Spacing & Radius  
\* \*\*Radius:\*\*  
    \* \`rounded-lg\`: 8px (Small buttons)  
    \* \`rounded-xl\`: 12px (Cards, Modals)  
    \* \`rounded-2xl\`: 16px (Chat bubbles)  
    \* \`rounded-full\`: 9999px (Input pills, Icon buttons)  
\* \*\*Gap/Padding:\*\*  
    \* \`p-4\` (16px): Standard container padding.  
    \* \`gap-3\` (12px): Space between grid items.

\---

\#\# 2\. Component Specifications

\#\#\# 2.1. "Studio" Card (Grid Item)  
\* \*\*Dimensions:\*\* Fixed height \`88px\` (Web), \`80px\` (Mobile).  
\* \*\*Styling:\*\*  
    \* Default: \`bg-\[\#2D2D2D\] border border-transparent rounded-xl p-3\`  
    \* Hover: \`bg-\[\#383838\] border-\[\#444444\] transition-all duration-200\`  
    \* Active/Press: \`scale-98\` (Subtle shrink).  
\* \*\*Content Layout:\*\*  
    \* Icon: Top-left, size \`20px\`, color \`text-accent-blue\`.  
    \* Text: Bottom-left, \`text-sm font-medium text-white\`.  
    \* Edit Button (Icon): Top-right, \`opacity-0 group-hover:opacity-100\`.

\#\#\# 2.2. Chat Message (Assistant)  
\* \*\*Container:\*\* No background bubble (blends with canvas).  
\* \*\*Text:\*\* \`text-base text-gray-100 leading-relaxed\`.  
\* \*\*Citations:\*\*  
    \* Display as \`\[1\]\` superscript-aligned.  
    \* Style: \`bg-\[\#444746\] text-\[\#E3E3E3\] px-1.5 rounded text-xs cursor-pointer\`.  
    \* Interaction: Hover shows a "Tooltip" with source preview.

\#\#\# 2.3. Source Item (Left Sidebar)  
\* \*\*Layout:\*\* Flex row, \`items-center gap-3\`.  
\* \*\*State (Selected):\*\* Checkbox checked, text white.  
\* \*\*State (Unselected):\*\* Checkbox unchecked, text gray.  
\* \*\*Truncation:\*\* Title must truncate after 2 lines with ellipsis (\`line-clamp-2\`).  
\* \*\*Icon:\*\* Shows PDF icon (Red) or Web icon (Blue) based on type.

\#\#\# 2.4. Mobile Navigation (React Native)  
\* \*\*Drawer (Sources):\*\*  
    \* Implementation: \`react-native-drawer-layout\`.  
    \* Behavior: Slide from left. Overlay background with \`opacity-50\` black.  
\* \*\*Floating Action Button (Studio):\*\*  
    \* Position: Bottom Right (above input).  
    \* Style: \`w-12 h-12 bg-accent-blue rounded-full shadow-lg\`.  
    \* Icon: Sparkles/Magic Wand.

\---

\#\# 3\. Interaction & Animation  
\* \*\*Loading State (Chat):\*\*  
    \* Do not use a spinner.  
    \* Use a "Shimmer" skeleton on the text lines.  
    \* Text should stream in character-by-character (Typewriter effect).  
\* \*\*Studio Generation:\*\*  
    \* Show a progress bar toast: "Generating Quiz... (Processing 4 Sources)".  
\* \*\*Transitions:\*\*  
    \* All hover effects: \`duration-200 ease-in-out\`.  
    \* Modals: \`scale-95 opacity-0\` \-\> \`scale-100 opacity-100\`.

