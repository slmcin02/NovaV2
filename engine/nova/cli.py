from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from nova.config import load_config
from nova.phase1.cli import cmd_phase1_eval
from nova.data.finra_adapter import FINRAAdapter
from nova.data.occ_adapter import OCCAdapter
from nova.data.cftc_adapter import CFTCAdapter
from nova.data.fda_calendar_adapter import FDACalendarAdapter
from nova.data.clinicaltrials_adapter import ClinicalTrialsAdapter
from nova.data.fred_adapter import FREDMacroAdapter
from nova.data.nasdaq_halts_adapter import NasdaqHaltsAdapter
from nova.data.sec_ftd_adapter import SECFTDAdapter
from nova.data.provider_router import get_provider
from nova.data.sec_adapter import SECAdapter
from nova.engine.alerts import make_dedupe_key, send_discord
from nova.engine.backtest import simple_exit_backtest
from nova.engine.calibration import calibrate_from_store
from nova.engine.cohorts import cohort_summary
from nova.engine.execution_quality import persist_execution_quality
from nova.engine.score_optimizer import recommend_scoring_weights, write_scoring_optimization_report
from nova.engine.features import build_feature_row
from nova.engine.learner import Learner
from nova.engine.market_ops import compute_sector_coherence, get_market_ops_state, sector_etf_for
from nova.engine.paper import PaperBroker, PaperRiskEngine
from nova.engine.preflight import run_preflight
from nova.engine.probability import apply_probability_overlay, load_calibration_report
from nova.engine.retention import compact_old_snapshots
from nova.engine.risk import dynamic_contracts, position_risk_ok, sector_exposure_ok
from nova.engine.scoring import passes_contract_gates, score_row
from nova.engine.signal_quality import score_dynamics, spin_coherence
from nova.engine.strategies import strategy_tags
from nova.engine.universe import UniverseBuilder
from nova.llm.vector_memory import VectorMemory
from nova.storage.duckdb_store import DuckDBStore
from nova.storage.parquet_lake import ParquetLake


def _components(provider_name: str | None = None):
    cfg = load_config()
    store = DuckDBStore(cfg.storage["duckdb_path"])
    lake = ParquetLake(cfg.storage["lake_root"])
    provider = get_provider(cfg, provider_name) if provider_name is not None else None
    sec = SECAdapter(cfg.raw["env"]["sec_user_agent"])
    finra = FINRAAdapter()
    occ = OCCAdapter()
    return cfg, store, lake, provider, sec, finra, occ


def cmd_validate(_: argparse.Namespace) -> None:
    cfg, store, lake, provider, sec, finra, occ = _components(None)
    print("config loaded")
    print(f"duckdb={cfg.storage['duckdb_path']}")
    print(f"lake={cfg.storage['lake_root']}")
    print("validate: ok")


def _prior_scores(store, symbol: str) -> list[float]:
    try:
        df = store.conn.execute(
            "SELECT score FROM signals WHERE symbol = ? ORDER BY signal_ts DESC LIMIT 3",
            [symbol],
        ).df()
    except Exception:
        return []
    if df.empty:
        return []
    return [float(x) for x in df['score'].tolist()][::-1]


