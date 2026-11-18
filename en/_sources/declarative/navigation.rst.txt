5. Navigation, Toolbars, & Modal Overlays
=========================================

Real desktop applications combine multi-page navigation shells, document tabs,
command toolbars, and modal confirmation dialogs—all driven declaratively from
``Model`` fields.

Multi-Page App Shell with ``NavigationView``
--------------------------------------------

``xtk_nav`` (register ``&flux_ctrl_nav``) provides a full WinUI
``NavigationView`` with collapsible sidebar pane, headers, separators, footer
items, and optional custom window title bar integration:

.. code-block:: c

   enum {
       PAGE_HOME = 0,
       PAGE_PROJECTS,
       PAGE_SEP_1,
       PAGE_SETTINGS,
       PAGE_COUNT
   };

   static XtkNavItemDesc const kNavItems[PAGE_COUNT] = {
       [PAGE_HOME]     = {.kind = XTK_NAV_ITEM,      .icon = "Home",     .label = "Home"},
       [PAGE_PROJECTS] = {.kind = XTK_NAV_ITEM,      .icon = "Folder",   .label = "Projects"},
       [PAGE_SEP_1]    = {.kind = XTK_NAV_SEPARATOR},
       [PAGE_SETTINGS] = {.kind = XTK_NAV_FOOTER,    .icon = "Settings", .label = "Settings"},
   };

   static XtkEl *active_page(XtkUi *ui, Model const *m) {
       switch (m->page) {
       case PAGE_PROJECTS : return view_projects(ui, m);
       case PAGE_SETTINGS : return view_settings(ui, m);
       default            : return view_home(ui, m);
       }
   }

   static XtkEl *view(XtkUi *ui, void *model) {
       Model const *m = model;
       XtkEl *body = xtk_grow(
           xtk_keyed_u64(
               xtk_scroll(
                   ui, (XtkScrollDesc) {0},
                   xtk_kids(xtk_column(
                       ui, (XtkStackDesc) {.padding = {36, 28, 36, 28}, .gap = 20, .align = XENT_FLEX_ALIGN_STRETCH},
                       xtk_kids(active_page(ui, m))
                   ))
               ),
               (uint64_t) m->page
           ),
           1.0f
       );

       return xtk_grow(
           xtk_nav(
               ui,
               (XtkNavDesc) {
                   .items            = kNavItems,
                   .nitem            = PAGE_COUNT,
                   .sel              = m->page,
                   .window_title_bar = true,
                   .app_title        = "My Xent App",
                   .select           = xtk_msg(MSG_NAV_SELECT),
               },
               xtk_kids(body)
           ),
           1.0f
       );
   }

Wrapping the scrollable page container in ``xtk_keyed_u64(..., m->page)`` gives
each route its own scroll viewport so every page starts cleanly at its own
offset.

``SplitView`` and Custom ``TitleBar``
-------------------------------------

When you want a custom collapsible side drawer or custom window chrome without a
``NavigationView``:

- ``xtk_splitview(ui, desc, pane_el, content_el)`` (``&flux_ctrl_splitview``) —
  Supports ``XTK_SPLITVIEW_INLINE``, ``COMPACT_INLINE``, ``OVERLAY``, and
  ``COMPACT_OVERLAY`` modes on either ``XTK_SPLITVIEW_LEFT`` or ``RIGHT``.
- ``xtk_titlebar(ui, "App Title", desc)`` (``&flux_ctrl_titlebar``) — Setting
  ``.integrate_window = true`` removes the standard Win32 title bar, draws
  themed caption buttons (Minimize / Maximize / Close) with Snap Layouts support,
  marks the bar draggable, and posts ``.on_back`` and ``.on_pane_toggle``
  messages.

Document ``TabView``, ``SelectorBar``, & ``Expander``
-----------------------------------------------------

- **Closable & addable tabs** (``xtk_tabs``, ``&flux_ctrl_tab``): Keep your open
  document list and active index in ``Model``. Build a stack or arena array of
  ``XtkTabDesc`` headers and render the active tab's body as the child:

  .. code-block:: c

     XtkTabDesc headers[16];
     for (int i = 0; i < m->tab_count; i++) {
         headers[i] = (XtkTabDesc) {.icon = "Document", .label = m->tabs[i].title};
     }

     xtk_tabs(
         ui,
         (XtkTabViewDesc) {
             .tabs   = headers,
             .ntab   = m->tab_count,
             .sel    = m->active_tab,
             .select = xtk_msg(MSG_TAB_SELECT), // msg.i = clicked tab index
             .close  = xtk_msg(MSG_TAB_CLOSE),  // msg.i = closed tab index
             .add    = xtk_msg(MSG_TAB_NEW),
         },
         xtk_kids(m->tab_count > 0 ? view_document(ui, &m->tabs[m->active_tab]) : NULL)
     )

