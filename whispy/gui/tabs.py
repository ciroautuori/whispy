"""Tab builders — each function builds one Notebook tab and returns nothing."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..providers import PROVIDER_NAMES
from . import const
from .components.log_view import LogView, make_header
from .components.provider_row import ProviderRow
from .components.toast import Toast
from .const import MONO
from .state import FormState, provider_key_var_names


def _entry(parent, var, width, style="Dark.TEntry", font=None):
    kw = {"textvariable": var, "width": width, "style": style}
    if font:
        kw["font"] = font
    return ttk.Entry(parent, **kw)


def build_provider_tab(parent, state: FormState, ctx) -> None:
    outer = ttk.Frame(parent, padding=16)
    outer.pack(fill="both", expand=True)

    ttk.Label(outer, text="Active provider", style="TLabel", font=("", 11, "bold")).grid(
        row=0, column=0, sticky="w"
    )
    combo = ttk.Combobox(
        outer,
        textvariable=ctx.var_provider,
        values=PROVIDER_NAMES,
        state="readonly",
        width=16,
        style="Dark.TCombobox",
    )
    combo.grid(row=0, column=1, sticky="w", padx=(10, 0))
    # _apply_provider, not on_provider_change: picking one saves it right away
    combo.bind("<<ComboboxSelected>>", ctx._apply_provider)

    ttk.Label(outer, text="Model override", style="TLabel").grid(
        row=1, column=0, sticky="w", pady=(10, 2)
    )
    _entry(outer, ctx.var_cloud_model, 34, font=(MONO, 10)).grid(
        row=1, column=1, sticky="w", padx=(10, 0), pady=(10, 2)
    )
    ttk.Label(
        outer,
        text=(
            "blank = provider's default — doesn't apply to google "
            "(different field, see providers/google.py)"
        ),
        style="BgMuted.TLabel",
        font=("", 8),
    ).grid(row=2, column=0, columnspan=2, sticky="w")

    rows_frame = tk.Frame(
        outer, bg=const.SURFACE, highlightbackground=const.BORDER, highlightthickness=1
    )
    rows_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(16, 0))
    rows_frame.columnconfigure(0, weight=1)
    outer.columnconfigure(1, weight=1)

    for i, (name, env_var, needs_key) in enumerate(provider_key_var_names()):
        row = ProviderRow(
            rows_frame,
            name,
            env_var,
            needs_key,
            state.keys.get(env_var, ""),
            i,
            on_key_change=ctx.on_key_change,
            on_test=ctx.on_test,
        )
        ctx.rows[name] = row

    ctx.extra_ollama = ttk.Frame(outer, padding=(0, 12, 0, 0))
    ttk.Label(ctx.extra_ollama, text="Ollama host", style="TLabel").grid(
        row=0, column=0, sticky="w"
    )
    _entry(ctx.extra_ollama, ctx.var_ollama_host, 34, font=(MONO, 10)).grid(
        row=0, column=1, sticky="w", padx=(10, 0)
    )

    ctx.extra_nvidia = ttk.Frame(outer, padding=(0, 12, 0, 0))
    ttk.Label(ctx.extra_nvidia, text="NVIDIA self-hosted server", style="TLabel").grid(
        row=0, column=0, sticky="w"
    )
    _entry(ctx.extra_nvidia, ctx.var_nvidia_server, 34, font=(MONO, 10)).grid(
        row=0, column=1, sticky="w", padx=(10, 0)
    )
    ttk.Label(
        ctx.extra_nvidia,
        text="host:port — blank uses NVIDIA's cloud endpoint",
        style="BgMuted.TLabel",
        font=("", 8),
    ).grid(row=1, column=0, columnspan=2, sticky="w")
    ttk.Label(ctx.extra_nvidia, text="function-id", style="TLabel").grid(
        row=2, column=0, sticky="w", pady=(8, 0)
    )
    _entry(ctx.extra_nvidia, ctx.var_nvidia_function_id, 34, font=(MONO, 10)).grid(
        row=2, column=1, sticky="w", padx=(10, 0), pady=(8, 0)
    )
    ttk.Label(
        ctx.extra_nvidia,
        text=("required for the cloud endpoint — copy from your model's page on build.nvidia.com"),
        style="BgMuted.TLabel",
        font=("", 8),
    ).grid(row=3, column=0, columnspan=2, sticky="w")

    ctx.extra_ollama.grid(row=4, column=0, columnspan=2, sticky="w")
    ctx.extra_nvidia.grid(row=4, column=0, columnspan=2, sticky="w")

    result_frame = ttk.Frame(outer, padding=(0, 16, 0, 0))
    result_frame.grid(row=5, column=0, columnspan=2, sticky="ew")
    ctx.test_result = Toast(
        result_frame,
        text="Click Test on any row to record ~5s and try it live.",
        ttl_ms=0,
    )
    ctx.test_result.pack(anchor="w")


def build_recording_tab(parent, ctx) -> None:
    frame = ttk.Frame(parent, padding=16)
    frame.pack(fill="both", expand=True)
    frame.columnconfigure(1, weight=1)

    r = 0
    ttk.Label(frame, text="Language (whisper code, e.g. it/en/es)", style="TLabel").grid(
        row=r, column=0, sticky="w", pady=6
    )
    _entry(frame, ctx.var_whisper_language, 10).grid(
        row=r, column=1, sticky="w", padx=(10, 0), pady=6
    )
    r += 1

    ttk.Label(frame, text="Local model path (blank = auto-detect)", style="TLabel").grid(
        row=r, column=0, sticky="w", pady=6
    )
    _entry(frame, ctx.var_whisper_model, 44, font=(MONO, 10)).grid(
        row=r, column=1, sticky="ew", padx=(10, 0), pady=6
    )
    r += 1
    ttk.Label(
        frame,
        text=f"currently resolved: {ctx.cfg.whisper_model}",
        style="BgMuted.TLabel",
        font=(MONO, 8),
    ).grid(row=r, column=1, sticky="w", padx=(10, 0))
    r += 1

    ttk.Label(frame, text="Threads (local provider only)", style="TLabel").grid(
        row=r, column=0, sticky="w", pady=6
    )
    ttk.Spinbox(
        frame, from_=1, to=32, textvariable=ctx.var_whisper_threads, width=8, style="Dark.TSpinbox"
    ).grid(row=r, column=1, sticky="w", padx=(10, 0), pady=6)
    r += 1

    ttk.Label(frame, text="Silence duration before auto-stop (s)", style="TLabel").grid(
        row=r, column=0, sticky="w", pady=6
    )
    _entry(frame, ctx.var_silence_duration, 10).grid(
        row=r, column=1, sticky="w", padx=(10, 0), pady=6
    )
    r += 1

    ttk.Label(frame, text="Silence threshold", style="TLabel").grid(
        row=r, column=0, sticky="w", pady=6
    )
    ttk.Spinbox(
        frame,
        from_=1,
        to=20,
        textvariable=ctx.var_silence_threshold,
        width=8,
        style="Dark.TSpinbox",
    ).grid(row=r, column=1, sticky="w", padx=(10, 0), pady=6)
    r += 1

    ttk.Label(frame, text="Max recording seconds", style="TLabel").grid(
        row=r, column=0, sticky="w", pady=6
    )
    ttk.Spinbox(
        frame,
        from_=3,
        to=300,
        textvariable=ctx.var_max_record_seconds,
        width=8,
        style="Dark.TSpinbox",
    ).grid(row=r, column=1, sticky="w", padx=(10, 0), pady=6)
    r += 1

    ttk.Label(frame, text="Push-to-talk key combo", style="TLabel").grid(
        row=r, column=0, sticky="w", pady=6
    )
    _entry(frame, ctx.var_ptt_key, 18, font=(MONO, 10)).grid(
        row=r, column=1, sticky="w", padx=(10, 0), pady=6
    )
    r += 1

    ttk.Checkbutton(
        frame,
        text="Auto-paste at cursor after transcribing",
        variable=ctx.var_autopaste,
        style="Dark.TCheckbutton",
    ).grid(row=r, column=0, columnspan=2, sticky="w", pady=(14, 6))
    r += 1
    ttk.Checkbutton(
        frame,
        text="Keep the WAV file after transcribing",
        variable=ctx.var_keep_audio,
        style="Dark.TCheckbutton",
    ).grid(row=r, column=0, columnspan=2, sticky="w", pady=6)
    r += 1

    ttk.Label(frame, text="Notifications", style="TLabel").grid(
        row=r, column=0, sticky="w", pady=(14, 6)
    )
    ttk.Combobox(
        frame,
        textvariable=ctx.var_notify_level,
        values=("normal", "quiet", "off"),
        state="readonly",
        width=10,
        style="Dark.TCombobox",
    ).grid(row=r, column=1, sticky="w", padx=(10, 0), pady=(14, 6))


def build_log_tab(parent, ctx) -> None:
    frame = ttk.Frame(parent, padding=16)
    frame.pack(fill="both", expand=True)
    header = make_header(frame, ctx.refresh_log)
    header.pack(fill="x")
    ctx.log_view = LogView(frame)
    ctx.log_view.text.pack(fill="both", expand=True, pady=(8, 0))
    ctx.refresh_log()
