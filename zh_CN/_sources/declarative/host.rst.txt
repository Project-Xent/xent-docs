6. File Dialogs, Drag-and-Drop, Theme, & Worker Threads
=======================================================

Desktop applications frequently interact with the OS shell—opening native file
pickers, accepting dropped files from Explorer, reading the clipboard, switching
themes, and running long tasks off the UI thread. Here is how all four integrate
cleanly into the declarative MVU loop.

Capturing ``FluxApp *`` via ``on_start`` and ``on_stop``
--------------------------------------------------------

``flux_run`` creates and owns the ``FluxApp *`` instance for you. Populate
``on_start``, ``on_stop``, and ``user`` on ``FluxAppCfg`` to store the
``FluxApp *`` pointer inside ``Model`` for the lifetime of the window:

.. code-block:: c

   typedef struct Model {
       FluxApp *app;
       char    *chosen_folder;
       bool     dark_mode;
   } Model;

   static void app_start(FluxApp *app, void *user) {
       Model *m = user;
       m->app   = app;
   }

   static void app_stop(FluxApp *app, void *user) {
       (void) app;
       Model *m = user;
       // Join any background threads before clearing m->app
       m->app = NULL;
   }

   int WINAPI WinMain(HINSTANCE hInst, HINSTANCE hPrev, LPSTR cmdLine, int showCmd) {
       (void) hInst; (void) hPrev; (void) cmdLine; (void) showCmd;
       flux_controls_all();

       static Model model;
       FluxAppCfg cfg = {
           .title    = L"Shell Integration",
           .width    = 720,
           .height   = 480,
           .backdrop = FLUX_BACKDROP_MICA,
           .on_start = app_start,
           .on_stop  = app_stop,
           .user     = &model,
       };
       return flux_run(&cfg, &model, update, view);
   }

Native File & Folder Pickers
----------------------------

Include ``<fluxent/flux_filedialog.h>`` and call ``flux_filedialog_post`` inside
``update()`` when the user clicks a "Browse…" button. It opens the Windows
Common Item Dialog without tangling your ``view()`` code and posts the result
back as an ``XtkMsg``:

.. code-block:: c

   static FluxFileFilter const kDocFilters[] = {
       {.name = "Markdown & Text", .spec = "*.md;*.txt"},
       {.name = "All Files",       .spec = "*.*"},
   };

   // Inside update():
   case MSG_BROWSE_OPEN: {
       FluxFileDialogDesc desc = {
           .kind         = FLUX_FILEDIALOG_OPEN, // or FLUX_FILEDIALOG_SAVE / FLUX_FILEDIALOG_FOLDER
           .title        = "Open Document",
           .filters      = kDocFilters,
           .filter_count = 2,
           .multiple     = false,
       };
       flux_filedialog_post(m->app, &desc, xtk_msg(MSG_FILE_PICKED));
       break;
   }
   case MSG_FILE_PICKED:
       // msg.b is true when the user confirmed; msg.ptr holds UTF-8 path(s), one per line
       if (msg.b && msg.ptr) {
           free(m->chosen_folder);
           m->chosen_folder = strdup((char const *) msg.ptr);
       }
       break;

OLE Drag-and-Drop & Clipboard
-----------------------------