def _scan_core(cfg, store, lake, provider, sec, finra, fixture_name: str | None = None):
    if fixture_name and getattr(provider, 'name', '') == 'replay' and hasattr(provider, 'load_fixture'):
        provider.default_fixture_name = fixture_name
    universe = UniverseBuilder(cfg, provider)
    universe_rows = universe.filtered_symbols()
    store.upsert_universe(universe_rows)

    now = datetime.now(UTC).replace(tzinfo=None)
    raw_rows: list[dict] = []
    signal_rows: list[dict] = []
    dedupe_seen = store.recent_alert_keys(int(cfg.alerts["dedupe_hours"]))
    cal_report = load_calibration_report(cfg.calibration['output_path'])
    ops = get_market_ops_state(now.replace(tzinfo=UTC))
    occ = OCCAdapter()
    ftd = SECFTDAdapter()
    halts = NasdaqHaltsAdapter()
    fred = FREDMacroAdapter(cfg.raw["env"].get("fred_api_key", ""))

    for urow in universe_rows:
        symbol = urow["symbol"]
        momentum = provider.momentum_20d(symbol)
        vix_val = provider.vix_value()
        offline_mode = getattr(provider, 'name', '') == 'replay'
        # Historical replay must not reach SEC's live network. A missing
        # historical dilution flag is UNKNOWN, not evidence of zero risk.
        dilution_flag = False if offline_mode else sec.has_recent_dilution_risk(
            symbol, int(cfg.edges["sec_dilution_lookback_days"])
        )[0]
        finra_ratio = finra.short_ratio_for_symbol(symbol, now.date()) if (cfg.edges["finra_short_volume_enabled"] and not offline_mode) else 0.0
        occ_oi = occ.open_interest_for_symbol(symbol, now.date()) if (cfg.edges.get("occ_open_interest_enabled", False) and not offline_mode) else 0
        sec_ftd_qty = ftd.ftd_quantity_for_symbol(symbol, now.date()) if (cfg.edges.get("ftd_enabled", False) and not offline_mode) else 0
        macro_regime_score = fred.risk_regime_score() if (cfg.edges.get("fred_macro_enabled", False) and not offline_mode) else 0.5
        sector_etf = sector_etf_for(urow.get('sector'))
        sector_momentum = provider.momentum_20d(sector_etf) if sector_etf else 0.0
        sector_coh, reflex_mult = compute_sector_coherence(momentum, sector_momentum, vix_val)

        snapshots = provider.scan_calls(
            symbol=symbol,
            max_dte=int(cfg.contracts["max_dte"]),
            min_dte=int(cfg.contracts["min_dte"]),
            max_ask=float(cfg.contracts["max_ask"]),
        )
        raw_rows.extend([s.to_dict() for s in snapshots])

        kept = 0
        ranked_rows = []
        for snap in snapshots:
            row = build_feature_row(
                snap=snap,
                config=cfg,
                momentum_20d=momentum,
                finra_short_ratio=finra_ratio,
                insider_buy_flag=False,
                edgar_dilution_flag=dilution_flag,
                vix_value=vix_val,
                sector_etf=sector_etf,
                sector_momentum_20d=sector_momentum,
                occ_open_interest=occ_oi,
                sec_ftd_qty=sec_ftd_qty,
                macro_regime_score=macro_regime_score,
            )
            row.sector_coherence = sector_coh
            row.reflexivity_multiplier = reflex_mult
            row.event_risk = ops.event_risk
            row.blocked_market_ops = (provider.name != 'replay') and ((not ops.can_open_new) or halts.is_symbol_halted(symbol))
            row.spin_coherence, row.spin_lock = spin_coherence(row.momentum_20d, row.technical_score, row.sector_coherence, row.vix_value)
            row = score_row(row, cfg)
            row.calibrated_win_prob = max(0.05, min(0.95, row.score / 100.0))
            row = apply_probability_overlay(row, cal_report)
            prior = _prior_scores(store, symbol)
            row.sci_velocity, row.sci_acceleration, row.failure_tag = score_dynamics(prior, row.score)
            row.suggested_contracts = dynamic_contracts(row, cfg)
            row.strategy_tags = ",".join(strategy_tags(row) + [row.failure_tag])
            if not passes_contract_gates(row, cfg):
                continue
            if row.score < float(cfg.scoring["min_score"]):
                continue
            if not position_risk_ok(row, cfg):
                continue
            ranked_rows.append(row)

        ranked_rows.sort(key=lambda r: (r.score_lcb, r.score, max(r.sci_velocity, 0.0), r.sector_coherence, -r.expected_slippage_bps), reverse=True)
        for row in ranked_rows:
            payload = row.to_dict()
            signal = {"signal_ts": now, **payload, "payload_json": json.dumps(payload, default=str)}
            signal_rows.append(signal)
            kept += 1

            dedupe_key = make_dedupe_key(row)
            if not offline_mode and dedupe_key not in dedupe_seen and cfg.alerts["discord_enabled"]:
                if send_discord(cfg.raw["env"]["discord_webhook_url"], row):
                    dedupe_seen.add(dedupe_key)
                    store.insert_dataframe("alerts", pd.DataFrame([{
                        "alert_ts": now,
                        "dedupe_key": dedupe_key,
                        "channel": "discord",
                        "payload_json": signal["payload_json"],
                    }]))
            if kept >= int(cfg.contracts["max_contracts_per_symbol"]):
                break

        store.upsert_edge_daily([{
            "asof_date": now.date(),
            "symbol": symbol,
            "finra_short_ratio": finra_ratio,
            "occ_open_interest": occ_oi,
            "edgar_dilution_flag": dilution_flag,
        }])

    if raw_rows:
        lake.write_batch("options_snapshot", raw_rows, ts=now)
    if signal_rows:
        signal_df = pd.DataFrame(signal_rows)
        signal_cols = store.conn.execute("PRAGMA table_info('signals')").df()["name"].tolist()
        store.insert_dataframe("signals", signal_df[[c for c in signal_df.columns if c in signal_cols]])
        lake.write_batch("signals", signal_rows, ts=now)
    return universe_rows, raw_rows, signal_rows


