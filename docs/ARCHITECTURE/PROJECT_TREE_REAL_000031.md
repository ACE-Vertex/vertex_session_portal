# VERTEX SESSION PORTAL - PROJECT TREE REAL 000031

## Purpose

Replace the decorative Project Explorer placeholder with a real, read-only filesystem tree for the active Session Portal project.

This patch is deliberately dedicated to the Project Tree. It does not redesign Vera lanes, VRA/Works Dispatch, VCR/VCA, or ChatGPT browser sessions.

## Contract

- Source: real filesystem rooted at the Session Portal process working directory.
- Scope: project root only. Requests that escape the project root are rejected.
- Read-only: the tree does not create, edit, rename, move, or delete project files.
- Directory-first, case-insensitive/numeric sorting.
- Lazy expansion: only expanded directories are enumerated.
- Symbolic links are shown but are not traversed as directories.
- Expansion state and selected path are persisted as local UI state and restored after restart.

## UI / UX

- Real root name and real files/folders are rendered; hard-coded fake rows are removed.
- Chevron toggle for directories.
- Hierarchy guide lines and file/folder/symlink distinction.
- Single click selects without resizing or opening anything.
- Double click on a directory expands/collapses it.
- Double click on a file opens it through the OS default handler.
- Right click provides OPEN, REVEAL IN EXPLORER, COPY PATH, and REFRESH.
- Refresh works at root or selected directory/file parent.
- Keyboard: Enter opens/toggles, ArrowRight expands, ArrowLeft collapses, F5 refreshes.
- Existing PROJECT_REVEAL control now resolves and expands the real tree to the requested path.

## Existing boundaries preserved

- VRA / Works Dispatch remains unchanged.
- Search Vera remains retired from the main UI.
- No ChatGPT DOM scraping is introduced.
- No filesystem mutation path is added.