Drop Targets & Drag Sources (``xtk_dragdrop``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Wrap any container or card in ``xtk_dragdrop(ui, desc, child)`` to accept files
or text dragged from Windows Explorer and other apps, or to turn an element into
a drag source:

.. code-block:: c

   // Drop target:
   xtk_dragdrop(
       ui,
       (XtkDragDropDesc) {
           .drop       = XTK_DROP_COPY,
           .hover      = xtk_msg(MSG_DROP_HOVER), // msg.b = pointer is hovering over target
           .drop_files = xtk_msg(MSG_DROP_FILES), // msg.ptr = newline-separated UTF-8 paths
           .drop_text  = xtk_msg(MSG_DROP_TEXT),  // msg.ptr = dropped UTF-8 text
       },
       xtk_card(
           ui, (XtkStackDesc) {.padding = {24, 24, 24, 24}},
           xtk_kids(xtk_text(ui, m->hovering ? "Release to import" : "Drop files here", (XtkTextDesc) {0}))
       )
   )

   // Drag source:
   xtk_dragdrop(
       ui,
       (XtkDragDropDesc) {
           .drag_text = "Snippet from Xent", // or .drag_files = "C:\\path\\file.txt"
           .dragged   = xtk_msg(MSG_DRAG_FINISHED),
       },
       xtk_card(ui, (XtkStackDesc) {0}, xtk_kids(xtk_text(ui, "Drag me", (XtkTextDesc) {0})))
   )

As with ``TextBox``, duplicate ``(char const *) msg.ptr`` with ``strdup`` inside
``update()`` when handling ``MSG_DROP_FILES`` or ``MSG_DROP_TEXT``.

Clipboard Read & Write
~~~~~~~~~~~~~~~~~~~~~~

Include ``<fluxent/flux_data.h>`` inside ``update()`` to read or write the
Windows clipboard:

.. code-block:: c

   // Copy UTF-8 text to clipboard:
   flux_clipboard_settext(text, strlen(text));

   // Paste UTF-8 text from clipboard (caller frees the returned buffer):
   char *pasted = flux_clipboard_text();
   if (pasted) {
       free(m->notes);
       m->notes = pasted; // Transfer ownership directly into Model
   }

For multi-format clipboard payloads (files, raw RGBA ``FluxBitmap`` images, or
custom MIME/clipboard formats), construct a ``FluxData *`` via
``flux_data_create()`` and pass it to ``flux_clipboard_set``.

Switching Theme, Backdrop, & Window State
-----------------------------------------

With ``m->app`` stored from ``on_start``, ``update()`` can adjust live window
chrome in response to settings controls:

- **Theme mode**: ``flux_theme_setmode(flux_app_theme(m->app), FLUX_THEME_DARK);``
  (accepts ``FLUX_THEME_SYSTEM``, ``FLUX_THEME_LIGHT``, or ``FLUX_THEME_DARK``).
- **Window backdrop**:
  ``flux_window_setbackdrop(flux_app_window(m->app), FLUX_BACKDROP_MICA_ALT);``
  (accepts ``FLUX_BACKDROP_NONE``, ``MICA``, ``MICA_ALT``, or ``ACRYLIC``).
- **Dynamic window title & close**:
  ``flux_window_settitle(flux_app_window(m->app), L"Unsaved *");`` and
  ``flux_window_close(flux_app_window(m->app));`` (for example after confirming
  an exit ``ContentDialog``).

Background Worker Threads
-------------------------

Keep ``update()`` fast and non-blocking by offloading network calls, archive
extraction, or heavy indexing to a worker thread. Pass ``FluxApp *`` into your
worker context and report progress back via thread-safe message posting:

.. code-block:: c

   static DWORD WINAPI worker_proc(void * param) {
       FluxApp *app = param;
       for (int step = 0; step < 100; step++) {
           // Perform background work...
           flux_app_post(app, xtk_msg_i(MSG_PROGRESS_STEP, step + 1));
       }
       char const *summary = "All 100 items processed.";
       flux_app_poststring(app, xtk_msg(MSG_WORKER_LOG), summary, (uint32_t) strlen(summary));
       flux_app_post(app, xtk_msg(MSG_WORKER_DONE));
       return 0;
   }

- ``flux_app_post`` enqueues scalar ``XtkMsg`` values from any thread and wakes
  the UI loop.
- ``flux_app_poststring`` copies the UTF-8 string safely onto the queue and
  delivers it as ``(char const *) msg.ptr`` inside ``update()`` on the UI
  thread.
- Always join active worker threads inside ``FluxAppCfg.on_stop`` before the
  process destroys ``FluxApp``. See ``fluxent/examples/installer_wizard/`` for a
  complete multi-page setup wizard with pause, cancel, and worker synchronization.
