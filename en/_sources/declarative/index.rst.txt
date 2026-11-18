Declarative UI Guide
====================

The **declarative track** (``fluxent.decl``) builds native Windows applications
around ``flux_run`` and the element builders in ``<xtk/xtk.h>``. Your code keeps
application state in a C ``struct``, processes integer-tagged messages in
``update()``, and describes the current interface in ``view()`` while the
reconciler updates retained controls incrementally.

Read the chapters in order when starting from scratch, or jump directly to the
control family your screen needs:

1. :doc:`mvu` — Master the Elm Model–View–Update cycle, dissect the
   ``fluxent.decl`` template, organize large message tables, register control
   modules, and manage per-frame scratch strings.
2. :doc:`layout` — Arrange interfaces with Flex stacks, cards, modifiers,
   controlled ``ScrollViewer`` viewports, inherited typography, and async WIC
   images.
3. :doc:`inputs` — Handle buttons, toggles, sliders, localized ``NumberBox``,
   controlled ``TextBox`` / ``AutoSuggestBox`` edits, and date, time, calendar,
   and color pickers.
4. :doc:`collections` — Render 100,000-row virtualized ``ListView`` and
   ``GridView`` collections, sticky group headers, sortable column headers,
   ``TreeView`` hierarchies, keys, and memoized subtrees.
5. :doc:`navigation` — Structure multi-page shells with ``NavigationView``,
   ``TabView``, ``SplitView``, custom ``TitleBar``, ``CommandBar`` overflow
   menus, modal ``ContentDialog``, ``TeachingTip``, and status bars.
6. :doc:`host` — Access ``FluxApp *`` for native file dialogs, OLE
   drag-and-drop, clipboard data, live theme/backdrop switching, and background
   worker threads.

.. toctree::
   :maxdepth: 2

   mvu
   layout
   inputs
   collections
   navigation
   host