def cmd_scan(args: argparse.Namespace) -> None:
    cfg, store, lake, provider, sec, finra, occ = _components(args.provider)
    universe_rows, raw_rows, signal_rows = _scan_core(cfg, store, lake, provider, sec, finra)
    print(f"scan complete: provider={provider.name} universe={len(universe_rows)} raw_snapshots={len(raw_rows)} signals={len(signal_rows)}")


def cmd_provider_check(args: argparse.Namespace) -> None:
    cfg, store, lake, provider, sec, finra, occ = _components(args.provider)
    symbol = args.symbol.upper()
    try:
        profile = provider.get_profile(symbol)
        rows = provider.scan_calls(symbol=symbol, max_dte=int(cfg.contracts['max_dte']), min_dte=int(cfg.contracts['min_dte']), max_ask=float(cfg.contracts['max_ask']))
        status = 'ok' if rows else 'empty'
        detail = f"profile={bool(profile)} rows={len(rows)}"
        store.provider_health(provider.name, status, detail)
        print(json.dumps({"provider": provider.name, "status": status, "detail": detail, "profile": profile}, default=str, indent=2))
    except Exception as exc:
        store.provider_health(getattr(provider, 'name', args.provider), 'error', str(exc))
        print(json.dumps({"provider": getattr(provider, 'name', args.provider), "status": "error", "detail": str(exc)}, indent=2))