- **Pivot & path bars**: ``xtk_selector`` (lightweight horizontal view switcher),
  ``xtk_breadcrumb`` (clickable path hierarchy posting segment index in
  ``msg.i``), ``xtk_expander`` (collapsible disclosure card controlled by
  ``.expanded`` and ``.toggle``), and ``xtk_flip`` / ``xtk_pips`` /
  ``xtk_pager`` for paged media carousels.

``MenuBar`` and ``CommandBar`` (0.3.3)
--------------------------------------

- **Desktop MenuBar** (``xtk_menubar``, ``&flux_ctrl_menubar``): Takes an array
  of ``XtkMenuDesc`` top-level menus (``File``, ``Edit``, ``View``), each
  pointing to an array of ``XtkMenuItemDesc`` items with ``.click`` messages.
- **Fluent CommandBar** (``xtk_commandbar``, ``&flux_ctrl_commandbar``,
  ``&flux_ctrl_appbarbutton``, ``&flux_ctrl_appbartoggle``,
  ``&flux_ctrl_appbarsep``): Places primary icon/label commands on a toolbar,
  moves ``.secondary = true`` commands into the ``...`` overflow menu, and
  automatically overflows primary commands as the window narrows when
  ``.dynamic = true``:

  .. code-block:: c

     xtk_commandbar(
         ui,
         (XtkCommandBarDesc) {.labels = XTK_LABEL_RIGHT, .dynamic = true},
         xtk_kids(
             xtk_appbarbutton(ui, "New",  (XtkAppBarDesc) {.icon = "Add",  .accel = "Ctrl+N", .click = xtk_msg(MSG_NEW)}),
             xtk_appbarbutton(ui, "Save", (XtkAppBarDesc) {.icon = "Save", .accel = "Ctrl+S", .click = xtk_msg(MSG_SAVE)}),
             xtk_appbarsep(ui, (XtkAppBarDesc) {0}),
             xtk_appbartoggle(ui, "Wrap", (XtkAppBarDesc) {.icon = "AlignLeft", .checked = m->word_wrap, .change = xtk_msg(MSG_WRAP)}),
             xtk_appbarbutton(ui, "Export PDF…", (XtkAppBarDesc) {.secondary = true, .click = xtk_msg(MSG_EXPORT_PDF)})
         )
     )

Modal ``ContentDialog``, ``TeachingTip``, & Status Controls
-----------------------------------------------------------

Overlays in declarative Xent are controlled by boolean flags in ``Model``—place
the ``xtk_dialog`` or ``xtk_teachtip`` element in your ``view()`` tree and
toggle ``.open``:

.. code-block:: c

   // In update():
   case MSG_ASK_DELETE:
       m->confirm_open = true;
       break;
   case MSG_CONFIRM_RESULT:
       m->confirm_open = false;
       if (msg.i == 1) {          // 1 = primary, 2 = secondary, 0 = close/cancel
           delete_selected_item(m);
       }
       break;

   // In view() (register &flux_ctrl_dialog):
   xtk_dialog(
       ui, "Delete project?",
       (XtkDialogDesc) {
           .open      = m->confirm_open,
           .primary   = "Delete",
           .secondary = "Archive instead",
           .close     = "Cancel",
           .w         = 420.0f,
           .contenth  = 64.0f,
           .result    = xtk_msg(MSG_CONFIRM_RESULT),
       },
       xtk_kids(
           xtk_text(ui, "Removing this project deletes local build caches permanently.", (XtkTextDesc) {.size = 14})
       )
   )

- **TeachingTip** (``xtk_teachtip``, ``&flux_ctrl_teachtip``): Non-modal callout
  with ``.subtitle``, ``.action_text``, ``.on_action``, ``.light_dismiss = true``,
  and ``.close`` message.
- **Status & feedback**: ``xtk_infobar`` (``XTK_INFOBAR_INFORMATIONAL``,
  ``SUCCESS``, ``WARNING``, ``ERROR`` banner with optional ``.closable``
  button), ``xtk_progress`` (determinate or ``.indeterminate = true`` bar with
  ``XTK_PROGRESS_NORMAL`` / ``PAUSED`` / ``ERROR`` states),
  ``xtk_progressring``, and ``xtk_badge``.
