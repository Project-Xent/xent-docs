6. Dialogs, Drag-and-Drop, Clipboard, & Windowing
=================================================

Imperative applications have direct access to ``FluxApp *``, ``FluxWindow *``,
and ``FluxTheme *`` from the moment ``WinMain`` starts, making modal dialogs,
file pickers, OLE drag-and-drop, clipboard transfers, and cross-thread UI
updates straightforward.

Modal ``ContentDialog``
-----------------------

Create a ``ContentDialog`` (register ``&flux_ctrl_dialog``) once inside your
scene transaction with ``.open = false``, save its ``XtkCtrl`` handle, and open
it on demand via ``xtk_dialog_setopen``:

.. code-block:: c

   // 1. Inside your build XtkTxn:
   XtkLocalId dlg = xtk_dialog_create(
       &txn, parent,
       &(XtkDialogProps) {
           .set      = XTK_DIALOG_W_MASK | XTK_DIALOG_CONTENTH_MASK | XTK_DIALOG_TEXT_MASK
                     | XTK_DIALOG_PRIMARY_MASK | XTK_DIALOG_CLOSE_MASK | XTK_DIALOG_OPEN_MASK,
           .w        = 400.0f,
           .contenth = 56.0f,
           .text     = "Discard unsaved changes?",
           .primary  = "Discard",
           .close    = "Cancel",
           .open     = false,
       }
   );
   xtk_text_create(
       &txn, xtk_ref_local(dlg),
       &(XtkTextProps) {
           .set      = XTK_TEXT_TEXT_MASK | XTK_TEXT_FONTSIZE_MASK,
           .text     = "Your current edits will be lost.",
           .fontsize = 14.0f,
       }
   );
   xtk_dialog_onclose(&txn, xtk_ref_local(dlg), on_dialog_closed, app);

   // 2. Show the dialog from any button callback:
   xtk_dialog_setopen(&app->scene, app->confirm_dlg, true, (XtkChangeStamp) {0});

   // 3. Handle the user's choice in on_dialog_closed:
   static uint32_t on_dialog_closed(void *arg, XtkEvent const *e) {
       App *app = arg;
       xtk_dialog_setopen(&app->scene, app->confirm_dlg, false, (XtkChangeStamp) {0});
       int32_t choice = e->payload.u.i32; // 1 = primary, 2 = secondary, 0 = close/Esc
       if (choice == 1) {
           reset_document(app);
       }
       return XTK_EVENT_HANDLED;
   }

Native File & Folder Dialogs
----------------------------

Include ``<fluxent/flux_filedialog.h>`` and call ``flux_filedialog_show`` from a
UI button callback to display the native Windows Open, Save, or Folder picker:

.. code-block:: c

   static FluxFileFilter const kFilters[] = {
       {.name = "C Source Files", .spec = "*.c;*.h"},
       {.name = "All Files",      .spec = "*.*"},
   };

   FluxFileDialogDesc desc = {
       .kind         = FLUX_FILEDIALOG_OPEN,
       .title        = "Select Source Files",
       .filters      = kFilters,
       .filter_count = 2,
       .multiple     = true,
   };

   // Returns malloc'd UTF-8 paths (one path per line), or NULL when cancelled:
   char *paths = flux_filedialog_show(app->flux, &desc);
   if (paths) {
       open_selected_paths(app, paths);
       free(paths);
   }

OLE Drag-and-Drop on Containers & Cards
---------------------------------------

Every ``container`` and ``card`` control in ``<xtk/xtk_controls.h>`` carries
built-in OLE drag-and-drop properties and events:

.. code-block:: c

   // Configure a card as a file/text drop target:
   XtkLocalId drop_card = xtk_card_create(
       &txn, parent,
       &(XtkContainerProps) {
           .set  = XTK_CONTAINER_DROP_MASK | XTK_CONTAINER_PL_MASK | XTK_CONTAINER_PT_MASK
                 | XTK_CONTAINER_PR_MASK | XTK_CONTAINER_PB_MASK,
           .drop = XTK_DROP_COPY,
           .pl   = 24, .pt = 24, .pr = 24, .pb = 24,
       }
   );
   xtk_card_ondraghover(&txn, xtk_ref_local(drop_card), on_drag_hover, app);
   xtk_card_ondropfiles(&txn, xtk_ref_local(drop_card), on_drop_files, app);
   xtk_card_ondroptext(&txn, xtk_ref_local(drop_card), on_drop_text, app);

- ``on_drag_hover`` receives ``e->payload.u.b`` (``true`` on enter, ``false`` on
  leave).
- ``on_drop_files`` and ``on_drop_text`` receive a borrowed UTF-8 slice in
  ``e->payload.u.string.{data, len}`` (newline-delimited file paths for files).
  While a drag or drop callback is executing, you can also inspect custom or
  bitmap formats on the active OLE data object via ``flux_drag_data()`` from
  ``<fluxent/flux_data.h>``.
- To make a container or card a **drag source**, set ``XTK_CONTAINER_DRAGTEXT_MASK``
  (``.dragtext``) or ``XTK_CONTAINER_DRAGFILES_MASK`` (``.dragfiles``) and
  subscribe with ``xtk_container_ondragcompleted``.

Clipboard Data (``FluxData``)
-----------------------------

``<fluxent/flux_data.h>`` provides text shortcuts as well as multi-format
``FluxData`` containers:

.. code-block:: c

   // Plain UTF-8 text:
   flux_clipboard_settext("Copied from Xent", 16);
   char *clip = flux_clipboard_text(); // Caller frees with free(clip)
   free(clip);

   // Rich multi-format payload (text + custom binary format):
   FluxData *data = flux_data_create();
   flux_data_settext(data, "Node #42", 8);
   flux_data_setcustom(data, "application/x-myapp-node", &node_id, sizeof(node_id));
   flux_clipboard_set(data);
   flux_data_destroy(data);

Window Chrome, Themes, & Background Threads
-------------------------------------------

- **Themes & Backdrops**: Access ``FluxTheme *`` with ``flux_app_theme(app)``
  (``flux_theme_setmode`` for Light/Dark/System; ``flux_theme_colors`` to read
  active Fluent palette brushes) and ``FluxWindow *`` with
  ``flux_app_window(app)`` (``flux_window_setbackdrop``, ``flux_window_settitle``,
  ``flux_window_size``, ``flux_window_dpi``, ``flux_window_close``).
- **Custom title bar**: Either instantiate ``xtk_titlebar_create`` with
  ``XTK_TITLEBAR_INTEGRATE_MASK`` (``.integrate = true``), or call
  ``flux_window_extendtitlebar`` and ``flux_window_settitlebar`` directly to
  define custom caption drag and interactive passthrough rectangles.
- **Cross-thread UI dispatch**: Worker threads marshal results onto the window
  thread via ``flux_app_invoke(app, apply_worker_result, result_ctx)``. Note
  that ``flux_app_invoke`` borrows ``result_ctx`` until ``apply_worker_result``
  executes on the UI thread, where you can safely open an ``XtkTxn`` or call
  ``xtk_<ctrl>_set*`` and then free ``result_ctx``.