def cmd_ingest_edges(_: argparse.Namespace) -> None:
    cfg, store, lake, provider, sec, finra, occ = _components(
        getattr(_, "provider", "auto")
    )
    # A replay fixture contains no versioned historical SEC/FINRA/OCC/FRED
    # provenance. Never synthesize current-day zero values in the edge ledger.
    if getattr(provider, "name", None) == "replay":
        print("edge ingest: offline replay has no authenticated historical edge fixtures; skipped without writing")
        return
    ftd = SECFTDAdapter()
    fred = FREDMacroAdapter(cfg.raw["env"].get("fred_api_key", ""))
    universe_df = store.conn.execute("SELECT symbol FROM universe WHERE active = TRUE").df()
    if universe_df.empty:
        print("no universe rows; run scan first")
        return
    now = datetime.now(UTC).replace(tzinfo=None)
    rows = []
    for symbol in universe_df["symbol"].tolist():
        offline_mode = getattr(provider, 'name', '') == 'replay'
        finra_ratio = finra.short_ratio_for_symbol(symbol, now.date()) if (cfg.edges["finra_short_volume_enabled"] and not offline_mode) else 0.0
        occ_oi = occ.open_interest_for_symbol(symbol, now.date()) if (cfg.edges.get("occ_open_interest_enabled", False) and not offline_mode) else 0
        sec_ftd_qty = ftd.ftd_quantity_for_symbol(symbol, now.date()) if (cfg.edges.get("ftd_enabled", False) and not offline_mode) else 0
        macro_regime_score = fred.risk_regime_score() if (cfg.edges.get("fred_macro_enabled", False) and not offline_mode) else 0.5
        dilution_flag, _ = sec.has_recent_dilution_risk(symbol, int(cfg.edges["sec_dilution_lookback_days"]))
        rows.append({
            "asof_date": now.date(),
            "symbol": symbol,
            "finra_short_ratio": finra_ratio,
            "occ_open_interest": occ_oi,
            "edgar_dilution_flag": dilution_flag,
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        store.upsert_edge_daily(df)
        lake.write_batch("edge_daily", rows, ts=now)
    print(f"edge ingest complete: rows={len(rows)}")


def cmd_backtest(args: argparse.Namespace) -> None:
    """Forbid a synthetic score proxy from being reported as price-based P&L."""
    if not getattr(args, "diagnostic_score_proxy", False):
        raise SystemExit(
            "backtest: historical bid/ask options quotes, entry-execution lag, "
            "partial-fill and transaction-cost records are required. "
            "This legacy engine has ONLY a score-derived proxy. "
            "Use --diagnostic-score-proxy for nonfinancial pipeline tests."
        )
    cfg, store, lake, provider, sec, finra, occ = _components(None)
    signals_df = store.signal_rows(days=730)
    hypothetical = simple_exit_backtest(
        signals_df,
        stop_loss_pct=float(cfg.risk["stop_loss_pct"]),
        take_profit_pct=float(cfg.risk["take_profit_pct"]),
    )
    print(json.dumps({
        "mode": "NON_FINANCIAL_SCORE_PROXY_DIAGNOSTIC",
        "historical_price_based": False,
        "training_eligible": False,
        "portfolio_performance_evidence": False,
        "hypothetical_examples": len(hypothetical),
        "trade_ledger_mutated": False,
        "note": "No actual future option quotes or fills; never interpret as win rate or P&L.",
    }, sort_keys=True))



def cmd_train(_: argparse.Namespace) -> None:
    cfg, store, lake, provider, sec, finra, occ = _components(None)
    trades_df = store.completed_trades()
    # Historical score-derived exits are NOT observed market outcomes. Refuse
    # all training until a versioned execution-provenance column and actual
    # matched fill/quote history can demonstrate verified inputs.
    if (
        trades_df.empty
        or "data_provenance" not in trades_df.columns
        or not trades_df["data_provenance"].eq("verified_paper_fills").all()
        or (
            "exit_reason" in trades_df.columns
            and trades_df["exit_reason"].astype(str).str.endswith("_proxy").any()
        )
    ):
        print("train blocked: verified_paper_fills provenance required; score-derived proxy labels are forbidden")
        return
    learner = Learner()
    pack, metrics = learner.train_from_trades(trades_df)
    if pack is None:
        print(f"train skipped: rows={metrics['train_rows']}")
        return
    learner.save(pack)
    store.insert_dataframe("model_runs", pd.DataFrame([{
        "run_ts": datetime.now(UTC).replace(tzinfo=None),
        "model_name": "signal_ensemble",
        "train_rows": metrics["train_rows"],
        "auc": metrics["auc"],
        "accuracy": metrics["accuracy"],
        "notes": "local ensemble trained from trades",
    }]))
    sigs = store.signal_rows(days=365)
    if not sigs.empty and len(sigs) >= 60:
        base = sigs.head(len(sigs)//2)
        recent = sigs.tail(len(sigs)//2)
        for feat in ["spread_pct", "implied_vol", "delta", "oi", "momentum_20d", "m_sigma"]:
            if feat not in sigs.columns:
                continue
            psi = learner.compute_psi(base[feat], recent[feat])
            status = "drift" if psi >= 0.25 else "watch" if psi >= 0.10 else "ok"
            store.insert_dataframe("drift_reports", pd.DataFrame([{
                "report_ts": datetime.now(UTC).replace(tzinfo=None),
                "feature_name": feat,
                "psi": psi,
                "status": status,
            }]))
    print(f"train complete: rows={metrics['train_rows']} accuracy={metrics['accuracy']} auc={metrics['auc']}")


def cmd_compact(_: argparse.Namespace) -> None:
    cfg, store, lake, provider, sec, finra, occ = _components(None)
    removed = compact_old_snapshots(
        cfg.storage["lake_root"],
        snapshot_name="options_snapshot",
        retention_days=int(cfg.storage["retention_days_full_snapshots"]),
    )
    daily = lake.collapse_symbol_summary("options_snapshot")
    print(f"compact complete: removed={removed} day_summaries={daily}")


def cmd_preflight(_: argparse.Namespace) -> None:
    cfg = load_config()
    print(json.dumps(run_preflight(cfg), default=str, indent=2))


def cmd_replay(args: argparse.Namespace) -> None:
    cfg, store, lake, provider, sec, finra, occ = _components("replay")
    fixture = args.fixture or cfg.replay.get("default_fixture", "sample_option_scan.csv")
    universe_rows, raw_rows, signal_rows = _scan_core(cfg, store, lake, provider, sec, finra, fixture_name=fixture)
    run_id = args.run_id or datetime.now(UTC).replace(tzinfo=None).strftime("replay-%Y%m%d-%H%M%S")
    store.insert_dataframe("replay_runs", pd.DataFrame([{
        "run_id": run_id,
        "created_ts": datetime.now(UTC).replace(tzinfo=None),
        "fixture_name": fixture,
        "provider": provider.name,
        "signal_count": len(signal_rows),
        "notes": "offline replay scan",
    }]))
    print(f"replay complete: run_id={run_id} fixture={fixture} universe={len(universe_rows)} signals={len(signal_rows)}")


def cmd_paper_step(args: argparse.Namespace) -> None:
    cfg, store, lake, provider, sec, finra, occ = _components(args.provider)
    broker = PaperBroker(store, float(cfg.paper["entry_slippage_bps"]), float(cfg.paper["exit_slippage_bps"]))
    risk = PaperRiskEngine(float(cfg.risk["stop_loss_pct"]), float(cfg.risk["take_profit_pct"]), float(cfg.risk["thesis_break_score"]))
    signals_df = store.signal_rows(days=30).sort_values("signal_ts")
    if signals_df.empty:
        print("paper-step: no signals")
        return
    open_positions = store.open_paper_positions()
    if len(open_positions) < int(cfg.paper["max_open_positions"]):
        newest = signals_df.sort_values(['score_lcb','score']).iloc[-1].to_dict() if 'score_lcb' in signals_df.columns else signals_df.iloc[-1].to_dict()
        from nova.models import FeatureRow
        fields = {k: newest.get(k) for k in FeatureRow.__dataclass_fields__.keys() if k in newest}
        for k, fld in FeatureRow.__dataclass_fields__.items():
            fields.setdefault(k, fld.default if fld.default is not None else None)
        fields.setdefault("market_cap", None)
        fields.setdefault("sector", None)
        fields.setdefault("technical_score", 0.5)
        fields.setdefault("strategy_tags", newest.get("strategy_tags", ""))
        fields.setdefault("suggested_contracts", int(newest.get("suggested_contracts", 1) or 1))
        row = FeatureRow(**fields)
        open_rows = []
        if not open_positions.empty:
            for _, pos in open_positions.iterrows():
                f = {k: FeatureRow.__dataclass_fields__[k].default for k in FeatureRow.__dataclass_fields__.keys()}
                f.update({
                    "symbol": str(pos.get("symbol") or ""),
                    "contract_symbol": str(pos.get("contract_symbol") or ""),
                    "expiration": pos.get("expiration"),
                    "strike": float(pos.get("strike") or 0.0),
                    "right": str(pos.get("right") or "call"),
                    "bid": 0.0,
                    "ask": float(pos.get("current_price") or pos.get("entry_price") or 0.0),
                    "mid": float(pos.get("current_price") or pos.get("entry_price") or 0.0),
                    "spread_pct": 0.0,
                    "implied_vol": 0.0,
                    "underlying_price": 0.0,
                    "dte": 0,
                    "delta": 0.0,
                    "volume": 0,
                    "oi": 0,
                    "market_cap": pos.get("market_cap"),
                    "sector": pos.get("sector"),
                    "finra_short_ratio": 0.0,
                    "insider_buy_flag": False,
                    "edgar_dilution_flag": False,
                    "momentum_20d": 0.0,
                    "vix_value": None,
                    "m_sigma": 0.0,
                    "technical_score": 0.0,
                    "score": float(pos.get("score_at_entry") or 0.0),
                    "elite": False,
                    "strategy_tags": str(pos.get("tags") or ""),
                    "suggested_contracts": int(pos.get("qty") or 1),
                })
                open_rows.append(FeatureRow(**f))
        if sector_exposure_ok(row, open_rows, cfg):
            pid = broker.open_position(row)
            print(f"paper-step: opened {pid} {row.contract_symbol}")
        else:
            print(f"paper-step: blocked by sector exposure for {row.symbol} sector={row.sector}")
    else:
        print("paper-step: max open positions reached")
    quotes = signals_df[["contract_symbol", "mid", "ask"]].drop_duplicates(subset=["contract_symbol"], keep="last")
    broker.mark_to_market(quotes)
    open_positions = store.open_paper_positions()
    closed = 0
    for _, pos in open_positions.iterrows():
        current_score_row = signals_df[signals_df["contract_symbol"] == pos["contract_symbol"]].tail(1)
        current_score = float(current_score_row["score"].iloc[0]) if not current_score_row.empty else float(pos["score_at_entry"])
        current_price = float(pos["current_price"])
        decision = risk.evaluate(float(pos["entry_price"]), current_price, current_score)
        if decision.action == "close":
            broker.close_position(str(pos["position_id"]), decision.reason, current_price)
            closed += 1
    print(f"paper-step: mtm={len(open_positions)} closed={closed}")


def cmd_cohorts(_: argparse.Namespace) -> None:
    cfg, store, lake, provider, sec, finra, occ = _components(None)
    trades_df = store.completed_trades()
    out = cohort_summary(trades_df)
    if out.empty:
        print("cohorts: no completed trades")
        return
    store.insert_dataframe("cohort_stats", out)
    print(out.to_string(index=False))


def cmd_memory_build(_: argparse.Namespace) -> None:
    cfg, store, lake, provider, sec, finra, occ = _components(None)
    memory = VectorMemory(cfg.memory["store_path"])
    signals_df = store.signal_rows(days=365)
    if signals_df.empty:
        print("memory-build: no signals")
        return
    for i, row in signals_df.tail(500).reset_index(drop=True).iterrows():
        text = f"{row['symbol']} {row['contract_symbol']} score {row['score']} lcb {row.get('score_lcb', 0.0)} dte {row['dte']} delta {row['delta']} tags {row['strategy_tags']}"
        memory.add(f"signal-{i}", text, {"symbol": row['symbol'], "contract_symbol": row['contract_symbol']})
    print(f"memory-build: rows={min(len(signals_df), 500)}")


def cmd_memory_query(args: argparse.Namespace) -> None:
    cfg = load_config()
    memory = VectorMemory(cfg.memory["store_path"])
    hits = memory.query(args.query, top_k=int(cfg.memory["top_k"]))
    print(json.dumps(hits, indent=2))


def cmd_calibrate(_: argparse.Namespace) -> None:
    cfg, store, lake, provider, sec, finra, occ = _components(None)
    report = calibrate_from_store(store, cfg.calibration['output_path'], int(cfg.calibration['min_trades']))
    store.insert_dataframe('calibration_runs', pd.DataFrame([{
        'run_ts': datetime.now(UTC).replace(tzinfo=None),
        'source': 'trades+paper_orders',
        'trades_used': int(report['trades_used']),
        'entry_slippage_bps': float(report['entry_slippage_bps']),
        'exit_slippage_bps': float(report['exit_slippage_bps']),
        'recommended_thesis_break_score': float(report['recommended_thesis_break_score']),
        'recommended_take_profit_pct': float(report['recommended_take_profit_pct']),
        'recommended_stop_loss_pct': float(report['recommended_stop_loss_pct']),
        'notes': f"confidence={report['confidence']}",
        'report_json': json.dumps(report),
    }]))
    print(json.dumps(report, indent=2))


def cmd_optimize_scoring(_: argparse.Namespace) -> None:
    cfg, store, lake, provider, sec, finra, occ = _components(None)
    report = recommend_scoring_weights(store, cfg)
    out_path = Path('data/calibration/scoring_optimization.json')
    write_scoring_optimization_report(report, out_path)
    print(json.dumps({**report, 'output_path': str(out_path)}, indent=2, default=str))


def cmd_execution_quality(_: argparse.Namespace) -> None:
    cfg, store, lake, provider, sec, finra, occ = _components(None)
    out = persist_execution_quality(store)
    if out.empty:
        print("execution-quality: no filled orders")
        return
    print(out.to_string(index=False))


def cmd_market_ops(_: argparse.Namespace) -> None:
    state = get_market_ops_state()
    print(json.dumps({
        'now_ct': state.now_ct.isoformat(),
        'is_trading_day': state.is_trading_day,
        'is_early_close': state.is_early_close,
        'is_open': state.is_open,
        'can_open_new': state.can_open_new,
        'close_time_ct': state.close_time_ct.isoformat(),
        'event_risk': state.event_risk,
        'note': state.note,
    }, indent=2))


def cmd_audit(_: argparse.Namespace) -> None:
    import compileall
    cfg, store, lake, provider, sec, finra, occ = _components(None)
    checks = run_preflight(cfg)
    compiled = bool(compileall.compile_dir('nova', quiet=1, force=False))
    tables = [r[0] for r in store.conn.execute("SHOW TABLES").fetchall()] if store.backend == 'duckdb' else [r[0] for r in store.conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    snapshot_files = list(Path(cfg.storage['lake_root']).rglob('*.parquet')) + list(Path(cfg.storage['lake_root']).rglob('*.csv'))
    exec_df = persist_execution_quality(store)
    report = {
        'preflight_ok': bool(checks.get('ok')),
        'compiled': compiled,
        'backend': store.backend,
        'provider_default': cfg.runtime.get('provider'),
        'provider_fallback_order': cfg.runtime.get('provider_fallback_order'),
        'table_count': len(tables),
        'snapshot_file_count': len(snapshot_files),
        'market_ops_note': checks.get('market_ops_note'),
        'execution_quality_rows': len(exec_df),
        'tests_recommended': 'pytest -q',
    }
    print(json.dumps(report, indent=2, default=str))



def cmd_ingest_free_sources(args: argparse.Namespace) -> None:
    cfg, store, lake, provider, sec, finra, occ = _components(None)
    now = datetime.now(UTC).replace(tzinfo=None)
    rows = []
    fred = FREDMacroAdapter(cfg.raw["env"].get("fred_api_key", ""))
    nasdaq = NasdaqHaltsAdapter()
    ftd = SECFTDAdapter()
    clinical = ClinicalTrialsAdapter()
    fda = FDACalendarAdapter()
    cftc = CFTCAdapter()

    macro_score = fred.risk_regime_score()
    rows.append({"event_ts": now, "source": "fred", "symbol": None, "event_key": "risk_regime_score", "event_value": str(macro_score), "payload_json": json.dumps({"risk_regime_score": macro_score})})

    halts_df = nasdaq.current_halts()
    if not halts_df.empty:
        for _, r in halts_df.iterrows():
            rows.append({"event_ts": now, "source": "nasdaq_halts", "symbol": str(r.get("Issue Symbol") or "").upper() or None, "event_key": str(r.get("Reason Code") or "halt"), "event_value": str(r.get("Halt Time") or ""), "payload_json": json.dumps(r.to_dict(), default=str)})

    if args.symbol:
        symbol = args.symbol.upper()
        rows.append({"event_ts": now, "source": "sec_ftd", "symbol": symbol, "event_key": "latest_ftd_qty", "event_value": str(ftd.ftd_quantity_for_symbol(symbol, now.date())), "payload_json": json.dumps({"symbol": symbol})})
        q = symbol
        for ev in clinical.search(q, page_size=5):
            rows.append({"event_ts": now, "source": "clinicaltrials", "symbol": symbol, "event_key": "study", "event_value": str(ev.get("NCTId", [""])[0] if isinstance(ev.get("NCTId"), list) and ev.get("NCTId") else ev.get("NCTId", "")), "payload_json": json.dumps(ev, default=str)})
    for ev in fda.advisory_events()[:10]:
        rows.append({"event_ts": now, "source": "fda_calendar", "symbol": None, "event_key": "advisory_event", "event_value": ev.get("title", ""), "payload_json": json.dumps(ev, default=str)})
    cot_df = cftc.latest_financial_futures()
    if not cot_df.empty:
        rows.append({"event_ts": now, "source": "cftc", "symbol": None, "event_key": "rows", "event_value": str(len(cot_df)), "payload_json": cot_df.head(10).to_json(orient="records")})

    if rows:
        store.insert_dataframe("free_source_events", pd.DataFrame(rows))
        lake.write_batch("free_source_events", rows, ts=now)
    print(json.dumps({"rows_written": len(rows), "symbol": args.symbol or None, "macro_score": macro_score}, indent=2))

def main() -> None:
    parser = argparse.ArgumentParser(description="NOVA laptop CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("validate")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("scan")
    p.add_argument("--provider", default="yfinance")
    p.set_defaults(func=cmd_scan)

    p = sub.add_parser("provider-check")
    p.add_argument("--provider", default="auto")
    p.add_argument("--symbol", default="PLTR")
    p.set_defaults(func=cmd_provider_check)

    p = sub.add_parser("ingest-edges")
    p.add_argument("--provider", default="auto", help="explicit feed router; replay skips live edge ingestion")
    p.set_defaults(func=cmd_ingest_edges)

    p = sub.add_parser("backtest")
    p.add_argument("--diagnostic-score-proxy", action="store_true", help="synthetic QA only: no P&L or trade-ledger write")
    p.set_defaults(func=cmd_backtest)

    p = sub.add_parser("train")
    p.set_defaults(func=cmd_train)

    p = sub.add_parser("compact")
    p.set_defaults(func=cmd_compact)

    p = sub.add_parser("audit")
    p.set_defaults(func=cmd_audit)

    p = sub.add_parser("preflight")
    p.set_defaults(func=cmd_preflight)

    p = sub.add_parser("replay")
    p.add_argument("--run-id", default="")
    p.add_argument("--fixture", default="")
    p.set_defaults(func=cmd_replay)

    p = sub.add_parser("paper-step")
    p.add_argument("--provider", default="replay")
    p.set_defaults(func=cmd_paper_step)

    p = sub.add_parser("cohorts")
    p.set_defaults(func=cmd_cohorts)

    p = sub.add_parser("memory-build")
    p.set_defaults(func=cmd_memory_build)

    p = sub.add_parser("memory-query")
    p.add_argument("query")
    p.set_defaults(func=cmd_memory_query)

    p = sub.add_parser("calibrate")
    p.set_defaults(func=cmd_calibrate)

    p = sub.add_parser("optimize-scoring")
    p.set_defaults(func=cmd_optimize_scoring)

    p = sub.add_parser("execution-quality")
    p.set_defaults(func=cmd_execution_quality)

    p = sub.add_parser("market-ops")
    p.set_defaults(func=cmd_market_ops)

    p = sub.add_parser("phase1-eval", help="offline calls-only phase-1 scoring with auditable local fixture")
    p.add_argument("--input", required=True)
    p.add_argument("--output", default="")
    p.set_defaults(func=cmd_phase1_eval)

    p = sub.add_parser("ingest-free-sources")
    p.add_argument("--symbol", default="")
    p.set_defaults(func=cmd_ingest_free_sources)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
