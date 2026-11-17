Architecture & Core Concepts
============================

This page explains how ``xent-core``, ``xent-kit``, and ``fluxent`` divide
responsibilities in **Xent 0.3.3**, along with the core runtime guarantees for
retained controls, binary size, and background threads.

Three-Layer Package Responsibilities
------------------------------------

Project Xent separates layout calculation, control semantics, and native OS
rendering into three distinct layers:

1. ``xent-core`` — **Headless Layout & Display Lists**

   - Maintains the generation-checked ``XentNodeId`` tree so stale handles are
     detected reliably even after node slots are reused.
   - Computes ``ABSOLUTE``, ``FLEX``, ``SWIFTSTACK``, and ``GRID`` layout,
     intrinsic content sizing, dirty propagation, focus order, accessibility
     semantics roles, and immutable ``XentDisplayList`` command buffers.
   - Written in portable C23 for use by platform hosts, headless layout tools,
     and shared layout types (``XentFlexAlign``, ``XentInsets``) re-exported
     through ``xent-kit``.

2. ``xent-kit`` — **Control Protocol, Retained Host ABI, & Reconciler**

   - Defines the standard catalog of 70+ controls, typed properties, and
     normalized events generated from ``tools/catalog.lua``.
   - Defines ``XtkBatch``, the atomic mutation wire format: a host validates and
     prepares every operation in a batch before committing, preserving the
     previous live tree intact whenever an error occurs.
   - Provides both public programming models on top of that protocol: the
     imperative ``XtkScene`` / ``XtkTxn`` API and the declarative ``xtk_*``
     reconciler.

3. ``fluxent`` — **Native Windows Host**

   - Implements ``XtkHost`` on Windows 10 1903+ over Win32, Direct2D,
     DirectWrite (text shaping, grapheme editing, IME), DirectComposition and
     DirectManipulation (smooth scrolling and Mica/Acrylic backdrops), Windows
     Imaging Component (async image decoding), UI Automation (screen readers),
     and ``cwinrt`` (pure-C WinRT projections).
   - Provides ``flux_run`` for declarative applications alongside
     ``flux_app_*`` and ``flux_host_*`` for imperative applications and desktop
     shell integration (file dialogs, menus, popups, drag-and-drop, clipboard).

Retained Control Architecture
-----------------------------

Xent uses a **retained** UI architecture across both declarative and imperative
modes:

- The Fluxent host owns persistent native control instances with stateful text
  selection, IME composition, keyboard focus navigation, inertial scrolling, and
  OS accessibility peers.
- In declarative mode, ``view()`` constructs lightweight arena-allocated
  descriptors when messages arrive; the reconciler diffs them against the prior
  composition and commits incremental ``XtkBatch`` patches to the existing
  controls.
- Event-driven scheduling keeps idle windows asleep until user input, active
  animations, async image completion, or ``flux_app_post`` /
  ``flux_app_redraw`` requests a frame.

Modular Control Registration & Binary Size
------------------------------------------

In **Fluxent 0.3.3**, every control is packaged as an independent
``FluxControlModule`` declared in ``<fluxent/flux_controls.h>`` (such as
``flux_ctrl_container``, ``flux_ctrl_text``, ``flux_ctrl_button``,
``flux_ctrl_textbox``, and ``flux_ctrl_list``), allowing linker dead-stripping
to include only the controls your application registers:

- **Selective registration (** ``flux_controls_use(&flux_ctrl_<name>)`` **)**:
  Registers individual control modules (each module automatically registers any
  internal sub-controls it depends on). Unused controls are stripped by the
  linker, keeping single-file executables compact.
- **Full catalog registration (** ``flux_controls_all()`` **)**: Registers every
  built-in control module in one call—handy during rapid prototyping or in
  applications that use a wide variety of controls.

.. important::

   Register every control module your application instantiates before the first
   batch commits; creating an unregistered control returns
   ``XTK_BATCH_ERR_BACKEND``.

Thread Safety & Background Work
-------------------------------

UI trees, ``XtkScene``, and ``FluxApp`` windows run on the main UI thread.
Background worker threads performing network requests, disk I/O, or compute
tasks deliver results back to the UI thread through ``FluxApp``'s thread-safe
posting functions:

- ``flux_app_post(app, xtk_msg_i(MSG_DONE, status))`` — Enqueues an ``XtkMsg``
  from any thread and wakes the window event loop.
- ``flux_app_poststring(app, xtk_msg(MSG_LOG), text, len)`` — Copies a UTF-8
  buffer and delivers it to ``update()`` on the UI thread.
- ``flux_app_invoke(app, fn, ctx)`` — Schedules ``fn(ctx)`` to execute on the UI
  thread.
